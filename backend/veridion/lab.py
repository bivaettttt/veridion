import json
from uuid import UUID, uuid4

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy import text
from sqlalchemy.orm import Session

from veridion import access, contracts, demo, lifecycle, research, sources, worker
from veridion.embedding import MODEL

CAPACITY = "Does the platform support 10 000 concurrent users?"
AVAILABILITY = "What availability was measured in build 2.0?"


def import_file(db, project, title, category, body):
    job = sources.queue(db, project, title, category, "northstar.md", body.encode())
    row = db.execute(text("SELECT * FROM jobs WHERE id=:id"), {"id": job["id"]}).one()
    version = row.version_id or worker.import_version(db, row)
    if row.state == "QUEUED":
        db.execute(
            text("""
            UPDATE jobs SET state='DONE',payload=NULL,version_id=:version,finished_at=clock_timestamp()
            WHERE id=:id
        """),
            {"id": job["id"], "version": version},
        )
    return job | {"version_id": version}


def exercise(db: Session, project: UUID, actor: UUID):
    results = []

    def record(name, passed, observed, used, expectation):
        results.append(
            {
                "scenario": name,
                "passed": bool(passed),
                "observed": observed,
                "sources": list(dict.fromkeys(used)),
                "expectation": expectation,
            }
        )

    def ask(question, **kwargs):
        answer_id = research.answer(
            db, project, actor, contracts.Question(query=question, **kwargs)
        )
        return research.detail(db, project, answer_id)

    def status(run):
        return run["output"]["assessment"]

    def titles(run):
        return [hit["title"] for hit in run["context"]]

    def kind(run, value):
        return any(item["type"] == value for item in run["output"]["contradictions"])

    def find(query, mode):
        _, hits, config = research.keep_search(
            db, project, actor, contracts.Search(query=query, mode=mode, limit=12)
        )
        return hits, config

    documents = {}
    for title, category, content in demo.DOCUMENTS:
        documents.setdefault(title, []).append(
            import_file(db, project, title, category, content)
        )

    measured = ask("Did the load test observe 2000 concurrent users?")
    record(
        "01 · Supported statement",
        status(measured) == "SUPPORTED_BY_SOURCES",
        status(measured),
        titles(measured),
        "Observed 2,000 users support the bounded claim",
    )

    missing = ask("Has an independent auditor certified the platform?")
    record(
        "02 · Missing evidence",
        status(missing) == "INSUFFICIENT_EVIDENCE",
        status(missing),
        titles(missing),
        "Abstain without direct evidence",
    )

    conflict = ask(AVAILABILITY)
    record(
        "03 · Conflicting documents",
        status(conflict) == "MIXED_EVIDENCE",
        status(conflict),
        titles(conflict),
        "Record a disagreement among comparable observations",
    )

    v1, v2 = documents["Platform specification"]
    history_at = db.scalar(
        text("SELECT created_at FROM source_versions WHERE id=:id"),
        {"id": v1["version_id"]},
    )
    old = ask(
        "Does the platform have a REST integration interface?",
        as_of=history_at,
        source_id=v1["source_id"],
    )
    current = ask(
        "Does the platform have a webhook integration interface?",
        source_id=v2["source_id"],
    )
    versions = [
        citation["version"] for run in (old, current) for citation in run["citations"]
    ]
    record(
        "04 · Historical version",
        1 in versions and 2 in versions,
        versions,
        titles(old) + titles(current),
        "Historical and current queries select different versions of the same source",
    )

    gap = ask(CAPACITY)
    record(
        "05 · False confirmation",
        status(gap) == "INSUFFICIENT_EVIDENCE",
        gap["output"]["summary"],
        titles(gap),
        "A target of 10,000 users cannot establish measured capacity",
    )

    numeric = [
        item["left"]["value"] + " vs " + item["right"]["value"]
        for item in conflict["output"]["contradictions"]
        if item["type"] == "POTENTIAL_CONFLICT"
    ]
    record(
        "06 · Numeric conflict",
        bool(numeric),
        numeric,
        titles(conflict),
        "Evidence contains incompatible monthly availability measurements under matching conditions",
    )

    record(
        "07 · Temporal context",
        kind(conflict, "DIFFERENT_CONTEXT"),
        [item["type"] for item in conflict["output"]["contradictions"]],
        titles(conflict),
        "Measurements across different builds or periods have a distinct classification",
    )

    cite = gap["citations"][0]
    params = (cite["chunk_id"], cite["version_id"], cite["quote"], cite["content_hash"])
    fake = research.check(db, project, gap, uuid4(), *params[1:])
    record(
        "08 · Unknown citation",
        fake["integrity"] == "INVALID",
        fake,
        [cite["title"]],
        "Reject an unknown chunk",
    )

    version_mismatch = research.check(
        db, project, gap, params[0], v1["version_id"], *params[2:]
    )
    record(
        "09 · Version mismatch",
        version_mismatch["integrity"] == "INVALID",
        version_mismatch,
        [cite["title"]],
        "Reject an unrelated source version",
    )

    receipt = lifecycle.new_report(
        db,
        project,
        actor,
        contracts.Report(answer_id=current["id"], title="Integration evidence"),
    )
    snapshot_id = receipt["snapshot"]["id"]
    frozen = db.scalar(
        text("SELECT body FROM snapshots WHERE id=:id"), {"id": snapshot_id}
    )
    import_file(
        db,
        project,
        "Platform specification",
        "specification",
        "# Integration\n\nBuild 3.0 documents a SOAP integration interface.",
    )
    reopened = research.detail(db, project, current["id"])
    record(
        "10 · Source changed",
        reopened["context"] == current["context"]
        and all(c["freshness"] == "HISTORICAL" for c in reopened["citations"]),
        [c["freshness"] for c in reopened["citations"]],
        titles(reopened),
        "Saved retrieval stays byte-for-byte stable while citation freshness changes",
    )

    count = worker.reindex(db, v2["version_id"])
    worker.reindex(db, v2["version_id"])
    indexed = db.scalar(
        text("""
        SELECT count(*) FROM embeddings e JOIN chunks c ON c.id=e.chunk_id WHERE c.version_id=:id AND e.model=:model
    """),
        {"id": v2["version_id"], "model": MODEL},
    )
    record(
        "11 · Reindex",
        indexed == count,
        {"chunks": count, "embeddings": indexed, "model": MODEL},
        ["Platform specification"],
        "A repeated index pass preserves one vector per chunk and model",
    )

    keyword, _ = find("Run 17 load test", "keyword")
    record(
        "12 · Keyword",
        any(hit["title"] == "Load test · Run 17" for hit in keyword),
        [hit["title"] for hit in keyword[:3]],
        [hit["title"] for hit in keyword],
        "Lexical search finds the test",
    )

    semantic, _ = find("maximum simultaneous platform usage", "semantic")
    record(
        "13 · Semantic",
        any(hit["title"] == "Capacity requirements" for hit in semantic[:6]),
        [hit["title"] for hit in semantic[:6]],
        [hit["title"] for hit in semantic],
        "Vector search finds the capacity terminology",
    )

    hybrid, config = find("load test concurrent users", "hybrid")
    record(
        "14 · Hybrid",
        config["rrf_k"] == 60
        and any(hit["title"] == "Load test · Run 17" for hit in hybrid[:6]),
        [hit["title"] for hit in hybrid[:6]],
        [hit["title"] for hit in hybrid],
        "Fusion preserves relevant lexical and vector ranks",
    )

    ru, _ = find(
        "Одновременная работа пользователей и нагрузочные испытания", "semantic"
    )
    record(
        "15 · Russian to English",
        any(hit["title"] == "Load test · Run 17" for hit in ru[:8]),
        [hit["title"] for hit in ru[:8]],
        [hit["title"] for hit in ru],
        "Russian query retrieves the English load-test source",
    )

    en, _ = find("How does project membership control access to documents?", "semantic")
    record(
        "16 · English to Russian",
        any(hit["title"] == "Security assessment" for hit in en[:8]),
        [hit["title"] for hit in en[:8]],
        [hit["title"] for hit in en],
        "English query retrieves the Russian security assessment",
    )

    content = documents["Untrusted document handling"][0]
    untrusted = ask(
        "What does the quoted operational note say?", source_id=content["source_id"]
    )
    record(
        "17 · Instruction as data",
        status(untrusted) == "INSUFFICIENT_EVIDENCE"
        and not untrusted["citations"]
        and any("violet" in hit["content"] for hit in untrusted["context"]),
        status(untrusted),
        titles(untrusted),
        "Instruction-shaped text is retrieved as data and has no effect on the extractive assessment",
    )

    brochure = documents["Capacity announcement"][0]
    poisoned = ask(CAPACITY, source_id=brochure["source_id"])
    record(
        "18 · Unverified source",
        status(poisoned) == "INSUFFICIENT_EVIDENCE" and not poisoned["citations"],
        poisoned["output"]["summary"],
        titles(poisoned),
        "Advisory copy alone cannot qualify as test evidence",
    )

    foreign = db.scalar(text("SELECT id FROM users WHERE email='guest@northstar.test'"))
    refused = 0
    try:
        access.membership(db, project, foreign)
    except HTTPException as exc:
        refused = exc.status_code
    record(
        "19 · Foreign project",
        refused == 404,
        {"status": refused},
        [],
        "Membership rejects access before retrieval",
    )

    for revision, decision in enumerate(("IN_REVIEW", "VERIFIED")):
        lifecycle.add_review(
            db,
            project,
            current["id"],
            actor,
            "ADMIN",
            contracts.Review(
                decision=decision,
                revision=revision,
                rationale="Checked the source and build recorded in this run.",
            ),
        )
    history = research.review_history(db, current["id"])
    record(
        "20 · Human review",
        [item["decision"] for item in history] == ["IN_REVIEW", "VERIFIED"],
        [item["decision"] for item in history],
        titles(current),
        "Both review transitions remain visible",
    )

    record(
        "21 · Report generation",
        bool(frozen["citations"])
        and all(c["integrity"] == "VALID" for c in frozen["citations"]),
        {"revision": 1, "citations": len(frozen["citations"])},
        titles(current),
        "Report freezes exact citations and the answer configuration",
    )

    second = lifecycle.add_snapshot(
        db, project, receipt["id"], "Reviewed after the specification changed."
    )
    before = db.scalar(
        text("SELECT body FROM snapshots WHERE id=:id"), {"id": snapshot_id}
    )
    after = db.scalar(
        text("SELECT body FROM snapshots WHERE id=:id"), {"id": second["id"]}
    )
    record(
        "22 · Snapshot comparison",
        before == frozen
        and not before["reviews"]
        and len(after["reviews"]) == 2
        and any(c["freshness"] == "HISTORICAL" for c in after["citations"]),
        {
            "first_review_count": len(before["reviews"]),
            "second_review_count": len(after["reviews"]),
            "citation_freshness": [c["freshness"] for c in after["citations"]],
        },
        titles(current),
        "The next snapshot records review and freshness changes while the first remains immutable",
    )

    code = 0
    try:
        research.Ollama(endpoint="http://127.0.0.1:1").generate(CAPACITY, [])
    except HTTPException as exc:
        code = exc.status_code
    record(
        "23 · Local provider failure",
        code == 503,
        {"status": code},
        [],
        "Actual connection failure returns 503",
    )

    title, category, original = demo.DOCUMENTS[0]
    again = import_file(db, project, title, category, original)
    record(
        "24 · Repeated import",
        again == v1,
        {
            "same_job": again["id"] == v1["id"],
            "same_version": again["version_id"] == v1["version_id"],
        },
        [title],
        "Identical original bytes reuse the earlier version and job",
    )
    return results


def run(db: Session, host: UUID, actor: UUID):
    isolated = db.begin_nested()
    try:
        project = db.scalar(
            text("""
            INSERT INTO projects(name,owner_id,lab) VALUES ('Northstar isolated run',:owner,true) RETURNING id
        """),
            {"owner": actor},
        )
        db.execute(
            text("INSERT INTO members VALUES (:project,:actor,'ADMIN')"),
            {"project": project, "actor": actor},
        )
        results = exercise(db, project, actor)
    finally:
        isolated.rollback()
    run_id = db.scalar(
        text("""
        INSERT INTO lab_runs(project_id,user_id,results) VALUES (:project,:user,CAST(:result AS jsonb)) RETURNING id
    """),
        {
            "project": host,
            "user": actor,
            "result": json.dumps(jsonable_encoder(results), ensure_ascii=False),
        },
    )
    return {"id": run_id, "results": results}
