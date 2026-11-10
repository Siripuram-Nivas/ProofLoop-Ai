import { Link } from "react-router-dom";
import {
  AlertTriangle,
  Check,
  ChevronDown,
  ExternalLink,
  FileSearch,
  Minus,
  Pencil,
  Trash2,
  X,
} from "lucide-react";
import { useState } from "react";
import { api, ApiError } from "../lib/api";
import { CATEGORY_LABEL, formatDate, truncate, VERDICT_META } from "../lib/format";
import type { Claim, Evidence } from "../lib/types";
import { Badge, Button, InlineAlert, Textarea, VerdictBadge, cn } from "./ui";

function RelationshipBadge({ evidence }: { evidence: Evidence }) {
  if (evidence.relationship === "supports") {
    return <Badge className="border-support/25 bg-[#EDF6F1] text-support" dot="bg-support">Supports</Badge>;
  }
  if (evidence.relationship === "contradicts") {
    return <Badge className="border-contradict/25 bg-[#FBEDEB] text-contradict" dot="bg-contradict">Contradicts</Badge>;
  }
  return <Badge className="border-caution/25 bg-[#FBF4E7] text-caution" dot="bg-caution">Insufficient</Badge>;
}

function EvidenceCard({ evidence }: { evidence: Evidence }) {
  const [expanded, setExpanded] = useState(false);
  const long = evidence.excerpt.length > 320;
  return (
    <li className="rounded-xl border border-line bg-surface/50 p-4">
      <div className="flex flex-wrap items-center gap-2">
        <RelationshipBadge evidence={evidence} />
        <Badge className="border-line bg-white text-ink-soft">{evidence.match_kind.replaceAll("_", " ")}</Badge>
        {evidence.stale ? (
          <Badge className="border-caution/25 bg-[#FBF4E7] text-caution">
            <AlertTriangle className="size-3" aria-hidden />
            Older than 3 years
          </Badge>
        ) : null}
        <span className="ml-auto text-[10px] text-ink-soft">
          Retrieved {formatDate(evidence.retrieved_at)}
        </span>
      </div>
      <blockquote className="mt-3 border-l-2 border-powder pl-3 text-[13px] leading-relaxed text-ink">
        “{expanded || !long ? evidence.excerpt : truncate(evidence.excerpt, 320)}”
      </blockquote>
      {long ? (
        <button
          type="button"
          className="mt-1.5 text-[11px] font-medium text-powder-deep hover:underline"
          onClick={() => setExpanded((value) => !value)}
        >
          {expanded ? "Show less" : "Show full excerpt"}
        </button>
      ) : null}
      <p className="mt-2 text-[12px] leading-relaxed text-ink-soft">{evidence.explanation}</p>
      <div className="mt-2.5 flex flex-wrap items-center gap-x-3 gap-y-1.5 text-[11px]">
        <a
          href={evidence.source_url}
          target="_blank"
          rel="noreferrer noopener"
          className="inline-flex items-center gap-1 font-medium text-powder-deep hover:underline"
        >
          {evidence.source_title}
          <ExternalLink className="size-3" aria-hidden />
        </a>
        <span className="text-ink-soft">{evidence.source_type}</span>
        <span className="text-ink-soft">· {evidence.quality} quality</span>
      </div>
    </li>
  );
}

