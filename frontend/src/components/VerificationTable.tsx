import { Link } from "react-router-dom";
import { ArrowUpRight, FileText } from "lucide-react";
import { formatDate, inputKindLabel, VERDICT_META } from "../lib/format";
import type { VerificationSummary } from "../lib/types";
import { Badge, EmptyState, VerdictBadge, cn } from "./ui";

export function VerificationTable({ items }: { items: VerificationSummary[] }) {
  if (items.length === 0) {
    return (
      <EmptyState
        icon={FileText}
        title="No verifications yet"
        description="Submit a statement, document, or URL to extract claims and retrieve real evidence."
        action={
          <Link to="/app/new" className="inline-flex h-10 items-center rounded-xl bg-ink px-4 text-sm font-medium text-white">
            Start a verification
          </Link>
        }
      />
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[760px] border-collapse text-left">
        <thead>
          <tr className="border-b border-line text-[10px] font-semibold uppercase tracking-[0.12em] text-ink-soft">
            <th className="px-5 py-3">Verification</th>
            <th className="px-3 py-3">Status</th>
            <th className="px-3 py-3">Claims</th>
            <th className="px-3 py-3">Verdicts</th>
            <th className="px-3 py-3">Sources</th>
            <th className="px-3 py-3">Conflicts</th>
            <th className="px-3 py-3">Created</th>
            <th className="px-5 py-3" />
          </tr>
        </thead>
        <tbody>
          {items.map((item) => {
            const counts = Object.entries(item.verdicts).filter(([, value]) => value > 0);
            return (
              <tr key={item.id} className="border-b border-line/70 last:border-0 hover:bg-lavender/20">
                <td className="px-5 py-4">
                  <Link to={`/app/verifications/${item.id}`} className="block max-w-[280px]">
                    <span className="line-clamp-1 text-[13px] font-medium text-ink">{item.title}</span>
                    <span className="mt-0.5 block text-[10px] text-ink-soft">
                      {inputKindLabel(item.input_kind)} · {item.id}
                    </span>
                  </Link>
                </td>
                <td className="px-3 py-4">
                  <Badge
                    className={cn(
                      "capitalize",
                      item.status === "completed" && "border-support/25 bg-[#EDF6F1] text-support",
                      item.status === "failed" && "border-contradict/25 bg-[#FBEDEB] text-contradict",
                      item.status !== "completed" &&
                        item.status !== "failed" &&
                        "border-powder/40 bg-[#F1F8FE] text-powder-deep",
                    )}
                    dot={item.status === "failed" ? "bg-contradict" : item.status === "completed" ? "bg-support" : "bg-powder-deep"}
                  >
                    {item.status}
                  </Badge>
                </td>
                <td className="px-3 py-4 text-[13px] tabular-nums text-ink">{item.claim_count}</td>
                <td className="px-3 py-4">
                  <div className="flex flex-wrap gap-1">
                    {counts.length === 0 ? (
                      <span className="text-[11px] text-ink-soft">—</span>
                    ) : (
                      counts.map(([verdict, count]) => {
                        const meta = VERDICT_META[verdict as keyof typeof VERDICT_META];
                        return (
                          <span
                            key={verdict}
                            title={`${meta?.label}: ${count}`}
                            className={cn(
                              "inline-flex items-center gap-1 rounded-full border px-1.5 py-0.5 text-[10px] font-medium",
                              meta?.tone || "",
                            )}
                          >
                            <span className={cn("size-1 rounded-full", meta?.dot)} aria-hidden />
                            <span className="sr-only">{meta?.label}: </span>
                            {count}
                          </span>
                        );
                      })
                    )}
                  </div>
                </td>
                <td className="px-3 py-4 text-[13px] tabular-nums text-ink">{item.source_count}</td>
                <td className="px-3 py-4 text-[13px] tabular-nums">
                  <span className={item.conflict_count ? "font-semibold text-contradict" : "text-ink-soft"}>
                    {item.conflict_count}
                  </span>
                </td>
                <td className="px-3 py-4 text-[11px] text-ink-soft">{formatDate(item.created_at)}</td>
                <td className="px-5 py-4 text-right">
                  <Link
                    to={`/app/verifications/${item.id}`}
                    className="inline-flex items-center gap-1 text-[11px] font-medium text-powder-deep hover:underline"
                  >
                    Open
                    <ArrowUpRight className="size-3" aria-hidden />
                  </Link>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export function VerdictStrip({ verdicts }: { verdicts: VerificationSummary["verdicts"] }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {(Object.keys(verdicts) as Array<keyof typeof verdicts>).map((verdict) =>
        verdicts[verdict] > 0 ? (
          <VerdictBadge key={verdict} verdict={verdict} />
        ) : null,
      )}
    </div>
  );
}
