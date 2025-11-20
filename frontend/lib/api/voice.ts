/**
 * 音声UI関連のAPI関数
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

/**
 * 音声文字起こしレスポンス
 */
export interface TranscriptionResponse {
  text: string;
  language: string;
  duration_sec: number;
}

/**
 * RAGクエリレスポンス
 */
export interface RAGQueryResponse {
  answer: string;
  used_strategy: string;
  context_chunks: ContextChunk[];
}

/**
 * コンテキストチャンク
 */
export interface ContextChunk {
  chunk_id: string;
  text: string;
  score: number;
  source_url?: string;
  metadata: {
    campus?: string;
    department?: string;
    lab?: string;
    professor?: string[];
    tags?: string[];
  };
}

/**
 * 音声ファイルを文字起こし
 */
export async function transcribeAudio(audioBlob: Blob): Promise<TranscriptionResponse> {
  const formData = new FormData();
  formData.append('file', audioBlob, 'recording.webm');

  const response = await fetch(`${API_BASE_URL}/api/transcription`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `Transcription failed: ${response.status}`);
  }

  return response.json();
}

/**
 * RAGクエリ（検索 + 回答生成）
 */
export async function ragQuery(
  query: string,
  strategy: 'dense' | 'prefilter_dense' | 'hybrid' = 'prefilter_dense',
  filters?: Record<string, string>,
  topK: number = 5
): Promise<RAGQueryResponse> {
  const response = await fetch(`${API_BASE_URL}/api/rag_query`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      query,
      strategy,
      filters,
      top_k: topK,
    }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `RAG query failed: ${response.status}`);
  }

  return response.json();
}

