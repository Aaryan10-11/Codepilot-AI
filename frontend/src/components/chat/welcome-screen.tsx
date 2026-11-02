import { motion } from "framer-motion";
import { BookOpen, Bug, Lightbulb, ShieldCheck } from "lucide-react";
import { useChatStore } from "../../stores/chat";
import { useSettingsStore } from "../../stores/settings";

const SUGGESTIONS = [
  { icon: Bug, title: "Debug my code", prompt: "Debug this error in my code" },
  { icon: Lightbulb, title: "Explain this algorithm", prompt: "Explain this sorting algorithm and its complexity analysis" },
  { icon: ShieldCheck, title: "Review & improve", prompt: "Review this code for security issues, complexity, and suggest improvements" },
  { icon: BookOpen, title: "Understand codebase", prompt: "Understand the architecture of this FastAPI application and its components" },
];

export function WelcomeScreen({ sessionId }: { sessionId?: string | null }) {
  const { send } = useChatStore();
  const settings = useSettingsStore();

  const onSuggest = async (prompt: string) => {
    try {
      await send({ sessionId: sessionId ?? undefined, content: prompt, model: settings.models.solver });
    } catch (error) {
      console.error("Send failed:", error);
    }
  };

  return (
    <motion.div
      className="flex flex-1 flex-col items-center justify-center gap-8 px-4 py-8"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: "easeOut" }}
    >
      <div className="flex flex-col items-center gap-4 text-center">
        <div className="text-[38px] font-bold tracking-tight text-text sm:text-[44px]">
          Think. Code. Verify.
        </div>
        <p className="max-w-xl text-base text-muted">
          CodePilot turns intent into reviewed, tested, optimized code — grounded in your actual codebase.
        </p>
      </div>

      <div className="flex flex-col gap-3 w-full max-w-2xl">
        {SUGGESTIONS.map((suggestion, idx) => {
          const Icon = suggestion.icon;
          return (
            <motion.div
              key={suggestion.title}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: idx * 0.05, duration: 0.3 }}
            >
              <button
                type="button"
                onClick={() => onSuggest(suggestion.prompt)}
                className="flex w-full items-start gap-4 rounded-[12px] border border-border bg-surface p-4 text-left transition-all hover:border-control hover:shadow-md"
              >
                <Icon className="mt-0.5 h-5 w-5 shrink-0 text-accent" strokeWidth={1.75} />
                <div className="flex-1">
                  <span className="text-sm font-medium text-text">{suggestion.title}</span>
                </div>
              </button>
            </motion.div>
          );
        })}
      </div>
    </motion.div>
  );
}