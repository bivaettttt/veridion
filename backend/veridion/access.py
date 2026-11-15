import hashlib
import secrets
from uuid import UUID

from fastapi import HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session


def digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def password_hash(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    hashed = hashlib.scrypt(
        password.encode(), salt=bytes.fromhex(salt), n=2**14, r=8, p=1
    )
    return f"{salt}:{hashed.hex()}"


def sign_in(db: Session, email: str, password: str) -> str:
    user = db.execute(
        text("SELECT id,password FROM users WHERE email=:email"),
        {"email": email.casefold().strip()},
    ).one_or_none()
    salt = user.password.split(":")[0] if user else "0" * 32
    candidate = password_hash(password, salt)
    if user is None or not secrets.compare_digest(candidate, user.password):
        raise HTTPException(401, "Invalid credentials")
    token = secrets.token_urlsafe(32)
    db.execute(
        text("INSERT INTO sessions(digest,user_id) VALUES (:hash,:id)"),
        {"hash": digest(token), "id": user.id},
    )
    db.commit()
    return token


def identity(db: Session, request: Request):
    token = request.cookies.get("veridion_session")
    if not token or len(token) > 100:
        raise HTTPException(401, "Sign in required")
    if (
        request.method not in {"GET", "HEAD", "OPTIONS"}
        and request.headers.get("x-veridion-client") != "1"
    ):
        raise HTTPException(403, "Client header required")
    user = (
        db.execute(
            text("""
        SELECT u.id,u.email,u.name,u.is_admin
        FROM sessions s JOIN users u ON u.id=s.user_id
        WHERE s.digest=:hash AND expires_at>now()
    """),
            {"hash": digest(token)},
        )
        .mappings()
        .one_or_none()
    )
    if user is None:
        raise HTTPException(401, "Session expired")
    return user


def membership(db: Session, project: UUID, user: UUID, *allowed: str) -> str:
    role = db.scalar(
        text("SELECT role FROM members WHERE project_id=:project AND user_id=:user"),
        {"project": project, "user": user},
    )
    if role is None:
        raise HTTPException(404, "Project not found")
    if allowed and role not in allowed:
        raise HTTPException(403, "Operation unavailable for this role")
    return role


def event(
    db: Session, project: UUID, user: UUID, action: str, obj: UUID, request_id: str
) -> None:
    db.execute(
        text("""
        INSERT INTO audit(project_id,user_id,action,object_id,request_id)
        VALUES (:project,:user,:action,:obj,:request)
    """),
        {
            "project": project,
            "user": user,
            "action": action,
            "obj": obj,
            "request": request_id,
        },
    )
