# ProofLoop AI — multi-engine AI layer

Additive integration of three provider capabilities into the existing application:

| Capability | Provider | SDK |
| --- | --- | --- |
| Structured reasoning, extraction, review | OpenAI Responses API | `openai==3.50.0` |
| Independent analysis and review | Google Gemini | `google-genai==3.3.0` |
| Source discovery and citations | Google Search via Gemini grounding | `google-genai==3.3.0` |

Nothing in the deterministic pipeline, the SQLite store, the frontend routes, or the Momen
integration was replaced. AI stages attach analysis to a job; they never write verdicts, never
write evidence, and never touch Momen.

## Provider architecture

```text
backend/app/engines/
  base.py                 SDK probing, availability records, usage payloads, bounded retries
  errors.py               EngineError + typed provider failures (refusal, safety, timeout, rate limit)
  schemas.py              Pydantic contracts sent as JSON Schema / response_schema
  openai_engine.py        Responses API + Structured Outputs
  gemini_engine.py        google-genai generate_content + response_schema
  google_search_engine.py Gemini Google Search grounding -> citations -> safe excerpt retrieval
  registry.py             construction, availability, per-job selection, live test entry point
```

`base.py` and `errors.py` hold the only shared machinery: correlation IDs, token/cost metadata,
and `call_with_retries`, which retries **only** failures the provider marks retryable, with a
capped exponential backoff (`0.5s`, `1s`, `2s`, ... bounded by `PROOFLOOP_AI_MAX_RETRIES`).

All SDK imports are lazy (`import openai` / `from google import genai` inside the call path, and
`importlib.util.find_spec` for availability). A missing package therefore produces a
`sdk_missing` availability state instead of an import crash at boot.

## API configuration

Read from `backend/.env` only. No `VITE_` secret exists, and the browser bundle is checked for
provider keys and endpoints during the build review.

| Variable | Meaning |
| --- | --- |
| `PROOFLOOP_AI_LIVE_CALLS_ENABLED` | Master gate. Default `false`. When false every engine is unavailable and every call raises `live_calls_disabled`. |
| `OPENAI_API_KEY` | Server-side key. Never returned by an API. |
| `OPENAI_MODEL` | No default on purpose. Unset means "not configured", not "guess a model". |
| `GEMINI_API_KEY` | Used by both the Gemini engine and Search grounding. |
| `GEMINI_MODEL` | Default generation model. |
| `GEMINI_SEARCH_MODEL` | Optional; falls back to `GEMINI_MODEL`. |
| `GOOGLE_SEARCH_ENABLED` | Default `false`. Grounding is opt-in. |
| `PROOFLOOP_CLAIM_ENGINE` | `deterministic` \| `openai` \| `gemini` (empty = deterministic). |
| `PROOFLOOP_RESEARCH_ENGINE` | `wikipedia` \| `google_search` (empty = `PROOFLOOP_RESEARCH`). |
| `PROOFLOOP_ANALYSIS_ENGINE` | empty \| `openai` \| `gemini`. |
| `PROOFLOOP_REVIEW_ENGINE` | empty \| `openai` \| `gemini`. |
| `PROOFLOOP_SECOND_REVIEW_ENGINE` | empty \| `openai` \| `gemini`. |
| `PROOFLOOP_AI_TIMEOUT_SECONDS` | Per provider request timeout (default 20). |
| `PROOFLOOP_SEARCH_TIMEOUT_SECONDS` | Search grounding timeout (default 25). |
| `PROOFLOOP_AI_MAX_RETRIES` | Retry budget, never unbounded (default 2). |
| `PROOFLOOP_AI_MAX_INPUT_CHARS` | Prompt trimming cap (default 12000). |
| `PROOFLOOP_AI_MAX_OUTPUT_TOKENS` | Output cap (default 1200). |
| `AI_AUTO_FALLBACK_ENABLED` | Default `true`. `false` restricts execution to the first configured provider. |
| `AI_PROVIDER_ORDER` | Priority list, default `openai,gemini`. Comma-separated; unknown names are ignored. |
| `AI_FALLBACK_MAX_ATTEMPTS` | Attempts per request (default 2, minimum 1). This is the loop bound. |
| `AI_PROVIDER_COOLDOWN_SECONDS` | Cooldown after quota/auth/permission failure (default 300). |
| `PROOFLOOP_LIVE_SMOKE_AUTHORIZED` | Test-only opt-in for the live smoke suite. |

