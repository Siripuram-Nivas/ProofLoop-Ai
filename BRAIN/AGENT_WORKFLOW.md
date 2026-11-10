# ProofLoop AI — Agent / Verification Workflow

Six responsibilities are implemented as coordinated pipeline stages sharing one structured record.
They are **not** six independent LLM calls. Only extraction may optionally call an LLM; everything
that produces evidence or verdicts is deterministic and auditable.

```text
Ingest → Claim Extraction → Research → Evidence Extraction
        → Evaluation → Contradiction Analysis → Graph → Report
```

| Responsibility | Implemented by | Output | Can it invent evidence? |
|---|---|---|---|
| Claim Extraction Agent | `services/extraction.py` (+ optional Gemini proposer) | atomic claims with spans, numbers, dates, entities | No — proposals must appear in source text |
| Research Agent | `services/research.py` (Wikipedia API) | sources with URL, timestamps, excerpts | No — every URL/excerpt comes from the API |
| Source Quality Agent | `services/research.py` + `evaluation.py` | source_type, quality, quality_note; stale flag | No — rule-based labels |
| Evidence Extraction / Verification Agent | `services/evaluation.py` | relationship + explanation + verdict | No — token overlap, numeric/date comparison |
| Contradiction Detection Agent | `services/contradictions.py` | genuine numeric/date conflicts | No — derived from stored evidence |
| Report Generation Agent | `services/report.py` | summary, per-claim findings, limitations | No — assembles stored records only |

## Stage contract

Each stage writes `{key,label,status,detail,at}` into `job.stages`. `status` is one of
`pending|active|done|failed`. The UI renders exactly these states; there is no simulated progress bar.
If research fails (network/API), the stage becomes `failed`, affected claims become `inconclusive` or
`unverified`, and the limitation is written into the report.

## Verdict algorithm (v1, deterministic)

For each claim and each candidate excerpt (max 3 per claim):

1. Relevance = overlap of content tokens (stopwords removed) between claim and excerpt.
2. Require ≥ 2 shared content tokens and ≥ 0.30 coverage; otherwise discard the excerpt.
3. Numeric comparison: for each claim number, find excerpt numbers in the same excerpt whose
   magnitude is comparable (0.5×–2×). Relative difference ≤ 1% → numeric support; > 5% → numeric
   contradiction; 1–5% → weakly supports (rounding) and is noted.
4. Year comparison: both contain 4-digit years, same context, difference ≥ 2 → date contradiction.
5. Relationship: contradiction dominates; else numeric match; else strong overlap (≥ 0.6) = supports;
   else `insufficient`.
6. Claim verdict: contradiction + support → `mixed`; contradiction only → `contradicted`;
   ≥ 2 supports (or 1 numeric support) → `supported`; evidence but weak → `insufficient`;
   no evidence → `unverified` (research failure → `inconclusive`).
7. Staleness: `updated_at` older than 3 years marks evidence `stale`; if all support is stale the
   verdict is `outdated`.

## Rules that must never be violated

- A model's own reasoning is never stored as an evidence excerpt.
- A source's authority never implies that a specific passage supports a claim.
- Different numbers across sources are reported as disagreement, not resolved by recency.
- "Unverified" is never rendered as "false".
- Confidence labels state they are extraction confidence, not truth probability.
