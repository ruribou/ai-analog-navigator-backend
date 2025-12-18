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

/**
 * 話者情報
 */
export interface Speaker {
  id: number;
  name: string;
}

/**
 * テキストを音声に変換（TTS）
 */
export async function synthesizeSpeech(
  text: string,
  speakerId: number = 3,
  speedScale: number = 1.0
): Promise<Blob> {
  const response = await fetch(`${API_BASE_URL}/api/tts/synthesize`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      text,
      speaker_id: speakerId,
      speed_scale: speedScale,
    }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `TTS failed: ${response.status}`);
  }

  return response.blob();
}

/**
 * 利用可能な話者一覧を取得
 */
export async function getSpeakers(): Promise<Speaker[]> {
  const response = await fetch(`${API_BASE_URL}/api/tts/speakers`);

  if (!response.ok) {
    throw new Error(`Failed to get speakers: ${response.status}`);
  }

  return response.json();
}

/**
 * 音声を再生するヘルパー関数
 */
export function playAudioBlob(audioBlob: Blob): Promise<void> {
  return new Promise((resolve, reject) => {
    const audioUrl = URL.createObjectURL(audioBlob);
    const audio = new Audio(audioUrl);

    audio.onended = () => {
      URL.revokeObjectURL(audioUrl);
      resolve();
    };

    audio.onerror = () => {
      URL.revokeObjectURL(audioUrl);
      reject(new Error('音声の再生に失敗しました'));
    };

    audio.play().catch(reject);
  });
}
