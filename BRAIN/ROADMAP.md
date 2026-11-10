# ProofLoop AI — Roadmap and Milestone Gates

Each milestone is gated by the 10xThink checklist. Status is updated only with observed evidence.

## M0 — Repository audit and baseline
- Objective: establish ground truth of the workspace and constraints.
- Deliverable: `BRAIN/PROJECT_AUDIT.md`, risk register.
- Verification: filesystem inventory, toolchain versions, provider reachability.
- Status: **PASS** (greenfield documented; no baseline app existed to break).

## M1 — Product specification and design freeze
- Objective: freeze scope, palette, routes, architecture, API contract, data model.
- Deliverables: `PROJECT.md`, `ARCHITECTURE.md`, `DESIGN_SYSTEM.md`, `DECISIONS.md`,
  `API_CONTRACTS.md`, `DATA_MODEL.md`, `AGENT_WORKFLOW.md`.
- Acceptance: no unresolved ambiguity blocking M2; all deviations have ADRs.
- Status: **PASS**.

## M2 — Landing page
- Objective: explain the product and provide a working entry point.
- Scope: branded hero (in-house liquid sculpture), problem, workflow, interactive sample graph,
  contradiction radar, agents, CTA, footer, responsive nav.
- Verification: production build, browser checks at 1440/390, CTAs navigate, no console errors.
- Do not build: fake logos/testimonials/metrics.

## M3 — App shell and dashboard
- Scope: responsive shell, sidebar/topbar, overview with real aggregates, history, empty/loading/error
  states, shared UI primitives.
- Verification: navigation reachable, metrics match stored data, mobile drawer works.

## M4 — Input and claim extraction
- Scope: text, PDF, URL; validation; upload progress; atomic claims with edit/remove/verify;
  persisted stages. Image OCR only with vision key, explicit 422 otherwise.
- Verification: unit tests for splitter; E2E submission; invalid input rejected.

## M5 — Research and evidence pipeline
- Scope: real Wikipedia retrieval, source metadata, excerpt selection, provenance, error handling.
- Verification: live run shows real URLs/excerpts; failure path marks claims inconclusive; mocked
  integration test is deterministic.

## M6 — Verification and contradictions
- Scope: deterministic classification, numeric/date checks, mixed/insufficient/outdated handling,
  contradiction grouping.
- Verification: unit tests for each verdict; no contradiction is invented; conflicting values kept.

## M7 — Evidence Graph and Contradiction Radar
- Scope: React Flow graph from stored records, filters, inspection, search; radar workspace with
  sources/excerpts/dates; empty and failure states.
- Verification: graph endpoints match job document; browser interaction tested (select/filter/zoom).

## M8 — Proof Reports
- Scope: structured report, claim findings, evidence, source index, limitations, copy/print/JSON export.
- Verification: exported report contains every conclusion's evidence; limitations always present.

## M9 — Security and QA
- Scope: auth/authz review, validation, SSRF, uploads, rate limits, headers, CORS, tests.
- Verification: pytest + build + browser negative tests; no critical issue open.

## M10 — Packaging and demo
- Scope: README, run scripts, Docker/compose, demo script, final screenshots, handoff.
- Verification: clean install → build → start → health 200; judge journey documented.
- Constraint: no public URL will be claimed because no deployment credentials exist here.

## Explicit non-goals

Billing/teams, OAuth/email flows, OCR engine, paid search providers, LLM-synthesised verdicts,
public cloud deployment from this machine.
