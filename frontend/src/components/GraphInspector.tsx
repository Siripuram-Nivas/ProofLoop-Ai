import { ExternalLink } from "lucide-react";
import { formatDateTime } from "../lib/format";
import type { SelectedNode } from "./EvidenceGraph";
import { VerdictBadge } from "./ui";

export function GraphInspector({ selected }: { selected: SelectedNode | null }) {
  if (!selected) {
    return (
      <p className="mt-2 text-[12px] leading-relaxed text-ink-soft">
        Select any node to inspect its excerpt, relationship, source, and retrieval time. Edges are
        generated from stored evidence only.
      </p>
    );
  }
  const node = selected.node;
  return (
    <div className="mt-3 space-y-3">
      <div>
        <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-ink-soft">{node.kind}</p>
        <p className="mt-1 text-[13px] leading-relaxed text-ink">{node.label}</p>
      </div>
      {node.verdict ? <VerdictBadge verdict={node.verdict} /> : null}
      {node.relationship ? (
        <p className="text-[11px] text-ink-soft">
          Relationship: <span className="font-medium text-ink">{node.relationship}</span>
          {node.matchKind ? ` · ${node.matchKind.replaceAll("_", " ")}` : ""}
        </p>
      ) : null}
      {node.url || node.sourceUrl ? (
        <a
          href={node.url || node.sourceUrl}
          target="_blank"
          rel="noreferrer noopener"
          className="inline-flex items-center gap-1 text-[12px] font-medium text-powder-deep hover:underline"
        >
          Open source
          <ExternalLink className="size-3" aria-hidden />
        </a>
      ) : null}
      {node.quality ? (
        <p className="text-[11px] text-ink-soft">
          {node.quality} quality · {node.sourceType}
        </p>
      ) : null}
      {node.retrievedAt ? (
        <p className="text-[11px] text-ink-soft">Retrieved {formatDateTime(node.retrievedAt)}</p>
      ) : null}
      <div className="border-t border-line pt-3">
        <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-ink-soft">Relationships</p>
        {selected.incoming.length + selected.outgoing.length === 0 ? (
          <p className="mt-1 text-[11px] text-ink-soft">No edges.</p>
        ) : (
          <ul className="mt-1.5 space-y-1 text-[11px] text-ink-soft">
            {[
              ...selected.incoming.map((edge) => ({ ...edge, direction: "from" })),
              ...selected.outgoing.map((edge) => ({ ...edge, direction: "to" })),
            ].map((edge) => (
              <li key={`${edge.direction}-${edge.id}`} className="flex gap-1.5">
                <span className="shrink-0 text-ink">{edge.label}</span>
                <span className="truncate" title={edge.text}>
                  {edge.direction === "from" ? "from" : "to"} {edge.text}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
