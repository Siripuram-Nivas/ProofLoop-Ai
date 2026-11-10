import { AlertTriangle, Check, Circle, Loader2 } from "lucide-react";
import { cn } from "./ui";
import type { Stage } from "../lib/types";

export function StageTimeline({ stages }: { stages: Stage[] }) {
  return (
    <ol className="grid gap-2 sm:grid-cols-3 lg:grid-cols-6" aria-label="Verification stages">
      {stages.map((stage) => {
        const active = stage.status === "active";
        const done = stage.status === "done";
        const failed = stage.status === "failed";
        const partial = stage.status === "partial";
        return (
          <li
            key={stage.key}
            className={cn(
              "relative rounded-xl border px-3 py-2.5",
              active && "border-powder-deep/30 bg-[#F1F8FE]",
              done && "border-support/20 bg-[#F3FAF6]",
              failed && "border-contradict/25 bg-[#FDF3F1]",
              partial && "border-caution/30 bg-[#FCF7EC]",
              !active && !done && !failed && !partial && "border-line bg-white",
            )}
            aria-current={active ? "step" : undefined}
          >
            <div className="flex items-center gap-1.5">
              <span
                className={cn(
                  "grid size-4 shrink-0 place-items-center rounded-full",
                  done && "bg-support text-white",
                  active && "bg-powder-deep text-white",
                  failed && "bg-contradict text-white",
                  partial && "bg-caution text-white",
                  !active && !done && !failed && !partial && "bg-lavender text-ink-soft",
                )}
              >
                {done ? (
                  <Check className="size-2.5" aria-hidden />
                ) : active ? (
                  <Loader2 className="size-2.5 animate-spin" aria-hidden />
                ) : failed || partial ? (
                  <AlertTriangle className="size-2.5" aria-hidden />
                ) : (
                  <Circle className="size-2" aria-hidden />
                )}
              </span>
              <span className="text-[10px] font-semibold uppercase tracking-[0.08em] text-ink-soft">
                {stage.label}
              </span>
            </div>
            {stage.detail ? (
              <p className="mt-1.5 line-clamp-2 text-[11px] leading-snug text-ink-soft" title={stage.detail}>
                {stage.detail}
              </p>
            ) : (
              <p className="mt-1.5 text-[11px] text-ink-soft/50">{active ? "Working…" : "Pending"}</p>
            )}
          </li>
        );
      })}
    </ol>
  );
}