## Engine responsibilities

**OpenAIEngine** — claim extraction, per-claim evidence analysis, independent review. Uses the
Responses API with `text.format = {type: "json_schema", strict: true}`, `store: false`. Temperature
is not sent: the configured `gpt-6-luna` rejects that parameter. Refusals, `status: incomplete`,
empty output and schema violations are mapped to explicit errors rather than partial objects.

**GeminiEngine** — the same three capabilities through `client.models.generate_content` with
`response_mime_type="application/json"` and `response_schema=<Pydantic model>`. Safety blocks are
detected from `prompt_feedback.block_reason` and `finish_reason` in
`{SAFETY, BLOCKLIST, PROHIBITED_CONTENT, SPII, RECITATION}`. Parsed objects are preserved when the
SDK returns them; otherwise the JSON text is validated against the same schema.

**GoogleSearchEngine** — grounding discovery only. It accepts a claim, runs Gemini with
`tools=[types.Tool(google_search=types.GoogleSearch())]`, and returns candidate sources. It never
decides truth.

Both LLM engines filter returned notes against the URLs the pipeline actually retrieved, so a model
cannot introduce an unsupported source. The Gemini engine replaced the previous hand-rolled REST
extraction client, so there is one Gemini client in the codebase.

## Google Search grounding

From `grounding_metadata` the engine preserves:

- `web_search_queries` — the queries Google actually executed.
- `grounding_chunks[].web.{uri,title,domain}` — the citation set.
- `grounding_supports` count and `search_entry_point.rendered_content` (trimmed) — attribution
  markup, kept but not rendered as evidence.

URLs are normalised (scheme/host lowercased, fragment dropped, trailing slash trimmed, default
ports removed), validated as `http(s)` with a hostname and no embedded credentials, and deduplicated
in first-seen order. Invalid or non-string URIs increment `invalid_sources` and are never emitted.

Discovery time is stamped once per search (`retrieved_at`). Each source carries
`provenance = {discovery: "gemini_google_search_grounding", chunk_index, queries}` and
`locator = grounding_chunk:<n>` unless the retrieval step supplies a better one.

Snippets are never used as excerpts. For each discovered source the engine calls
`research.excerpt_from_url`, which reuses the ingest fetch path (public-host validation, size and
timeout caps) and returns the passage whose tokens best match the claim. A source that could not be
fetched stays in the list with `accessible: false`, `excerpt: null`, and a `note` explaining why —
clearly marked as unverified rather than silently dropped.

## Pydantic schemas

`backend/app/engines/schemas.py` holds the provider contracts, deliberately free of JSON Schema
features the providers reject:

| Model | Purpose |
| --- | --- |
| `ExtractedClaim` / `ClaimExtraction` | atomic claims with category and confidence (max 8) |
| `EvidenceNote` / `EvidenceAnalysis` | per-source stance, relevance, rationale (max 12) |
| `ClaimReview` | `recommended_verdict`, confidence, concerns, reasoning |
| `SearchSource` / `SearchDiscovery` | citation metadata, accessibility, provenance, usage |

Stances are limited to `supports` / `contradicts` / `insufficient`; recommended verdicts to
`supported` / `contradicted` / `mixed` / `insufficient` / `unverified`. Confidence is bounded
`[0,1]` and stored as model opinion, never as a pipeline verdict.

## Pipeline wiring

The deterministic stages are unchanged. `pipeline.run_pipeline` now:

1. Resolves per-job engine selection (`job["engines"]`) over server defaults, rejecting unknown
   identifiers with `invalid_engine_selection` instead of substituting another provider.
2. Extraction — `deterministic` (default), or an explicitly selected engine. Engine claims must
   appear in the normalised source text, otherwise they are discarded; no grounded claim means the
   stage fails loudly.
3. Research — `wikipedia` (default) or `google_search`. Grounding candidates go through the same
   evidence extraction as Wikipedia sources; sources with no readable excerpt cannot support a
   claim.
