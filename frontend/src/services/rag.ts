import { httpRequest } from "./api";
import type { RetrievalChunk, RetrievalResponse } from "../types/rag";

export const contextService = {
  retrieve: (query: string, topK = 5) =>
    httpRequest<RetrievalResponse>(`/context/retrieve?query=${encodeURIComponent(query)}&top_k=${topK}`),
};

export type { RetrievalChunk };
