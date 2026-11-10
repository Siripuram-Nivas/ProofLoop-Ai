# ProofLoop AI — Product Definition

**Tagline:** Don't just trust an answer. Follow the proof.
**Definition:** An evidence-intelligence platform that turns pasted text, documents, or URLs into
atomic claims, retrieves real sources, evaluates support/contradiction, exposes uncertainty, and
renders a traceable Evidence Graph plus a Proof Report.

## Non-negotiable product principles

1. A plausible answer is not a verified fact.
2. Every evidence item must have a real URL, a real excerpt, a retrieval timestamp, and provenance.
3. Missing evidence stays missing. It is never replaced with model confidence.
4. Contradictory evidence is never silently reconciled; it is surfaced with both sides.
5. LLM output is never used as evidence. LLM may assist *extraction* only; verification comparisons
   are deterministic (numbers, dates, token overlap) and explainable.

## Primary user journey

1. Land on `/` → understand the product in seconds.
2. Click **Verify a Claim** → `/app/new`.
3. Paste text / upload a PDF / submit a URL (image OCR requires a vision key; explicit otherwise).
4. Review and edit extracted atomic claims.
5. Run verification → live source retrieval → evidence evaluation.
6. Inspect claims, evidence passages, and source metadata.
7. Inspect the Evidence Graph and Contradiction Radar.
8. Open the Proof Report, copy/print/export it, and independently check every source.

## Scope of the MVP (built)

- Public landing page with functional interactive evidence-graph demo (clearly labelled sample).
- Guest-first workspace with optional email/password account.
- Text, PDF, and URL ingestion; explicit, honest image limitation.
- Atomic claim extraction with edit/remove/verify.
- Live research against the Wikipedia API (real sources, real timestamps, real excerpts).
- Deterministic evidence classification: supported / contradicted / mixed / insufficient / unverified,
  plus stale-source flagging.
- Evidence Graph (React Flow) driven by stored records.
- Contradiction Radar aggregating genuine numeric/date conflicts.
- Proof Report with evidence snapshot, limitations, copy/print/JSON export.
- Automated backend tests + browser-validated E2E journey.

## Explicitly out of scope (documented, not faked)

- Multi-tenant billing, teams, OAuth providers, email verification.
- Paid search APIs, OCR, and LLM synthesis (all optional future adapters).
- Public cloud deployment (no credentials in this environment).
- Claims of "truth" beyond the retrieved evidence snapshot.

## Success criteria

A judge can submit a multi-claim statement, watch real retrieval happen, see at least one claim
classified with visible evidence, inspect the graph and radar, and export a report in which every
conclusion carries a clickable source and honest limitations.
