import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ArrowUpRight, Plus, Radar, ShieldAlert } from "lucide-react";
import { api, ApiError } from "../lib/api";
import type { VerificationJob, VerificationSummary } from "../lib/types";
import { ContradictionList } from "../components/ContradictionList";
import { RunSelector } from "../components/RunSelector";
import { Button, Card, EmptyState, InlineAlert, Skeleton } from "../components/ui";

export function RadarPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [items, setItems] = useState<VerificationSummary[]>([]);
  const [selectedId, setSelectedId] = useState(searchParams.get("job") || "");
  const [job, setJob] = useState<VerificationJob | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    api
      .listVerifications({ limit: 50 })
      .then((result) => {
        if (!active) return;
        const completed = result.items.filter((item) => item.status === "completed");
        setItems(completed);
        const requested = searchParams.get("job");
        const initial =
          (requested && completed.some((item) => item.id === requested) ? requested : "") ||
          completed[0]?.id ||
          "";
        setSelectedId(initial);
        setLoading(false);
      })
      .catch((err) => {
        if (!active) return;
        setError(err instanceof ApiError ? err.message : "Could not load your verifications.");
        setLoading(false);
      });
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    let active = true;
    setJob(null);
    api
      .getVerification(selectedId)
      .then((data) => {
        if (active) setJob(data);
      })
      .catch((err) => {
        if (active) setError(err instanceof ApiError ? err.message : "Could not load this verification.");
      });
    return () => {
      active = false;
    };
  }, [selectedId]);

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-9 w-72" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (error) return <InlineAlert tone="error">{error}</InlineAlert>;

  if (items.length === 0) {
    return (
      <div className="space-y-5">
        <div>
          <p className="eyebrow">Contradiction radar</p>
          <h1 className="display mt-2 text-4xl text-ink md:text-5xl">
            Find disagreements before they become decisions.
          </h1>
        </div>
        <Card>
          <EmptyState
            icon={Radar}
            title="No completed verification to analyse"
            description="The radar only shows conflicts stored by a real verification. It will not invent a disagreement to look impressive."
            action={
              <Link to="/app/new">
                <Button icon={Plus}>Start a verification</Button>
              </Link>
            }
          />
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
        <div>
          <p className="eyebrow">Contradiction radar</p>
          <h1 className="display mt-2 text-4xl text-ink md:text-5xl">
            Find disagreements before they become decisions.
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-ink-soft">
            Numeric mismatches, date mismatches, and source disagreement. ProofLoop reports them with both
            passages and never picks a winner automatically.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <RunSelector
            items={items}
            value={selectedId}
            onChange={(id) => {
              setSelectedId(id);
              setSearchParams({ job: id });
            }}
          />
          <Link
            to={`/app/verifications/${selectedId}?tab=radar`}
            className="inline-flex h-9 items-center gap-1 rounded-xl border border-line bg-white px-3 text-[12px] font-medium text-ink"
          >
            Open run
            <ArrowUpRight className="size-3" aria-hidden />
          </Link>
        </div>
      </div>

      {job ? (
        <>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {[
              ["Claims", job.claims.length, "text-ink"],
              ["Conflicts", job.contradictions.length, job.contradictions.length ? "text-contradict" : "text-ink"],
              ["Sources", job.sources.length, "text-ink"],
              ["Status", job.status, "text-powder-deep"],
            ].map(([label, value, tone]) => (
              <div key={String(label)} className="rounded-2xl border border-line bg-white p-4">
                <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-ink-soft">{label}</p>
                <p className={`mt-1.5 text-xl font-semibold capitalize tabular-nums ${tone}`}>{value}</p>
              </div>
            ))}
          </div>

          {job.contradictions.length === 0 ? (
            <div className="flex items-start gap-2 rounded-xl border border-line bg-white p-4 text-[12px] leading-relaxed text-ink-soft">
              <ShieldAlert className="mt-0.5 size-4 shrink-0 text-caution" aria-hidden />
              <span>
                No conflict was recorded for <strong className="text-ink">{job.title}</strong>. That is not a
                clean bill of health: check the claims marked unverified or insufficient in the claims tab.
              </span>
            </div>
          ) : null}

          <ContradictionList job={job} />
        </>
      ) : (
        <Skeleton className="h-64 w-full" />
      )}
    </div>
  );
}
