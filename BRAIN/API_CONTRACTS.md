# ProofLoop AI — API Contracts (v1)

Base URL: `/api/v1`. Session: httpOnly cookie `proofloop_session` (JWT, 30 days). Guest sessions are
created explicitly via `POST /auth/guest`. All non-auth endpoints require a session.

Errors: `{"error": {"code": "snake_case", "message": "human readable", "details"?: {...}}}`.

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/health` | no | Liveness + engine capability report |
| POST | `/auth/guest` | no | Create guest user + cookie |
| POST | `/auth/register` | no | `{email, password}` → user + cookie |
| POST | `/auth/login` | no | `{email, password}` → user + cookie |
| POST | `/auth/logout` | yes | Clear cookie |
| GET | `/auth/me` | no | `{user}` or 401 |
| POST | `/uploads` | yes | multipart `file` (PDF/TXT/MD) → extracted text; images return 422 (OCR not enabled) |
| POST | `/verifications` | yes | `{title?, text?, url?}` or `{title?, upload_id?}` → 202 `{id, status, title}` |
| GET | `/verifications` | yes | `?limit=20&offset=0&status=` → `{items, total, limit, offset}` |
| GET | `/verifications/{id}` | owner | full job document |
| PATCH | `/verifications/{id}/claims/{claim_id}` | owner | `{text}` → updated claim |
| DELETE | `/verifications/{id}/claims/{claim_id}` | owner | remove claim + rule out of report |
| POST | `/verifications/{id}/claims` | owner | `{text}` → append manual claim |
| POST | `/verifications/{id}/run` | owner | no body → 202 `{id, status}`; 409 if already running |
| GET | `/verifications/{id}/graph` | owner | `{nodes, edges}` projection |
| GET | `/verifications/{id}/contradictions` | owner | `{contradictions, claims}` |
| GET | `/verifications/{id}/report` | owner | report object (evidence snapshot) |
| GET | `/stats` | yes | dashboard aggregates for the current user |

## Job document (abridged)

```jsonc
{
  "id": "ver_...",
  "title": "…",
  "input_kind": "text|document|pdf|url|image",
  "input_text": "original text (never overwritten)",
  "input_url": "https://…",
  "status": "queued|extracting|researching|evaluating|completed|failed",
  "error": null,
  "created_at": "ISO-8601Z",
  "updated_at": "ISO-8601Z",
  "engine": {"extraction": "deterministic|gemini", "research": "wikipedia"},
  "stages": [{"key":"ingest","label":"Input received","status":"done|active|pending|failed|partial","detail":"...","at":"ISO"}],
  "claims": [{
    "id": "clm_...",
    "text": "…",
    "original_span": "…",
    "category": "date|quantity|identity|attribution|general",
    "entities": ["…"],
    "numbers": [1889],
    "dates": ["1889"],
    "confidence": 0.72,
    "confidence_kind": "extraction_confidence",
    "verdict": "supported|contradicted|mixed|insufficient|outdated|unverified|inconclusive",
    "evidence": [{
      "id": "ev_...",
      "source_id": "src_...",
      "excerpt": "…",
      "relationship": "supports|contradicts|insufficient",
      "explanation": "…",
      "matched_terms": ["…"],
      "retrieved_at": "ISO"
    }]
  }],
  "sources": [{
    "id": "src_...",
    "title": "…",
    "url": "https://en.wikipedia.org/?curid=…",
    "publisher": "Wikipedia, The Free Encyclopedia",
    "source_type": "encyclopedia (tertiary)",
    "published_at": null,
    "updated_at": "ISO",
    "retrieved_at": "ISO",
    "quality": "medium|low",
    "quality_note": "Community-edited tertiary source; prefer primary sources."
  }],
  "contradictions": [{
    "id": "con_...",
    "claim_id": "clm_...",
    "kind": "numeric_mismatch|date_mismatch|source_disagreement",
    "severity": "high|medium",
    "summary": "…",
    "evidence_ids": ["ev_..."]
  }],
  "report": {"…": "see report.py / Report page"}
}
```

## Status semantics (must not be collapsed)

- `supported` — ≥1 numeric match or ≥2 independent strong excerpts, no contradiction.
- `contradicted` — at least one deterministic numeric/date mismatch, no meaningful support.
- `mixed` — both support and contradiction exist. Contradictions stay visible.
- `insufficient` — evidence found but too weak/ambiguous to conclude.
- `outdated` — only support is stale (> 3 years since source update).
- `unverified` — no relevant evidence retrieved; explicitly *not* false.
- `inconclusive` — research could not run (network/provider failure).

Confidence shown is **extraction confidence**, never a probability of truth. Verdict strength is
communicated by the evidence counts and the source-quality labels.

## Pagination

`limit` 1–50 (default 20), `offset` ≥ 0. Response carries `total`. Stats are computed from stored
jobs, never invented.
