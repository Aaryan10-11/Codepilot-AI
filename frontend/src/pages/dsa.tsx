import { useState } from "react";
import { CheckCircle2, Play, XCircle } from "lucide-react";
import { MonacoEditor } from "../components/editor/monaco-editor";
import { Button } from "../components/ui/button";
import { Card, CardHeader, CardTitle } from "../components/ui/card";
import { Select } from "../components/ui/inputs";
import { executionService, type RunCodeResponse } from "../services/execution";
import type { Difficulty } from "../types/dsa";

const LANGUAGES = [
  { value: "python", label: "Python" },
  { value: "javascript", label: "JavaScript" },
  { value: "java", label: "Java" },
  { value: "cpp", label: "C++" },
];

const DIFFICULTIES: Array<{ value: Difficulty; label: string }> = [
  { value: "easy", label: "Easy" },
  { value: "medium", label: "Medium" },
  { value: "hard", label: "Hard" },
];

const DEFAULT_CODE = `def two_sum(nums, target):
    seen = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
        seen[num] = i
    return []


def main():
    assert two_sum([2, 7, 11, 15], 9) == [0, 1]
    assert two_sum([3, 2, 4], 6) == [1, 2]
    assert two_sum([3, 3], 6) == [0, 1]


if __name__ == "__main__":
    main()
`;

const SOLUTION_SECTIONS: Array<{ key: string; title: string; body: string }> = [
  { key: "approach", title: "Approach", body: "Use a single hash map: for each number, check whether its complement already exists; store each number's index on first sight." },
  { key: "explanation", title: "Explanation", body: "Iterate once, trading space for time. The map holds value → index so lookups are O(1)." },
  { key: "brute-force", title: "Brute Force", body: "For every pair, test whether the two values sum to the target. O(n²) time, O(1) space." },
  { key: "optimized", title: "Optimized", body: "Hash map complement lookup. O(n) time, O(n) space." },
];

const COMPLEXITY = {
  time: "O(n)",
  space: "O(n)",
};

export function DSAPage() {
  const [language, setLanguage] = useState("python");
  const [difficulty, setDifficulty] = useState<Difficulty>("medium");
  const [code, setCode] = useState(DEFAULT_CODE);
  const [running, setRunning] = useState(false);
  const [execution, setExecution] = useState<RunCodeResponse | null>(null);

  const run = async () => {
    setRunning(true);
    setExecution(null);
    try {
      const result = await executionService.run({ language, code });
      setExecution(result);
    } catch {
      setExecution({
        status: "error",
        stdout: "",
        stderr: "Execution sandbox is not reachable.",
        exit_code: null,
        duration_ms: null,
        tests: null,
      });
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="flex h-full min-h-0 flex-1 flex-col overflow-hidden">
      <header className="flex items-center justify-between gap-4 pb-4">
        <div>
          <h1 className="text-title font-semibold tracking-tight">DSA Practice</h1>
          <p className="text-small text-muted">Retrieval-grounded solutions with reviewer verification</p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={difficulty} onChange={(event) => setDifficulty(event.target.value as Difficulty)} aria-label="Difficulty">
            {DIFFICULTIES.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </Select>
          <Select value={language} onChange={(event) => setLanguage(event.target.value)} aria-label="Language">
            {LANGUAGES.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </Select>
          <Button variant="secondary" size="sm" onClick={() => void run()} disabled={running}>
            <Play className="h-3 w-3" />
            {running ? "Running" : "Run"}
          </Button>
        </div>
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="grid gap-6 pb-4 lg:grid-cols-2">
          <section aria-label="Solution" className="flex min-w-0 flex-col gap-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-semibold">Solution</CardTitle>
              </CardHeader>
              <div className="flex flex-col gap-4">
                {SOLUTION_SECTIONS.map((section) => (
                  <div key={section.key}>
                    <h3 className="text-sm font-semibold">{section.title}</h3>
                    <p className="mt-1 text-sm text-muted">{section.body}</p>
                  </div>
                ))}
              </div>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-semibold">Generated code</CardTitle>
              </CardHeader>
              <MonacoEditor value={code} language={language} onChange={setCode} height={320} />
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-semibold">Execution</CardTitle>
              </CardHeader>
              {execution ? (
                <div className="flex flex-col gap-2 text-sm">
                  <div className="flex items-center gap-2">
                    {execution.status === "passed" ? <CheckCircle2 className="h-4 w-4 text-positive" /> : <XCircle className="h-4 w-4 text-negative" />}
                    <span className="status-pill" data-status={execution.status}>
                      <span className="dot" />
                      {execution.status}
                    </span>
                  </div>
                  <pre className="overflow-x-auto rounded-[6px] bg-ground p-3 text-xs whitespace-pre-wrap">{execution.stdout || execution.stderr}</pre>
                </div>
              ) : (
                <p className="text-sm text-muted">Run the solution to execute it in the sandbox.</p>
              )}
            </Card>
          </section>

          <aside className="flex min-w-0 flex-col gap-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-semibold">Problem</CardTitle>
              </CardHeader>
              <p className="text-sm text-muted">Two Sum — given an array of integers and a target, return the indices of the two numbers that add up to the target.</p>
              <dl className="mt-4 flex flex-col gap-2 text-sm">
                <div className="flex justify-between">
                  <dt className="text-muted">Difficulty</dt>
                  <dd>{difficulty}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-muted">Language</dt>
                  <dd>{language}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-muted">Time complexity</dt>
                  <dd>{COMPLEXITY.time}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-muted">Space complexity</dt>
                  <dd>{COMPLEXITY.space}</dd>
                </div>
              </dl>
            </Card>
          </aside>
        </div>
      </div>
    </div>
  );
}
