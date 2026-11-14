import { useEffect, useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import {
  ArrowLeft,
  Bot,
  ChevronDown,
  ExternalLink,
  FileSearch,
  FileText,
  Loader2,
  Network,
  Plus,
  Radar,
  RefreshCw,
  ShieldAlert,
  TriangleAlert,
} from "lucide-react";
import { api, ApiError } from "../lib/api";
import type { AiInfo, GraphData, Report, VerificationJob } from "../lib/types";
import { isActiveStatus, JOB_STATUS_LABEL, inputKindLabel, relativeTime } from "../lib/format";
import { StageTimeline } from "../components/StageTimeline";
import { ClaimList } from "../components/ClaimCard";
import { EvidenceGraph, type SelectedNode } from "../components/EvidenceGraph";
import { GraphInspector } from "../components/GraphInspector";
import { ContradictionList } from "../components/ContradictionList";
import { ProofReport } from "../components/ProofReport";
import { Button, Card, EmptyState, InlineAlert, Skeleton, Textarea, VerdictBadge, cn } from "../components/ui";

type Tab = "claims" | "graph" | "radar" | "report";

const TABS: { id: Tab; label: string; icon: typeof FileText }[] = [
  { id: "claims", label: "Claims & evidence", icon: FileSearch },
  { id: "graph", label: "Evidence graph", icon: Network },
  { id: "radar", label: "Contradiction radar", icon: Radar },
  { id: "report", label: "Proof report", icon: FileText },
];

const PROVIDER_LABEL: Record<string, string> = {
  openai: "OpenAI",
  gemini: "Gemini",
  google_search: "Google Search",
};

const AI_UNAVAILABLE_CODES = new Set([
  "all_providers_failed",
  "no_providers_configured",
  "providers_cooling_down",
]);

function aiUnavailable(ai: AiInfo): boolean {
  if (ai.provider) return false;
  return [ai.analysis, ai.review, ai.second_review].some(
    (section) => section?.error && AI_UNAVAILABLE_CODES.has(section.error.code),
  );
}

export function VerificationDetail() {
  const { id = "" } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const tab = (searchParams.get("tab") as Tab) || "claims";
  const [job, setJob] = useState<VerificationJob | null>(null);
  const [graph, setGraph] = useState<GraphData | null>(null);
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshKey, setRefreshKey] = useState(0);
  const [rerunning, setRerunning] = useState(false);
  const [selected, setSelected] = useState<SelectedNode | null>(null);
  const [showInput, setShowInput] = useState(false);
  const [adding, setAdding] = useState(false);
  const [newClaim, setNewClaim] = useState("");
  const [savingClaim, setSavingClaim] = useState(false);

  useEffect(() => {
    let active = true;
    let timer: number | undefined;

    const load = async () => {
      try {
        const data = await api.getVerification(id);
        if (!active) return;
        setJob(data);
        setError(null);
        setLoading(false);
        if (isActiveStatus(data.status)) {
          timer = window.setTimeout(load, 1200);
        }
      } catch (err) {
        if (!active) return;
        setError(err instanceof ApiError ? err.message : "Could not load this verification.");
        setLoading(false);
      }
    };

    setLoading(true);
    void load();
    return () => {
      active = false;
      if (timer) window.clearTimeout(timer);
    };
  }, [id, refreshKey]);

  useEffect(() => {
    if (!job || tab !== "graph") return;
    let active = true;
    api
      .graph(job.id)
      .then((data) => {
        if (active) setGraph(data);
      })
      .catch((err) => {
        if (active) setError(err instanceof ApiError ? err.message : "Could not load the evidence graph.");
      });
    return () => {
      active = false;
    };
  }, [job, tab]);

  useEffect(() => {
    if (!job || tab !== "report" || job.status !== "completed") return;
    let active = true;
    api
      .report(job.id)
      .then((data) => {
        if (active) setReport(data);
      })
      .catch((err) => {
        if (active) setError(err instanceof ApiError ? err.message : "Could not load the proof report.");
      });
    return () => {
      active = false;
    };
  }, [job, tab]);

  const refresh = () => {
    setRefreshKey((value) => value + 1);
    setGraph(null);
    setReport(null);
  };

  const rerun = async () => {
    if (!job || rerunning) return;
    setRerunning(true);
    try {
      await api.rerun(job.id);
      setGraph(null);
      setReport(null);
      setRefreshKey((value) => value + 1);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not re-run the verification.");
    } finally {
      setRerunning(false);
    }
  };

  const addClaim = async () => {
    if (!job || newClaim.trim().length < 3) return;
    setSavingClaim(true);
    try {
      await api.addClaim(job.id, newClaim.trim());
      setNewClaim("");
      setAdding(false);
      refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not add the claim.");
    } finally {
      setSavingClaim(false);
    }
  };

  const active = job ? isActiveStatus(job.status) : false;
  const counts = useMemo(() => {
    if (!job) return { claims: 0, conflicts: 0, sources: 0 };
    return {
      claims: job.claims.length,
      conflicts: job.contradictions.length,
      sources: job.sources.length,
    };
  }, [job]);

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-40" />
        <Skeleton className="h-14 w-full" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (error && !job) {
    return (
      <div className="space-y-4">
        <Link to="/app/history" className="inline-flex items-center gap-1.5 text-[12px] font-medium text-ink-soft hover:text-ink">
          <ArrowLeft className="size-3.5" aria-hidden />
          Back to history
        </Link>
        <InlineAlert tone="error">{error}</InlineAlert>
      </div>
    );
  }

  if (!job) return null;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-2 text-[11px] text-ink-soft">
        <Link to="/app/history" className="inline-flex items-center gap-1 font-medium hover:text-ink">
          <ArrowLeft className="size-3.5" aria-hidden />
          History
        </Link>
        <span>/</span>
        <span className="font-mono">{job.id}</span>
      </div>

      <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-start">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={cn(
                "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[10px] font-semibold",
                job.status === "completed" && "border-support/25 bg-[#EDF6F1] text-support",
                job.status === "failed" && "border-contradict/25 bg-[#FBEDEB] text-contradict",
                active && "border-powder/40 bg-[#F1F8FE] text-powder-deep",
              )}
            >
              {active ? <Loader2 className="size-3 animate-spin" aria-hidden /> : null}
              {JOB_STATUS_LABEL[job.status] || job.status}
            </span>
            <span className="text-[11px] text-ink-soft">
              {inputKindLabel(job.input_kind)} · created {relativeTime(job.created_at)} · updated{" "}
              {relativeTime(job.updated_at)}
            </span>
          </div>
          <h1 className="mt-2.5 max-w-3xl text-2xl font-semibold leading-tight tracking-[-0.02em] text-ink md:text-3xl">
            {job.title}
          </h1>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {job.claims.map((claim) => (
              <VerdictBadge key={claim.id} verdict={claim.verdict} />
            ))}
          </div>
        </div>
        <div className="flex shrink-0 flex-wrap gap-2">
          <Button size="sm" variant="secondary" icon={RefreshCw} onClick={() => void rerun()} loading={rerunning} disabled={active}>
            {job.status === "failed" ? "Retry verification" : "Re-run research"}
          </Button>
          <Button size="sm" variant="secondary" icon={FileText} onClick={() => setSearchParams({ tab: "report" })}>
            Report
          </Button>
        </div>
      </div>

      <Card className="p-4">
        <StageTimeline stages={job.stages} />
        {job.ai ? (
          <div className="mt-3 space-y-1.5 border-t border-line pt-3" aria-live="polite">
            {job.ai.provider ? (
              <p className="flex items-center gap-2 text-[11px] font-medium text-ink">
                <Bot className="size-3.5 shrink-0 text-ink-soft" aria-hidden />
                Powered by {PROVIDER_LABEL[job.ai.provider] || job.ai.provider}
              </p>
            ) : null}
            {job.ai.notices.map((text) => (
              <p key={text} className="flex items-start gap-2 text-[11px] text-ink-soft">
                <RefreshCw className="mt-0.5 size-3 shrink-0" aria-hidden />
                {text}
              </p>
            ))}
            {aiUnavailable(job.ai) ? (
              <p className="flex items-start gap-2 text-[11px] text-ink-soft">
                <TriangleAlert className="mt-0.5 size-3 shrink-0" aria-hidden />
                All configured AI providers are currently unavailable. Deterministic results are unaffected.
              </p>
            ) : null}
          </div>
        ) : null}
        {active ? (
          <p className="mt-3 flex items-center gap-2 text-[11px] text-ink-soft" aria-live="polite">
            <Loader2 className="size-3 animate-spin" aria-hidden />
            Work is persisted as it happens. This page will update automatically — no simulated progress.
          </p>
        ) : null}
        {job.status === "failed" ? (
          <div className="mt-3">
            <InlineAlert tone="error">
              <span className="flex items-start gap-2">
                <TriangleAlert className="mt-0.5 size-4 shrink-0" aria-hidden />
                <span>
                  <strong>Verification stopped.</strong> {job.error || "The pipeline could not complete."}
                </span>
              </span>
            </InlineAlert>
          </div>
        ) : null}
      </Card>

      <Card className="overflow-hidden">
        <button
          type="button"
          onClick={() => setShowInput((value) => !value)}
          className="flex w-full items-center gap-2 px-5 py-3.5 text-left"
          aria-expanded={showInput}
        >
          <FileText className="size-4 text-ink-soft" aria-hidden />
          <span className="text-[12px] font-semibold text-ink">Original input</span>
          <span className="text-[11px] text-ink-soft">Preserved verbatim</span>
          <ChevronDown className={cn("ml-auto size-4 text-ink-soft transition-transform", showInput && "rotate-180")} aria-hidden />
        </button>
        {showInput ? (
          <div className="border-t border-line px-5 py-4">
            {job.input_url ? (
              <a
                href={job.input_url}
                target="_blank"
                rel="noreferrer noopener"
                className="mb-2 inline-flex items-center gap-1 text-[12px] text-powder-deep hover:underline"
              >
                {job.input_url}
                <ExternalLink className="size-3" aria-hidden />
              </a>
            ) : null}
            <pre className="max-h-64 overflow-auto whitespace-pre-wrap rounded-xl bg-surface/70 p-4 font-sans text-[12px] leading-relaxed text-ink">
              {job.input_text || "No readable text was stored for this input."}
            </pre>
            <p className="mt-2 text-[10px] text-ink-soft">
              Engine: {job.engine.extraction} extraction · {job.engine.research} research · {counts.sources} source(s)
            </p>
          </div>
        ) : null}
      </Card>

      {error ? <InlineAlert tone="error">{error}</InlineAlert> : null}

      <div className="flex gap-1 overflow-x-auto rounded-xl border border-line bg-white p-1">
        {TABS.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => setSearchParams({ tab: item.id })}
            aria-pressed={tab === item.id}
            className={cn(
              "inline-flex shrink-0 items-center gap-1.5 rounded-lg px-3.5 py-2 text-[12px] font-medium transition-colors",
              tab === item.id ? "bg-ink text-white" : "text-ink-soft hover:bg-lavender/60",
            )}
          >
            <item.icon className="size-3.5" aria-hidden />
            {item.label}
            {item.id === "claims" ? <span className="text-[10px] opacity-70">{counts.claims}</span> : null}
            {item.id === "radar" ? <span className="text-[10px] opacity-70">{counts.conflicts}</span> : null}
          </button>
        ))}
      </div>

      {tab === "claims" ? (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-[11px] text-ink-soft">
              Editing a claim clears its evidence until research is re-run. Extraction confidence is not
              a probability of truth.
            </p>
            <Button size="sm" variant="secondary" icon={Plus} onClick={() => setAdding((value) => !value)}>
              Add claim
            </Button>
          </div>
          {adding ? (
            <Card className="space-y-2 p-4">
              <Textarea
                value={newClaim}
                onChange={(event) => setNewClaim(event.target.value)}
                placeholder="Add a claim you want to verify independently…"
                aria-label="New claim text"
                className="min-h-20"
              />
              <div className="flex gap-2">
                <Button size="sm" onClick={() => void addClaim()} loading={savingClaim}>
                  Add claim
                </Button>
                <Button size="sm" variant="ghost" onClick={() => setAdding(false)}>
                  Cancel
                </Button>
              </div>
            </Card>
          ) : null}
          <ClaimList claims={job.claims} jobId={job.id} onChanged={refresh} onRerun={() => void rerun()} busy={active || rerunning} running={active} />
        </div>
      ) : null}

      {tab === "graph" ? (
        <div className="grid gap-4 xl:grid-cols-[1.55fr_0.75fr]">
          <Card className="p-4">
            {graph ? (
              <EvidenceGraph graph={graph} height={560} onSelect={setSelected} />
            ) : (
              <div className="space-y-3 p-2">
                <Skeleton className="h-8 w-64" />
                <Skeleton className="h-[480px] w-full" />
              </div>
            )}
          </Card>
          <Card className="p-5">
            <h2 className="text-sm font-semibold text-ink">Node inspector</h2>
            <GraphInspector selected={selected} />
            {job.contradictions.length ? (
              <div className="mt-5 rounded-xl border border-peach-deep/20 bg-[#FDF1EC] p-3">
                <p className="flex items-center gap-1.5 text-[11px] font-semibold text-peach-deep">
                  <ShieldAlert className="size-3.5" aria-hidden />
                  {job.contradictions.length} stored conflict(s)
                </p>
                <button
                  type="button"
                  onClick={() => setSearchParams({ tab: "radar" })}
                  className="mt-1 text-[11px] font-medium text-powder-deep hover:underline"
                >
                  Open the radar
                </button>
              </div>
            ) : null}
          </Card>
        </div>
      ) : null}

      {tab === "radar" ? <ContradictionList job={job} /> : null}

      {tab === "report" ? (
        job.status !== "completed" ? (
          <EmptyState
            icon={FileText}
            title={job.status === "failed" ? "No report: the run failed" : "Report is still being generated"}
            description={
              job.status === "failed"
                ? "A failed verification does not get a report. Fix the input error or retry; missing evidence is never replaced with a guess."
                : "The report is written only after research, evaluation, and contradiction analysis complete."
            }
            action={
              job.status === "failed" ? (
                <Button size="sm" onClick={() => void rerun()} loading={rerunning}>
                  Retry verification
                </Button>
              ) : undefined
            }
          />
        ) : report ? (
          <ProofReport report={report} />
        ) : (
          <div className="space-y-3">
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-64 w-full" />
          </div>
        )
      ) : null}
    </div>
  );
}
