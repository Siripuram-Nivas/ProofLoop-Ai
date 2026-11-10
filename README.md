# ProofLoop AI

> Don't just trust an answer. Follow the proof.

ProofLoop AI is an evidence-intelligence workspace. It splits a document into atomic claims, retrieves
real public sources, compares numbers and dates deterministically, and produces a proof report where
every verdict points back to a retrieved excerpt, URL, and timestamp. Uncertainty is preserved:
`unverified` never becomes `false`, and a missing contradiction is never reported as proof.

## What is actually implemented

| Capability | Status | Notes |
|---|---|---|
| Text, TXT/MD, PDF, and public URL input | Working | PDF text layer via `pypdf`; scanned PDFs fail with an explanation |
| URL ingestion | Working | SSRF-guarded; private/reserved addresses and redirects rejected |
| Screenshot OCR | **Not implemented** | Images are rejected with 422; the UI says so before upload |
| Claim extraction | Working | Deterministic rule-based splitter, max 8 claims per run |
| Optional LLM extraction | Conditional | Gemini only proposes splits when `GEMINI_API_KEY` is set; proposals must exist in the source text |
| Live research | Working | Wikipedia Action API; excerpts, URLs, retrieval times, tertiary-source labels |
| Evidence verdicts | Working | `supported`, `contradicted`, `mixed`, `insufficient`, `outdated`, `unverified`, `inconclusive` |
| Evidence graph | Working | React Flow projection from stored records, filters, search, node inspector |
| Contradiction radar | Working | Numeric/date/source disagreements, with both passages |
| Proof reports | Working | Read in-app, copy Markdown, export JSON, print/save as PDF |
| Accounts | Working | Guest-first, optional email/password, scrypt hashing, httpOnly JWT cookie |
| Public deployment | **Not performed** | No hosting credentials were available in this environment |

The landing-page graph is explicitly labelled **Illustrative sample**. The example input only prefills
the form; every research result in a run is live.

## Stack

- Frontend: React 19, Vite 6, TypeScript, Tailwind CSS v4, React Flow, Lucide.
- Backend: FastAPI (Python 3.11), httpx, pypdf, SQLite (stdlib `sqlite3`, WAL).
- Optional: Gemini for claim extraction only. Research and verdicts never depend on an LLM.

## Run locally

Prerequisites: Python 3.11+, Node 20+.

```powershell
# Backend
cd backend
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
Copy-Item .env.example .env          # optional; defaults are safe for local use
.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# Frontend (second terminal)
cd frontend
npm install
npm run dev                          # http://localhost:5173, proxies /api to :8000
```

The Vite dev server proxies `/api` to `http://127.0.0.1:8000`. The backend also serves the built SPA
from `frontend/dist` when that directory exists (useful for a single-process deployment).

## Test

```powershell
cd backend
.\.venv\Scripts\python -m pytest -q          # 50 unit/integration tests, network stubbed

cd frontend
npm test                                     # 5 formatter/metadata tests
npm run build                                # tsc --noEmit + production bundle
```

Live research is exercised manually in the browser; tests never depend on Wikipedia being reachable.

## Configuration

Set via environment variables or `backend/.env` (see `backend/.env.example`).

| Variable | Default | Purpose |
|---|---|---|
| `PROOFLOOP_ENV` | `development` | `production` enables Secure cookies, CSP, HSTS |
| `PROOFLOOP_SECRET` | dev fallback | JWT signing secret; use ≥24 random characters in production |
| `PROOFLOOP_DB` | `backend/data/proofloop.db` | SQLite file |
| `PROOFLOOP_CORS_ORIGINS` | localhost dev origins | Comma-separated allowed origins |
| `PROOFLOOP_RESEARCH` | `wikipedia` | Reported capability; only Wikipedia is implemented |
| `GEMINI_API_KEY` | empty | Optional claim-extraction adapter only |
| `GEMINI_MODEL` | `gemini-2.0-flash` | Model used by that adapter |

## Docker

A multi-stage `Dockerfile` builds the frontend, installs the API, and serves both from one container.
It is provided for reproducible packaging but **was not built in this environment** because the Docker
daemon was unavailable. Verify it before relying on it.

```bash
docker compose up --build
# http://localhost:8000
```

`PROOFLOOP_SECRET` should be set in the environment or a `.env` file next to `docker-compose.yml`.

## Security posture

- Sessions: HMAC-SHA256 JWT in an httpOnly, SameSite=Lax cookie; `Secure` in production.
- Passwords: scrypt with per-user salt; generic login errors.
- Authorization: every job/upload query is scoped to the session user; cross-user reads return 404.
- SSRF: scheme allow-list, DNS resolution and IP classification, redirects disabled, 12s timeout, 3 MB cap.
- Uploads: extension/MIME allow-list, 10 MB cap, PDF parsed in memory, sanitised filenames.
- Rate limits: in-memory sliding windows (auth 10/min, writes 30/min, reads 120/min).
- Headers: nosniff, frame denial, referrer policy, permissions policy, CSP/HSTS in production.

Known limitations are listed in `BRAIN/SECURITY.md`; the short version is no OAuth/MFA, no password
reset, no deletion UI, in-memory rate limits, and SQLite is single-writer.

## Project map

```
backend/app/          FastAPI app, routers, security, SQLite repository
backend/app/services/ extraction, research, evaluation, contradictions, graph, report, pipeline
backend/tests/        pytest suite (50)
frontend/src/         React app: landing, workspace, graph, radar, reports, auth
BRAIN/                product, architecture, API, data, testing, security, roadmap, handoff
.planning/            GSD roadmap/state
Dockerfile            multi-stage image (unverified: no daemon available here)
```

## Honest limitations

- Research uses Wikipedia, a community-edited tertiary source. Reports say this and recommend primary
  sources for consequential decisions.
- Excerpt relevance is lexical; pronoun-led claims ("It was completed in 1889") often stay
  `unverified` because the antecedent is not resolved. That is a visible limitation, not a hidden guess.
- Only the top excerpts per claim are evaluated; absence of a conflict is not proof of consistency.
- Claim extraction is rule-based and capped at 8 claims per run.
- No public URL, no OCR, no Mongo Atlas, and no paid search provider were available or claimed.
- Background jobs are in-process; a crash mid-run leaves a failed/retryable job.

## Documentation

Start with `BRAIN/PROJECT.md`, then `BRAIN/ARCHITECTURE.md`, `BRAIN/API_CONTRACTS.md`,
`BRAIN/DECISIONS.md`, `BRAIN/TESTING.md`, `BRAIN/SECURITY.md`, and `BRAIN/HANDOFF.md`.