4. Evaluation and contradiction detection — unchanged, deterministic.
5. `services/ai_stages.apply_ai_stages` — optional analysis, review, and second review. Failures are
   recorded per section (`error: {code, message}`) and a failing provider is skipped for the rest
   of the job rather than retried per claim. The stage is wrapped so an unexpected AI exception can
   never fail the run.

AI output is attached as `ai_analysis`, `independent_review`, `second_review` on claims and mirrored
into the report. `job["ai"]` carries availability, per-section counters, `agreements`, and any
error; `job["ai_usage"]` carries one record per call; `job["ai_usage_total"]` aggregates request and
token counts.

Deterministic verdicts are computed before any AI stage and never mutated. `report.py` adds
`engine`, `ai`, `ai_usage`, `ai_usage_total`, `research_provenance`, and a limitation stating that
model output is a recommendation and that agreement between models is not independent
verification. Model confidence is never averaged into the verdict.

## Source provenance

Every evidence item keeps its URL, title, publisher, publication date (when the source supplies
one), retrieval timestamp, exact retrieved excerpt, locator, stance, and provenance. Reading a job or
report returns only what is stored — no re-fetch, no regeneration.

## Usage and cost monitoring

Each call records `provider`, `model`, provider `request_id`, internal `correlation_id`,
`input_tokens`, `output_tokens`, `total_tokens`, `latency_ms`, and `at`. Token counts come from the
providers' usage objects where present and are `null` otherwise. Cost is derivable from token counts
and the operator's price list; no prices are hardcoded. `GET /api/v1/engines` exposes
`max_retries`, input/output caps and the live-call gate for operational checks.

## Error handling

| Code | Meaning | Retryable |
| --- | --- | --- |
| `provider_timeout` | no response within the timeout | yes |
| `provider_rate_limited` | HTTP 429 / `ResourceExhausted` (per-minute throttling) | yes |
| `provider_quota_exhausted` | 429 with an account-level quota/credit message | no |
| `provider_unavailable` | 5xx / connection failure | yes |
| `provider_refusal` | OpenAI refusal | no |
| `provider_safety_block` | Gemini safety stop | no |
| `provider_invalid_output` | unparseable or schema-invalid output, incomplete response | no |
| `provider_rejected` | 400/401/403/404 — wrong key or model | no |
| `live_calls_disabled` | master gate off | no |
| `search_disabled` | `GOOGLE_SEARCH_ENABLED=false` | no |
| `missing_api_key`, `missing_model`, `sdk_missing` | unavailable configuration | no |
| `provider_auth_failed` | 401 / `Unauthenticated` — credentials rejected | no |
| `provider_permission_denied` | 403 / `PermissionDenied` | no |
| `provider_model_not_found` | 404 / `model_not_found` | no |
| `provider_invalid_request` | 400 / `InvalidArgument` — the request itself is wrong | no |
| `provider_connection_failed` | the provider could not be reached | yes |
| `no_providers_configured` | no provider has both a key and a model | no |
| `providers_cooling_down` | every configured provider is inside a cooldown | no |
| `all_providers_failed` | every eligible provider was tried and failed | no |

`resolve(name)` raises when the requested provider is unavailable. There is no silent downgrade.

## Readiness states

`GET /api/v1/engines` returns `available` (can be called right now) plus a `state` that says why:

| `state` | Meaning |
| --- | --- |
| `available` | Configuration valid, live calls on, and a call has already succeeded. |
| `configured` | Configuration valid and selectable, but no successful call has been recorded yet. |
| `disabled` | `PROOFLOOP_AI_LIVE_CALLS_ENABLED=false`. Not an error — the switch is off. |
| `missing_api_key` / `missing_model` | The provider cannot be called and says exactly what is missing. |
| `sdk_missing` | The provider SDK is not installed in the environment. |
| `search_disabled` | `GOOGLE_SEARCH_ENABLED=false`. |
| `quota_exhausted` | A billing/quota failure put the provider in cooldown; `detail` carries the countdown. |
| `temporarily_unavailable` | A non-quota failure put the provider in cooldown. |

`available` is not set merely because a variable exists: the key, the model, the SDK, the live gate
and the cooldown must all agree. Keys are never validated by format guessing — the provider itself
answers on the first real call, which is what moves `configured` to `available`. `backend/.env` is
read once at process start, so a changed gate or key needs a backend restart.

