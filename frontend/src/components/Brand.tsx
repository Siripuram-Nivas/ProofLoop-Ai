import { Link } from "react-router-dom";
import { cn } from "./ui";

export function BrandMark({ className, dark = false }: { className?: string; dark?: boolean }) {
  return (
    <svg
      viewBox="0 0 40 40"
      className={cn("size-9", className)}
      role="img"
      aria-label="ProofLoop AI mark"
    >
      <rect width="40" height="40" rx="11" fill={dark ? "#E9E8F8" : "#171923"} />
      <circle
        cx="20"
        cy="20"
        r="10"
        fill="none"
        stroke={dark ? "#171923" : "#80B9F0"}
        strokeWidth="2.4"
        strokeDasharray="42 21"
        strokeLinecap="round"
        transform="rotate(-32 20 20)"
      />
      <circle cx="20" cy="20" r="3.2" fill="#F5B69E" />
      <circle cx="30.5" cy="11.5" r="2.6" fill={dark ? "#171923" : "#80B9F0"} />
    </svg>
  );
}

export function Brand({
  className,
  dark = false,
  compact = false,
}: {
  className?: string;
  dark?: boolean;
  compact?: boolean;
}) {
  return (
    <Link to="/" className={cn("inline-flex items-center gap-2.5", className)} aria-label="ProofLoop AI home">
      <BrandMark dark={dark} />
      {compact ? null : (
        <span className="flex flex-col leading-none">
          <span className={cn("text-[17px] font-semibold tracking-[-0.02em]", dark ? "text-white" : "text-ink")}>
            ProofLoop
          </span>
          <span
            className={cn(
              "mt-0.5 text-[9px] font-semibold uppercase tracking-[0.24em]",
              dark ? "text-white/55" : "text-ink-soft",
            )}
          >
            Evidence intelligence
          </span>
        </span>
      )}
    </Link>
  );
}
