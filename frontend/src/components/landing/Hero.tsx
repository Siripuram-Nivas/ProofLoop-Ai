import { Link } from "react-router-dom";
import { ArrowRight, BadgeCheck, CircleDot, GitFork, Layers, ShieldCheck } from "lucide-react";
import { buttonClass } from "../ui";

function FloatingCard({
  className,
  label,
  value,
  tone,
  icon: Icon,
}: {
  className: string;
  label: string;
  value: string;
  tone: string;
  icon: typeof BadgeCheck;
}) {
  return (
    <div
      className={`absolute z-10 flex items-center gap-2.5 rounded-xl border border-white/70 bg-white/85 px-3 py-2 shadow-[0_18px_40px_-24px_rgba(23,25,35,0.5)] backdrop-blur-md ${className}`}
    >
      <span className={`grid size-7 place-items-center rounded-lg ${tone}`}>
        <Icon className="size-3.5" aria-hidden />
      </span>
      <span className="leading-tight">
        <span className="block text-[9px] font-semibold uppercase tracking-[0.14em] text-ink-soft">
          {label}
        </span>
        <span className="block text-[12px] font-medium text-ink">{value}</span>
      </span>
    </div>
  );
}

export function Hero() {
  return (
    <section className="relative overflow-hidden pb-20 pt-10 md:pb-28 md:pt-16">
      <div
        className="pointer-events-none absolute inset-0 -z-10 opacity-70"
        style={{
          background:
            "radial-gradient(60% 55% at 82% 12%, rgba(245,182,158,0.28) 0%, transparent 60%), radial-gradient(50% 45% at 12% 8%, rgba(128,185,240,0.24) 0%, transparent 65%)",
        }}
      />
      <div className="page-wrap grid items-center gap-12 lg:grid-cols-[1.02fr_0.98fr] lg:gap-16">
        <div className="max-w-xl">
          <p className="inline-flex items-center gap-2 rounded-full border border-line bg-white/70 px-3 py-1.5 text-[11px] font-medium text-ink-soft backdrop-blur">
            <span className="size-1.5 rounded-full bg-support" aria-hidden />
            Evidence intelligence, not answer generation
          </p>
          <h1 className="display mt-6 text-[52px] leading-[0.95] text-ink sm:text-[64px] lg:text-[72px]">
            Don&rsquo;t just trust
            <br />
            an answer.
            <br />
            <span className="italic text-powder-deep">Follow the proof.</span>
          </h1>
          <p className="mt-6 max-w-lg text-[15px] leading-relaxed text-ink-soft md:text-base">
            Turn information into verifiable evidence. Extract claims, investigate authoritative
            sources, uncover contradictions, and follow every conclusion back to its proof.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-3">
            <Link to="/app/new" className={buttonClass("primary", "lg")}>
              Verify a Claim
              <ArrowRight className="size-4" aria-hidden />
            </Link>
            <a href="#how-it-works" className={buttonClass("secondary", "lg")}>
              Explore How It Works
            </a>
          </div>
          <ul className="mt-8 flex flex-wrap gap-x-6 gap-y-2.5 text-[12px] text-ink-soft">
            {[
              "Live source retrieval",
              "Excerpts with URLs",
              "Uncertainty stays visible",
            ].map((item) => (
              <li key={item} className="flex items-center gap-1.5">
                <ShieldCheck className="size-3.5 text-support" aria-hidden />
                {item}
              </li>
            ))}
          </ul>
        </div>

        <div className="relative mx-auto w-full max-w-[520px]">
          <div className="sculpture aspect-[4/5] w-full">
            <div className="sculpture__blob sculpture__blob--a" />
            <div className="sculpture__blob sculpture__blob--b" />
            <div className="sculpture__blob sculpture__blob--c" />
            <div className="sculpture__ring" />
            <div className="sculpture__ring" style={{ inset: "22%", transform: "rotate(24deg)" }} />
            <div className="sculpture__grain" />
            <div className="absolute inset-0 grid place-items-center">
              <div className="text-center">
                <div className="mx-auto grid size-16 place-items-center rounded-full border border-white/60 bg-white/30 backdrop-blur-sm">
                  <span className="display text-2xl text-ink">Proof</span>
                </div>
                <p className="mt-3 text-[10px] font-semibold uppercase tracking-[0.28em] text-ink/60">
                  claim → evidence → report
                </p>
              </div>
            </div>
          </div>
          <FloatingCard
            className="-left-3 top-[18%] float-slow md:-left-6"
            label="Atomic claim"
            value="One checkable statement"
            tone="bg-ink text-white"
            icon={CircleDot}
          />
          <FloatingCard
            className="-right-2 top-[40%] md:-right-5"
            label="Supporting source"
            value="Excerpt + URL + date"
            tone="bg-[#EDF6F1] text-support"
            icon={BadgeCheck}
          />
          <FloatingCard
            className="bottom-[14%] left-2 md:left-6"
            label="Unresolved"
            value="Kept visible, never guessed"
            tone="bg-[#FDF1EC] text-peach-deep"
            icon={GitFork}
          />
          <FloatingCard
            className="bottom-[2%] right-3 md:right-8"
            label="Proof report"
            value="Every conclusion traceable"
            tone="bg-[#F1F8FE] text-powder-deep"
            icon={Layers}
          />
          <p className="mt-3 text-center text-[10px] text-ink-soft/70">
            Illustration of the verification loop — not a live result.
          </p>
        </div>
      </div>
    </section>
  );
}
