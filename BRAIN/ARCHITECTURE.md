# ProofLoop AI — Architecture

## Runtime topology

```text
Browser (React 19 + Vite + TS + Tailwind v4)
   |  JSON over /api/v1  (httpOnly session cookie)
   v
FastAPI (Python 3.11, uvicorn)
   |-- auth (scrypt + HMAC-SHA256 JWT, stdlib)
   |-- ingest (text / PDF via pypdf / URL with SSRF guard)
   |-- extraction (deterministic; optional Gemini adapter)
   |-- research (Wikipedia Action API, real sources)
   |-- evaluation (deterministic overlap + numeric/date comparison)
   |-- contradictions / graph / report builders
   |-- SQLite (stdlib) -> JSON document snapshot per verification
   v
Wikimedia API (research)  |  optional Gemini API (extraction only)
```

## Design choices

- **One document store, one table pair.** `verifications` holds an immutable-ish JSON payload plus
  indexed list columns. This preserves historical evidence snapshots and avoids an ORM for an MVP.
  Migration path to MongoDB is a repository swap (`db.py`), documented in `DATA_MODEL.md`.
- **Background pipeline.** `POST /verifications` persists a job and runs the pipeline in a FastAPI
  background task. The UI polls the job and renders persisted stage states. No fake progress.
- **Deterministic core.** Numbers and dates are compared programmatically. The LLM (if configured)
  is only allowed to propose claim splits, validated against the original text before acceptance.
- **Conservative verdicts.** "Supported" requires either a numeric match or strong lexical grounding
  across at least two independent excerpts; a single weak overlap yields "insufficient evidence".

## Module boundaries

```text
app/
  main.py            app factory, middleware, routers, SPA static serving
  config.py          env config (single source)
  db.py              SQLite schema + repository functions
  security.py        password hashing, JWT, session cookie, current-user dependency
  schemas.py         Pydantic request/response models
  routers/           auth, verifications, uploads, stats, health
  services/
    text.py          sentence split, tokenisation, number/year extraction
    ingest.py        URL fetch (SSRF guard), PDF text extraction
    extraction.py    atomic claim split, categorisation, provenance
    research.py      Wikipedia search + excerpt extraction
    evaluation.py    evidence relevance + relationship + claim verdict
    contradictions.py conflict detection and grouping
    graph.py         graph projection (nodes/edges) from stored records
    report.py        report assembly + limitations
    pipeline.py      orchestration + stage persistence
```

## Error handling

All errors return `{"error": {"code": "...", "message": "..."}}`. Pipeline failures are persisted on
the job (`status=failed`, `error`) and visible in the UI; they are never rendered as "no evidence".
External HTTP calls use 12s timeouts and are never allowed to crash the worker.

## Frontend structure

```text
src/
  App.tsx                    router
  lib/api.ts                 typed fetch wrapper (cookies included)
  lib/types.ts               API types
  components/ui.tsx          Button/Card/Badge/Input/Spinner/etc.
  components/Brand.tsx       logo + wordmark
  components/landing/*       hero, workflow, graph showcase, radar, agents
  components/EvidenceGraph   React Flow projection + inspector
  components/ClaimCard
  layouts/AppShell.tsx       sidebar + topbar + responsive drawer
  pages/                     Landing, Overview, NewVerification, History,
                             VerificationDetail, GraphExplorer, Radar,
                             Reports, Settings, Auth
```

Styling is Tailwind v4 with palette tokens declared in `index.css` (`@theme`). No component library;
shared primitives live in `ui.tsx` to keep the surface small.

## Non-goals in code

No websockets, no queue service, no client-side API keys, no mock evidence generators. The only
sample data in the product is the clearly labelled landing-page graph illustration and a labelled
demo example the user can choose to prefill.
