import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface AgentModels {
  solver: string;
  reviewer: string;
  context: string;
}

interface SettingsState {
  providerId: string;
  models: AgentModels;
  defaultLanguage: string;
  ragTopK: number;
  embeddingModel: string;
  vectorDbUrl: string;
  dockerImage: string;
  setProviderId: (providerId: string) => void;
  setModel: (agent: keyof AgentModels, model: string) => void;
  setDefaultLanguage: (language: string) => void;
  setRagTopK: (ragTopK: number) => void;
  setEmbeddingModel: (embeddingModel: string) => void;
  setVectorDbUrl: (vectorDbUrl: string) => void;
  setDockerImage: (dockerImage: string) => void;
}

export const DEFAULT_SETTINGS = {
  providerId: "openai",
  models: { solver: "gpt-4o", reviewer: "gpt-4o-mini", context: "gpt-4o-mini" },
  defaultLanguage: "python",
  ragTopK: 5,
  embeddingModel: "text-embedding-3-small",
  vectorDbUrl: "http://localhost:6333",
  dockerImage: "codepilot-solver:latest",
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
