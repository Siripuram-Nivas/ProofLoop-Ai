import type { Verdict } from "./types";

export const VERDICT_META: Record<
  Verdict,
  { label: string; tone: string; dot: string }
> = {
  supported: {
    label: "Supported",
    tone: "border-support/25 bg-[#EDF6F1] text-support",
    dot: "bg-support",
  },
  contradicted: {
    label: "Contradicted",
    tone: "border-contradict/25 bg-[#FBEDEB] text-contradict",
    dot: "bg-contradict",
  },
  mixed: {
    label: "Mixed evidence",
    tone: "border-peach-deep/25 bg-[#FDF1EC] text-peach-deep",
    dot: "bg-peach-deep",
  },
  insufficient: {
    label: "Insufficient",
    tone: "border-caution/25 bg-[#FBF4E7] text-caution",
    dot: "bg-caution",
  },
  outdated: {
    label: "Outdated",
    tone: "border-caution/25 bg-[#FBF4E7] text-caution",
    dot: "bg-caution",
  },
  unverified: {
    label: "Unverified",
    tone: "border-line bg-lavender/60 text-ink-soft",
    dot: "bg-ink-soft/50",
  },
  inconclusive: {
    label: "Inconclusive",
    tone: "border-line bg-lavender/60 text-ink-soft",
    dot: "bg-ink-soft/50",
  },
};

export const JOB_STATUS_LABEL: Record<string, string> = {
  queued: "Queued",
  extracting: "Extracting claims",
  researching: "Researching sources",
  evaluating: "Evaluating evidence",
  completed: "Completed",
  failed: "Failed",
};

export const CATEGORY_LABEL: Record<string, string> = {
  date: "Date",
  quantity: "Quantity",
  identity: "Identity",
  attribution: "Attribution",
  general: "Statement",
};

export function formatDate(iso?: string | null): string {
  if (!iso) return "Unknown";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "Unknown";
  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function formatDateTime(iso?: string | null): string {
  if (!iso) return "Unknown";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "Unknown";
  return date.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function relativeTime(iso?: string | null): string {
  if (!iso) return "unknown";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "unknown";
  const seconds = Math.round((Date.now() - then) / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} h ago`;
  const days = Math.round(hours / 24);
  if (days < 30) return `${days} d ago`;
  return formatDate(iso);
}

export function truncate(value: string, max = 120): string {
  return value.length > max ? `${value.slice(0, max - 1)}…` : value;
}

export function inputKindLabel(kind: string): string {
  return (
    {
      text: "Pasted text",
      document: "Text document",
      pdf: "PDF document",
      url: "Web page",
      image: "Screenshot",
    }[kind] || kind
  );
}

export function plural(count: number, singular: string, pluralForm?: string): string {
  return `${count} ${count === 1 ? singular : pluralForm || `${singular}s`}`;
}

export function isActiveStatus(status: string): boolean {
  return ["queued", "extracting", "researching", "evaluating"].includes(status);
}
