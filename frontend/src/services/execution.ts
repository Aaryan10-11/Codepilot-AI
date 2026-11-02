import { httpRequest } from "./api";

export interface RunCodeRequest {
  language: string;
  code: string;
  problem_id?: string;
}

export interface RunCodeResponse {
  status: "passed" | "failed" | "error";
  stdout: string;
  stderr: string;
  exit_code: number | null;
  duration_ms: number | null;
  tests: { passed: number; failed: number; total: number } | null;
}

class ExecutionService {
  /**
   * Runs user code against the configured sandbox (Docker execution backend).
   * The endpoint ships with the execution milestone; until then the call surfaces
   * the backend's typed error envelope instead of pretending to run.
   */
  run(_request: RunCodeRequest): Promise<RunCodeResponse> {
    return httpRequest<RunCodeResponse>("/execution/run", {
      method: "POST",
      body: JSON.stringify(_request),
    });
  }
}

export const executionService = new ExecutionService();
