import { describe, expect, it } from "vitest";
import { buildMomenSubmission } from "./momen";

describe("buildMomenSubmission", () => {
  it("preserves padded TEXT exactly and keeps the title separate", () => {
    const body = buildMomenSubmission({
      workspaceId: 6,
      mode: "text",
      title: "  Eiffel check  ",
      text: "  The Eiffel Tower is 330 metres tall.  ",
      url: "",
    });
    expect(body).toEqual({
      workspace_id: 6,
      input_type: "TEXT",
      title: "Eiffel check",
      original_text: "  The Eiffel Tower is 330 metres tall.  ",
    });
  });

  it("maps URL mode to original_url", () => {
    const body = buildMomenSubmission({
      workspaceId: 6,
      mode: "url",
      title: "",
      text: "",
      url: "https://example.org/report",
    });
    expect(body?.input_type).toBe("URL");
    expect(body?.original_url).toBe("https://example.org/report");
    expect(body?.original_text).toBeUndefined();
    expect(body?.title).toBe("https://example.org/report");
  });

  it("returns null for document and image modes with no Momen upload URL", () => {
    for (const mode of ["document", "image"] as const) {
      expect(
        buildMomenSubmission({ workspaceId: 6, mode, title: "", text: "", url: "" }),
      ).toBeNull();
    }
  });
});
