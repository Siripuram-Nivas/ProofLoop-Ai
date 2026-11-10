import { afterEach, describe, expect, it, vi } from "vitest";
import {
  formatDate,
  inputKindLabel,
  isActiveStatus,
  plural,
  relativeTime,
  truncate,
  VERDICT_META,
} from "./format";

afterEach(() => {
  vi.useRealTimers();
});

describe("verdict metadata", () => {
  it("keeps every backend verdict labelled and never maps unverified to false", () => {
    expect(Object.keys(VERDICT_META).sort()).toEqual(
      ["contradicted", "inconclusive", "insufficient", "mixed", "outdated", "supported", "unverified"],
    );
    expect(VERDICT_META.unverified.label).toBe("Unverified");
    expect(VERDICT_META.inconclusive.label).toBe("Inconclusive");
  });
});

describe("relativeTime", () => {
  it("formats recent and older timestamps", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-11-10T12:00:00Z"));
    expect(relativeTime("2026-11-10T11:59:30Z")).toBe("just now");
    expect(relativeTime("2026-11-10T11:58:00Z")).toBe("2 min ago");
    expect(relativeTime("2026-11-10T10:00:00Z")).toBe("2 h ago");
    expect(relativeTime("2026-11-08T12:00:00Z")).toBe("2 d ago");
    expect(relativeTime("not-a-date")).toBe("unknown");
    expect(relativeTime(null)).toBe("unknown");
  });
});

describe("small formatters", () => {
  it("handles missing and invalid dates without throwing", () => {
    expect(formatDate(null)).toBe("Unknown");
    expect(formatDate("2026-11-10T12:00:00Z")).not.toBe("Unknown");
  });

  it("truncates only when needed and preserves the ellipsis", () => {
    expect(truncate("short", 10)).toBe("short");
    expect(truncate("abcdefghijkl", 10)).toBe("abcdefghi…");
  });

  it("labels input kinds, statuses, and plurals", () => {
    expect(inputKindLabel("pdf")).toBe("PDF document");
    expect(inputKindLabel("document")).toBe("Text document");
    expect(inputKindLabel("unknown-kind")).toBe("unknown-kind");
    expect(isActiveStatus("researching")).toBe(true);
    expect(isActiveStatus("completed")).toBe(false);
    expect(plural(1, "claim")).toBe("1 claim");
    expect(plural(3, "claim")).toBe("3 claims");
  });
});