Google Search grounding is ready when the search switch is on, a Gemini key exists and a search
model is set. Whether that model accepts the `google_search` tool can only be proven by a call;
if it does not, the call fails as a categorized error and Wikipedia research still runs.

## Automatic provider failover

`app/engines/router.py` is the only place that decides which provider runs a generation stage.
`registry.get_engine` builds providers; the router owns selection, attempt bounding and cooldowns.
Classification lives in `app/engines/classify.py`, health state in `app/engines/health.py`.

Each provider exception carries a stable `category` (`quota_exhausted`, `rate_limited`, `temporary`,
`connection`, `auth`, `permission`, `invalid_model`, `invalid_request`, `refusal`, `safety`,
`invalid_output`, `timeout`, `disabled`, `unavailable`). The router switches only for
`quota_exhausted`, `rate_limited`, `temporary`, `connection` and `unavailable`; every other category
stops the chain, because another provider would receive the same bad request.

- Default order: `openai,gemini`; `AI_PROVIDER_ORDER=gemini,openai` reverses it.
- `AI_FALLBACK_MAX_ATTEMPTS` bounds attempts per request (default 2, i.e. no loops).
- `AI_AUTO_FALLBACK_ENABLED=false` restricts execution to the first configured provider.
- Unconfigured providers are filtered before any call, so a missing key is never a 401.
- `AI_PROVIDER_COOLDOWN_SECONDS` (default 300) applies only to `quota_exhausted`, `auth` and
  `permission`; other failures increment a counter without hiding the provider. Expiry (not a probe
  request) is what makes a provider eligible again, so no extra paid call is made to test recovery.
- A timeout is ambiguous: it marks `outcome_unknown`, is never replayed on the second provider, and
  the pipeline records that the request may already have been billed.
- Inside one provider, `call_with_retries` retries only `retryable` errors, honours `Retry-After`
  (capped at 10s), and adds up to 20% jitter over exponential backoff.
- `google_search` resolves to itself only. Grounding can never be served by a text model, and a
  grounding failure is recorded as `research_provenance[].unavailable` rather than a downgrade.
- Usage objects come from the provider that actually answered; `job.ai.provider` is that provider,
  not the requested one.

Health data is process-local by design (single API process). It tracks availability, last success,
last quota failure, last error category, cooldown expiry and failure count. It never claims to know
a remaining credit balance, because neither API reports one.

Sanitized events (`selected`, `started`, `succeeded`, `<category>`, `switched`) are kept in a
200-entry ring buffer with stage/provider/outcome/code only. Job snapshots carry the same fields in
`ai.events`, plus human-readable `ai.notices` such as
`OpenAI quota exhausted. Switched to Gemini.`

## Frontend

`Settings` gained an "AI engines" card: per-provider state (`Ready` / `Configured` /
`Not configured`), selected model, the availability reason, and a connection test button that is
only enabled when the engine is ready. Tests send `confirm: true` explicitly; the API rejects
unconfirmed tests with `confirmation_required`.

`NewVerification` gained per-run selectors for claim extraction, research, analysis, and independent
review. Providers that are not available are rendered disabled with an "(unavailable)" label, so the
UI cannot request an engine the server would refuse.

`VerificationDetail` shows `Powered by OpenAI|Gemini` from `job.ai.provider` (the provider that
actually answered), one line per failover notice, and an "All configured AI providers are currently
unavailable" note when every attempt failed. `Settings` shows the configured priority, the attempt
cap, the cooldown, and a live cooldown countdown per provider. No key, header or document text is
sent to the browser.

## Testing

`backend/tests/test_engines.py` (26 tests, all fully mocked — zero provider calls):

- OpenAI: structured success, strict-schema shape, refusal, timeout with backoff, bounded
  rate-limit retries, quota exhaustion not retried, incomplete response, missing key, unapproved
  source URLs dropped.
- Gemini: structured success, safety block, timeout, quota exhaustion not retried, parsed-object
  preservation.
- Google Search: multiple citations with duplicate removal, missing annotations, invalid URL
  counting, exact excerpt preservation plus unreadable-source state.
- Registry: availability, no silent fallback, live-call gate, per-job selection and rejection.
- Pipeline: cross-provider disagreement, failure recorded without crash, deterministic verdict
  unchanged, report limitation text.
