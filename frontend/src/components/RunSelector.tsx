import { ChevronDown } from "lucide-react";
import type { VerificationSummary } from "../lib/types";
import { formatDate } from "../lib/format";

export function RunSelector({
  items,
  value,
  onChange,
  label = "Verification run",
}: {
  items: VerificationSummary[];
  value: string;
  onChange: (id: string) => void;
  label?: string;
}) {
  return (
    <div className="flex items-center gap-2">
      <label htmlFor="run-selector" className="shrink-0 text-[11px] font-medium text-ink-soft">
        {label}
      </label>
      <div className="relative min-w-0">
        <select
          id="run-selector"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          className="h-9 w-full max-w-[380px] appearance-none truncate rounded-xl border border-line bg-white pl-3 pr-9 text-[12px] text-ink focus:border-powder-deep focus:outline-none"
        >
          {items.map((item) => (
            <option key={item.id} value={item.id}>
              {item.title} · {formatDate(item.created_at)}
            </option>
          ))}
        </select>
        <ChevronDown className="pointer-events-none absolute right-3 top-1/2 size-3.5 -translate-y-1/2 text-ink-soft" aria-hidden />
      </div>
    </div>
  );
}
