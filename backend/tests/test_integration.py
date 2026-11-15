import os
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from uuid import uuid4

import httpx
import pytest

BASE = os.getenv("VERIDION_TEST_URL", "http://127.0.0.1:8817/api/v1")


@contextmanager
def login(role):
    with httpx.Client(
        base_url=BASE, headers={"X-Veridion-Client": "1"}, timeout=120, trust_env=False
    ) as client:
        response = client.post(
            "/auth/login",
            json={
                "email": f"{role}@northstar.test",
                "password": "northstar" + "-workspace",
            },
        )
        assert response.status_code == 200, response.text
        assert "HttpOnly" in response.headers["set-cookie"]
        yield client


@pytest.fixture
def reader():
    with login("researcher") as client:
        project = next(p for p in client.get("/projects").json() if p["lab"])
        yield client, f"/projects/{project['id']}"


def wait_for_import(client, project, jid):
    for _ in range(75):
        row = next(
            item for item in client.get(project + "/jobs").json() if item["id"] == jid
        )
        if row["state"] != "QUEUED":
            assert row["state"] == "DONE", row
            return row
        time.sleep(0.25)
    pytest.fail("Import did not finish")


def test_project_scope_and_structured_errors(reader):
    client, project = reader
    with login("guest") as guest:
        denied = guest.post(project + "/search", json={"query": "Northstar"})
        assert denied.status_code == 404
        assert denied.json()["error"]["request_id"] == denied.headers["X-Request-ID"]
    assert client.get(project + "/audit").status_code == 403
    invalid = client.post(project + "/search", json={"query": "x"})
    assert invalid.status_code == 422 and invalid.json()["error"]["fields"]


def test_real_import_repeat_and_historical_citation(reader):
    client, project = reader
    title = "Integration test " + uuid4().hex
    body = b"Build 2.0 documents a webhook integration interface."

    def upload(payload):
        response = client.post(
            project + "/documents",
            data={"title": title, "category": "specification"},
            files={"file": ("fixture.txt", payload)},
        )
        assert response.status_code == 202, response.text
        return response.json()

    first = upload(body)
    assert first == upload(body)
    wait_for_import(client, project, first["id"])
    source_path = project + "/sources/" + first["source_id"] + "/versions/"
    assert client.get(source_path + "1/original").content == body
    answer = client.post(
        project + "/answers",
        json={
            "query": "Is there a webhook integration?",
            "source_id": first["source_id"],
        },
    )
    assert answer.status_code == 201, answer.text
    answer = answer.json()
    valid = answer["citations"][0]
    payload = {
        key: valid[key] for key in ("chunk_id", "version_id", "quote", "content_hash")
    }
    payload["answer_id"] = answer["id"]
    assert (
        client.post(project + "/citations/verify", json=payload).json()["integrity"]
        == "VALID"
    )
    assert (
        client.post(
            project + "/citations/verify", json=payload | {"quote": "different"}
        ).json()["integrity"]
        == "INVALID"
    )
    second = upload(b"Build 3.0 documents a SOAP integration interface.")
    wait_for_import(client, project, second["id"])
    historical = client.post(project + "/citations/verify", json=payload).json()
    assert (
        historical["integrity"] == "VALID" and historical["freshness"] == "HISTORICAL"
    )


def test_concurrent_review_and_snapshots(reader):
    client, project = reader
    result = client.post(
        project + "/answers",
        json={"query": "Does the platform support 10000 concurrent users?"},
    )
    assert result.status_code == 201, result.text
    root = project + "/answers/" + result.json()["id"]
    payload = {
        "decision": "IN_REVIEW",
        "revision": 0,
        "rationale": "Check evidence sources and figures.",
    }
    with ThreadPoolExecutor(max_workers=2) as pool:
        response = list(
            pool.map(
                lambda _: client.post(root + "/reviews", json=payload).status_code,
                range(2),
            )
        )
    assert sorted(response) == [201, 409]
    decision = payload | {"decision": "VERIFIED", "revision": 1}
    assert client.post(root + "/reviews", json=decision).status_code == 403
    report = client.post(
        project + "/reports",
        json={"answer_id": result.json()["id"], "title": "Review evidence"},
    )
    assert report.status_code == 201, report.text
    url = project + "/reports/" + report.json()["id"]
    with login("reviewer") as reviewer:
        assert reviewer.post(root + "/reviews", json=decision).status_code == 201
    assert (
        client.post(url + "/snapshots", data={"notes": "After review"}).status_code
        == 201
    )
    snapshots = client.get(url).json()["snapshots"]
    assert [len(s["body"]["reviews"]) for s in snapshots] == [2, 1]


def test_evaluation_and_isolated_lab(reader):
    client, project = reader
    result = client.post(project + "/evaluations", json={})
    assert result.status_code == 201, result.text
    assert result.json()["results"]["metrics"]["citation_integrity"] == 1.0
    lab = client.post(project + "/lab", json={})
    assert lab.status_code == 201, lab.text
    cases = lab.json()["results"]
    assert len(cases) == 24
    assert all(case["passed"] for case in cases), [
        case for case in cases if not case["passed"]
    ]
    assert not any(
        item["name"] == "Northstar isolated run"
        for item in client.get("/projects").json()
    )


def test_question_idempotency(reader):
    client, project = reader
    headers = {"Idempotency-Key": uuid4().hex}
    request = {"query": "Can we confirm independent certification?"}
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda _: client.post(
                    project + "/answers", json=request, headers=headers
                ),
                range(2),
            )
        )
    assert all(result.status_code == 201 for result in results), [
        result.text for result in results
    ]
    assert len({result.json()["id"] for result in results}) == 1
    changed = client.post(
        project + "/answers", json={"query": "Different question"}, headers=headers
    )
    assert changed.status_code == 409
