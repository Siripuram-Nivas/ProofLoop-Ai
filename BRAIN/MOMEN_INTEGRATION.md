# ProofLoop AI × Momen integration

Additive integration with the existing Momen backend-only project. The local SQLite pipeline is
untouched; Momen is a second backend for real verification jobs. Nothing in Momen was created,
renamed, migrated, synced or deployed as part of this work.

## Actual Momen project

| Field | Value |
| --- | --- |
| Project | `ProofLoop Ai` |
| `projectExId` | `vXL04vkvze2` |
| Type | `BACKEND_ONLY` |
| Schema | `5oEyq7VqjMB` |
| Published | `false` |
| `deployedSchemaExId` | `5oEyq7VqjMB` |
| `hasUndeployedChanges` | `false` |
| Environment | `PRODUCTION` |

Runtime endpoints (no credentials in this document or in the repo):

- GraphQL: `https://villa.momen.app/zero/vXL04vkvze2/api/graphql-v2`
- Subscriptions (discovered, unused): `wss://villa.momen.app/zero/vXL04vkvze2/api/graphql-subscription`

Tables present: `account`, `fz_permission_role`, `fz_account_has_permission_role`, `workspace`,
`verification_job`, `claim`, `source`, `evidence_item`, `contradiction`, `proof_report`,
`audit_log`. Column names and relations were read from the live schema, not assumed.

## Architecture

```text
Browser (React)
  |  /api/v1/momen/*  (HttpOnly session cookie + CSRF header)
  v
FastAPI (existing app)
  |-- local auth (unchanged) decides who may connect a Momen account
  |-- momen/client.py   exact GraphQL contracts + error mapping
  |-- momen/session.py  signed HttpOnly cookie carrying the Momen JWT
  v
Momen Runtime GraphQL (vXL04vkvze2)
  |-- writes: user JWT  -> CreateVerificationJob
  |-- reads : server admin token -> workspace / verification_job (and nested rows)
```

Why two credentials:

- `CreateVerificationJob` runs as the Momen user and resolves the caller from the user JWT; the job is
  attributed to that account, and workspace ownership is enforced inside the action flow.
- The `Logged-in User` role has `select/update` on restricted `account` columns only, **zero grants**
  on `workspace`, `verification_job`, `claim`, `source`, `evidence_item`, `contradiction`,
  `proof_report`, `audit_log`, and is allowed to run `CreateVerificationJob`. `Anonymous User` has no
  table or action-flow grants. So job reads must run server-side with the admin token; ownership is
  then enforced in the query filters with the numeric Momen account ID from the session.

## Authentication design

1. The browser must already have a local ProofLoop session (guests are created automatically).
2. `POST /api/v1/momen/auth/login` receives Momen email + password over TLS and exchanges them for a
   user JWT via `authenticateWithEmail(email, password, register: false)`. Registration is
   deliberately never requested; only existing Momen accounts can connect.
3. The JWT is stored server-side inside the signed cookie `proofloop_momen`:
   - `HttpOnly`, `SameSite=strict`, `Secure` when `PROOFLOOP_ENV=production`,
     `Path=/api/v1/momen`, max 8 h or the JWT expiry if sooner.
   - Payload: local user id (`uid`), numeric Momen account id (`sub`), email, username, Momen JWT,
     `iat`, `exp`; HMAC-SHA256 with a key derived from `PROOFLOOP_SECRET`.
   - Rejected if the signature, expiry, or `uid`/local-user match fails.
4. CSRF: double-submit. `proofloop_csrf` is a readable cookie; mutating requests must echo it in
   `X-CSRF-Token`. Enforced on `POST /momen/verifications` and `POST /momen/auth/logout`.
5. Responses never contain the Momen JWT or password. The JWT is never placed in Vite env vars, the
   bundle, or logs.

Note: the Momen JWT `sub` is a hashid (`ky7r5zezgBZ`), not the numeric account id, so the numeric
`account.id` from `LoginResult` is what the session stores and what read filters use.

## CreateVerificationJob (write path)

