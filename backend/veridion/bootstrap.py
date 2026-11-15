from getpass import getpass

from sqlalchemy import text
from sqlalchemy.orm import Session

from veridion.access import password_hash
from veridion.db import engine


def main() -> None:
    email = input("Administrator email: ").strip().casefold()
    name = input("Display name: ").strip()
    password = getpass("Administrator password: ")
    if "@" not in email or not name or not 12 <= len(password) <= 150:
        raise SystemExit(
            "Provide an email, a display name and a password of 12–150 characters"
        )
    with Session(engine) as db, db.begin():
        db.execute(text("SELECT pg_advisory_xact_lock(17418)"))
        if db.scalar(text("SELECT EXISTS (SELECT 1 FROM users WHERE is_admin)")):
            raise SystemExit("An administrator already exists")
        db.execute(
            text(
                "INSERT INTO users(email,name,password,is_admin) VALUES (:email,:name,:pw,true)"
            ),
            {"email": email, "name": name, "pw": password_hash(password)},
        )
    print("Administrator created")


if __name__ == "__main__":
    main()
