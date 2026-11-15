import json
from statistics import mean
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from veridion import contracts, research

DATASET = "northstar-grounding/v1"
CASES = (
    (
        "capacity-gap",
        "Does the platform support 10 000 concurrent users?",
        {"Capacity requirements", "Load test · Run 17"},
        "INSUFFICIENT_EVIDENCE",
    ),
    (
        "measured-capacity",
        "Поддерживает ли сборка 2.0 нагрузку в 2000 одновременных пользователей?",
        {"Load test · Run 17"},
        "SUPPORTED_BY_SOURCES",
    ),
    (
        "numeric-conflict",
        "What availability was measured in build 2.0?",
        {"Availability · West", "Availability · East"},
        "MIXED_EVIDENCE",
    ),
    (
        "rest",
        "Does build 2.0 document the REST integration interface?",
        {"Platform specification"},
        "SUPPORTED_BY_SOURCES",
    ),
    (
        "missing",
        "Has the platform been certified by an independent auditor?",
        {"Certification notes"},
        "INSUFFICIENT_EVIDENCE",
    ),
)


def evaluate(db: Session, project: UUID, user: UUID, data: contracts.Evaluation):
    cases = []
    for case, query, expected_sources, expected_assessment in CASES:
        answer_id = research.answer(
            db,
            project,
            user,
            contracts.Question(
                query=query, mode=data.mode, provider=data.provider, limit=8
            ),
        )
        answer = research.detail(db, project, answer_id)
        titles = list(dict.fromkeys(hit["title"] for hit in answer["context"]))
        positions = [
            index for index, title in enumerate(titles, 1) if title in expected_sources
        ]
        citations = answer["citations"]
        status = answer["output"]["assessment"]
        cases.append(
            {
                "case": case,
                "question": query,
                "answer_id": str(answer_id),
                "expected_sources": sorted(expected_sources),
                "expected": expected_assessment,
                "actual": status,
                "sources": titles,
                "correct": status == expected_assessment,
                "recall": len(positions) / len(expected_sources),
                "rr": 1 / positions[0] if positions else 0,
                "citations": len(citations),
                "valid": sum(
                    citation["integrity"] == "VALID" for citation in citations
                ),
                "generation": answer["output"].get("generation", {}).get("status"),
            }
        )
    count = sum(case["citations"] for case in cases)
    abstention = [case for case in cases if case["expected"] == "INSUFFICIENT_EVIDENCE"]
    result = {
        "cases": cases,
        "metrics": {
            "source_recall": mean(case["recall"] for case in cases),
            "mrr": mean(case["rr"] for case in cases),
            "citation_integrity": sum(case["valid"] for case in cases) / count
            if count
            else None,
            "assessment_accuracy": mean(case["correct"] for case in cases),
            "abstention_rate": mean(case["correct"] for case in abstention),
        },
    }
    configuration = data.model_dump() | {"dataset": DATASET, "k_chunks": 8}
    run = db.scalar(
        text("""
        INSERT INTO evaluation_runs(project_id,user_id,configuration,results)
        VALUES (:project,:user,CAST(:config AS jsonb),CAST(:result AS jsonb)) RETURNING id
    """),
        {
            "project": project,
            "user": user,
            "config": json.dumps(configuration),
            "result": json.dumps(result, ensure_ascii=False),
        },
    )
    return {"id": run, "configuration": configuration, "results": result}