- API: status endpoint leaks no secrets, test requires confirmation, disabled live calls produce
  `openai_live_calls_disabled`.

`backend/tests/test_live_smoke.py` holds one opt-in smoke test per provider. It skips unless
`PROOFLOOP_LIVE_SMOKE_AUTHORIZED=true`, `PROOFLOOP_AI_LIVE_CALLS_ENABLED=true`, and the engine is
available. `backend/scripts/live_smoke.py` is the one-shot controlled runner: one request per
provider, `max_retries=0`, no database or job writes.

`backend/tests/test_provider_router.py` (22 mocked tests, no provider call): primary success without
touching the fallback, quota fallback in both directions, both exhausted, rate-limit fallback,
Gemini quota vs plain 429 classification, OpenAI quota code variants, invalid key, invalid request,
invalid output, both unconfigured, fallback disabled, cooldown skip, recovery after cooldown,
bounded attempts, reverse priority, timeout marked unknown without replay, grounding never routed to
OpenAI, no key in status/errors, and the exact switch notice text.

Results at hand-off: `141 passed, 3 skipped` (backend), `8 passed` (frontend), production build
clean. `backend/tests/conftest.py` pins `PROOFLOOP_AI_LIVE_CALLS_ENABLED=false` before the app cfg
loads, so a local `.env` with live calls on can never spend credits during tests.

## Live verification log (2026-11-13)

Credentials were supplied for `gpt-6-luna` and `gemini-3.8-flash`; both models were confirmed to
exist through zero-token metadata lookups. Live calls were authorized for one request per provider
and the gate was restored to `PROOFLOOP_AI_LIVE_CALLS_ENABLED=false` afterwards.

| Provider | Result | Cause |
| --- | --- | --- |
| OpenAI | `provider_quota_exhausted` (429) | `insufficient_quota` / `credit_balance_exhausted` — the organization has no credits. |
| Gemini | `provider_unavailable` (503, twice) | `UNAVAILABLE: This model is currently experiencing high demand.` |
| Google Search | `provider_quota_exhausted` (429) | `RESOURCE_EXHAUSTED` — Gemini API quota exhausted for the key. |

Two defects were found and fixed by this run, both covered by tests:

1. Pydantic schemas were sent to OpenAI without `additionalProperties: false`, with optional
   properties and `default` values, which strict Structured Outputs rejects. `strict_schema()` now
   closes every object and makes every property required.
2. `temperature` was sent to a model that does not support it. It is now omitted.

No structured response was produced by any provider, so response validation against real output is
still unproven. Neither failure is a code defect: they are account quota and provider availability.


## Known limitations

1. **No successful live response yet.** The live run was blocked by account quota (OpenAI, Gemini
   Search) and a transient 503 (Gemini generation). Structured-output handling is still verified only
   against SDK signatures and mocked responses. Re-run `scripts/live_smoke.py` once billing and
   quota are in place.
2. **Search grounding model support is unverified.** Which models accept the `google_search` tool
   depends on the account tier. If the configured `GEMINI_SEARCH_MODEL` does not support grounding
   the call fails with `provider_rejected` — it does not silently fall back to another model.
3. **Model-specific parameters vary.** `temperature` was rejected by `gpt-6-luna`, so the OpenAI
   engine omits it; the Gemini engine still sends it and may need the same treatment on some models.
4. **Grounding yields discovery, not evidence.** Only pages that can be fetched and matched produce
   an excerpt; the rest stay visible as inaccessible sources.
5. **Excerpt matching is token overlap**, inherited from the existing research service. It selects a
   passage, it does not prove the passage is sufficient context.
6. **No cost accounting.** Token usage is recorded; currency estimates are left to the operator.
7. **Gemini and OpenAI share the same prompt contracts** but run independently. Two models agreeing
   is still not independent factual verification, and the report says so.
8. **Per-job second review is API/env only.** The frontend exposes extraction, research, analysis,
   and review; `second_review` is configurable through `PROOFLOOP_SECOND_REVIEW_ENGINE` or the API
   body.
9. **Prompt text is trimmed, not summarised.** Very long inputs are cut at
   `PROOFLOOP_AI_MAX_INPUT_CHARS`; extraction still only accepts claims present in the full source
   text.
