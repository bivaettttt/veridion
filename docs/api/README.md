# REST API

The [published contract](openapi.json) is generated from FastAPI and Pydantic. After starting Compose, open `http://localhost:3817/api/docs` or download `/api/openapi.json`. All business routes are under `/api/v1`.

| Route relative to /api/v1 | Main operations |
| --- | --- |
| `/auth/login`, `/auth/me`, `/auth/logout` | Session lifecycle |
| `/users`, `/projects`, `/projects/{id}/members` | Users, workspaces and roles |
| `/projects/{id}/documents`, `/sources`, `/jobs` | Multipart imports, versions, originals and work |
| `/projects/{id}/search`, `/search/runs`, `/answers` | Retrieval and saved research |
| `/projects/{id}/citations/verify`, `/answers/{id}/reviews` | Provenance and transitions |
| `/projects/{id}/reports`, `/evaluations`, `/lab`, `/audit` | Snapshots, metrics, scenarios and history |

Set the `X-Veridion-Client: 1` header for authenticated writes. Origin pages and API share the same reverse proxy. List endpoints use zero-based `offset` and bounded page sizes. The middleware returns `X-Request-ID`. Submit a repeated file with the same title, category and bytes to recover its existing job. Submit the last seen review revision to guard concurrent changes. Send an optional `Idempotency-Key` on question creation. A matching retry reuses the answer, while a different payload with the same key returns 409.

| Status | Reason |
| --- | --- |
| 401 | No valid session |
| 403 | Project role or client header restriction |
| 404 | Resource unavailable in project scope |
| 409 | Current state, duplicate label or stale review blocks a command |
| 413 | File exceeds import bounds |
| 422 | Invalid client inputs |
| 503 | Local LLM unavailable or returned unusable output |

A syntactically valid citation verification call returns `integrity: INVALID` for an unverified relation. Technical status and age are reported separately from the claim assessment.
