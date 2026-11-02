import Editor from "@monaco-editor/react";

export interface MonacoEditorProps {
  value: string;
  language: string;
  onChange?: (value: string) => void;
  height?: number;
  readOnly?: boolean;
}

export function MonacoEditor({ value, language, onChange, height = 340, readOnly = false }: MonacoEditorProps) {
  return (
    <Editor
      height={height}
      defaultLanguage={language}
      value={value}
      onChange={onChange ? (next) => onChange(next ?? "") : undefined}
      path={`solution.${language === "python" ? "py" : language}`}
      options={{
        minimap: { enabled: false },
        fontSize: 13,
        lineNumbers: "on",
        automaticLayout: true,
        scrollBeyondLastLine: false,
        padding: { top: 12 },
        readOnly,
      }}
    />
  );
}
