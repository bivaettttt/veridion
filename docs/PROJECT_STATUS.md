# Project status

Veridion is a locally runnable portfolio MVP for traceable research on synthetic documents. The repository includes the API, import worker, React workspace, PostgreSQL migrations, documentation, validation lab and deterministic CI workflow.

## Implemented

- Versioned originals, chunk provenance, local embeddings, lexical and semantic retrieval, hybrid search and historical cutoffs.
- Extractive answers and an explicit local Ollama adapter, verified citation integrity and freshness, typed evidence assessments and structured comparisons.
- Project membership and scoped roles, optimistic reviews with a history, reports with immutable JSON/Markdown snapshots, evaluation and isolated lab runs.

## Known gaps and boundaries

- Automatic grounding recognizes Northstar-style capacity, availability and interface claims. It cannot determine support for arbitrary propositions, conditions or arbitrary mixed-modality prose.
- The English UI provides shared evidence and review screens. Some specification views use shared records, including claims and reports. There is no separate claim editing workflow or generator-independent human ground-truth calibration.
- The small labelled corpus evaluates the provided demo cases. Reviewers are responsible for evaluating generated drafts and source trust. The lab instruction-as-data test exercises the deterministic path. Broader adversarial and model-specific evaluations remain outstanding.
- PDF requires a text layer, DOCX uses paragraph text, and archival is one-way. Database storage and exact cosine scoring suit the demo corpus. OCR, PDF report export, SSO, tenant infrastructure, and production operations are outside this build.
- The configuration uses loopback ports and a single database credential for the demo stack. A production deployment would require separate migration/application identities, TLS, quotas and operational controls.
- Model reconstruction records artifact digest and configuration. Generative output may vary when rerun. Markdown snapshot original-file links are relative to a running workspace and need its authentication.
- Local Docker had exhausted automatic subnet allocation. A host-only Compose override assigned a free subnet for Veridion. CI uses standard Compose networking. The local Docker VM has 4 GB shared with other stacks. Local browser and model verification used the already indexed corpus with the import worker paused after memory pressure interrupted the full local test run.

## Verification

- The [Actions workflow](https://github.com/bivaettttt/veridion/actions/workflows/quality.yml) runs Compose on Ubuntu 24.04, PostgreSQL integration, API and browser checks, type validation and secret scanning.
- The real local Qwen draft for the capacity question preserved the evidence gap and cited two valid original excerpts. Rule-based checks cover that specific class of unsupported inference.
- The [screenshot gallery](../assets/screenshots/README.md) contains captures from the running local stack. Each image is 1440 × 1000.

Verification details and instructions are in the [test results](testing/verification.md). Use the [portfolio case](PORTFOLIO.md) for the interview walkthrough.
