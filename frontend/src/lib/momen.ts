export type MomenMode = "text" | "document" | "url" | "image";

export interface MomenSubmission {
  workspace_id: number;
  input_type: "TEXT" | "URL";
  title: string;
  original_text?: string;
  original_url?: string;
}

function defaultTitle(source: string): string {
  const compact = source.replace(/\s+/g, " ").trim();
  if (!compact) return "Momen verification";
  return compact.length > 72 ? `${compact.slice(0, 72)}…` : compact;
}

export function buildMomenSubmission(input: {
  workspaceId: number;
  mode: MomenMode;
  title: string;
  text: string;
  url: string;
}): MomenSubmission | null {
  const title = input.title.trim() || defaultTitle(input.text || input.url);
  if (input.mode === "text") {
    return {
      workspace_id: input.workspaceId,
      input_type: "TEXT",
      title,
      original_text: input.text,
    };
  }
  if (input.mode === "url") {
    return {
      workspace_id: input.workspaceId,
      input_type: "URL",
      title,
      original_url: input.url,
    };
  }
  return null;
}
