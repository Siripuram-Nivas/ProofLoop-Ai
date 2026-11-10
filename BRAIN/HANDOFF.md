# ProofLoop AI — Handoff

Written at the end of the build. Everything below was observed in this environment unless marked
otherwise. "Not verified" means exactly that: do not present it as working.

## State at handoff

- Repository: local git repo initialized at the project root. **No commits were made** — all files are
  untracked/uncommitted. Run `git status` before assuming anything is committed.
- Backend and frontend run locally and were exercised in a real browser.
- No public deployment was performed (no hosting account/credentials were available).
- Docker packaging exists (`Dockerfile`, `docker-compose.yml`, `.dockerignore`) but the image was
  **never built** because the Docker daemon was not running. Treat it as unverified.
- Screenshot OCR is **not implemented**. Image uploads return HTTP 422 with an explicit message.
- MongoDB Atlas and a research LLM were not used. SQLite and Wikipedia (keyless) are the real stack.
  Gemini is optional and, if configured, is used only to propose claim splits.

## Run it

Prerequisites: Python 3.11+, Node 20+.

```powershell
# Terminal 1 — API
cd backend
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
Copy-Item .env.example .env      # optional; omit for local defaults
.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# Terminal 2 — UI
cd frontend
npm install
npm run dev                      # http://localhost:5173
```

Single-process alternative: `npm run build` in `frontend/`, then start only the API. The backend
serves `frontend/dist` and falls back to `index.html` for client routes.

Health check: `curl http://127.0.0.1:8000/api/v1/health`.

## Commands and observed results

| Command | Result (observed) |
|---|---|
| `cd backend; .\.venv\Scripts\python -m pytest -q` | **50 passed**, 1 unrelated Starlette deprecation warning, 2.70s |
| `cd frontend; npm test` | **5 passed** (`src/lib/format.test.ts`), 1.43s |
| `cd frontend; npm run build` | **Success**, 1642 modules, JS 607.40 kB (182.38 kB gzip), CSS 71.99 kB; only the >500 kB chunk warning |
| Browser E2E (manual, Playwright-driven browser) | Passed — see the checklist below |
| Live Wikipedia research | Passed repeatedly; real URL, excerpt, and retrieval timestamp stored |
| Docker build | **Not run** — daemon unavailable (`npipe:////./pipe/dockerDesktopLinuxEngine` missing) |
| Public deployment | **Not performed** |

Tests never call the network; research is stubbed in pytest and verified manually in the browser.
`pytest` includes upload/TXT, image-OCR-422, SSRF, ownership isolation, graph integrity, and report
stability cases.

## Browser checklist (what was actually clicked)

- Landing renders; sample graph is labelled **Illustrative sample**; CTA enters the app.
- First visit bootstraps a guest session via `POST /auth/guest`.
- Example input prefills the form without auto-submitting.
- Submit text → stage progress (ingest/extract/research/evaluate) → completed.
- Claim cards show verdicts, evidence excerpts, source links, and limitations.
- Evidence graph: filter/search, select node, inspector shows readable neighbour labels.
- Contradiction radar: honest empty state when no conflict was found.
- Report: renders Markdown, copy, JSON export, print.
- History lists past runs; verdict chips expose screen-reader labels.
- Settings: account state, sign out, sign in with email/password.
- Negative paths: invalid/private URL rejected (SSRF), image upload rejected (OCR), unknown route → 404,
  document title updates on Auth/NotFound.

Test account created in the local dev DB: `audit-demo@proofloop.test` / `audit-pass-9812`.
Local runs referenced during QA: `ver_6ec92152cb724c78924d` (guest),
`ver_23e65622d4e34a078a4d`, `ver_e7826d8021b04897862c` (account). These live only in the local
`backend/data/proofloop.db`.

## Demo script (≈4 minutes)

1. Open the landing page. Say the tagline: "Don't just trust an answer. Follow the proof."
2. Scroll to the workflow and the graph; note the graph is an illustrative sample, not a result.
3. Click **Verify a claim**. Use the prefilled Eiffel Tower example.
4. Submit. Point out each stage as it completes, then the verdicts.
5. Open a supported claim: show excerpt, URL, retrieval timestamp, and the tertiary-source warning.
6. Show the claim that stayed `unverified` and explain why (no excerpt directly supports it). This is
   the honesty feature, not a bug.
7. Open the graph and the radar. If the radar is empty, say so — absence of a detected conflict is not
   proof of consistency.
8. Open the report, copy Markdown or export JSON.
9. Close on limitations: Wikipedia-only research, lexical relevance, 8-claim cap, no OCR.

## Known limitations (carry these forward)

- Research: Wikipedia Action API only; community-edited tertiary source; top 3 pages, one excerpt each.
- Relevance: lexical overlap (≥2 shared content tokens, ≥0.30 overlap). Pronoun-led claims often remain
  `unverified` because the antecedent is not resolved. This was attempted and reverted rather than
  hidden.
- Verdicts: deterministic number/date comparison with 1% support and 5% conflict tolerance; no semantic
  entailment model.
- Contradiction radar only reports observed disagreements, never "no contradiction found = true".
- Extraction: rule-based splitter, max 8 claims. Gemini adapter only proposes splits contained in the
  source text.
- OCR: absent by design until a real OCR engine/key exists.
- Jobs: FastAPI `BackgroundTasks`, in-process. A restart mid-run leaves a failed/retryable job; no queue.
- Rate limits: in-memory, per-process; not shared across workers.
- SQLite: single writer; fine for a demo/single instance, not for horizontal scale.
- Auth: no OAuth, MFA, password reset, email verification, or account deletion UI.
- Frontend bundle is one 607 kB chunk; code splitting is the obvious next optimization.
- Production CSP allows Google Fonts (`style-src`/`font-src`) because the UI loads them; tighten if
  fonts are self-hosted.

## Docker (unverified)

```bash
# Requires a running daemon and a secret of ≥24 chars
$env:PROOFLOOP_SECRET="<random 24+ chars>"
docker compose up --build
# http://localhost:8000
```

The image builds the frontend in a Node stage, copies `dist` to `/app/frontend/dist`, runs the API as
UID 10001, and persists SQLite in the `proofloop-data` volume. If the build fails, the likely causes are
the `frontend/dist` path expectation in `backend/app/main.py` or the data-directory permissions.

## Where to continue

1. **Deploy** to a host (Fly.io/Render/Railway) with `PROOFLOOP_SECRET`, `PROOFLOOP_ENV=production`,
   a persistent volume for SQLite, and HTTPS. Then re-run the browser checklist against the public URL.
2. **Commit the work** (currently uncommitted), and add CI running pytest, vitest, and the build.
3. **OCR** behind a feature flag only if a real engine is available; keep the 422 fallback honest.
4. **Research breadth**: add a second provider (e.g. a primary-source API) with the same excerpt and
   provenance contract; never fabricate fallbacks.
5. **Scale path**: move jobs to a queue and SQLite to Postgres/Mongo only when load requires it.

## Documentation map

`BRAIN/PROJECT.md` → `PROJECT_AUDIT.md` → `ARCHITECTURE.md` → `DESIGN_SYSTEM.md` →
`API_CONTRACTS.md` → `DATA_MODEL.md` → `AGENT_WORKFLOW.md` → `DECISIONS.md` → `TESTING.md` →
`SECURITY.md` → `ROADMAP.md` → this file.
