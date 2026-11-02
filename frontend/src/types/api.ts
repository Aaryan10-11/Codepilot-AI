/** Error envelope shared by every failing backend response. */

export interface ApiErrorPayload {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

export interface ApiErrorBody {
  error: ApiErrorPayload;
  request_id: string;
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details?: Record<string, unknown>;
  readonly requestId: string;

  constructor(
    status: number,
    payload: ApiErrorPayload,
    requestId: string,
  ) {
    super(payload.message);
    this.name = "ApiError";
    this.status = status;
    this.code = payload.code;
    this.details = payload.details;
    this.requestId = requestId;
  }
}

export interface HealthComponent {
  name: string;
  status: "up" | "down" | "unknown";
  required: boolean;
  latency_ms: number | null;
  detail: string | null;
}

export interface HealthReport {
  status: "ok" | "degraded" | "unavailable";
  version: string;
  environment: string;
  checked_at: string;
  uptime_seconds: number;
  components: HealthComponent[];
}

export interface LivenessReport {
  status: "ok";
  version: string;
}

export interface ProviderSummary {
  id: string;
  configured: boolean;
  default_model: string;
}

export interface ProviderListResponse {
  default_provider: string;
  providers: ProviderSummary[];
}

export interface ProviderVerificationResponse {
  provider_id: string;
  status: "ok";
  latency_ms: number;
}

export interface TokenUsage {
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  model?: string;
}
