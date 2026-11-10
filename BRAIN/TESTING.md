# ProofLoop AI — Testing Strategy and Results

## Pyramid

**Unit (deterministic, no network)**
- Atomic claim splitting: multi-predicate sentence, semicolon lists, single claim, empty input.
- Number/date extraction and tolerance comparisons (1%, 5%, rounding, year mismatch).
- Evidence relevance threshold and relationship selection.
- Verdict aggregation incl. mixed, contradicted, insufficient, unverified.
- Contradiction detection (numeric + date + source disagreement).
- SSRF guard: private/loopback/link-local/metadata IPs and non-http schemes rejected.
- JWT sign/verify, tampered token rejection, password hash verify.
- Report includes limitations and source index.

**Integration (fixtures, mocked HTTP)**
- `POST /verifications` validation (empty input → 422, bad URL → 422).
- Ownership isolation: another session cannot read a job.
- Pipeline with a stubbed research provider produces claims + verdicts and persists stages.
- Graph projection node/edge integrity (edge endpoints exist).
- Report snapshot is stable after evidence mutation.

**End-to-end (live browser, live research)**
- Landing → Verify a Claim → submit text → poll → claims → graph → radar → report.
- Negative: empty submit disabled, invalid URL, unsupported file type, unauthenticated mutation.

Live-provider tests are separated from the default suite (`-m live` / manual) so CI never depends on
Wikipedia or an LLM.

## Commands

```bash
cd backend && .venv/Scripts/python -m pytest -q        # unit + integration
cd frontend && npm run build                            # typecheck + production build
cd frontend && npm test                                 # frontend unit tests (vitest)
```

## Results

Observed on the final pass (Windows, Python 3.11, Node 20):

| Check | Command | Result |
|---|---|---|
| Backend unit + integration | `cd backend; .\.venv\Scripts\python -m pytest -q` | `50 passed, 1 warning in 2.70s` |
| Frontend unit | `cd frontend; npm test` | `5 passed` (`src/lib/format.test.ts`) |
| Typecheck + production build | `cd frontend; npm run build` | Success, 1642 modules; JS 607.40 kB (182.38 kB gzip), CSS 71.99 kB; chunk-size warning only |
| Live research | Manual, browser | Wikipedia URL, excerpt, and retrieval timestamp persisted; verdicts rendered |
| Browser E2E | Manual, Playwright-driven browser | Landing → guest session → submit → stages → claims → graph → radar → report → history → settings → sign in/out; negative URL/OCR/404 paths |
| Docker image | `docker compose up --build` | **Not run** — daemon unavailable |
| Public deployment | — | **Not performed** |

The one pytest warning is an upstream Starlette `anyio` deprecation, unrelated to ProofLoop.
A feature is not marked verified without an observed result. See `HANDOFF.md` for the full checklist.
