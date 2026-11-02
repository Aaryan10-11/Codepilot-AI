import { useEffect, useState } from "react";
import { CheckCircle2, RefreshCw, XCircle } from "lucide-react";
import { Button } from "../components/ui/button";
import { Card, CardHeader, CardTitle } from "../components/ui/card";
import { Input } from "../components/ui/inputs";
import { Switch } from "../components/ui/switch";
import { useSettingsStore } from "../stores/settings";
import { useUIStore } from "../stores/ui";
import { providersService } from "../services/api";

const MODEL_CATALOG: Record<string, string[]> = {
  openai: ["gpt-4o", "gpt-4o-mini", "o3"],
  anthropic: ["claude-sonnet-4-5", "claude-opus-4-1", "claude-haiku-4-5"],
  gemini: ["gemini-2.5-pro", "gemini-2.5-flash"],
  deepseek: ["deepseek-chat", "deepseek-reasoner"],
};

interface ProviderStatus {
  id: string;
  configured: boolean;
  default_model: string;
}

export function SettingsPage() {
  const settings = useSettingsStore();
  const { theme, toggleTheme } = useUIStore();
  const [providers, setProviders] = useState<ProviderStatus[]>([]);
  const [verifying, setVerifying] = useState<string | null>(null);
  const [verification, setVerification] = useState<Record<string, { ok: boolean; latency_ms?: number }>>({});

  useEffect(() => {
    let cancelled = false;
    providersService
      .list()
      .then((response) => {
        if (cancelled) return;
        setProviders(response.providers);
        const next: Record<string, { ok: boolean; latency_ms?: number }> = {};
        for (const provider of response.providers) {
          next[provider.id] = { ok: provider.configured };
        }
        setVerification(next);
      })
      .catch(() => {
        if (!cancelled) setVerification({});
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const verify = async (providerId: string) => {
    setVerifying(providerId);
    try {
      const result = await providersService.verify(providerId);
      setVerification((state) => ({ ...state, [providerId]: { ok: true, latency_ms: result.latency_ms } }));
    } catch {
      setVerification((state) => ({ ...state, [providerId]: { ok: false } }));
    } finally {
      setVerifying(null);
    }
  };

  const modelsForProvider = MODEL_CATALOG[settings.providerId] ?? [settings.models.solver];

  return (
    <div className="flex h-full min-h-0 flex-1 flex-col overflow-hidden">
      <header className="flex items-center justify-between gap-4 pb-4">
        <div>
          <h1 className="text-title font-semibold tracking-tight">Settings</h1>
          <p className="text-small text-muted">Models, retrieval and execution configuration</p>
        </div>
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="grid gap-6 pb-4 lg:grid-cols-2">
          <section aria-label="Theme" className="flex flex-col gap-3">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-semibold">Appearance</CardTitle>
              </CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm">Theme</p>
                  <p className="text-xs text-muted">Dark-first interface</p>
                </div>
                <Switch checked={theme === "dark"} onChange={() => toggleTheme()} aria-label="Toggle theme" />
              </div>
            </Card>
          </section>

          <section aria-label="Execution" className="flex flex-col gap-3">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-semibold">Execution sandbox</CardTitle>
              </CardHeader>
              <label className="flex flex-col gap-2 text-sm">
                <span className="text-muted">Docker image</span>
                <Input value={settings.dockerImage} onChange={(event) => settings.setDockerImage(event.target.value)} />
              </label>
            </Card>
          </section>

          <section aria-label="Retrieval" className="flex flex-col gap-3 lg:col-span-2">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-semibold">Retrieval</CardTitle>
              </CardHeader>
              <div className="grid gap-4 sm:grid-cols-2">
                <label className="flex flex-col gap-2 text-sm">
                  <span className="text-muted">Embedding model</span>
                  <Input value={settings.embeddingModel} onChange={(event) => settings.setEmbeddingModel(event.target.value)} />
                </label>
                <label className="flex flex-col gap-2 text-sm">
                  <span className="text-muted">Top-K chunks</span>
                  <Input type="number" min={1} max={20} value={settings.ragTopK} onChange={(event) => settings.setRagTopK(Number(event.target.value))} />
                </label>
              </div>
            </Card>
          </section>

          <section aria-label="Providers" className="flex flex-col gap-3 lg:col-span-2">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-semibold">Model providers</CardTitle>
              </CardHeader>
              <div className="flex flex-col gap-3">
                {providers.map((provider) => (
                  <div key={provider.id} className="flex items-center justify-between gap-3 rounded-[6px] border border-border px-3 py-2">
                    <div className="flex items-center gap-2">
                      {verification[provider.id]?.ok ? (
                        <CheckCircle2 className="h-4 w-4 text-positive" />
                      ) : verification[provider.id] ? (
                        <XCircle className="h-4 w-4 text-negative" />
                      ) : (
                        <RefreshCw className="h-4 w-4 text-muted" />
                      )}
                      <span className="text-sm capitalize">{provider.id}</span>
                      <span className="text-xs text-muted">{provider.configured ? `configured · ${provider.default_model}` : "not configured"}</span>
                    </div>
                    <Button variant="secondary" size="sm" disabled={!provider.configured || verifying === provider.id} onClick={() => void verify(provider.id)}>
                      {verifying === provider.id ? "Checking…" : "Verify"}
                    </Button>
                  </div>
                ))}
              </div>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-semibold">Agent models</CardTitle>
              </CardHeader>
              <div className="grid gap-4 sm:grid-cols-3">
                <label className="flex flex-col gap-2 text-sm">
                  <span className="text-muted">Solver</span>
                  <select className="h-[34px] rounded-[6px] border border-control bg-surface px-3 text-sm" value={settings.models.solver} onChange={(event) => settings.setModel("solver", event.target.value)}>
                    {modelsForProvider.map((model) => (
                      <option key={model} value={model}>
                        {model}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="flex flex-col gap-2 text-sm">
                  <span className="text-muted">Reviewer</span>
                  <select className="h-[34px] rounded-[6px] border border-control bg-surface px-3 text-sm" value={settings.models.reviewer} onChange={(event) => settings.setModel("reviewer", event.target.value)}>
                    {modelsForProvider.map((model) => (
                      <option key={model} value={model}>
                        {model}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="flex flex-col gap-2 text-sm">
                  <span className="text-muted">Context</span>
                  <select className="h-[34px] rounded-[6px] border border-control bg-surface px-3 text-sm" value={settings.models.context} onChange={(event) => settings.setModel("context", event.target.value)}>
                    {modelsForProvider.map((model) => (
                      <option key={model} value={model}>
                        {model}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
            </Card>
          </section>
        </div>
      </div>
    </div>
  );
}
