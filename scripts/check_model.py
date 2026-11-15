"""Run a local model end to end through the real Veridion API."""

import http.cookiejar
import json
import os
import urllib.request

base = os.environ.get("VERIDION_API_URL", "http://127.0.0.1:8817/api/v1")
client = urllib.request.build_opener(
    urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
)


def call(path, body=None):
    request = urllib.request.Request(
        base + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"X-Veridion-Client": "1", "Content-Type": "application/json"},
    )
    with client.open(request, timeout=150) as response:
        return json.load(response)


call(
    "/auth/login",
    {"email": "researcher@northstar.test", "password": "northstar" + "-workspace"},
)
project = next(item for item in call("/projects") if item["lab"])
result = call(
    f"/projects/{project['id']}/answers",
    {
        "query": "Does the platform support 10 000 concurrent users?",
        "provider": "ollama",
        "mode": "hybrid",
    },
)
generation = result["output"]["generation"]
assert result["provider"] == "ollama" and result["parameters"]["digest"]
assert result["output"]["assessment"] == "INSUFFICIENT_EVIDENCE"
assert generation["status"] == "REQUIRES_REVIEW" and generation["candidate"]
assert all(citation["integrity"] == "VALID" for citation in result["citations"])
assert {citation["title"] for citation in result["citations"]} >= {
    "Capacity requirements",
    "Load test · Run 17",
}
print(
    json.dumps(
        {
            "id": result["id"],
            "model": result["model"],
            "parameters": result["parameters"],
            "assessment": result["output"]["assessment"],
            "candidate": generation["candidate"],
            "citations": [citation["title"] for citation in result["citations"]],
        },
        ensure_ascii=False,
        indent=2,
    )
)
