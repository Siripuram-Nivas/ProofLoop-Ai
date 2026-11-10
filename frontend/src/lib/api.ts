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

  health: () => request<HealthInfo>("/health"),
  stats: () => request<Stats>("/stats"),

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
  createVerification: (body: { title?: string; text?: string; url?: string; upload_id?: string }) =>
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
