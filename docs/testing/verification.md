# Verification plan and evidence

Run a fresh Compose project with the default Northstar dataset. After the API is healthy, wait for the seeded imports in Ingestion. Use Python 3.13 and Node 24 for the checked toolchain.

```bash
python -m pip install -r backend/requirements.txt -r backend/requirements-dev.txt
(cd backend && ruff check . && mypy veridion/contracts.py veridion/documents.py veridion/grounding.py && python -m pytest -q)
(cd frontend && npm ci && npm run build && npx playwright install chromium && npm test)
python scripts/check_docs.py
```

| Requirement | Implementation | Verification |
| --- | --- | --- |
| FR-01 / BR-01 | [Project access](../../backend/veridion/access.py) and project-scoped queries | `test_project_scope_and_structured_errors`, lab 19 |
| FR-02 / BR-02 | [Import](../../backend/veridion/worker.py) and [DB constraints](../../backend/migrations/versions/0001_provenance.py) | `test_formats`, `test_chunk_offsets_cover_normalized_unicode_text`, `test_real_import_repeat_and_historical_citation`, lab 4, 10, 11, 24 |
| FR-03 / BR-03 | [Retrieval](../../backend/veridion/retrieval.py) and local embeddings | Lab 4, 12–16 and evaluation cases |
| FR-04 / BR-04 | [Answer and verification](../../backend/veridion/research.py) | Integration citation test, Playwright, lab 2, 8, 9, 17 and 23, `scripts/check_model.py` |
| FR-05 / BR-05 | [Typed grounding](../../backend/veridion/grounding.py) | `test_modalities_and_compound_claims`, lab 1, 3, 5–7 and 18 |
| FR-06 / BR-06 | [Review transition](../../backend/veridion/lifecycle.py) | `test_concurrent_review_and_snapshots`, lab 20 |
| FR-07 / BR-07 | [Snapshots](../../backend/veridion/lifecycle.py) | `test_concurrent_review_and_snapshots`, lab 21–22 |
| FR-08 / BR-08 | [Labelled evaluation](../../backend/veridion/evaluation.py) and [isolated runs](../../backend/veridion/lab.py) | `test_evaluation_and_isolated_lab` |
| NFR-01–04 | [Compose](../../compose.yaml), [API](../../backend/veridion/api.py), [migrations](../../backend/migrations/versions/0002_research.py) | Docker, OpenAPI and live integration checks |

## Evaluation methodology

The Northstar dataset fixes five questions and accepted source titles. Source recall divides distinct relevant returned titles by the labelled titles. MRR uses the rank of the first relevant title after collapsing duplicates in the first eight chunks. Citation integrity divides exact valid citations by all saved citations. Assessment accuracy compares the evidence-state label for each case. Abstention rate measures the fraction of labelled missing-evidence questions that received `INSUFFICIENT_EVIDENCE`. A run with zero citations has no citation-integrity score.

A local hybrid extractive run returned 1.00 for each of those five metrics on the five-case synthetic set. A separate local lab batch passed 24 of 24 scenarios. These runs test the behaviour of the seed corpus, supported properties and configured rules.

## Model-dependent evaluation

`python scripts/check_model.py` submits the capacity question to a real configured Ollama endpoint. It checks that the API saves a model digest and supplied context, reports the evidence gap, returns a reviewable draft and verifies both source links. The candidate still needs semantic review. An early run incorrectly interpreted incomplete measurements as evidence of an upper bound. The deterministic assessment preserved the evidence gap. The revised prompt explicitly distinguishes an untested threshold from a measured maximum.

See the [latest project status](../PROJECT_STATUS.md) for local and GitHub verification and remaining gaps.