export function ClaimCard({
  claim,
  jobId,
  onChanged,
  onRerun,
  busy,
  running,
}: {
  claim: Claim;
  jobId: string;
  onChanged: () => void;
  onRerun: () => void;
  busy?: boolean;
  running?: boolean;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(claim.text);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState(true);
  const meta = VERDICT_META[claim.verdict] || VERDICT_META.unverified;

  const save = async () => {
    if (draft.trim().length < 3) {
      setError("Enter at least 3 characters.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await api.updateClaim(jobId, claim.id, draft.trim());
      setEditing(false);
      onChanged();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not update the claim.");
    } finally {
      setSaving(false);
    }
  };

  const remove = async () => {
    if (!window.confirm("Remove this claim and its evidence from the verification?")) return;
    setSaving(true);
    try {
      await api.deleteClaim(jobId, claim.id);
      onChanged();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not delete the claim.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <article className="card overflow-hidden">
      <div className="flex flex-wrap items-start gap-3 p-5">
        <span className={cn("mt-1 size-2.5 shrink-0 rounded-full", meta.dot)} aria-hidden />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <VerdictBadge verdict={claim.verdict} />
            <Badge className="border-line bg-lavender/50 text-ink-soft">
              {CATEGORY_LABEL[claim.category] || claim.category}
            </Badge>
            <span className="font-mono text-[10px] text-ink-soft/60">{claim.id}</span>
            {claim.manual ? (
              <Badge className="border-line bg-white text-ink-soft">Added manually</Badge>
            ) : null}
          </div>

          {editing ? (
            <div className="mt-3 space-y-2">
              <Textarea
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                aria-label="Edit claim text"
                className="min-h-20 text-[14px]"
              />
              {error ? <InlineAlert tone="error">{error}</InlineAlert> : null}
              <div className="flex gap-2">
                <Button size="sm" onClick={() => void save()} loading={saving} icon={Check}>
                  Save claim
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => {
                    setEditing(false);
                    setDraft(claim.text);
                    setError(null);
                  }}
                  icon={X}
                >
                  Cancel
                </Button>
              </div>
            </div>
          ) : (
            <p className="mt-2.5 text-[15px] font-medium leading-relaxed text-ink">{claim.text}</p>
          )}

          {!editing ? (
            <p className="mt-2 text-[12px] leading-relaxed text-ink-soft">{claim.verdict_basis}</p>
          ) : null}

          <div className="mt-3 flex flex-wrap items-center gap-2 text-[11px] text-ink-soft">
            <span
              className="rounded-full border border-line bg-white px-2 py-0.5"
              title="Confidence in the extraction. This is not a probability that the claim is true."
            >
              Extraction confidence {(claim.confidence * 100).toFixed(0)}%
            </span>
            {claim.entities.slice(0, 4).map((entity) => (
              <span key={entity} className="rounded-full bg-lavender/70 px-2 py-0.5 text-ink">
                {entity}
              </span>
            ))}
            {claim.numbers.slice(0, 3).map((number) => (
              <span key={`n-${number}`} className="rounded-full bg-lavender/70 px-2 py-0.5 tabular-nums text-ink">
                {number.toLocaleString()}
              </span>
            ))}
            {claim.dates.slice(0, 2).map((date) => (
              <span key={`d-${date}`} className="rounded-full bg-lavender/70 px-2 py-0.5 text-ink">
                {date}
              </span>
            ))}
          </div>

          {error && !editing ? <InlineAlert tone="error" className="mt-3">{error}</InlineAlert> : null}
        </div>

        <div className="flex shrink-0 items-center gap-1">
          <button
            type="button"
            onClick={() => {
              setEditing(true);
              setDraft(claim.text);
            }}
            className="grid size-8 place-items-center rounded-lg text-ink-soft hover:bg-lavender"
            aria-label={`Edit claim ${claim.id}`}
            title="Edit claim"
          >
            <Pencil className="size-3.5" aria-hidden />
          </button>
          <button
            type="button"
            onClick={() => void remove()}
            className="grid size-8 place-items-center rounded-lg text-ink-soft hover:bg-[#FBEDEB] hover:text-contradict"
            aria-label={`Delete claim ${claim.id}`}
            title="Delete claim"
            disabled={saving}
          >
            <Trash2 className="size-3.5" aria-hidden />
          </button>
        </div>
      </div>

      <div className="border-t border-line bg-surface/40 px-5 py-3">
        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={() => setOpen((value) => !value)}
            className="inline-flex items-center gap-1.5 text-[12px] font-medium text-ink"
            aria-expanded={open}
          >
            <FileSearch className="size-3.5" aria-hidden />
            {claim.evidence.length === 0
              ? running
                ? "Research pending"
                : "No evidence recorded"
              : `${claim.evidence.length} evidence excerpt${claim.evidence.length === 1 ? "" : "s"}`}
            <ChevronDown className={cn("size-3.5 transition-transform", open && "rotate-180")} aria-hidden />
          </button>
          <span className="text-[11px] text-ink-soft">
            {claim.research_failed ? "Research failed for this claim" : null}
          </span>
          <Button size="sm" variant="ghost" className="ml-auto" onClick={onRerun} disabled={busy} icon={FileSearch}>
            Re-run research
          </Button>
        </div>
        {open ? (
          claim.evidence.length ? (
            <ul className="mt-3 space-y-3">
              {claim.evidence.map((evidence) => (
                <EvidenceCard key={evidence.id} evidence={evidence} />
              ))}
            </ul>
          ) : (
            <p className="mt-2 flex items-center gap-1.5 text-[12px] text-ink-soft">
              <Minus className="size-3" aria-hidden />
              {running
                ? "Research for this claim has not finished yet. This page updates automatically."
                : "No excerpt cleared the relevance threshold. The claim stays unverified — not false."}
            </p>
          )
        ) : null}
      </div>
    </article>
  );
}

export function ClaimList({
  claims,
  jobId,
  onChanged,
  onRerun,
  busy,
  running,
}: {
  claims: Claim[];
  jobId: string;
  onChanged: () => void;
  onRerun: () => void;
  busy?: boolean;
  running?: boolean;
}) {
  if (claims.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-line bg-white p-8 text-center">
        <p className="text-sm text-ink-soft">No claims in this verification.</p>
        <Link to="/app/new" className="mt-2 inline-block text-[13px] font-medium text-powder-deep hover:underline">
          Start a new verification
        </Link>
      </div>
    );
  }
  return (
    <div className="space-y-4">
      {claims.map((claim) => (
        <ClaimCard
          key={claim.id}
          claim={claim}
          jobId={jobId}
          onChanged={onChanged}
          onRerun={onRerun}
          busy={busy}
          running={running}
        />
      ))}
    </div>
  );
}
