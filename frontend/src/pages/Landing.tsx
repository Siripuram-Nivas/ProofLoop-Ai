import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  ArrowUpRight,
  BadgeCheck,
  BookOpenCheck,
  Bot,
  Boxes,
  CircleDot,
  FileSearch,
  FileText,
  Fingerprint,
  GitCompareArrows,
  Layers,
  Menu,
  Network,
  Radar,
  ScanText,
  ShieldAlert,
  ShieldCheck,
  X,
} from "lucide-react";
import { Brand } from "../components/Brand";
import { Hero } from "../components/landing/Hero";
import { EvidenceGraph } from "../components/EvidenceGraph";
import { buttonClass, cn, SectionHeading } from "../components/ui";
import type { GraphData } from "../lib/types";

const NAV = [
  { label: "Product", href: "#product" },
  { label: "How it works", href: "#how-it-works" },
  { label: "Evidence graph", href: "#evidence-graph" },
  { label: "Technology", href: "#technology" },
];

const SAMPLE_GRAPH: GraphData = {
  nodes: [
    {
      id: "sample-claim",
      kind: "claim",
      label: "The Eiffel Tower is 330 metres tall.",
      verdict: "supported",
    },
    {
      id: "sample-evidence",
      kind: "evidence",
      label:
        "The tower is 330 metres (1,083 ft) tall, about the same height as an 81-storey building, and the tallest structure in Paris.",
      relationship: "supports",
      matchKind: "numeric",
      sourceTitle: "Eiffel Tower",
      sourceUrl: "https://en.wikipedia.org/wiki/Eiffel_Tower",
    },
    {
      id: "sample-source",
      kind: "source",
      label: "Eiffel Tower — Wikipedia",
      url: "https://en.wikipedia.org/wiki/Eiffel_Tower",
      quality: "Medium",
      sourceType: "Tertiary reference",
    },
  ],
  edges: [
    { id: "sample-e1", source: "sample-claim", target: "sample-evidence", label: "supports", kind: "supports" },
    {
      id: "sample-e2",
      source: "sample-evidence",
      target: "sample-source",
      label: "derived from",
      kind: "derived_from",
    },
  ],
};

const PROBLEMS = [
  {
    icon: Bot,
    title: "Confidence without evidence",
    body: "Answers can sound certain while resting on no checkable source. Fluency is not proof.",
  },
  {
    icon: GitCompareArrows,
    title: "Sources that disagree",
    body: "Reports conflict, figures drift between editions, and pages change after you read them.",
  },
  {
    icon: Fingerprint,
    title: "Conclusions without a trail",
    body: "When the reasoning is hidden, nobody can re-check it. A verdict you cannot trace is a guess.",
  },
];

const WORKFLOW = [
  { icon: Layers, title: "Input", body: "Paste text, a PDF, or a URL. The original is preserved." },
  { icon: ScanText, title: "Claim extraction", body: "Compound statements become independent claims." },
  { icon: FileSearch, title: "Source research", body: "Real pages are retrieved with URLs and timestamps." },
  { icon: BadgeCheck, title: "Evidence evaluation", body: "Relevance, numbers, and dates compared deterministically." },
  { icon: Network, title: "Evidence graph", body: "Claims, excerpts, and sources become one inspectable trail." },
  { icon: FileText, title: "Proof report", body: "Findings, conflicts, and limitations in one auditable snapshot." },
];

const AGENTS = [
  {
    icon: ScanText,
    name: "Claim Extraction",
    body: "Splits input into atomic claims and records the original span, entities, numbers, and dates.",
    tag: "Deterministic (+ optional LLM)",
  },
  {
    icon: FileSearch,
    name: "Research",
    body: "Searches a live source provider and keeps the exact excerpt, URL, publisher, and retrieval time.",
    tag: "Live retrieval",
  },
  {
    icon: ShieldCheck,
    name: "Source Quality",
    body: "Labels source type and authority in context. A passage's relevance is judged separately.",
    tag: "Rule-based",
  },
  {
    icon: GitCompareArrows,
    name: "Contradiction Detection",
    body: "Compares numeric values and years with explicit tolerances. Disagreement is reported, not resolved.",
    tag: "Deterministic",
  },
  {
    icon: BadgeCheck,
    name: "Verification",
    body: "Aggregates support, contradiction, and insufficiency into a conservative verdict.",
    tag: "Deterministic",
  },
  {
    icon: FileText,
    name: "Report",
    body: "Assembles the snapshot, source index, and limitations. It cannot add facts of its own.",
    tag: "Assembled from records",
  },
];

