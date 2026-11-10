import { useMemo, useState } from "react";
import { Check, Copy, Download, ExternalLink, Printer, ShieldAlert } from "lucide-react";
import { formatDateTime, VERDICT_META } from "../lib/format";
import type { Report } from "../lib/types";
import { Badge, Button, cn } from "./ui";

function toMarkdown(report: Report): string {
  const lines: string[] = [
    `# Proof Report — ${report.title}`,
    "",
    `Verification ID: ${report.verification_id}`,
    `Generated: ${report.generated_at}`,
    `Engine: extraction=${report.engine.extraction}, research=${report.engine.research}`,
    "",
    "## Summary",
    ...Object.entries(report.summary).map(([key, value]) => `- ${key}: ${value}`),
    "",
    "## Original input",
    report.input_url ? `URL: ${report.input_url}` : "",
    "```",
    report.input_text || "(no stored text)",
    "```",
    "",
    "## Claim findings",
  ];
  for (const claim of report.claims) {
    lines.push(
      "",
      `### ${claim.verdict_label}: ${claim.text}`,
      claim.verdict_basis,
      "",
    );
    for (const evidence of claim.evidence) {
      lines.push(
        `- [${evidence.relationship}] "${evidence.excerpt}"`,
        `  ${evidence.explanation}`,
        `  Source: ${evidence.source_title} — ${evidence.source_url} (retrieved ${evidence.retrieved_at})`,
      );
    }
    for (const conflict of claim.conflicts) {
      lines.push(`- CONFLICT (${conflict.kind}, ${conflict.severity}): ${conflict.summary}`);
    }
  }
  lines.push("", "## Sources");
  for (const source of report.sources) {
    lines.push(
      `- ${source.title} — ${source.url} (${source.source_type}; retrieved ${source.retrieved_at})`,
    );
  }
  lines.push("", "## Limitations");
  report.limitations.forEach((item) => lines.push(`- ${item}`));
  lines.push("", "## Methodology");
  report.methodology.forEach((item, index) => lines.push(`${index + 1}. ${item}`));
  lines.push("", `> ${report.disclaimer}`);
  return lines.filter((line) => line !== undefined).join("\n");
}

function SummaryTile({ label, value, tone }: { label: string; value: number; tone?: string }) {
  return (
    <div className="rounded-xl border border-line bg-white p-3.5">
      <p className="text-[10px] font-semibold uppercase tracking-[0.1em] text-ink-soft">{label}</p>
      <p className={cn("mt-1 text-2xl font-semibold tabular-nums", tone || "text-ink")}>{value}</p>
    </div>
  );
}

