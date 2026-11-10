import { ExternalLink, Radar, ShieldAlert } from "lucide-react";
import { formatDate } from "../lib/format";
import type { Contradiction, Evidence, VerificationJob } from "../lib/types";
import { Badge, EmptyState } from "./ui";

const KIND_LABEL: Record<string, string> = {
  numeric_mismatch: "Numeric mismatch",
  date_mismatch: "Date mismatch",
  source_disagreement: "Sources disagree",
};

export function ContradictionList({ job }: { job: VerificationJob }) {
  const evidenceById = new Map<string, Evidence>();
  const claimById = new Map<string, string>();
  for (const claim of job.claims) {
    claimById.set(claim.id, claim.text);
    for (const evidence of claim.evidence) {
      evidenceById.set(evidence.id, evidence);
    }
  }

  if (job.contradictions.length === 0) {
    return (
      <EmptyState
        icon={Radar}
        title="No stored conflicts in this verification"
        description="That does not prove the claims are true. It means no conflicting value or date was found in the retrieved excerpts. Unverified claims remain unverified."
      />
    );
  }

  return (
    <div className="space-y-4">
      {job.contradictions.map((contradiction: Contradiction) => (
        <article key={contradiction.id} className="card overflow-hidden">
          <div className="flex flex-wrap items-center gap-2 border-b border-line bg-[#FDF7F4] px-5 py-3">
            <span className="grid size-7 place-items-center rounded-lg bg-[#FBE9E4] text-contradict">
              <ShieldAlert className="size-3.5" aria-hidden />
            </span>
            <span className="text-[13px] font-semibold text-ink">
              {KIND_LABEL[contradiction.kind] || contradiction.kind}
            </span>
            <Badge
              className={
                contradiction.severity === "high"
                  ? "border-contradict/25 bg-[#FBEDEB] text-contradict"
                  : "border-caution/25 bg-[#FBF4E7] text-caution"
              }
            >
              {contradiction.severity} severity
            </Badge>
            <span className="ml-auto font-mono text-[10px] text-ink-soft/60">{contradiction.id}</span>
          </div>
          <div className="p-5">
            <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-soft">
              Claim under review
            </p>
            <p className="mt-1.5 text-[14px] font-medium leading-relaxed text-ink">
              {contradiction.claim_text || claimById.get(contradiction.claim_id) || "Unknown claim"}
            </p>
            <p className="mt-3 rounded-xl border border-line bg-surface/60 p-3.5 text-[13px] leading-relaxed text-ink-soft">
              {contradiction.summary}
            </p>
            <div className="mt-4 grid gap-3 md:grid-cols-2">
              {contradiction.evidence_ids.map((evidenceId) => {
                const evidence = evidenceById.get(evidenceId);
                if (!evidence) return null;
                return (
                  <div key={evidenceId} className="rounded-xl border border-line bg-white p-4">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge
                        className={
                          evidence.relationship === "contradicts"
                            ? "border-contradict/25 bg-[#FBEDEB] text-contradict"
                            : "border-support/25 bg-[#EDF6F1] text-support"
                        }
                      >
                        {evidence.relationship}
                      </Badge>
                      <span className="text-[10px] text-ink-soft">{evidence.match_kind.replaceAll("_", " ")}</span>
                    </div>
                    <blockquote className="mt-2.5 border-l-2 border-powder pl-3 text-[12px] leading-relaxed text-ink">
                      “{evidence.excerpt}”
                    </blockquote>
                    <p className="mt-2 text-[11px] leading-relaxed text-ink-soft">{evidence.explanation}</p>
                    <a
                      href={evidence.source_url}
                      target="_blank"
                      rel="noreferrer noopener"
                      className="mt-2 inline-flex items-center gap-1 text-[11px] font-medium text-powder-deep hover:underline"
                    >
                      {evidence.source_title}
                      <ExternalLink className="size-3" aria-hidden />
                    </a>
                    <p className="mt-1 text-[10px] text-ink-soft">
                      Retrieved {formatDate(evidence.retrieved_at)}
                      {evidence.source_updated_at ? ` · source updated ${formatDate(evidence.source_updated_at)}` : ""}
                    </p>
                  </div>
                );
              })}
            </div>
            <p className="mt-4 text-[11px] italic leading-relaxed text-ink-soft">
              ProofLoop does not decide which source is correct. Check reporting dates, definitions, and
              the primary source before acting on either value.
            </p>
          </div>
        </article>
      ))}
    </div>
  );
}
