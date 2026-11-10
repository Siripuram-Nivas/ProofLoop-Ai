import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ArrowUpRight, FileText, Plus } from "lucide-react";
import { api, ApiError } from "../lib/api";
import type { Report, VerificationSummary } from "../lib/types";
import { ProofReport } from "../components/ProofReport";
import { RunSelector } from "../components/RunSelector";
import { Button, Card, EmptyState, InlineAlert, Skeleton } from "../components/ui";

export function Reports() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [items, setItems] = useState<VerificationSummary[]>([]);
  const [selectedId, setSelectedId] = useState(searchParams.get("job") || "");
  const [report, setReport] = useState<Report | null>(null);
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
        setError(err instanceof ApiError ? err.message : "Could not load your reports.");
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
    setReport(null);
    api
      .report(selectedId)
      .then((data) => {
        if (active) setReport(data);
      })
      .catch((err) => {
        if (active) setError(err instanceof ApiError ? err.message : "Could not load the report.");
      });
    return () => {
      active = false;
    };
  }, [selectedId]);

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-9 w-64" />
        <Skeleton className="h-80 w-full" />
      </div>
    );
  }

  if (error) return <InlineAlert tone="error">{error}</InlineAlert>;

  if (items.length === 0) {
    return (
      <div className="space-y-5">
        <div>
          <p className="eyebrow">Reports</p>
          <h1 className="display mt-2 text-4xl text-ink md:text-5xl">Proof you can inspect.</h1>
        </div>
        <Card>
          <EmptyState
            icon={FileText}
            title="No proof reports yet"
            description="A report is generated after a verification completes. It preserves the evidence snapshot, the source index, and the limitations."
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
          <p className="eyebrow">Reports</p>
          <h1 className="display mt-2 text-4xl text-ink md:text-5xl">Proof you can inspect.</h1>
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-ink-soft">
            Each report is an evidence snapshot. Copy it as Markdown, export JSON, or print it to PDF.
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
            label="Report for"
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

      {report ? (
        <ProofReport report={report} />
      ) : (
        <div className="space-y-3">
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      )}
    </div>
  );
}
