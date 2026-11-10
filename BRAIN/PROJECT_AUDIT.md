# ProofLoop AI — Repository Intelligence Audit (M0)

**Audit date:** 2026-11-10
**Auditor role:** Principal Product Architect / Senior Full-Stack Engineer
**Path audited:** `C:\Users\sirip\OneDrive\2yr 2nd term\Hackathons\ProofLoop Ai`

## 1. Executive finding

The workspace was **completely empty** at audit time (0 files, 0 directories, no `.git`). There is no
existing frontend, backend, database, authentication, graph implementation, test suite, environment
configuration, documentation, or deployment configuration to preserve.

This means the brief's "repository preservation" rules are trivially satisfied, but also that:

- The `liquid-sculpture-hero` component referenced in the brief is **not present** anywhere in the
  workspace. An equivalent, self-contained hero was built instead (see DECISIONS.md ADR-002).
- No MongoDB Atlas URI, LLM API key, or search API key exists in the environment. The build therefore
  defaults to a zero-credential live configuration (see ADR-003 / ADR-004).
- Every feature listed as "delivered" below was written in this build, not inherited.

## 2. Baseline checks (executed)

| Check | Command | Result |
|---|---|---|
| File inventory | `Get-ChildItem -Force` (recursive) | 0 entries |
| Git state | `git status` | Not a repository before init |
| Node | `node -v` | v24.12.0 |
| npm | `npm -v` | 11.6.2 |
| Python | `py -3.11 --version` | 3.11.9 (also 3.14.7 available) |
| Git | `git --version` | 2.55.0.windows.4 |
| npm registry reachability | HEAD `registry.npmjs.org/vite` | 200 |
| Wikipedia API reachability | `en.wikipedia.org/w/api.php` search | 200 (real, keyless research source) |

Because there was no application, the following baseline checks were **not applicable** and are
recorded as such rather than falsely marked passing: dependency install, typecheck, lint, unit tests,
integration tests, production build, startup, API health check.

## 3. Feature inventory

| Area | Status | Notes |
|---|---|---|
| Frontend app | Missing | Greenfield |
| Backend API | Missing | Greenfield |
| Database | Missing | No Mongo URI available |
| Auth | Missing | No identity provider configured |
| AI integration | Missing | No provider key available |
| Evidence graph | Missing | No React Flow install |
| Tests / CI | Missing | No test runner |
| Deployment | Missing | No host, domain, or credentials |
| Brand assets | Missing | No supplied hero component or logo |

## 4. Environment constraints discovered

1. **No secrets.** No `GEMINI_API_KEY`, `OPENAI_API_KEY`, `MONGODB_URI`, or search-provider key.
   Any feature that hard-depends on them would fail at startup or runtime for judges.
2. **Windows + OneDrive workspace.** Avoid long build paths and symlink-heavy tooling.
3. **Network is available.** Live HTTP research is possible.
4. **Public demo deployment is not possible from this machine** without an account/token. Deployment
   will be delivered as verified build artifacts plus Docker/compose configuration, and the final
   report will state clearly that no public URL was verified.

## 5. Risk register

| ID | Risk | Severity | Mitigation | Status |
|---|---|---|---|---|
| R1 | No LLM key → AI claims cannot run | High | Deterministic extraction core; optional Gemini mode; UI discloses active engine | Mitigated |
| R2 | No Mongo Atlas → persistence unavailable | High | SQLite (stdlib) with documented Mongo migration path | Mitigated |
| R3 | Research without paid search API | High | Wikipedia REST/Action API: real, keyless, timestamped, traceable | Mitigated |
| R4 | Wikipedia is tertiary, not authoritative | Medium | Source-type + quality labels; "tertiary" surfaces in report; no automatic truth claims | Mitigated |
| R5 | False "supported" verdicts | Critical | Conservative evidence thresholds; contradictions always surfaced; no LLM as evidence | Mitigated |
| R6 | Screenshot OCR unavailable without vision key | Medium | Explicit 422 with explanation; no silent fake OCR | Documented |
| R7 | SSRF via URL ingestion | Critical | Scheme allow-list, DNS/IP blocklist, redirects off, timeout, byte cap | Mitigated |
| R8 | Fabricated demo evidence | Critical | All evidence comes from live retrieval; sample data is labelled `SAMPLE` and never mixed with live runs | Mitigated |
| R9 | Secret leakage | High | Server-side env only; no keys in bundle; `.env` ignored | Mitigated |
| R10 | Public deployment unverified | Medium | No deployment claimed; handoff includes exact deploy steps | Accepted |

## 6. Proposed sequence (GSD)

M0 audit → M1 spec/design freeze → M2 landing → M3 shell/dashboard → M4 input/extraction →
M5 research/evidence → M6 verification/contradictions → M7 graph/radar → M8 reports →
M9 security/QA → M10 packaging/demo. Detailed acceptance criteria in `ROADMAP.md`.

## 7. Definition of "verified" used in this project

A feature is only marked verified when all three hold: (1) the code path exists, (2) an automated test
or a real browser interaction exercised it, and (3) the result was observed in this session. Otherwise
it is listed as partial or unverified in `HANDOFF.md`.
