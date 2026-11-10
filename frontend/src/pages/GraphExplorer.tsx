import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ArrowUpRight, Network, Plus } from "lucide-react";
import { api, ApiError } from "../lib/api";
import type { GraphData, VerificationSummary } from "../lib/types";
import { EvidenceGraph, type SelectedNode } from "../components/EvidenceGraph";
import { GraphInspector } from "../components/GraphInspector";
import { RunSelector } from "../components/RunSelector";
import { Button, Card, EmptyState, InlineAlert, Skeleton } from "../components/ui";

export function GraphExplorer() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [items, setItems] = useState<VerificationSummary[]>([]);
  const [selectedId, setSelectedId] = useState(searchParams.get("job") || "");
  const [graph, setGraph] = useState<GraphData | null>(null);
  const [selected, setSelected] = useState<SelectedNode | null>(null);
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
    setGraph(null);
    setSelected(null);
    api
      .graph(selectedId)
      .then((data) => {
        if (active) setGraph(data);
      })
      .catch((err) => {
        if (active) setError(err instanceof ApiError ? err.message : "Could not load the graph.");
      });
    return () => {
      active = false;
    };
  }, [selectedId]);

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-9 w-64" />
        <Skeleton className="h-[520px] w-full" />
      </div>
    );
  }

  if (error) return <InlineAlert tone="error">{error}</InlineAlert>;

  if (items.length === 0) {
    return (
      <div className="space-y-5">
        <div>
          <p className="eyebrow">Evidence graph</p>
          <h1 className="display mt-2 text-4xl text-ink md:text-5xl">Every claim has a trail.</h1>
        </div>
        <Card>
          <EmptyState
            icon={Network}
            title="No completed verification to graph"
            description="The graph is built from stored claim and evidence records. Run a verification first — there is no demo data in this workspace."
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

  const claimCount = graph?.nodes.filter((node) => node.kind === "claim").length ?? 0;
  const evidenceCount = graph?.nodes.filter((node) => node.kind === "evidence").length ?? 0;
  const sourceCount = graph?.nodes.filter((node) => node.kind === "source").length ?? 0;

  return (
    <div className="space-y-5">
      <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
        <div>
          <p className="eyebrow">Evidence graph</p>
          <h1 className="display mt-2 text-4xl text-ink md:text-5xl">Every claim has a trail.</h1>
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-ink-soft">
            {claimCount} claim(s), {evidenceCount} evidence excerpt(s), {sourceCount} source(s). Edges show
            support, contradiction, and derivation — nothing is decorative.
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
            to={`/app/verifications/${selectedId}`}
            className="inline-flex h-9 items-center gap-1 rounded-xl border border-line bg-white px-3 text-[12px] font-medium text-ink"
          >
            Open run
            <ArrowUpRight className="size-3" aria-hidden />
          </Link>
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.55fr_0.75fr]">
        <Card className="p-4">
          {graph ? (
            <EvidenceGraph graph={graph} height={560} onSelect={setSelected} />
          ) : (
            <div className="space-y-3">
              <Skeleton className="h-8 w-64" />
              <Skeleton className="h-[500px] w-full" />
            </div>
          )}
        </Card>
        <div className="space-y-4">
          <Card className="p-5">
            <h2 className="text-sm font-semibold text-ink">Node inspector</h2>
            <GraphInspector selected={selected} />
          </Card>
          <Card className="p-5">
            <h2 className="text-sm font-semibold text-ink">Legend</h2>
            <ul className="mt-3 space-y-2 text-[11px] text-ink-soft">
              <li className="flex items-center gap-2"><span className="size-2.5 rounded-sm bg-ink" aria-hidden /> Claim</li>
              <li className="flex items-center gap-2"><span className="size-2.5 rounded-sm bg-support" aria-hidden /> Supporting evidence</li>
              <li className="flex items-center gap-2"><span className="size-2.5 rounded-sm bg-contradict" aria-hidden /> Contradicting evidence</li>
              <li className="flex items-center gap-2"><span className="size-2.5 rounded-sm bg-caution" aria-hidden /> Insufficient evidence</li>
              <li className="flex items-center gap-2"><span className="size-2.5 rounded-sm border border-powder bg-[#F1F8FE]" aria-hidden /> Source</li>
            </ul>
            <p className="mt-3 text-[10px] leading-relaxed text-ink-soft">
              Dashed edges mean “derived from”. A source page may support more than one claim.
            </p>
          </Card>
        </div>
      </div>
    </div>
  );
}
