import { useEffect, useMemo, useState } from "react";
import {
  Background,
  BackgroundVariant,
  Controls,
  Handle,
  Position,
  ReactFlow,
  type Edge,
  type Node,
  type NodeProps,
} from "@xyflow/react";
import { ExternalLink, FileText, Search, ShieldCheck } from "lucide-react";
import { cn } from "./ui";
import { truncate, VERDICT_META } from "../lib/format";
import type { GraphData, GraphNode } from "../lib/types";

type FlowData = {
  node: GraphNode;
};

const NODE_WIDTH = 248;

function kindStyles(node: GraphNode): string {
  if (node.kind === "claim") return "border-ink/70 bg-ink text-white";
  if (node.kind === "source") return "border-powder/70 bg-[#F4FAFF] text-ink";
  if (node.relationship === "contradicts") return "border-contradict/40 bg-[#FDF3F1] text-ink";
  if (node.relationship === "insufficient") return "border-caution/35 bg-[#FCF7EC] text-ink";
  return "border-support/30 bg-[#F3FAF6] text-ink";
}

function GraphNodeCard({ data, selected }: NodeProps<Node<FlowData>>) {
  const node = data.node;
  const meta = node.verdict ? VERDICT_META[node.verdict] : null;
  return (
    <div
      className={cn(
        "w-[248px] rounded-xl border px-3.5 py-3 shadow-sm transition-shadow",
        kindStyles(node),
        selected && "ring-2 ring-powder-deep ring-offset-2",
      )}
    >
      <Handle type="target" position={Position.Left} />
      <div className="flex items-center gap-1.5">
        <span
          className={cn(
            "grid size-5 shrink-0 place-items-center rounded-md",
            node.kind === "claim" ? "bg-white/15" : "bg-white",
          )}
        >
          {node.kind === "claim" ? (
            <FileText className="size-3" aria-hidden />
          ) : node.kind === "source" ? (
            <ExternalLink className="size-3" aria-hidden />
          ) : (
            <Search className="size-3" aria-hidden />
          )}
        </span>
        <span
          className={cn(
            "text-[9px] font-semibold uppercase tracking-[0.14em]",
            node.kind === "claim" ? "text-white/60" : "text-ink-soft",
          )}
        >
          {node.kind === "claim" ? "Claim" : node.kind === "source" ? "Source" : "Evidence excerpt"}
        </span>
        {meta ? (
          <span
            className={cn(
              "ml-auto rounded-full px-1.5 py-0.5 text-[9px] font-semibold",
              node.kind === "claim" ? "bg-white/15 text-white" : meta.tone,
            )}
          >
            {meta.label}
          </span>
        ) : null}
      </div>
      <p
        className={cn(
          "mt-2 line-clamp-3 text-[12px] leading-snug",
          node.kind === "claim" ? "text-white/90" : "text-ink",
        )}
      >
        {truncate(node.label, 150)}
      </p>
      {node.stale ? <p className="mt-1.5 text-[10px] text-caution">Source last updated &gt; 3 years ago</p> : null}
      {node.kind === "source" && node.quality ? (
        <p className="mt-1.5 text-[10px] text-ink-soft">{node.quality} quality · {node.sourceType}</p>
      ) : null}
      <Handle type="source" position={Position.Right} />
    </div>
  );
}

const nodeTypes = { proof: GraphNodeCard };

function layout(nodes: GraphNode[], edges: GraphData["edges"]): { nodes: Node<FlowData>[]; edges: Edge[] } {
  const claims = nodes.filter((node) => node.kind === "claim");
  const evidence = nodes.filter((node) => node.kind === "evidence");
  const sources = nodes.filter((node) => node.kind === "source");
  const positions = new Map<string, { x: number; y: number }>();

  let claimY = 0;
  const evidenceByClaim = new Map<string, GraphNode[]>();
  for (const edge of edges) {
    if (edge.kind === "derived_from") continue;
    const list = evidenceByClaim.get(edge.source) || [];
    const target = evidence.find((node) => node.id === edge.target);
    if (target) list.push(target);
    evidenceByClaim.set(edge.source, list);
  }

  for (const claim of claims) {
    const items = evidenceByClaim.get(claim.id) || [];
    const blockHeight = Math.max(1, items.length) * 132;
    positions.set(claim.id, { x: 0, y: claimY });
    items.forEach((item, index) => {
      positions.set(item.id, { x: NODE_WIDTH + 120, y: claimY + index * 132 });
    });
    claimY += blockHeight + 46;
  }

  const orphanEvidence = evidence.filter((node) => !positions.has(node.id));
  orphanEvidence.forEach((node, index) => {
    positions.set(node.id, { x: NODE_WIDTH + 120, y: claimY + index * 132 });
  });
  const sourceY = new Map<string, number>();
  let cursor = 0;
  for (const node of evidence) {
    const sourceEdge = edges.find((edge) => edge.source === node.id && edge.kind === "derived_from");
    if (sourceEdge && !sourceY.has(sourceEdge.target)) {
      sourceY.set(sourceEdge.target, cursor);
      cursor += 124;
    }
  }
  let fallback = 0;
  for (const source of sources) {
    positions.set(source.id, {
      x: 2 * NODE_WIDTH + 240,
      y: sourceY.get(source.id) ?? fallback,
    });
    if (!sourceY.has(source.id)) fallback += 124;
  }

  const flowNodes: Node<FlowData>[] = nodes.map((node) => ({
    id: node.id,
    type: "proof",
    position: positions.get(node.id) || { x: 0, y: 0 },
    data: { node },
    ariaLabel: `${node.kind}: ${truncate(node.label, 80)}`,
  }));

  const flowEdges: Edge[] = edges.map((edge) => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    label: edge.label,
    type: "smoothstep",
    animated: false,
    style: {
      stroke:
        edge.kind === "contradicts"
          ? "#B4443C"
          : edge.kind === "derived_from"
            ? "#9A9AAD"
            : edge.kind === "insufficient"
              ? "#A9711F"
              : "#2F7D5D",
      strokeWidth: 1.4,
      strokeDasharray: edge.kind === "derived_from" ? "3 3" : undefined,
    },
    labelStyle: { fill: "#4B4F5C", fontSize: 9 },
    labelBgStyle: { fill: "#F7F6FC", fillOpacity: 0.9 },
  }));

  return { nodes: flowNodes, edges: flowEdges };
}

