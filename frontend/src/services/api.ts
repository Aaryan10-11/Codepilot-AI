import { ApiError, type ApiErrorBody } from "../types/api";

const BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "/v1";

export async function httpRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...(init?.headers ?? {}),
    },
  });

  const raw = (await response.json().catch(() => null)) as ApiErrorBody | null;

  if (!response.ok) {
    const error = raw?.error ?? { code: "unknown_error", message: `Request failed (${response.status})` };
    throw new ApiError(response.status, error, raw?.request_id ?? "unknown");
  }

  return (raw as unknown as T) ?? ({} as T);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  return httpRequest<T>(path, init);
}

export const apiClient = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) => request<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
};

export const healthService = {
  getLive: () => apiClient.get<{ status: "ok"; version: string }>("/health/live"),
  getReady: () => apiClient.get<{ status: "ok" | "degraded" | "unavailable" }>("/health/ready"),
  getFull: () =>
    apiClient.get<{
      status: "ok" | "degraded" | "unavailable";
      version: string;
      components: Array<{ name: string; status: string; required: boolean; latency_ms: number | null; detail: string | null }>;
    }>("/health"),
};

export const providersService = {
  list: () =>
    apiClient.get<{ default_provider: string; providers: Array<{ id: string; configured: boolean; default_model: string }> }>("/providers"),
  verify: (providerId: string) =>
    apiClient.post<{ provider_id: string; status: "ok"; latency_ms: number }>(`/providers/${providerId}/verify`),
};
