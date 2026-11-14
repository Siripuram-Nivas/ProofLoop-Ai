import type {
  Claim,
  GraphData,
  HealthInfo,
  Report,
  Stats,
  UploadResult,
  User,
  VerificationJob,
  VerificationSummary,
} from "./types";

export const API_ROOT = import.meta.env.VITE_API_URL || "/api/v1";

export interface MomenAccount {
  id: number;
  email: string | null;
  username: string | null;
}

export interface MomenWorkspace {
  id: number;
  name: string;
  slug: string;
  status: string;
}

export interface MomenSession {
  connected: boolean;
  account?: MomenAccount;
  workspaces: MomenWorkspace[];
  read_access: boolean;
  persistence_available: false;
}

export interface MomenJobCreated {
  verification_job_id: number;
  status: string | null;
  created_at: string | null;
  persistence_available: false;
}

export interface MomenVerificationJob {
  id: number;
  title: string | null;
  input_type: string | null;
  status: string | null;
  current_stage: string | null;
  error_message: string | null;
  original_text?: string | null;
  original_url?: string | null;
  uploaded_file_url?: string | null;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  completed_at: string | null;
  workspace_id: number | null;
  created_by_id: number | null;
  metadata: unknown;
  claims?: unknown[];
  sources?: unknown[];
  contradictions?: unknown[];
  proof_reports?: unknown[];
  audit_logs?: unknown[];
}

export interface MomenJobList {
  items: MomenVerificationJob[];
  total: number;
  limit: number;
  offset: number;
  persistence_available: false;
}

export interface EngineAvailability {
  id: "openai" | "gemini" | "google_search";
  label: string;
  configured: boolean;
  available: boolean;
  live_enabled: boolean;
  model: string | null;
  capabilities: string[];
  reason: string | null;
  state?: string;
  detail?: string;
  cooldown_seconds?: number;
  last_error_category?: string | null;
  last_success?: string | null;
  last_quota_failure?: string | null;
  failure_count?: number;
}

export interface EngineConfig {
  claim_extraction: string;
  research: string;
  analysis: string;
  review: string;
  second_review: string;
  live_calls_enabled: boolean;
  research_provider: string;
  google_search_enabled: boolean;
  max_input_chars: number;
  max_output_tokens: number;
  max_retries: number;
  auto_fallback_enabled?: boolean;
  provider_order?: string[];
  fallback_max_attempts?: number;
  provider_cooldown_seconds?: number;
}

export interface EngineListing {
  engines: EngineAvailability[];
  config: EngineConfig;
}

export interface EngineTestResult {
  engine: string;
  ok: boolean;
  detail: string;
  usage?: Record<string, unknown>;
}

export interface EngineChoice {
  claim_extraction?: "deterministic" | "openai" | "gemini";
  research?: "wikipedia" | "google_search";
  analysis?: "" | "openai" | "gemini";
  review?: "" | "openai" | "gemini";
  second_review?: "" | "openai" | "gemini";
}

function csrfHeader(): Record<string, string> {
  const match = document.cookie.match(/(?:^|;\s*)proofloop_csrf=([^;]+)/);
  return match ? { "X-CSRF-Token": decodeURIComponent(match[1]) } : {};
}


