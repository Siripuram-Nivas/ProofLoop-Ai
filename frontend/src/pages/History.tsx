import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Plus, Search } from "lucide-react";
import { api, ApiError } from "../lib/api";
import type { VerificationSummary } from "../lib/types";
import { VerificationTable } from "../components/VerificationTable";
import { Button, Card, InlineAlert, Skeleton } from "../components/ui";
import { formatDate } from "../lib/format";

const PAGE_SIZE = 20;

export function History() {
  const [items, setItems] = useState<VerificationSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState<"all" | "completed" | "failed">("all");

  const load = async (offset = 0) => {
    if (offset === 0) setLoading(true);
    else setLoadingMore(true);
    try {
      const result = await api.listVerifications({ limit: PAGE_SIZE, offset });
      setItems((current) => (offset === 0 ? result.items : [...current, ...result.items]));
      setTotal(result.total);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not load verification history.");
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  };

  useEffect(() => {
    void load(0);
  }, []);

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return items.filter((item) => {
      if (status !== "all" && item.status !== status) return false;
      if (!needle) return true;
      return (
        item.title.toLowerCase().includes(needle) ||
        item.id.toLowerCase().includes(needle)
      );
    });
  }, [items, query, status]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="eyebrow">Archive</p>
          <h1 className="display mt-2 text-4xl text-ink md:text-5xl">Verification history</h1>
          <p className="mt-2 max-w-xl text-sm leading-relaxed text-ink-soft">
            Every run keeps its original input and evidence snapshot. {total} record{total === 1 ? "" : "s"} stored.
          </p>
        </div>
        <Link to="/app/new">
          <Button icon={Plus}>New verification</Button>
        </Link>
      </div>

      <Card className="overflow-hidden">
        <div className="flex flex-col gap-3 border-b border-line p-4 sm:flex-row sm:items-center">
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-ink-soft" aria-hidden />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search by title or ID"
              aria-label="Search verification history"
              className="h-10 w-full rounded-xl border border-line bg-white pl-9 pr-3 text-sm text-ink placeholder:text-ink-soft/60 focus:border-powder-deep focus:outline-none"
            />
          </div>
          <div className="flex gap-1 rounded-xl border border-line bg-white p-1">
            {(["all", "completed", "failed"] as const).map((value) => (
              <button
                key={value}
                type="button"
                onClick={() => setStatus(value)}
                aria-pressed={status === value}
                className={`rounded-lg px-3 py-1.5 text-[12px] font-medium capitalize ${
                  status === value ? "bg-ink text-white" : "text-ink-soft hover:bg-lavender/60"
                }`}
              >
                {value}
              </button>
            ))}
          </div>
        </div>

        {error ? (
          <div className="p-5">
            <InlineAlert tone="error">{error}</InlineAlert>
          </div>
        ) : loading ? (
          <div className="space-y-2 p-5">
            {Array.from({ length: 5 }).map((_, index) => (
              <Skeleton key={index} className="h-14" />
            ))}
          </div>
        ) : (
          <VerificationTable items={filtered} />
        )}

        {!loading && filtered.length === 0 && items.length > 0 ? (
          <p className="border-t border-line p-5 text-center text-sm text-ink-soft">
            No runs match this search.
          </p>
        ) : null}

        {items.length < total ? (
          <div className="border-t border-line p-4 text-center">
            <Button
              variant="secondary"
              size="sm"
              loading={loadingMore}
              onClick={() => void load(items.length)}
            >
              Load more ({total - items.length} remaining)
            </Button>
          </div>
        ) : null}
      </Card>

      {items.length > 0 ? (
        <p className="text-[11px] text-ink-soft">
          Oldest visible run: {formatDate(items[items.length - 1]?.created_at)}. Records are retained in the
          workspace database; deletion is not exposed in this version.
        </p>
      ) : null}
    </div>
  );
}
