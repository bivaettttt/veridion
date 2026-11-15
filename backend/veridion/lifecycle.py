import json
from uuid import UUID

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy import text
from sqlalchemy.orm import Session

from veridion import contracts, research


def add_review(
    db: Session,
    project: UUID,
    answer_id: UUID,
    user: UUID,
    role: str,
    data: contracts.Review,
):
    research.get_answer(db, project, answer_id, lock=True)
    history = research.review_history(db, answer_id)
    current = history[-1]["decision"] if history else "AUTO_ASSESSED"
    if data.revision != len(history):
        raise HTTPException(409, "Review changed. Refresh before submitting.")
    if data.decision == "IN_REVIEW":
        allowed = current in {"AUTO_ASSESSED", "NEEDS_MORE_EVIDENCE"}
    else:
        if role not in {"REVIEWER", "ADMIN"}:
            raise HTTPException(403, "Reviewer role required")
        allowed = current == "IN_REVIEW"
    if not allowed:
        raise HTTPException(
            409, f"Review cannot transition from {current} to {data.decision}"
        )
    return db.scalar(
        text("""
        INSERT INTO reviews(answer_id,user_id,revision,decision,rationale)
        VALUES (:answer,:user,:number,:decision,:rationale) RETURNING id
    """),
        {
            "answer": answer_id,
            "user": user,
            "number": len(history) + 1,
            "decision": data.decision,
            "rationale": data.rationale,
        },
    )


def get_report(db: Session, project: UUID, report_id: UUID, *, lock: bool = False):
    statement = "SELECT * FROM reports WHERE project_id=:project AND id=:id"
    if lock:
        statement += " FOR UPDATE"
    report = (
        db.execute(text(statement), {"project": project, "id": report_id})
        .mappings()
        .one_or_none()
    )
    if report is None:
        raise HTTPException(404, "Report not found")
    return report


def add_snapshot(
    db: Session,
    project: UUID,
    report_id: UUID,
    notes: str,
    answer_id: UUID | None = None,
):
    report = get_report(db, project, report_id, lock=True)
    body = research.detail(db, project, answer_id or report["answer_id"])
    body["notes"] = notes
    return (
        db.execute(
            text("""
        INSERT INTO snapshots(report_id,revision,body)
        SELECT :report,coalesce(max(revision),0)+1,CAST(:body AS jsonb)
        FROM snapshots WHERE report_id=:report RETURNING id,revision
    """),
            {
                "report": report_id,
                "body": json.dumps(jsonable_encoder(body), ensure_ascii=False),
            },
        )
        .mappings()
        .one()
    )


def new_report(db: Session, project: UUID, user: UUID, data: contracts.Report):
    research.get_answer(db, project, data.answer_id)
    report = db.scalar(
        text("""
        INSERT INTO reports(project_id,author_id,answer_id,title)
        VALUES (:project,:user,:answer,:title) RETURNING id
    """),
        {
            "project": project,
            "user": user,
            "answer": data.answer_id,
            "title": data.title,
        },
    )
    snapshot = add_snapshot(db, project, report, data.notes)
    return {"id": report, "snapshot": snapshot}


def markdown(title: str, revision: int, snapshot: dict) -> str:
    def literal(value: str) -> str:
        return "".join(
            "\\" + char if char in "\\`*_{}[]()<>!#|" else char
            for char in " ".join(value.split())
        )

    output = snapshot["output"]
    lines = [
        f"# {literal(title)}",
        "",
        f"Snapshot {revision} · {snapshot['created_at']}",
        "",
        "## Research question",
        "",
        literal(snapshot["query"]),
        "",
        "## Assessment",
        "",
        literal(output["summary"]),
        "",
        f"Status: {output['assessment']}",
        "",
        "## Configuration",
        "",
        f"- Provider: {literal(snapshot['provider'])}",
        f"- Model: {literal(snapshot['model'])}",
        f"- Index: {literal(snapshot['configuration']['index'])}",
        "",
        "## Review history",
        "",
    ]
    lines.extend(
        f"- {item['decision']}: {literal(item['rationale'])}"
        for item in snapshot["reviews"]
    )
    if not snapshot["reviews"]:
        lines.append("No recorded decision.")
    lines.extend(
        ["", "## Notes", "", literal(snapshot["notes"]), "", "## References", ""]
    )
    for item in snapshot["citations"]:
        lines.extend(
            [
                f"- [{literal(item['title'])} · v{item['version']}]({item['original_url']})",
                f"  · {literal(item['heading'])} · {item['integrity']} · SHA-256 `{item['content_hash']}`",
                "",
                f"  > {literal(item['quote'])}",
                "",
            ]
        )
    return "\n".join(lines) + "\n"
