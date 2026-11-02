import { motion } from "framer-motion";
import { BookOpen, Bug, Lightbulb, ShieldCheck, Workflow } from "lucide-react";
import { useChatStore } from "../../stores/chat";
import { Composer } from "./composer";

const SUGGESTIONS = [
  { icon: Workflow, title: "Solve a DSA problem", prompt: "Solve this DSA problem with an optimized solution: Two Sum" },
  { icon: Bug, title: "Debug my code", prompt: "Debug this error in my code" },
  { icon: Lightbulb, title: "Explain this algorithm", prompt: "Explain this algorithm" },
  { icon: ShieldCheck, title: "Review my code", prompt: "Review my code" },
  { icon: BookOpen, title: "Understand my codebase", prompt: "Understand my codebase" },
];

export function WelcomeScreen({ sessionId }: { sessionId?: string | null }) {
  const { send } = useChatStore();

  const onSuggest = (prompt: string) => {
    void send({ sessionId: sessionId ?? undefined, content: prompt, model: undefined });
  };

  return (
    <motion.div
      className="flex flex-1 flex-col items-center justify-center gap-8 px-4 py-8"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: "easeOut" }}
    >
      <div className="flex flex-col items-center gap-4 text-center">
        <div className="text-[44px] font-semibold tracking-[-0.03em] text-text">Think. Code. Verify.</div>
        <p className="max-w-xl text-base text-muted">CodePilot turns intent into reviewed, tested, optimized code — grounded in your actual codebase.</p>
      </div>

      <Composer sessionId={sessionId} placeholder="Describe the bug, the algorithm, or the feature…" />

      <div className="grid w-full max-w-2xl grid-cols-1 gap-2 sm:grid-cols-2">
        {SUGGESTIONS.map((suggestion) => {
          const Icon = suggestion.icon;
          return (
            <button
              key={suggestion.title}
              type="button"
              onClick={() => onSuggest(suggestion.prompt)}
              className="flex items-start gap-3 rounded-[10px] border border-border bg-surface p-3 text-left transition-colors hover:border-control hover:bg-raised"
            >
              <Icon className="mt-0.5 h-[16px] w-[16px] shrink-0 text-accent" strokeWidth={1.75} />
              <span className="text-sm text-text">{suggestion.title}</span>
            </button>
          );
        })}
      </div>
    </motion.div>
  );
}