export function ProofReport({ report }: { report: Report }) {
  const [copied, setCopied] = useState(false);
  const [copyError, setCopyError] = useState<string | null>(null);
  const markdown = useMemo(() => toMarkdown(report), [report]);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(markdown);
      setCopied(true);
      setCopyError(null);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopyError("Clipboard access was blocked. Download the JSON export instead.");
    }
  };

  const download = () => {
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${report.verification_id}-proof-report.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-5">
      <div className="no-print flex flex-wrap items-center gap-2">
        <Button size="sm" variant="secondary" icon={copied ? Check : Copy} onClick={() => void copy()}>
          {copied ? "Copied" : "Copy Markdown"}
        </Button>
        <Button size="sm" variant="secondary" icon={Download} onClick={download}>
          Export JSON
        </Button>
        <Button size="sm" variant="secondary" icon={Printer} onClick={() => window.print()}>
          Print / save as PDF
        </Button>
        {copyError ? <span className="text-xs text-contradict">{copyError}</span> : null}
      </div>

      <div className="print-report card overflow-hidden">
        <header className="border-b border-line bg-lavender/50 px-5 py-6 md:px-8">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="eyebrow">Proof report</p>
              <h2 className="display mt-2 text-3xl text-ink md:text-4xl">{report.title}</h2>
              <p className="mt-2 text-[11px] text-ink-soft">
                {report.verification_id} · Generated {formatDateTime(report.generated_at)}
              </p>
            </div>
            <div className="text-right text-[11px] text-ink-soft">
              <p>Extraction: {report.engine.extraction}</p>
              <p>Research: {report.engine.research}</p>
              <p>Input: {report.input_kind}</p>
            </div>
          </div>
        </header>

        <section className="border-b border-line px-5 py-6 md:px-8">
          <h3 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-ink-soft">
            Verification overview
          </h3>
          <div className="mt-3 grid grid-cols-2 gap-2.5 sm:grid-cols-4">
            <SummaryTile label="Claims" value={report.summary.claims} />
            <SummaryTile label="Supported" value={report.summary.supported} tone="text-support" />
            <SummaryTile label="Contradicted" value={report.summary.contradicted} tone="text-contradict" />
            <SummaryTile label="Mixed" value={report.summary.mixed} tone="text-peach-deep" />
            <SummaryTile label="Insufficient" value={report.summary.insufficient} tone="text-caution" />
            <SummaryTile label="Unverified" value={report.summary.unverified} tone="text-ink-soft" />
            <SummaryTile label="Sources" value={report.summary.sources} />
            <SummaryTile label="Conflicts" value={report.summary.conflicts} tone="text-contradict" />
          </div>
        </section>

        <section className="border-b border-line px-5 py-6 md:px-8">
          <h3 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-ink-soft">
            Original input
          </h3>
          {report.input_url ? (
            <a
              href={report.input_url}
              target="_blank"
              rel="noreferrer noopener"
              className="mt-2 inline-flex items-center gap-1 text-[13px] text-powder-deep hover:underline"
            >
              {report.input_url}
              <ExternalLink className="size-3" aria-hidden />
            </a>
          ) : null}
          <pre className="mt-3 max-h-64 overflow-auto whitespace-pre-wrap rounded-xl border border-line bg-surface/60 p-4 font-sans text-[12px] leading-relaxed text-ink">
            {report.input_text || "Original text was not stored for this input."}
          </pre>
        </section>

        <section className="border-b border-line px-5 py-6 md:px-8">
          <h3 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-ink-soft">
            Claim-by-claim findings
          </h3>
          <ol className="mt-4 space-y-5">
            {report.claims.map((claim, index) => (
              <li key={claim.id} className="rounded-xl border border-line p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-[10px] text-ink-soft/60">#{index + 1}</span>
                  <Badge
                    className={
                      VERDICT_META[claim.verdict]?.tone || VERDICT_META.unverified.tone
                    }
                    dot={VERDICT_META[claim.verdict]?.dot || VERDICT_META.unverified.dot}
                  >
                    {claim.verdict_label}
                  </Badge>
                  <span className="text-[10px] uppercase tracking-[0.1em] text-ink-soft">{claim.category}</span>
                  <span className="text-[10px] text-ink-soft">
                    Extraction confidence {(claim.confidence * 100).toFixed(0)}% (not truth probability)
                  </span>
                </div>
                <p className="mt-2.5 text-[14px] font-medium leading-relaxed text-ink">{claim.text}</p>
                <p className="mt-1.5 text-[12px] leading-relaxed text-ink-soft">{claim.verdict_basis}</p>

                {claim.evidence.length ? (
                  <ul className="mt-3 space-y-2.5">
                    {claim.evidence.map((evidence) => (
                      <li key={evidence.id} className="rounded-lg border border-line bg-surface/50 p-3">
                        <div className="flex flex-wrap items-center gap-2 text-[10px]">
                          <span
                            className={cn(
                              "rounded-full px-2 py-0.5 font-semibold",
                              evidence.relationship === "supports"
                                ? "bg-[#EDF6F1] text-support"
                                : evidence.relationship === "contradicts"
                                  ? "bg-[#FBEDEB] text-contradict"
                                  : "bg-[#FBF4E7] text-caution",
                            )}
                          >
                            {evidence.relationship}
                          </span>
                          <span className="text-ink-soft">{evidence.source_type}</span>
                          {evidence.stale ? <span className="text-caution">stale source</span> : null}
                        </div>
                        <blockquote className="mt-2 border-l-2 border-powder pl-2.5 text-[12px] leading-relaxed text-ink">
                          “{evidence.excerpt}”
                        </blockquote>
                        <p className="mt-1.5 text-[11px] leading-relaxed text-ink-soft">{evidence.explanation}</p>
                        <p className="mt-1.5 text-[10px] text-ink-soft">
                          <a
                            href={evidence.source_url}
                            target="_blank"
                            rel="noreferrer noopener"
                            className="font-medium text-powder-deep hover:underline"
                          >
                            {evidence.source_title}
                          </a>
                          {" · retrieved "}
                          {formatDateTime(evidence.retrieved_at)}
                          {evidence.source_updated_at
                            ? ` · source last updated ${formatDateTime(evidence.source_updated_at)}`
                            : ""}
                        </p>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-2 text-[12px] italic text-ink-soft">
                    No evidence excerpt cleared the relevance threshold.
                  </p>
                )}

                {claim.conflicts.length ? (
                  <div className="mt-3 rounded-lg border border-contradict/25 bg-[#FBEDEB] p-3">
                    <p className="flex items-center gap-1.5 text-[11px] font-semibold text-contradict">
                      <ShieldAlert className="size-3.5" aria-hidden />
                      Recorded conflicts
                    </p>
                    {claim.conflicts.map((conflict) => (
                      <p key={conflict.id} className="mt-1 text-[11px] leading-relaxed text-contradict/90">
                        {conflict.kind.replaceAll("_", " ")} ({conflict.severity}): {conflict.summary}
                      </p>
                    ))}
                  </div>
                ) : null}
              </li>
            ))}
          </ol>
        </section>

        <section className="border-b border-line px-5 py-6 md:px-8">
          <h3 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-ink-soft">
            Source references
          </h3>
          <ul className="mt-3 space-y-2.5">
            {report.sources.map((source) => (
              <li key={source.id} className="rounded-lg border border-line p-3">
                <a
                  href={source.url}
                  target="_blank"
                  rel="noreferrer noopener"
                  className="inline-flex items-center gap-1 text-[13px] font-medium text-powder-deep hover:underline"
                >
                  {source.title}
                  <ExternalLink className="size-3" aria-hidden />
                </a>
                <p className="mt-1 text-[11px] text-ink-soft">
                  {source.publisher} · {source.source_type} · {source.quality} quality · retrieved{" "}
                  {formatDateTime(source.retrieved_at)}
                </p>
                <p className="mt-0.5 text-[11px] text-ink-soft">{source.quality_note}</p>
              </li>
            ))}
          </ul>
        </section>

        <section className="border-b border-line px-5 py-6 md:px-8">
          <h3 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-ink-soft">
            Limitations and uncertainty
          </h3>
          <ul className="mt-3 list-disc space-y-2 pl-5 text-[12px] leading-relaxed text-ink-soft">
            {report.limitations.map((limitation) => (
              <li key={limitation}>{limitation}</li>
            ))}
          </ul>
        </section>

        <section className="px-5 py-6 md:px-8">
          <h3 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-ink-soft">Methodology</h3>
          <ol className="mt-3 list-decimal space-y-1.5 pl-5 text-[12px] leading-relaxed text-ink-soft">
            {report.methodology.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
          <p className="mt-5 rounded-xl bg-lavender/60 p-4 text-[12px] leading-relaxed text-ink">
            {report.disclaimer}
          </p>
        </section>
      </div>
    </div>
  );
}
