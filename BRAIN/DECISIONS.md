# ProofLoop AI — Architecture Decision Records

## ADR-001 — Build greenfield; repository was empty

**Context:** The brief references an existing repository, but the workspace contained zero files.
**Decision:** Treat M0 as a greenfield audit, scaffold a new app, and record every deviation.
**Consequence:** No preservation conflicts. All features must be verified from scratch.

## ADR-002 — Custom liquid-sculpture hero instead of the 21st.dev component

**Context:** `@/components/ui/liquid-sculpture-hero` and its source are absent from the workspace.
Recreating it verbatim would require the original source/licence; neither exists here.
**Decision:** Build an equivalent layered-gradient + animated "proof loop" sculpture in-house, with
`prefers-reduced-motion` support and no WebGL dependency (thus no WebGL failure path to manage).
**Consequence:** No third-party attribution required, no network dependency, deterministic rendering.
The hero is visually comparable but not a copy of the unavailable component.

## ADR-003 — SQLite instead of MongoDB Atlas

**Context:** No Atlas URI/credentials exist; judges must be able to run the app with zero setup.
**Decision:** Persist to SQLite via stdlib. Store each verification as a JSON snapshot plus indexed
list columns. Keep `db.py` as the only persistence boundary.
**Consequence:** Zero-credential runnable, transactional, backup-friendly. Documents describe the
Mongo migration; scaling beyond a single instance would require replacing `db.py`.

## ADR-004 — Keyless live research via Wikipedia, no fabricated fallback

**Context:** No paid search API key is available; fabricating sources violates the product's core
principle. The Wikimedia API requires no key and returns real URLs, excerpts, and page timestamps.
**Decision:** Use the Wikipedia Action API for live retrieval, label it as a *tertiary, community-
edited* source type, and record retrieval timestamps. If retrieval fails, claims become "unverified
— research unavailable", never "false".
**Consequence:** Demo works offline from paid providers but requires internet. Source authority is
honestly downgraded; the UI tells the user to prefer primary sources for decisions.

## ADR-005 — Deterministic verification, optional LLM extraction only

**Context:** LLM reasoning is not evidence and can hallucinate. No LLM key is configured.
**Decision:** Version 1 evaluation is deterministic: token overlap, number comparison (1% tolerance),
year comparison, stale-source detection. If `GEMINI_API_KEY` is set, Gemini may propose atomic claim
splits; every proposed claim must appear (normalised) in the source text or it is discarded.
**Consequence:** Explainable verdicts, reproducible tests, no ungrounded "AI evidence".

## ADR-006 — Guest-first identity with optional accounts

**Context:** Forcing signup hurts demo conversion; no auth provider is configured.
**Decision:** First visit creates a signed guest session (JWT, httpOnly cookie). Email/password
registration (scrypt) upgrades to a durable account. Every verification is scoped to its owner.
**Consequence:** No third-party identity dependency; password reset/email verification are out of
scope and documented as limitations.

## ADR-007 — Polling instead of SSE/WebSockets

**Context:** Pipeline takes seconds; stage visibility is required.
**Decision:** Persist stage transitions and poll every 1.2s from the detail view.
**Consequence:** Simple, proxy-friendly, trivially recoverable after refresh. Slight latency cost.

## ADR-008 — Image OCR is unavailable, never simulated

**Context:** No OCR engine (Tesseract) or vision-capable key is installed. Pretending to read
screenshots would violate the no-fake-features rule.
**Decision:** The upload endpoint accepts image files only to reject them with a 422 and an explicit
"OCR is not enabled" message. The UI states this before upload. `GEMINI_API_KEY`, when present, is used
only for claim extraction; it never reads images and never supplies evidence or verdicts.
**Consequence:** PNG/JPG upload fails visibly and honestly in this deployment. PDFs and text work.
Adding OCR later means implementing a real engine and updating this ADR.

## ADR-009 — BackgroundTasks instead of Celery/Redis

**Context:** Single-process demo deployment; no broker available.
**Decision:** Use `BackgroundTasks` to run the pipeline after the 202 response is persisted.
**Consequence:** Jobs are lost if the process dies mid-run (job remains "failed"/stuck and can be
retried). Acceptable for hackathon scale; documented in HANDOFF.
