import hashlib
from pathlib import PurePath
from urllib.parse import quote
from uuid import UUID

from fastapi import HTTPException
from fastapi.responses import Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from veridion.documents import MAX_BYTES, MEDIA


def source(db: Session, project: UUID, source_id: UUID, *, lock=False):
    statement = "SELECT * FROM sources WHERE project_id=:project AND id=:id"
    if lock:
        statement += " FOR UPDATE"
    row = (
        db.execute(text(statement), {"project": project, "id": source_id})
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise HTTPException(404, "Source not found")
    return row


def queue(
    db: Session, project: UUID, title: str, category: str, filename: str, payload: bytes
):
    filename = PurePath(filename.replace("\\", "/")).name
    if (
        not filename
        or len(filename) > 180
        or PurePath(filename).suffix.lower() not in MEDIA
    ):
        raise HTTPException(422, "Expected TXT, Markdown, HTML, PDF or DOCX")
    if not 0 < len(payload) <= MAX_BYTES:
        raise HTTPException(413, "File must be between 1 byte and 5 MiB")
    source_id = db.scalar(
        text("""
        INSERT INTO sources(project_id,title,category) VALUES (:project,:title,:category)
        ON CONFLICT(project_id,title) DO UPDATE SET title=excluded.title RETURNING id
    """),
        {"project": project, "title": title, "category": category},
    )
    entry = source(db, project, source_id, lock=True)
    if entry["archived_at"]:
        raise HTTPException(409, "Source is archived")
    if entry["category"] != category:
        raise HTTPException(409, "Source category differs")
    params = {
        "source": source_id,
        "filename": filename,
        "payload": payload,
        "digest": hashlib.sha256(payload).hexdigest(),
    }
    job = db.scalar(
        text("""
        INSERT INTO jobs(source_id,filename,payload,digest) VALUES (:source,:filename,:payload,:digest)
        ON CONFLICT(source_id,digest) WHERE state<>'FAILED' DO NOTHING RETURNING id
    """),
        params,
    )
    if job is None:
        job = db.scalar(
            text(
                "SELECT id FROM jobs WHERE source_id=:source AND digest=:digest AND state<>'FAILED'"
            ),
            params,
        )
    return {"id": job, "source_id": source_id}


def original(db: Session, project: UUID, source_id: UUID, number: int) -> Response:
    source(db, project, source_id)
    row = db.execute(
        text("""
        SELECT original,filename,content_hash FROM source_versions
        WHERE source_id=:source AND version=:number
    """),
        {"source": source_id, "number": number},
    ).one_or_none()
    if row is None:
        raise HTTPException(404, "Version not found")
    return Response(
        bytes(row.original),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": "attachment; filename*=UTF-8''"
            + quote(row.filename),
            "ETag": '"' + row.content_hash + '"',
            "X-Content-Type-Options": "nosniff",
        },
    )