export class ApiError extends Error {
  status: number;
  code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_ROOT}${path}`, {
    credentials: "include",
    ...init,
    headers: {
      ...(init.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...(init.headers || {}),
    },
  });
  if (response.status === 204) {
    return undefined as T;
  }
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const code = data?.error?.code || "request_failed";
    const message = data?.error?.message || `Request failed (${response.status}).`;
    throw new ApiError(response.status, code, message);
  }
  return data as T;
}

export const api = {
  me: () => request<{ user: User }>("/auth/me"),
  guest: () => request<{ user: User }>("/auth/guest", { method: "POST" }),
  login: (email: string, password: string) =>
    request<{ user: User }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  register: (email: string, password: string) =>
    request<{ user: User }>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  logout: () => request<{ ok: boolean }>("/auth/logout", { method: "POST" }),

  momenSession: () => request<MomenSession>("/momen/session"),
  momenLogin: (email: string, password: string) =>
    request<MomenSession>("/momen/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  momenLogout: () =>
    request<{ ok: boolean }>("/momen/auth/logout", {
      method: "POST",
      headers: csrfHeader(),
    }),
  momenWorkspaces: () =>
    request<{ items: MomenWorkspace[] }>("/momen/workspaces"),
  momenCreateVerification: (body: {
    workspace_id: number;
    input_type: "TEXT" | "URL" | "PDF" | "IMAGE";
    title: string;
    original_text?: string;
    original_url?: string;
    uploaded_file_url?: string;
  }) =>
    request<MomenJobCreated>("/momen/verifications", {
      method: "POST",
      headers: csrfHeader(),
      body: JSON.stringify(body),
    }),
  momenListVerifications: (params: { limit?: number; offset?: number } = {}) => {
    const search = new URLSearchParams();
    if (params.limit) search.set("limit", String(params.limit));
    if (params.offset) search.set("offset", String(params.offset));
    const suffix = search.toString() ? `?${search.toString()}` : "";
    return request<MomenJobList>(`/momen/verifications${suffix}`);
  },
  momenGetVerification: (id: number) =>
    request<{ job: MomenVerificationJob; persistence_available: false }>(
      `/momen/verifications/${id}`,
    ),
  momenReport: (id: number) =>
    request<{ report: unknown; persistence_available: false }>(
      `/momen/verifications/${id}/report`,
    ),


  health: () => request<HealthInfo>("/health"),
  stats: () => request<Stats>("/stats"),

  engines: () => request<EngineListing>("/engines"),
  testEngine: (id: EngineAvailability["id"]) =>
    request<EngineTestResult>(`/engines/${id}/test`, {
      method: "POST",
      body: JSON.stringify({ confirm: true }),
    }),

  listVerifications: (params: { limit?: number; offset?: number } = {}) => {
    const search = new URLSearchParams();
    if (params.limit) search.set("limit", String(params.limit));
    if (params.offset) search.set("offset", String(params.offset));
    const suffix = search.toString() ? `?${search.toString()}` : "";
    return request<{
      items: VerificationSummary[];
      total: number;
      limit: number;
      offset: number;
    }>(`/verifications${suffix}`);
  },
  getVerification: (id: string) => request<VerificationJob>(`/verifications/${id}`),
  createVerification: (body: {
    title?: string;
    text?: string;
    url?: string;
    upload_id?: string;
    engines?: EngineChoice;
  }) =>
    request<{ id: string; status: string; title: string }>("/verifications", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  rerun: (id: string) =>
    request<{ id: string; status: string }>(`/verifications/${id}/run`, { method: "POST" }),
  updateClaim: (jobId: string, claimId: string, text: string) =>
    request<Claim>(`/verifications/${jobId}/claims/${claimId}`, {
      method: "PATCH",
      body: JSON.stringify({ text }),
    }),
  addClaim: (jobId: string, text: string) =>
    request<Claim>(`/verifications/${jobId}/claims`, {
      method: "POST",
      body: JSON.stringify({ text }),
    }),
  deleteClaim: (jobId: string, claimId: string) =>
    request<{ ok: boolean; claims: number }>(`/verifications/${jobId}/claims/${claimId}`, {
      method: "DELETE",
    }),
  graph: (id: string) => request<GraphData>(`/verifications/${id}/graph`),
  contradictions: (id: string) =>
    request<{
      contradictions: VerificationJob["contradictions"];
      claims: { id: string; text: string }[];
    }>(`/verifications/${id}/contradictions`),
  report: (id: string) => request<Report>(`/verifications/${id}/report`),

  upload: async (file: File): Promise<UploadResult> => {
    const form = new FormData();
    form.append("file", file);
    return request<UploadResult>("/uploads", { method: "POST", body: form });
  },
};
