import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface AgentModels {
  solver: string;
  reviewer: string;
  context: string;
}

export interface Provider {
  id: string;
  name: string;
  apiKeyVar: string;
  defaultModel: string;
}

interface SettingsState {
  providerId: string;
  models: AgentModels;
  defaultLanguage: string;
  ragTopK: number;
  embeddingModel: string;
  vectorDbUrl: string;
  dockerImage: string;
  providerOptions: Provider[];
  setProviderId: (providerId: string) => void;
  setModel: (agent: keyof AgentModels, model: string) => void;
  setDefaultLanguage: (language: string) => void;
  setRagTopK: (ragTopK: number) => void;
  setEmbeddingModel: (embeddingModel: string) => void;
  setVectorDbUrl: (vectorDbUrl: string) => void;
  setDockerImage: (dockerImage: string) => void;
}

const PROVIDER_OPTIONS: Provider[] = [
  { id: "openai", name: "OpenAI", apiKeyVar: "OPENAI_API_KEY", defaultModel: "gpt-4.1" },
  { id: "anthropic", name: "Anthropic", apiKeyVar: "ANTHROPIC_API_KEY", defaultModel: "claude-sonnet-4-5" },
  { id: "google", name: "Google", apiKeyVar: "GEMINI_API_KEY", defaultModel: "gemini-2.5-flash" },
  { id: "deepseek", name: "DeepSeek", apiKeyVar: "DEEPSEEK_API_KEY", defaultModel: "deepseek-chat" },
];

export const DEFAULT_SETTINGS = {
  providerId: "openai",
  models: { solver: "gpt-4.1", reviewer: "claude-sonnet-4-5", context: "gpt-3.5-turbo" },
  defaultLanguage: "python",
  ragTopK: 5,
  embeddingModel: "text-embedding-3-small",
  vectorDbUrl: "http://localhost:6333",
  dockerImage: "codepilot-solver:latest",
  providerOptions: PROVIDER_OPTIONS,
};

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      ...DEFAULT_SETTINGS,
      setProviderId: (providerId) => set({ providerId }),
      setModel: (agent, model) => set((state) => ({ models: { ...state.models, [agent]: model } })),
      setDefaultLanguage: (language) => set({ defaultLanguage: language }),
      setRagTopK: (ragTopK) => set({ ragTopK }),
      setEmbeddingModel: (embeddingModel) => set({ embeddingModel }),
      setVectorDbUrl: (vectorDbUrl) => set({ vectorDbUrl }),
      setDockerImage: (dockerImage) => set({ dockerImage }),
    }),
    { name: "codepilot-settings" },
  ),
);
