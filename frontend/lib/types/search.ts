export type SearchStrategy = "dense" | "prefilter_dense" | "hybrid";

export interface SearchFilters {
  department?: string;
  professor?: string;
  campus?: string;
  lab?: string;
  [key: string]: string | undefined;
}

export interface SearchRequest {
  query: string;
  strategy: SearchStrategy;
  filters?: SearchFilters;
  top_k?: number;
  alpha?: number;  // Hybrid用
  beta?: number;   // Hybrid用
}

export interface SearchResultMetadata {
  campus?: string;
  department?: string;
  lab?: string;
  professor?: string[];
  tags?: string[];
  [key: string]: string | string[] | undefined;
}

export interface SearchResultItem {
  chunk_id: string;
  text: string;
  score: number;
  source_url?: string;
  metadata: SearchResultMetadata;
}

export interface SearchResponse {
  strategy: string;
  query: string;
  results: SearchResultItem[];
  total: number;
}