| Item | Value |
| --- | --- |
| Action flow | `CreateVerificationJob` |
| Id | `30a013b9-230d-4c3c-86d3-a26d9e5acd1e` |
| GraphQL field | `fz_af_30a013b9_230d_4c3c_86d3_a26d9e5acd1e` |
| Output type | `jsonb` |
| Timeout | 30 s |

Input arguments (all nullable in the schema, validated inside the flow):

| Argument | Type |
| --- | --- |
| `title` | `String` |
| `workspace_id` | `bigint` |
| `input_type` | `String` (`TEXT`, `URL`, `PDF`, `IMAGE`) |
| `original_text` | `String` |
| `original_url` | `String` |
| `uploaded_file_url` | `String` |

Output contract: `{ verification_job_id, status, created_at }`. The backend accepts either a JSON
object or a JSON-encoded string, and fails with `momen_output_missing` if `verification_job_id` is
absent.

Runtime behaviour confirmed with safe, failing calls against the deployed flow:

| Caller mistake | Momen response (excerpt) | Mapped code |
| --- | --- | --- |
| Empty title | `title must not be empty.` | `invalid_input` (422) |
| Missing/zero workspace | `workspace_id must be a positive ID.` | `invalid_input` (422) |
| Bad type/content pairing | `input_type must be TEXT, URL, PDF, or IMAGE, and its matching content field must be non-empty.` | `invalid_input` (422) |
| Whitespace-only `TEXT` | `original_text must contain non-whitespace content when input_type is TEXT.` | `invalid_input` (422) |
| Workspace not owned by caller | `Workspace not found or not owned by the caller.` | `workspace_forbidden` (403) |
| Wrong password | `authenticateWithEmail: Incorrect email or password` | `invalid_credentials` (401) |

The browser sends `original_text` byte-for-byte (trimmed only where the user typed the title). Titles
are trimmed and defaulted from the input by `frontend/src/lib/momen.ts`, which is unit-tested.

## Read services

`MOMEN_ADMIN_TOKEN` is required for any read. Without it the session endpoint still connects but
reports `read_access: false` and an empty workspace list; read routes return 503
`momen_read_unavailable`.

| Data | Query filter |
| --- | --- |
| Workspaces | `owner_id == session account id` |
| Job list | `created_by_id == account id AND workspace.owner_id == account id` |
| Job detail | above `AND id == job id` |

`GET /momen/verifications` returns `items` (summary columns), `total` from
`verification_job_aggregate`, `limit`, `offset`. `GET /momen/verifications/{id}` returns the job plus
nested `claims` (with `evidence_items.source`), `sources`, `contradictions`, `proof_reports`,
`audit_logs`. `GET /momen/verifications/{id}/report` returns the current (highest-version fallback)
`proof_report`, or 404 `report_not_available`.

Cross-account isolation is tested: a foreign job id yields 404, never data.