export interface SelectedNode {
  node: GraphNode;
  incoming: { label: string; id: string; text: string }[];
  outgoing: { label: string; id: string; text: string }[];
}

export function EvidenceGraph({
  graph,
  height = 560,
  sample = false,
  onSelect,
}: {
  graph: GraphData;
  height?: number;
  sample?: boolean;
  onSelect?: (selection: SelectedNode | null) => void;
}) {
  const [activeKinds, setActiveKinds] = useState<Record<string, boolean>>({
    claim: true,
    evidence: true,
    source: true,
  });
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<string | null>(null);

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    const matched = graph.nodes.filter((node) => {
      if (!activeKinds[node.kind]) return false;
      if (!needle) return true;
      return node.label.toLowerCase().includes(needle);
    });
    const matchedIds = new Set(matched.map((node) => node.id));
    const related = new Set(matchedIds);
    for (const edge of graph.edges) {
      if (matchedIds.has(edge.source) || matchedIds.has(edge.target)) {
        related.add(edge.source);
        related.add(edge.target);
      }
    }
    const nodes = graph.nodes.filter((node) => related.has(node.id) && activeKinds[node.kind]);
    const edges = graph.edges.filter(
      (edge) => related.has(edge.source) && related.has(edge.target),
    );
    return { nodes, edges };
  }, [graph, activeKinds, query]);

  const flow = useMemo(() => layout(filtered.nodes, filtered.edges), [filtered]);

  const handleSelect = (nodeId: string | null) => {
    setSelected(nodeId);
    if (!onSelect) return;
    if (!nodeId) {
      onSelect(null);
      return;
    }
    const node = graph.nodes.find((item) => item.id === nodeId);
    if (!node) return;
    const neighbour = (id: string) => graph.nodes.find((item) => item.id === id)?.label || id;
    onSelect({
      node,
      incoming: graph.edges.filter((edge) => edge.target === nodeId).map((edge) => ({ label: edge.label, id: edge.source, text: neighbour(edge.source) })),
      outgoing: graph.edges.filter((edge) => edge.source === nodeId).map((edge) => ({ label: edge.label, id: edge.target, text: neighbour(edge.target) })),
    });
  };

  return (
    <div className="relative">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        {(Object.keys(activeKinds) as Array<keyof typeof activeKinds>).map((kind) => (
          <button
            key={kind}
            type="button"
            aria-pressed={activeKinds[kind]}
            onClick={() => setActiveKinds((current) => ({ ...current, [kind]: !current[kind] }))}
            className={cn(
              "rounded-full border px-3 py-1.5 text-[11px] font-medium capitalize transition-colors",
              activeKinds[kind]
                ? "border-ink/20 bg-white text-ink"
                : "border-line bg-transparent text-ink-soft/60 line-through",
            )}
          >
            {kind === "evidence" ? "Evidence" : kind}
          </button>
        ))}
        <div className="relative ml-auto">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-3.5 -translate-y-1/2 text-ink-soft" aria-hidden />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Find a claim or source"
            aria-label="Search graph nodes"
            className="h-9 w-56 rounded-full border border-line bg-white pl-8 pr-3 text-xs text-ink placeholder:text-ink-soft/60 focus:border-powder-deep focus:outline-none"
          />
        </div>
      </div>
      <div
        className="relative overflow-hidden rounded-2xl border border-line bg-[#FBFAFE]"
        style={{ height }}
      >
        {sample ? (
          <div className="absolute left-4 top-4 z-10 rounded-full border border-peach-deep/25 bg-[#FDF1EC] px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.12em] text-peach-deep">
            Illustrative sample
          </div>
        ) : null}
        <ReactFlow
          nodes={flow.nodes}
          edges={flow.edges}
          nodeTypes={nodeTypes}
          fitView
          minZoom={0.2}
          maxZoom={1.6}
          onNodeClick={(_, node) => handleSelect(node.id)}
          onPaneClick={() => handleSelect(null)}
          aria-label="Evidence graph"
        >
          <Background variant={BackgroundVariant.Dots} gap={22} size={1} color="#C9C8DC" />
          <Controls showInteractive={false} />
        </ReactFlow>
        {filtered.nodes.length === 0 ? (
          <div className="pointer-events-none absolute inset-0 grid place-items-center p-6 text-center">
            <p className="max-w-xs text-sm text-ink-soft">
              No nodes match this filter. Clear the search or enable a node type.
            </p>
          </div>
        ) : null}
      </div>
      {selected ? null : (
        <p className="mt-2.5 flex items-center gap-1.5 text-[11px] text-ink-soft">
          <ShieldCheck className="size-3.5" aria-hidden />
          Click a node to inspect it. Drag to pan, scroll to zoom. Every edge comes from stored verification data.
        </p>
      )}
    </div>
  );
}
