export type Difficulty = "easy" | "medium" | "hard";

export interface DSAProblem {
  id: string;
  statement: string;
  language: string;
  difficulty: Difficulty;
  constraints: string[];
  examples: string[];
}

export interface DSASolution {
  explanation: string;
  approach: string;
  brute_force: string;
  optimized: string;
  time_complexity: string;
  space_complexity: string;
  dry_run: string;
  edge_cases: string[];
  tests: string;
}

export interface ExecutionOutcome {
  status: "passed" | "failed" | "error";
  stdout: string;
  stderr: string;
  exit_code: number | null;
  duration_ms: number | null;
  tests: { passed: number; failed: number; total: number } | null;
}

export interface DSAWork {
  problem: DSAProblem;
  solution: DSASolution;
  code: string;
  language: string;
}