## HTTP surface

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/v1/momen/auth/login` | Exchange existing Momen credentials, set session |
| POST | `/api/v1/momen/auth/logout` | Clear Momen cookies (CSRF) |
| GET | `/api/v1/momen/session` | Connection/workspace/read-access state |
| GET | `/api/v1/momen/workspaces` | Account-owned workspaces |
| POST | `/api/v1/momen/verifications` | `CreateVerificationJob` (CSRF) |
| GET | `/api/v1/momen/verifications` | Paged job list |
| GET | `/api/v1/momen/verifications/{id}` | Job detail with evidence graph |
| GET | `/api/v1/momen/verifications/{id}/report` | Current proof report |

Every Momen response includes `persistence_available: false` until `PersistVerificationPackage` is
certified.

## Files

Backend:

- `backend/app/momen/client.py` — endpoint calls, exact mutations/queries, error classification.
- `backend/app/momen/session.py` — signed cookie, expiry, CSRF dependency.
- `backend/app/momen/__init__.py`
- `backend/app/routers/momen.py` — routes above.
- `backend/app/config.py` — `MOMEN_GRAPHQL_URL`, `MOMEN_SUBSCRIPTION_URL`, `MOMEN_ADMIN_TOKEN`,
  `MOMEN_TIMEOUT_SECONDS`.
- `backend/app/main.py` — router mount + startup log (no secrets logged).
- `backend/.env.example` — placeholders only.

Frontend:

- `frontend/src/lib/api.ts` — Momen types, CSRF header, API methods.
- `frontend/src/lib/momen.ts` — TEXT/URL payload builder.
- `frontend/src/lib/momen.test.ts`
- `frontend/src/pages/NewVerification.tsx` — Momen connect/workspace/send card; the existing local
  verification form is unchanged.
- `frontend/src/components/ui.tsx` — added `Select`.

Tests:

- `backend/tests/test_momen_api.py` — auth, cookie flags, CSRF, create payload, isolation, reads.
- `backend/tests/test_momen_client.py` — MockTransport errors, timeouts, JSONB output, filters.
- `backend/tests/test_momen_session.py` — signing, tampering, expiry.

## Security checklist

- No Momen admin token in browser code, Vite env, or the repo; reads happen only server-side.
- Momen JWT lives only in an HttpOnly cookie and server memory; it is never returned or logged.
- CSRF double-submit on mutations; `SameSite=strict`.
- Account/workspace ids never come from the client: the account id comes from the signed session,
  and workspace ownership is enforced twice (action flow + read filters).
- `security.current_user` gates every Momen route; a Momen cookie belonging to another local user is
  rejected (`momen_session_mismatch`).
- Upstream error bodies are truncated before surfacing; unexpected errors map to generic messages.
- Login credentials are never persisted; `register: false` always.
- Error responses keep the app's `{"error":{"code","message"}}` envelope.

## Tests run

```bash
cd backend && .venv\Scripts\python -m pytest -q     # 85 passed
cd frontend && npm test                            # 8 passed
cd frontend && npm run build                       # tsc + vite build OK
```

Build output was grepped for `villa.momen.app`, `graphql-v2`, `MOMEN_ADMIN_TOKEN` and `Bearer` — no
service endpoint or credential appears in the bundle. Only the API path prefix is in browser code.

## Blockers and limitations

1. **No QA Momen user credentials.** Live login and a real `CreateVerificationJob` write were not
   exercised end-to-end; the write path is verified against the real runtime contract and safe
   failing calls only. Supply a QA Momen account before claiming live write success.
2. **`MOMEN_ADMIN_TOKEN` is not present in the local `.env`.** Login works, reads report
   `read_access: false` / 503 until the operator supplies the token. The token was never readable
   through the build tooling.
3. **Result persistence is unavailable.** `PersistVerificationPackage` is deployed but not certified;
   it is intentionally not called. A job created through this integration stays `QUEUED` with no
   claims/sources/evidence written, and reports return `report_not_available`.
4. **PDF/IMAGE submission is blocked.** No Momen file-upload wiring exists for `uploaded_file_url`,
   so the UI only sends `TEXT` and `URL`; the other tabs keep using the local pipeline.
5. **Residual Momen diagnostic.** `Unknown templateCodeId findCurrentUserId in action flow
   CreateVerificationJob` is still reported by the editor, although the flow executes correctly
   (its validation errors fire as expected). Non-blocking but should be confirmed with Momen support.
6. **No deployment.** Neither the app nor Momen was deployed/synced. Docker image and public
   deployment are unverified.

## Deployment and sync status

- Momen schema: unchanged by this integration; `deployedSchemaExId` equals the current schema and
  `hasUndeployedChanges=false`. No `sync_backend`, no deploy, no publish.
- App: local only (`127.0.0.1:8000` API, Vite `5173` with `/api` proxy). No image built, no hosting
  configured.

## Operator runbook

```bash
# backend/.env (never commit)
MOMEN_ADMIN_TOKEN=<server-only admin token>   # required for reads
PROOFLOOP_SECRET=<>=24 random chars>          # signs local + Momen session cookies
```

Then sign in locally, open **New verification → Momen backend**, connect an existing Momen account,
pick a workspace, and send TEXT or URL. Treat created jobs as input-only until persistence ships.
