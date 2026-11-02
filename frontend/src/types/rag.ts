import type { ContextFileRef } from "./agents";

export interface RetrievalChunk {
  id: string;
  source: string;
  path?: string;
  language?: string;
  content: string;
  score: number;
}

export interface RetrievalResponse {
  query: string;
  chunks: RetrievalChunk[];
  token_estimate: number;
}

export interface RetrievedContextFile extends ContextFileRef {
  chunk_id?: string;
  score?: number;
}
