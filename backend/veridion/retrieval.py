import re
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from veridion.contracts import Search
from veridion.embedding import INDEX, MODEL, embed

STOP = {
    "does",
    "the",
    "did",
    "do",
    "of",
    "in",
    "is",
    "are",
    "was",
    "were",
    "and",
    "what",
    "how",
    "to",
    "a",
    "ли",
    "в",
    "на",
    "и",
    "у",
    "к",
    "как",
    "что",
    "по",
    "для",
    "какой",
    "какие",
    "это",
}
LIMIT_CANDIDATES = 40
RRF_K = 60
SCOPE = """
    WITH chosen AS (
        SELECT DISTINCT ON (s.id) s.id AS source_id,s.title,s.category,v.id AS version_id,
               v.version,v.content_hash,v.created_at AS version_created
        FROM sources s JOIN source_versions v ON v.source_id=s.id
        WHERE s.project_id=:project AND v.created_at<=:cutoff
          AND (s.archived_at IS NULL OR s.archived_at>:cutoff)
          AND (CAST(:category AS text) IS NULL OR s.category=:category)
          AND (CAST(:source_id AS uuid) IS NULL OR s.id=:source_id)
        ORDER BY s.id,v.version DESC
    )
"""
PINNED = """
    WITH chosen AS (
        SELECT s.id AS source_id,s.title,s.category,v.id AS version_id,
               v.version,v.content_hash,v.created_at AS version_created
        FROM sources s JOIN source_versions v ON v.source_id=s.id
        WHERE s.project_id=:project AND v.id=ANY(CAST(:version_ids AS uuid[]))
    )
"""
MATCHES = """
    SELECT c.id AS chunk_id,z.*,c.start_at,c.end_at,c.content,sec.heading,sec.page,{score} AS score
    FROM chosen z JOIN chunks c ON c.version_id=z.version_id JOIN sections sec ON sec.id=c.section_id
    {join} WHERE {condition}
    ORDER BY score DESC,c.id LIMIT :candidates
"""


def fuse(ranks: list[list[dict[str, Any]]], limit: int):
    merged: dict[UUID, dict[str, Any]] = {}
    for result in ranks:
        for index, row in enumerate(result, 1):
            hit = merged.setdefault(row["chunk_id"], dict(row) | {"score": 0.0})
            hit["score"] += 1 / (RRF_K + index)
    return sorted(merged.values(), key=lambda row: (-row["score"], row["chunk_id"]))[
        :limit
    ]


def retrieve(db: Session, project: UUID, data: Search):
    cutoff = data.as_of or datetime.now(UTC)
    if cutoff.tzinfo is None:
        cutoff = cutoff.replace(tzinfo=UTC)
    params = {
        "project": project,
        "cutoff": cutoff,
        "category": data.category,
        "source_id": data.source_id,
        "candidates": LIMIT_CANDIDATES,
        "model": MODEL,
    }
    versions = (
        db.execute(text(SCOPE + " SELECT * FROM chosen ORDER BY source_id"), params)
        .mappings()
        .all()
    )
    params["version_ids"] = [version["version_id"] for version in versions]
    rankings = []
    if data.mode in {"keyword", "hybrid"}:
        terms = set(re.findall(r"[^\W_]+", data.query.casefold())) - STOP
        syntax = " OR ".join(sorted(terms)[:24])
        ts = "websearch_to_tsquery('simple',:query) || websearch_to_tsquery('russian',:query) || websearch_to_tsquery('english',:query)"
        stmt = MATCHES.format(
            score="ts_rank_cd(c.search,q.term)",
            join=f"CROSS JOIN LATERAL (SELECT {ts} AS term) q",
            condition="c.search @@ q.term",
        )
        rows = db.execute(text(PINNED + stmt), params | {"query": syntax}).mappings()
        rankings.append([dict(row) for row in rows])
    if data.mode in {"semantic", "hybrid"}:
        stmt = MATCHES.format(
            score="1-(e.value <=> CAST(:query AS vector))",
            join="JOIN embeddings e ON e.chunk_id=c.id",
            condition="e.model=:model",
        )
        rows = db.execute(
            text(PINNED + stmt), params | {"query": embed([data.query], query=True)[0]}
        ).mappings()
        rankings.append([dict(row) for row in rows])
    hits = (
        fuse(rankings, data.limit)
        if data.mode == "hybrid"
        else rankings[0][: data.limit]
    )
    return hits, {
        **data.model_dump(mode="json", exclude={"query", "provider"}),
        "cutoff": cutoff.isoformat(),
        "index": INDEX,
        "embedding": MODEL,
        "rrf_k": RRF_K,
        "versions": [
            {
                "source_id": str(v["source_id"]),
                "id": str(v["version_id"]),
                "number": v["version"],
                "hash": v["content_hash"],
            }
            for v in versions
        ],
    }
