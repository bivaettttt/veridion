import logging
import time

from sqlalchemy import text
from sqlalchemy.orm import Session

from veridion.db import engine
from veridion.documents import parse, windows
from veridion.embedding import MODEL, embed

log = logging.getLogger(__name__)


def import_version(db: Session, job):
    source = db.execute(
        text("SELECT archived_at FROM sources WHERE id=:id FOR UPDATE"),
        {"id": job.source_id},
    ).one()
    if source.archived_at:
        raise ValueError("Archived source")
    existing = db.scalar(
        text("""
        SELECT id FROM source_versions WHERE source_id=:source AND content_hash=:digest
    """),
        {"source": job.source_id, "digest": job.digest},
    )
    if existing:
        return existing
    media, parts = parse(job.filename, job.payload)
    version = db.scalar(
        text("""
        INSERT INTO source_versions(source_id,version,filename,media_type,content_hash,original,normalized)
        SELECT :source,coalesce(max(version),0)+1,:filename,:media,:digest,:payload,:normalized
        FROM source_versions WHERE source_id=:source RETURNING id
    """),
        {
            "source": job.source_id,
            "filename": job.filename,
            "media": media,
            "digest": job.digest,
            "payload": job.payload,
            "normalized": "\n\n".join(part.text for part in parts),
        },
    )
    offset = 0
    chunks = []
    for part in parts:
        section = db.scalar(
            text("""
            INSERT INTO sections(version_id,heading,page,start_at,end_at)
            VALUES (:version,:heading,:page,:start,:end) RETURNING id
        """),
            {
                "version": version,
                "heading": part.heading,
                "page": part.page,
                "start": offset,
                "end": offset + len(part.text),
            },
        )
        for start, end in windows(part.text):
            content = part.text[start:end]
            chunk_id = db.scalar(
                text("""
                INSERT INTO chunks(section_id,version_id,start_at,end_at,content)
                VALUES (:section,:version,:start,:end,:content) RETURNING id
            """),
                {
                    "section": section,
                    "version": version,
                    "start": offset + start,
                    "end": offset + end,
                    "content": content,
                },
            )
            chunks.append((chunk_id, content))
        offset += len(part.text) + 2
    index_chunks(db, chunks)
    return version


def index_chunks(db: Session, chunks):
    for index in range(0, len(chunks), 16):
        batch = chunks[index : index + 16]
        vectors = embed([content for _, content in batch])
        db.execute(
            text("""
            INSERT INTO embeddings(chunk_id,model,value) VALUES (:id,:model,CAST(:value AS vector))
            ON CONFLICT(chunk_id,model) DO NOTHING
        """),
            [
                {"id": chunk_id, "model": MODEL, "value": vector}
                for (chunk_id, _), vector in zip(batch, vectors, strict=True)
            ],
        )


def reindex(db: Session, version):
    rows = db.execute(
        text("SELECT id,content FROM chunks WHERE version_id=:id ORDER BY start_at"),
        {"id": version},
    ).all()
    index_chunks(db, rows)
    return len(rows)


def consume() -> bool:
    with Session(engine) as db, db.begin():
        job = db.execute(
            text("""
            SELECT * FROM jobs WHERE state='QUEUED' ORDER BY created_at
            FOR UPDATE SKIP LOCKED LIMIT 1
        """)
        ).one_or_none()
        if job is None:
            return False
        try:
            with db.begin_nested():
                version = import_version(db, job)
        except Exception:
            log.exception("Import failed for job %s", job.id)
            db.execute(
                text("""
                UPDATE jobs SET state='FAILED',payload=NULL,error='Document could not be imported',
                finished_at=clock_timestamp() WHERE id=:id
            """),
                {"id": job.id},
            )
        else:
            db.execute(
                text("""
                UPDATE jobs SET state='DONE',payload=NULL,version_id=:version,
                finished_at=clock_timestamp() WHERE id=:id
            """),
                {"id": job.id, "version": version},
            )
    return True


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    while True:
        if not consume():
            time.sleep(0.5)
