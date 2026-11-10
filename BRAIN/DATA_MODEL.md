# ProofLoop AI — Data Model

Persistence boundary: `backend/app/db.py` (SQLite, WAL). Every verification is stored as one JSON
document so the report always renders the evidence snapshot from the moment of verification.

## Tables

### users
| column | type | notes |
|---|---|---|
| id | TEXT PK | `usr_<uuid>` |
| email | TEXT UNIQUE NULL | null for guests |
| password_hash | TEXT NULL | `scrypt$n$r$p$salt$hash` (stdlib) |
| is_guest | INTEGER | 1/0 |
| created_at | TEXT | ISO-8601 UTC |

Index: `users(email)`.

### uploads
| column | type | notes |
|---|---|---|
| id | TEXT PK | `upl_<uuid>` |
| user_id | TEXT | owner; FK semantics enforced in code |
| filename | TEXT | sanitised display name |
| kind | TEXT | `pdf`, `text`, `image` |
| extracted_text | TEXT | never exceeds 120k chars |
| created_at | TEXT | ISO-8601 UTC |

Index: `uploads(user_id, created_at)`.

### verifications
| column | type | notes |
|---|---|---|
| id | TEXT PK | `ver_<uuid>` |
| user_id | TEXT | owner, always filtered in queries |
| title | TEXT | derived from input if omitted |
| status | TEXT | list filter |
| created_at | TEXT | ISO-8601 |
| updated_at | TEXT | ISO-8601 |
| data | TEXT | full job JSON (claims, sources, evidence, contradictions, report, stages) |

Indexes: `verifications(user_id, created_at DESC)`, `verifications(user_id, status)`.

## Logical entities inside the JSON snapshot

- **VerificationJob** → claims[], sources[], contradictions[], stages[], report.
- **Claim** → id, text, original_span, category, entities, numbers, dates, confidence, verdict.
- **Source** → id, title, url, publisher, source_type, updated_at, retrieved_at, quality.
- **Evidence** → id, source_id, excerpt, relationship, explanation, matched_terms, retrieved_at, stale.
- **Contradiction** → id, claim_id, kind, severity, summary, evidence_ids.
- **Report** → generated_at, summary counts, per-claim findings, limitations, source index.

Stable IDs are generated once with prefixes and never reused. Deleting a claim removes its evidence
and contradictions from the job; re-running a verification replaces evidence but keeps the original
input and claim identity.

## Retention

Uploads and verifications are retained until the user deletes them (`DELETE` is not exposed in the
MVP UI; documented limitation). The SQLite file is the only copy; backups are file copies.

## MongoDB migration path

Replace `db.py` with a Mongo repository exposing the same functions. Collections map 1:1:
`users`, `uploads`, and `verifications` (with the JSON document as the document body). Add indexes on
`verifications.user_id + created_at` and `uploads.user_id + created_at`. The rest of the codebase is
unaware of the storage engine.
