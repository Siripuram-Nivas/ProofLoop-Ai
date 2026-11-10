import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  ArrowUpRight,
  BadgeCheck,
  FileSearch,
  FileText,
  Network,
  Plus,
  Radar,
  ScanText,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { api, ApiError } from "../lib/api";
import type { Stats } from "../lib/types";
import { formatDate, relativeTime } from "../lib/format";
import { VerificationTable } from "../components/VerificationTable";
import { Button, Card, EmptyState, InlineAlert, Metric, Skeleton, VerdictBadge, cn } from "../components/ui";
import { useAuth } from "../lib/auth";

export function Overview() {
  const { user } = useAuth();
  const [stats, setStats] = useState<Stats | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    api
      .stats()
      .then((data) => {
        if (!cancelled) setStats(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Could not load your workspace.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return (
      <div className="space-y-5">
        <Skeleton className="h-10 w-72" />
        <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-6">
          {Array.from({ length: 6 }).map((_, index) => (
            <Skeleton key={index} className="h-28" />
          ))}
        </div>
        <Skeleton className="h-72" />
      </div>
    );
  }

  if (error) {
    return (
      <InlineAlert tone="error">
        {error} Make sure the API is running, then refresh this page.
      </InlineAlert>
    );
  }

  if (!stats) return null;
  const totals = stats.totals;
  const empty = totals.runs === 0 && stats.recent.length === 0;

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="eyebrow">Workspace</p>
          <h1 className="display mt-2 text-4xl text-ink md:text-5xl">
            {empty ? "Start with a claim." : "Evidence, not vibes."}
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-ink-soft">
            {empty
              ? "Submit text, a PDF, or a URL. ProofLoop extracts atomic claims, retrieves real sources, and keeps uncertainty visible."
              : `Signed in as ${user?.email || "guest"}. Every number below comes from your stored verification records.`}
          </p>
        </div>
        <Link
          to="/app/new"
          className="inline-flex h-11 shrink-0 items-center justify-center gap-2 rounded-xl bg-ink px-5 text-sm font-medium text-white hover:bg-[#262936]"
        >
          <Plus className="size-4" aria-hidden />
          New verification
        </Link>
      </div>

      {empty ? (
        <Card>
          <div className="relative overflow-hidden rounded-[20px] px-6 py-12 md:px-12">
            <div className="pointer-events-none absolute -right-10 -top-10 size-56 rounded-full bg-powder/25 blur-3xl" aria-hidden />
            <div className="relative max-w-2xl">
              <span className="inline-flex items-center gap-1.5 rounded-full border border-line bg-white px-3 py-1.5 text-[11px] font-medium text-ink-soft">
                <Sparkles className="size-3.5 text-powder-deep" aria-hidden />
                No verification runs yet
              </span>
              <h2 className="display mt-5 text-3xl text-ink md:text-4xl">
                What should we check first?
              </h2>
              <p className="mt-3 text-sm leading-relaxed text-ink-soft">
                ProofLoop will not pretend an answer is verified. If it cannot find evidence, it says so.
              </p>
              <div className="mt-6 grid gap-3 sm:grid-cols-3">
                {[
                  { icon: ScanText, title: "Extract", body: "One statement becomes independent claims." },
                  { icon: FileSearch, title: "Research", body: "Real excerpts with URLs and dates." },
                  { icon: ShieldCheck, title: "Decide", body: "Supported, contradicted, or unresolved." },
                ].map((step) => (
                  <div key={step.title} className="rounded-xl border border-line bg-white p-4">
                    <step.icon className="size-4 text-ink" aria-hidden />
                    <p className="mt-2 text-[13px] font-semibold">{step.title}</p>
                    <p className="mt-1 text-[12px] leading-relaxed text-ink-soft">{step.body}</p>
                  </div>
                ))}
              </div>
              <div className="mt-6 flex flex-wrap gap-2">
                <Link
                  to="/app/new"
                  className="inline-flex h-11 items-center gap-2 rounded-xl bg-ink px-5 text-sm font-medium text-white"
                >
                  Verify a claim
                  <ArrowRight className="size-4" aria-hidden />
                </Link>
                <Link
                  to="/app/settings"
                  className="inline-flex h-11 items-center gap-2 rounded-xl border border-line bg-white px-5 text-sm font-medium text-ink"
                >
                  See capabilities
                </Link>
              </div>
            </div>
          </div>
        </Card>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
            <Metric label="Runs" value={totals.runs} sub="completed" />
            <Metric label="Claims" value={totals.claims} />
            <Metric label="Supported" value={totals.supported} accent="support" />
            <Metric label="Contradicted" value={totals.contradicted} accent="contradict" />
            <Metric label="Unverified" value={totals.unverified_all} accent="caution" sub="not false" />
            <Metric label="Conflicts" value={totals.conflicts} accent="contradict" sub="stored" />
          </div>

          <div className="grid gap-5 xl:grid-cols-[1.6fr_0.9fr]">
            <Card className="overflow-hidden">
              <div className="flex items-center justify-between border-b border-line px-5 py-4">
                <div>
                  <h2 className="text-sm font-semibold text-ink">Recent verifications</h2>
                  <p className="text-[11px] text-ink-soft">Stored runs, newest first</p>
                </div>
                <Link to="/app/history" className="inline-flex items-center gap-1 text-[11px] font-medium text-powder-deep hover:underline">
                  View all
                  <ArrowUpRight className="size-3" aria-hidden />
                </Link>
              </div>
              <VerificationTable items={stats.recent} />
            </Card>

            <div className="space-y-5">
              <Card className="p-5">
                <div className="flex items-center gap-2">
                  <FileText className="size-4 text-ink" aria-hidden />
                  <h2 className="text-sm font-semibold text-ink">Latest proof report</h2>
                </div>
                {stats.latest_report ? (
                  <div className="mt-3">
                    <p className="line-clamp-2 text-[13px] font-medium text-ink">
                      {stats.latest_report.title}
                    </p>
                    <p className="mt-1 text-[11px] text-ink-soft">
                      Generated {relativeTime(stats.latest_report.generated_at)}
                    </p>
                    <div className="mt-3 grid grid-cols-3 gap-2 text-center">
                      {[
                        ["Supported", stats.latest_report.summary.supported, "text-support"],
                        ["Contradicted", stats.latest_report.summary.contradicted, "text-contradict"],
                        ["Conflicts", stats.latest_report.summary.conflicts, "text-caution"],
                      ].map(([label, value, tone]) => (
                        <div key={String(label)} className="rounded-lg bg-lavender/50 py-2">
                          <p className={cn("text-lg font-semibold tabular-nums", String(tone))}>{value}</p>
                          <p className="text-[9px] uppercase tracking-[0.08em] text-ink-soft">{label}</p>
                        </div>
                      ))}
                    </div>
                    <Link
                      to={`/app/verifications/${stats.latest_report.verification_id}?tab=report`}
                      className="mt-4 inline-flex items-center gap-1 text-[12px] font-medium text-powder-deep hover:underline"
                    >
                      Open report
                      <ArrowUpRight className="size-3" aria-hidden />
                    </Link>
                  </div>
                ) : (
                  <p className="mt-3 text-[12px] leading-relaxed text-ink-soft">
                    No generated report yet. Complete a verification to create one.
                  </p>
                )}
              </Card>

              <Card className="p-5">
                <div className="flex items-center gap-2">
                  <Radar className="size-4 text-peach-deep" aria-hidden />
                  <h2 className="text-sm font-semibold text-ink">Recent evidence conflicts</h2>
                </div>
                {stats.conflicts.length ? (
                  <ul className="mt-3 space-y-2.5">
                    {stats.conflicts.slice(0, 4).map((conflict, index) => (
                      <li key={`${conflict.verification_id}-${index}`} className="rounded-lg border border-line bg-surface/60 p-3">
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] font-semibold uppercase tracking-[0.1em] text-contradict">
                            {conflict.kind.replaceAll("_", " ")}
                          </span>
                          <span className="ml-auto text-[9px] text-ink-soft">{conflict.severity}</span>
                        </div>
                        <p className="mt-1 line-clamp-2 text-[11px] leading-relaxed text-ink-soft">
                          {conflict.summary}
                        </p>
                        <Link
                          to={`/app/verifications/${conflict.verification_id}?tab=radar`}
                          className="mt-1.5 inline-flex items-center gap-1 text-[10px] font-medium text-powder-deep hover:underline"
                        >
                          Inspect
                          <ArrowUpRight className="size-2.5" aria-hidden />
                        </Link>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-3 text-[12px] leading-relaxed text-ink-soft">
                    No stored conflicts. Absence of conflict is not proof — check which claims remain
                    unverified.
                  </p>
                )}
              </Card>

              <div className="grid grid-cols-2 gap-3">
                <Link
                  to="/app/graph"
                  className="group rounded-2xl border border-line bg-white p-4 transition-colors hover:border-ink/25"
                >
                  <Network className="size-4 text-powder-deep" aria-hidden />
                  <p className="mt-2 text-[12px] font-semibold">Evidence graph</p>
                  <p className="text-[10px] text-ink-soft">Follow the trail</p>
                </Link>
                <Link
                  to="/app/reports"
                  className="group rounded-2xl border border-line bg-white p-4 transition-colors hover:border-ink/25"
                >
                  <BadgeCheck className="size-4 text-support" aria-hidden />
                  <p className="mt-2 text-[12px] font-semibold">Proof reports</p>
                  <p className="text-[10px] text-ink-soft">Export &amp; inspect</p>
                </Link>
              </div>
            </div>
          </div>

          {stats.conflicts.length > 0 ? (
            <div className="flex items-start gap-2 rounded-xl border border-peach-deep/20 bg-[#FDF1EC] p-4 text-[12px] leading-relaxed text-peach-deep">
              <Radar className="mt-0.5 size-4 shrink-0" aria-hidden />
              <span>
                {stats.conflicts.length} stored conflict{stats.conflicts.length === 1 ? "" : "s"} need a human
                decision. ProofLoop does not resolve them automatically.
              </span>
            </div>
          ) : null}
        </>
      )}
    </div>
  );
}
