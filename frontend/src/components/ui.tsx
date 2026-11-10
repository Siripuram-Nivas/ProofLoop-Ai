import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode, TextareaHTMLAttributes } from "react";
import { Loader2, type LucideIcon } from "lucide-react";
import { VERDICT_META } from "../lib/format";
import type { Verdict } from "../lib/types";

export function cn(...values: Array<string | false | null | undefined>): string {
  return values.filter(Boolean).join(" ");
}

type Variant = "primary" | "secondary" | "ghost" | "peach" | "danger";
type Size = "sm" | "md" | "lg";

const VARIANTS: Record<Variant, string> = {
  primary: "bg-ink text-white hover:bg-[#262936] border border-ink",
  secondary: "bg-white text-ink border border-line hover:border-ink/35",
  ghost: "bg-transparent text-ink-soft border border-transparent hover:bg-lavender/70 hover:text-ink",
  peach: "bg-peach text-ink border border-peach hover:bg-[#f2a98f]",
  danger: "bg-white text-contradict border border-contradict/30 hover:bg-[#FBEDEB]",
};

const SIZES: Record<Size, string> = {
  sm: "h-9 px-3.5 text-[13px] gap-1.5 rounded-[10px]",
  md: "h-11 px-5 text-sm gap-2 rounded-xl",
  lg: "h-12 px-6 text-[15px] gap-2 rounded-xl",
};

export function buttonClass(variant: Variant = "primary", size: Size = "md"): string {
  return cn(
    "inline-flex items-center justify-center font-medium transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-45",
    VARIANTS[variant],
    SIZES[size],
  );
}

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  icon?: LucideIcon;
}

export function Button({
  variant = "primary",
  size = "md",
  loading,
  icon: Icon,
  className,
  children,
  disabled,
  ...rest
}: ButtonProps) {
  return (
    <button
      className={cn(buttonClass(variant, size), className)}
      disabled={disabled || loading}
      {...rest}
    >
      {loading ? <Loader2 className="size-4 animate-spin" aria-hidden /> : Icon ? <Icon className="size-4" aria-hidden /> : null}
      {children}
    </button>
  );
}

export function Card({ className, children }: { className?: string; children: ReactNode }) {
  return <div className={cn("card", className)}>{children}</div>;
}

export function Badge({
  children,
  className,
  dot,
}: {
  children: ReactNode;
  className?: string;
  dot?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium leading-none",
        className,
      )}
    >
      {dot ? <span className={cn("size-1.5 rounded-full", dot)} aria-hidden /> : null}
      {children}
    </span>
  );
}

export function VerdictBadge({ verdict, className }: { verdict: Verdict; className?: string }) {
  const meta = VERDICT_META[verdict] || VERDICT_META.unverified;
  return (
    <Badge className={cn(meta.tone, className)} dot={meta.dot}>
      {meta.label}
    </Badge>
  );
}

export function Spinner({ className }: { className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-2 text-sm text-ink-soft", className)}>
      <Loader2 className="size-4 animate-spin" aria-hidden />
      Loading
    </span>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("animate-pulse rounded-lg bg-lavender/80", className)} aria-hidden />;
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  className,
}: {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-col items-center justify-center px-6 py-14 text-center", className)}>
      <span className="mb-4 grid size-12 place-items-center rounded-2xl border border-line bg-lavender/60 text-ink">
        <Icon className="size-5" aria-hidden />
      </span>
      <h3 className="text-base font-semibold text-ink">{title}</h3>
      <p className="mt-1.5 max-w-md text-sm leading-relaxed text-ink-soft">{description}</p>
      {action ? <div className="mt-5">{action}</div> : null}
    </div>
  );
}

export function Field({
  label,
  hint,
  error,
  htmlFor,
  children,
  optional,
}: {
  label: string;
  hint?: string;
  error?: string;
  htmlFor?: string;
  children: ReactNode;
  optional?: boolean;
}) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-baseline justify-between gap-3">
        <label htmlFor={htmlFor} className="text-[13px] font-semibold text-ink">
          {label}
          {optional ? <span className="ml-1.5 font-normal text-ink-soft">optional</span> : null}
        </label>
        {hint ? <span className="text-[11px] text-ink-soft">{hint}</span> : null}
      </div>
      {children}
      {error ? <p className="text-xs text-contradict">{error}</p> : null}
    </div>
  );
}

const controlClass =
  "w-full rounded-xl border border-line bg-white px-3.5 py-3 text-sm text-ink placeholder:text-ink-soft/60 transition-colors focus:border-powder-deep focus:outline-none focus:ring-2 focus:ring-powder/30 disabled:bg-lavender/40";

export function Input({ className, ...rest }: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={cn(controlClass, "h-11 py-0", className)} {...rest} />;
}

export function Textarea({ className, ...rest }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea className={cn(controlClass, "min-h-32 resize-y leading-relaxed", className)} {...rest} />;
}

export function InlineAlert({
  tone = "info",
  children,
  className,
}: {
  tone?: "info" | "error" | "warn" | "success";
  children: ReactNode;
  className?: string;
}) {
  const tones = {
    info: "border-powder/50 bg-[#F1F8FE] text-[#25557a]",
    error: "border-contradict/30 bg-[#FBEDEB] text-contradict",
    warn: "border-caution/30 bg-[#FBF4E7] text-caution",
    success: "border-support/25 bg-[#EDF6F1] text-support",
  };
  return (
    <div
      role={tone === "error" ? "alert" : "status"}
      className={cn("rounded-xl border px-4 py-3 text-[13px] leading-relaxed", tones[tone], className)}
    >
      {children}
    </div>
  );
}

export function SectionHeading({
  eyebrow,
  title,
  description,
  align = "left",
  className,
}: {
  eyebrow?: string;
  title: ReactNode;
  description?: string;
  align?: "left" | "center";
  className?: string;
}) {
  return (
    <div className={cn(align === "center" ? "mx-auto max-w-2xl text-center" : "max-w-2xl", className)}>
      {eyebrow ? <p className="eyebrow mb-4">{eyebrow}</p> : null}
      <h2 className="display text-4xl text-ink md:text-5xl">{title}</h2>
      {description ? <p className="mt-4 text-[15px] leading-relaxed text-ink-soft">{description}</p> : null}
    </div>
  );
}

export function Metric({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: string | number;
  sub?: string;
  accent?: "ink" | "support" | "contradict" | "caution" | "powder";
}) {
  const colors = {
    ink: "text-ink",
    support: "text-support",
    contradict: "text-contradict",
    caution: "text-caution",
    powder: "text-powder-deep",
  };
  return (
    <div className="rounded-2xl border border-line bg-white p-5">
      <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-ink-soft">{label}</p>
      <p className={cn("mt-2.5 text-3xl font-semibold tabular-nums tracking-tight", colors[accent || "ink"])}>
        {value}
      </p>
      {sub ? <p className="mt-1 text-xs text-ink-soft">{sub}</p> : null}
    </div>
  );
}