const RADAR_SIGNALS = [
  { label: "Numeric disagreement", detail: "Two sources report different values for the same metric", icon: GitCompareArrows },
  { label: "Date mismatch", detail: "The claim's year does not match the retrieved passage", icon: ShieldAlert },
  { label: "Reporting-time gap", detail: "One source is materially older than another", icon: FileSearch },
  { label: "Unresolved uncertainty", detail: "No excerpt clears the evidence threshold", icon: CircleDot },
];

export function Landing() {
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    document.title = "ProofLoop AI — Don't just trust an answer. Follow the proof.";
  }, []);

  return (
    <div className="min-h-screen bg-surface">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-ink focus:px-4 focus:py-2 focus:text-white"
      >
        Skip to content
      </a>
      <header className="sticky top-0 z-40 border-b border-line/70 bg-surface/85 backdrop-blur-lg">
        <div className="page-wrap flex h-16 items-center justify-between gap-6">
          <Brand />
          <nav className="hidden items-center gap-7 lg:flex" aria-label="Main">
            {NAV.map((item) => (
              <a
                key={item.href}
                href={item.href}
                className="text-[13px] font-medium text-ink-soft transition-colors hover:text-ink"
              >
                {item.label}
              </a>
            ))}
          </nav>
          <div className="hidden items-center gap-2 lg:flex">
            <Link to="/auth" className={buttonClass("ghost", "sm")}>
              Sign in
            </Link>
            <Link to="/app/new" className={buttonClass("primary", "sm")}>
              Get started
              <ArrowRight className="size-3.5" aria-hidden />
            </Link>
          </div>
          <button
            type="button"
            className="grid size-10 place-items-center rounded-xl border border-line bg-white text-ink lg:hidden"
            aria-label={menuOpen ? "Close menu" : "Open menu"}
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((value) => !value)}
          >
            {menuOpen ? <X className="size-5" aria-hidden /> : <Menu className="size-5" aria-hidden />}
          </button>
        </div>
        {menuOpen ? (
          <div className="border-t border-line bg-surface px-5 py-4 lg:hidden">
            <nav className="flex flex-col" aria-label="Mobile">
              {NAV.map((item) => (
                <a
                  key={item.href}
                  href={item.href}
                  onClick={() => setMenuOpen(false)}
                  className="border-b border-line/70 py-3 text-sm font-medium text-ink"
                >
                  {item.label}
                </a>
              ))}
            </nav>
            <div className="mt-4 flex gap-2">
              <Link to="/auth" className={cn(buttonClass("secondary", "md"), "flex-1")}>
                Sign in
              </Link>
              <Link to="/app/new" className={cn(buttonClass("primary", "md"), "flex-1")}>
                Get started
              </Link>
            </div>
          </div>
        ) : null}
      </header>

      <main id="main">
        <Hero />

        <section id="product" className="border-y border-line/70 bg-white py-20 md:py-28">
          <div className="page-wrap">
            <SectionHeading
              eyebrow="The problem"
              title={
                <>
                  Information is everywhere.
                  <br />
                  <span className="italic text-ink-soft">Proof is not.</span>
                </>
              }
              description="ProofLoop exists to separate a confident sentence from a checkable one — and to keep the difference visible."
            />
            <div className="mt-12 grid gap-5 md:grid-cols-3">
              {PROBLEMS.map((problem, index) => (
                <article key={problem.title} className="rounded-2xl border border-line bg-surface/60 p-6">
                  <div className="flex items-center justify-between">
                    <span className="grid size-10 place-items-center rounded-xl border border-line bg-white text-ink">
                      <problem.icon className="size-4.5" aria-hidden />
                    </span>
                    <span className="display text-3xl text-ink/15">0{index + 1}</span>
                  </div>
                  <h3 className="mt-5 text-[15px] font-semibold text-ink">{problem.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-ink-soft">{problem.body}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section id="how-it-works" className="py-20 md:py-28">
          <div className="page-wrap">
            <div className="grid gap-10 lg:grid-cols-[0.9fr_1.1fr] lg:gap-16">
              <div>
                <SectionHeading
                  eyebrow="The loop"
                  title={
                    <>
                      From claims to
                      <br />
                      <span className="italic text-powder-deep">verifiable evidence.</span>
                    </>
                  }
                  description="Every stage writes a structured record. Nothing is hidden inside a chat transcript, and nothing is treated as evidence unless it came from a source."
                />
                <Link to="/app/new" className={cn(buttonClass("primary", "md"), "mt-7")}>
                  Start a verification
                  <ArrowRight className="size-4" aria-hidden />
                </Link>
              </div>
              <ol className="grid gap-3 sm:grid-cols-2">
                {WORKFLOW.map((step, index) => (
                  <li key={step.title} className="relative rounded-2xl border border-line bg-white p-5">
                    <div className="flex items-center gap-2.5">
                      <span className="grid size-8 place-items-center rounded-lg bg-lavender text-ink">
                        <step.icon className="size-4" aria-hidden />
                      </span>
                      <span className="text-[10px] font-semibold uppercase tracking-[0.16em] text-ink-soft">
                        Step {index + 1}
                      </span>
                    </div>
                    <h3 className="mt-3.5 text-sm font-semibold text-ink">{step.title}</h3>
                    <p className="mt-1.5 text-[13px] leading-relaxed text-ink-soft">{step.body}</p>
                  </li>
                ))}
              </ol>
            </div>
          </div>
        </section>

        <section id="evidence-graph" className="border-y border-line/70 bg-white py-20 md:py-28">
          <div className="page-wrap">
            <div className="flex flex-col justify-between gap-6 lg:flex-row lg:items-end">
              <SectionHeading
                eyebrow="Evidence graph"
                title={
                  <>
                    Every claim has
                    <br />
                    <span className="italic text-powder-deep">a trail.</span>
                  </>
                }
                description="Explore the relationship between a claim, the excerpt that supports or contradicts it, and the source it came from. This is the interface, populated with labelled sample data."
              />
              <a href="#technology" className={cn(buttonClass("secondary", "sm"), "shrink-0")}>
                How verification works
                <ArrowUpRight className="size-3.5" aria-hidden />
              </a>
            </div>
            <div className="mt-10 grid gap-8 lg:grid-cols-[1.35fr_0.65fr]">
              <EvidenceGraph graph={SAMPLE_GRAPH} height={430} sample />
              <div className="space-y-4">
                {[
                  ["Claim nodes", "Each independent statement, with its verdict and category."],
                  ["Evidence nodes", "The exact retrieved excerpt. Numeric matches and conflicts are explained."],
                  ["Source nodes", "The page, its URL, type, quality note, and retrieval time."],
                ].map(([title, body]) => (
                  <div key={title} className="rounded-xl border border-line bg-surface/70 p-4">
                    <h3 className="text-[13px] font-semibold text-ink">{title}</h3>
                    <p className="mt-1 text-[12px] leading-relaxed text-ink-soft">{body}</p>
                  </div>
                ))}
                <p className="rounded-xl border border-powder/40 bg-[#F1F8FE] p-4 text-[12px] leading-relaxed text-[#25557a]">
                  The sample above is illustrative and labelled. In the app, the graph is generated only
                  from stored verification records.
                </p>
              </div>
            </div>
          </div>
        </section>

        <section id="radar" className="py-20 md:py-28">
          <div className="page-wrap grid gap-12 lg:grid-cols-2 lg:items-center">
            <div>
              <SectionHeading
                eyebrow="Contradiction radar"
                title={
                  <>
                    Find disagreements
                    <br />
                    before they become decisions.
                  </>
                }
                description="When sources disagree, ProofLoop shows both passages and the dates behind them. It does not declare a winner because one page is newer or more popular."
              />
              <ul className="mt-8 space-y-4">
                {RADAR_SIGNALS.map((signal) => (
                  <li key={signal.label} className="flex gap-3">
                    <span className="mt-0.5 grid size-8 shrink-0 place-items-center rounded-lg border border-line bg-white text-ink">
                      <signal.icon className="size-4" aria-hidden />
                    </span>
                    <div>
                      <p className="text-sm font-semibold text-ink">{signal.label}</p>
                      <p className="text-[13px] leading-relaxed text-ink-soft">{signal.detail}</p>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
            <div className="relative">
              <div className="card overflow-hidden">
                <div className="flex items-center justify-between border-b border-line px-5 py-4">
                  <div className="flex items-center gap-2">
                    <Radar className="size-4 text-peach-deep" aria-hidden />
                    <span className="text-sm font-semibold">Conflict workspace</span>
                  </div>
                  <span className="rounded-full border border-peach-deep/25 bg-[#FDF1EC] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.12em] text-peach-deep">
                    Interface illustration
                  </span>
                </div>
                <div className="space-y-3 p-5">
                  <div className="rounded-xl border border-line bg-surface/60 p-4">
                    <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-ink-soft">
                      Claim under review
                    </p>
                    <div className="mt-2 space-y-1.5" aria-hidden>
                      <div className="h-2 w-11/12 rounded bg-ink/15" />
                      <div className="h-2 w-2/3 rounded bg-ink/10" />
                    </div>
                  </div>
                  <div className="grid gap-3 sm:grid-cols-2">
                    {["Source A", "Source B"].map((source) => (
                      <div key={source} className="rounded-xl border border-line bg-white p-4">
                        <div className="flex items-center justify-between">
                          <span className="text-[11px] font-semibold text-ink">{source}</span>
                          <span className="text-[10px] text-ink-soft">date</span>
                        </div>
                        <div className="mt-3 space-y-1.5" aria-hidden>
                          <div className="h-1.5 w-full rounded bg-lavender" />
                          <div className="h-1.5 w-5/6 rounded bg-lavender" />
                          <div className="h-1.5 w-3/4 rounded bg-lavender" />
                        </div>
                        <div className="mt-3 flex items-center gap-1.5 text-[10px] text-caution">
                          <ShieldAlert className="size-3" aria-hidden />
                          Values shown only when a real conflict is stored
                        </div>
                      </div>
                    ))}
                  </div>
                  <div className="rounded-xl border border-dashed border-line p-4 text-center text-[12px] text-ink-soft">
                    No automatic winner. Both readings stay attached to the report.
                  </div>
                </div>
              </div>
              <div className="absolute -bottom-4 -right-3 -z-10 size-32 rounded-full bg-peach/30 blur-2xl" aria-hidden />
            </div>
          </div>
        </section>

        <section id="technology" className="border-y border-line/70 bg-ink py-20 text-white md:py-28">
          <div className="page-wrap">
            <div className="max-w-2xl">
              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-powder">Technology</p>
              <h2 className="display mt-4 text-4xl md:text-5xl">
                Multiple perspectives.
                <br />
                <span className="italic text-powder">One traceable result.</span>
              </h2>
              <p className="mt-4 text-[15px] leading-relaxed text-white/65">
                Six responsibilities, coordinated through one structured record. They are not six
                independent chatbots, and no model is allowed to supply evidence.
              </p>
            </div>
            <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {AGENTS.map((agent) => (
                <article key={agent.name} className="rounded-2xl border border-white/12 bg-white/[0.045] p-5">
                  <span className="grid size-9 place-items-center rounded-lg bg-white/10 text-powder">
                    <agent.icon className="size-4" aria-hidden />
                  </span>
                  <h3 className="mt-4 text-sm font-semibold text-white">{agent.name}</h3>
                  <p className="mt-1.5 text-[13px] leading-relaxed text-white/60">{agent.body}</p>
                  <p className="mt-3 inline-block rounded-full border border-white/12 px-2.5 py-1 text-[10px] text-white/55">
                    {agent.tag}
                  </p>
                </article>
              ))}
            </div>
            <div className="mt-10 grid gap-4 rounded-2xl border border-white/12 bg-white/[0.03] p-6 md:grid-cols-3">
              {[
                ["Real sources only", "Every excerpt has a URL, publisher, and retrieval timestamp. If a source cannot be read, that limitation is recorded."],
                ["Deterministic comparison", "Numbers and years are compared in code with documented tolerances. There is no model confidence pretending to be evidence strength."],
                ["Uncertainty preserved", "Unverified is not false. Conflicting sources stay conflicting, and the report says so explicitly."],
              ].map(([title, body]) => (
                <div key={title}>
                  <div className="flex items-center gap-2 text-[13px] font-semibold text-white">
                    <ShieldCheck className="size-4 text-support" style={{ color: "#8fd3b4" }} aria-hidden />
                    {title}
                  </div>
                  <p className="mt-1.5 text-[12px] leading-relaxed text-white/55">{body}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="py-20 md:py-28">
          <div className="page-wrap">
            <div className="relative overflow-hidden rounded-[28px] border border-line bg-lavender px-6 py-14 text-center md:px-14 md:py-20">
              <div className="pointer-events-none absolute -left-10 top-6 size-48 rounded-full bg-powder/40 blur-3xl" aria-hidden />
              <div className="pointer-events-none absolute -right-6 bottom-0 size-44 rounded-full bg-peach/50 blur-3xl" aria-hidden />
              <p className="eyebrow relative">Ready when you are</p>
              <h2 className="display relative mx-auto mt-4 max-w-2xl text-4xl md:text-6xl">
                Ready to follow
                <br />
                <span className="italic text-powder-deep">the proof?</span>
              </h2>
              <p className="relative mx-auto mt-4 max-w-lg text-sm leading-relaxed text-ink-soft">
                Bring a statement, a document, or a link. ProofLoop will show you what the evidence
                supports — and what it does not.
              </p>
              <div className="relative mt-8 flex flex-wrap justify-center gap-3">
                <Link to="/app/new" className={buttonClass("primary", "lg")}>
                  Start Verifying
                  <ArrowRight className="size-4" aria-hidden />
                </Link>
                <Link to="/app" className={buttonClass("secondary", "lg")}>
                  Open the workspace
                </Link>
              </div>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-line bg-white">
        <div className="page-wrap grid gap-10 py-14 md:grid-cols-[1.4fr_1fr_1fr_1fr]">
          <div>
            <Brand />
            <p className="mt-4 max-w-xs text-[13px] leading-relaxed text-ink-soft">
              Evidence intelligence for people who need to know why a conclusion is trustworthy — and
              where it stops being trustworthy.
            </p>
          </div>
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-ink-soft">Product</p>
            <ul className="mt-3.5 space-y-2.5 text-[13px]">
              <li><a href="#how-it-works" className="text-ink-soft hover:text-ink">How it works</a></li>
              <li><a href="#evidence-graph" className="text-ink-soft hover:text-ink">Evidence graph</a></li>
              <li><a href="#radar" className="text-ink-soft hover:text-ink">Contradiction radar</a></li>
              <li><Link to="/app/new" className="text-ink-soft hover:text-ink">New verification</Link></li>
            </ul>
          </div>
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-ink-soft">Resources</p>
            <ul className="mt-3.5 space-y-2.5 text-[13px]">
              <li><a href="#technology" className="text-ink-soft hover:text-ink">Methodology</a></li>
              <li><Link to="/app/settings" className="text-ink-soft hover:text-ink">Capabilities</Link></li>
              <li><a href="/api/v1/health" className="text-ink-soft hover:text-ink">API status</a></li>
            </ul>
          </div>
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-ink-soft">Account</p>
            <ul className="mt-3.5 space-y-2.5 text-[13px]">
              <li><Link to="/auth" className="text-ink-soft hover:text-ink">Sign in</Link></li>
              <li><Link to="/app" className="text-ink-soft hover:text-ink">Workspace</Link></li>
            </ul>
          </div>
        </div>
        <div className="border-t border-line">
          <div className="page-wrap flex flex-col items-start justify-between gap-3 py-5 text-[11px] text-ink-soft md:flex-row md:items-center">
            <p>© {new Date().getFullYear()} ProofLoop AI. Built for verifiable conclusions.</p>
            <p className="flex flex-wrap items-center gap-x-4 gap-y-1">
              <span className="inline-flex items-center gap-1.5">
                <BookOpenCheck className="size-3.5" aria-hidden />
                Research powered by live public sources
              </span>
              <span className="inline-flex items-center gap-1.5">
                <Boxes className="size-3.5" aria-hidden />
                No fabricated evidence
              </span>
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
