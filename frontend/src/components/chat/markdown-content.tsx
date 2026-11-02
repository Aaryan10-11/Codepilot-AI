import { useState } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import bash from "react-syntax-highlighter/dist/esm/languages/prism/bash";
import cpp from "react-syntax-highlighter/dist/esm/languages/prism/cpp";
import java from "react-syntax-highlighter/dist/esm/languages/prism/java";
import javascript from "react-syntax-highlighter/dist/esm/languages/prism/javascript";
import json from "react-syntax-highlighter/dist/esm/languages/prism/json";
import markdown from "react-syntax-highlighter/dist/esm/languages/prism/markdown";
import python from "react-syntax-highlighter/dist/esm/languages/prism/python";
import typescript from "react-syntax-highlighter/dist/esm/languages/prism/typescript";
import yaml from "react-syntax-highlighter/dist/esm/languages/prism/yaml";
import { Check, Copy } from "lucide-react";

type PrismLanguage = string;

const languages: Partial<Record<string, PrismLanguage>> = {
  bash,
  cpp,
  java,
  javascript,
  json,
  markdown,
  python,
  typescript,
  yaml,
};

export interface MarkdownContentProps {
  content: string;
  streaming?: boolean;
  onApply?: (code: string, path?: string) => void;
}

function CodeBlock({ language, code, onApply }: { language: string; code: string; onApply?: (code: string, path?: string) => void }) {
  const [copied, setCopied] = useState(false);

  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
    } catch {
      // Clipboard access can be blocked; the copy affordance stays honest.
    }
  };

  return (
    <div className="codeblock">
      <div className="codeblock-header">
        <span className="codeblock-lang">{language}</span>
        <div className="codeblock-actions">
          <button type="button" className="codeblock-copy" onClick={() => void onCopy()}>
            {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
            {copied ? "Copied" : "Copy"}
          </button>
          {onApply ? (
            <button type="button" className="codeblock-copy" onClick={() => onApply(code, undefined)}>
              Apply
            </button>
          ) : null}
        </div>
      </div>
      <SyntaxHighlighter
        language={languages[language] ? language : "text"}
        style={vscDarkPlus}
        customStyle={{ margin: 0, background: "transparent" }}
        codeTagProps={{ style: { fontFamily: "var(--font-mono)", fontSize: "0.8125rem", lineHeight: 1.6 } }}
      >
        {code}
      </SyntaxHighlighter>
    </div>
  );
}

function buildComponents(onApply?: (code: string, path?: string) => void): Components {
  return {
    code({ className, children, ...props }) {
      const match = /language-([\w-]+)/.exec(className ?? "");
      const raw = Array.isArray(children) ? children.join("") : String(children ?? "");
      const code = String(raw).replace(/\n$/, "").replace(/\u2584$/, "");

      if (match) {
        return <CodeBlock language={match[1]} code={code} onApply={onApply} />;
      }

      return (
        <code className="rounded-[4px] bg-raised px-1 py-0.5 font-mono text-[0.85em]" {...props}>
          {children}
        </code>
      );
    },
  };
}

export function MarkdownContent({ content, streaming, onApply }: MarkdownContentProps) {
  const body = streaming ? `${content}\u2584` : content;

  return (
    <div className={streaming ? "markdown stream-cursor" : "markdown"}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={buildComponents(onApply)}>
        {body}
      </ReactMarkdown>
    </div>
  );
}
