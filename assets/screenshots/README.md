# Veridion screenshots

Captured at 1440 × 1000 with Playwright against the running Docker Compose application. Queries, citation checks, reviews, reports and laboratory results are backed by PostgreSQL.

| Research | Sources | Assurance |
| --- | --- | --- |
| [Overview](overview.png) | [Source library](source-library.png) | [Claim assessment](claim-assessment.png) |
| [Search workspace](search-workspace.png) | [Document viewer](document-viewer.png) | [Contradiction explorer](contradiction-explorer.png) |
| [Hybrid search results](hybrid-search.png) | [Version comparison](version-comparison.png) | [Human review](human-review.png) |
| [Research desk](research-desk.png) | [Citation inspector](citation-inspector.png) | [Report editor](report-editor.png) |
| [Evaluation](evaluation.png) | [Veridion Lab](lab.png) | [Snapshot comparison](snapshot-comparison.png) |

Reproduce from a running workspace with the completed seed corpus:

```bash
cd frontend
npm ci
npx playwright install chromium
node scripts/capture.mjs
```
