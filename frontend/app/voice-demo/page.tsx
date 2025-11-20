'use client';

import { useState, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { transcribeAudio, ragQuery, type RAGQueryResponse } from '@/lib/api/voice';
import { Mic, MicOff, Loader2 } from 'lucide-react';

type RecordingState = 'idle' | 'recording' | 'processing';

export default function VoiceDemoPage() {
  const [recordingState, setRecordingState] = useState<RecordingState>('idle');
  const [userQuery, setUserQuery] = useState<string>('');
  const [systemAnswer, setSystemAnswer] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [strategy, setStrategy] = useState<'dense' | 'prefilter_dense' | 'hybrid'>('prefilter_dense');
  const [contextChunks, setContextChunks] = useState<RAGQueryResponse['context_chunks']>([]);
  
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  /**
   * 録音開始
   */
  const startRecording = async () => {
    try {
      setError('');
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm',
      });
      
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];
      
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };
      
      mediaRecorder.onstop = async () => {
        // 録音停止時に音声データを処理
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        await processAudio(audioBlob);
        
        // ストリームを停止
        stream.getTracks().forEach(track => track.stop());
      };
      
      mediaRecorder.start();
      setRecordingState('recording');
      
    } catch (err) {
      console.error('録音開始エラー:', err);
      setError('マイクへのアクセスが拒否されました。ブラウザの設定を確認してください。');
    }
  };

  /**
   * 録音停止
   */
  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop();
      setRecordingState('processing');
    }
  };

  /**
   * 音声データを処理（文字起こし → RAG検索 → 回答生成）
   */
  const processAudio = async (audioBlob: Blob) => {
    try {
      setError('');
      setUserQuery('');
      setSystemAnswer('');
      setContextChunks([]);
      
      // 1. 音声を文字起こし
      console.log('文字起こし中...');
      const transcription = await transcribeAudio(audioBlob);
      const queryText = transcription.text;
      setUserQuery(queryText);
      
      if (!queryText.trim()) {
        setError('音声が認識できませんでした。もう一度お試しください。');
        setRecordingState('idle');
        return;
      }
      
      // 2. RAGクエリで回答を取得
      console.log('回答生成中...');
      const ragResponse = await ragQuery(queryText, strategy);
      setSystemAnswer(ragResponse.answer);
      setContextChunks(ragResponse.context_chunks);
      
      setRecordingState('idle');
      
    } catch (err) {
      console.error('音声処理エラー:', err);
      setError(err instanceof Error ? err.message : '音声処理中にエラーが発生しました');
      setRecordingState('idle');
    }
  };

  /**
   * 録音ボタンのクリックハンドラ
   */
  const handleRecordingButtonClick = () => {
    if (recordingState === 'idle') {
      startRecording();
    } else if (recordingState === 'recording') {
      stopRecording();
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-blue-950">
      <div className="container mx-auto px-4 py-8">
        {/* ヘッダー */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-white mb-2">
            音声AIナビゲーター
          </h1>
          <p className="text-slate-400">
            マイクボタンを押して質問してください
          </p>
        </div>

        {/* メインコンテンツ */}
        <div className="max-w-4xl mx-auto space-y-6">
          
          {/* 設定エリア */}
          <Card className="bg-slate-900/50 border-slate-700">
            <CardHeader>
              <CardTitle className="text-white">検索設定</CardTitle>
              <CardDescription className="text-slate-400">
                検索戦略を選択してください
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-4">
                <label className="text-sm text-slate-300">検索戦略:</label>
                <Select value={strategy} onValueChange={(v) => setStrategy(v as typeof strategy)}>
                  <SelectTrigger className="w-[200px] bg-slate-800 border-slate-700 text-white">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-slate-800 border-slate-700">
                    <SelectItem value="dense" className="text-white">Dense</SelectItem>
                    <SelectItem value="prefilter_dense" className="text-white">Prefilter + Dense</SelectItem>
                    <SelectItem value="hybrid" className="text-white">Hybrid</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>

          {/* 録音ボタンエリア */}
          <div className="flex flex-col items-center justify-center py-12">
            <Button
              onClick={handleRecordingButtonClick}
              disabled={recordingState === 'processing'}
              size="lg"
              className={`
                w-32 h-32 rounded-full
                ${recordingState === 'recording' 
                  ? 'bg-red-500 hover:bg-red-600 animate-pulse' 
                  : 'bg-blue-500 hover:bg-blue-600'
                }
                ${recordingState === 'processing' ? 'opacity-50 cursor-not-allowed' : ''}
              `}
            >
              {recordingState === 'processing' ? (
                <Loader2 className="w-16 h-16 animate-spin" />
              ) : recordingState === 'recording' ? (
                <MicOff className="w-16 h-16" />
              ) : (
                <Mic className="w-16 h-16" />
              )}
            </Button>
            
            <div className="mt-4 text-center">
              {recordingState === 'idle' && (
                <p className="text-slate-400">クリックして録音開始</p>
              )}
              {recordingState === 'recording' && (
                <p className="text-red-400 font-semibold">録音中... もう一度クリックで停止</p>
              )}
              {recordingState === 'processing' && (
                <p className="text-blue-400 font-semibold">処理中...</p>
              )}
            </div>
          </div>

          {/* エラー表示 */}
          {error && (
            <Card className="bg-red-900/20 border-red-700">
              <CardContent className="pt-6">
                <p className="text-red-400">{error}</p>
              </CardContent>
            </Card>
          )}

          {/* ユーザー発話 */}
          {userQuery && (
            <Card className="bg-slate-800/50 border-slate-600">
              <CardHeader>
                <CardTitle className="text-blue-400">あなたの質問</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-white text-lg">{userQuery}</p>
              </CardContent>
            </Card>
          )}

          {/* システム回答 */}
          {systemAnswer && (
            <Card className="bg-slate-800/50 border-slate-600">
              <CardHeader>
                <CardTitle className="text-green-400">AIの回答</CardTitle>
                <CardDescription className="text-slate-400">
                  検索戦略: {strategy} / 参照チャンク: {contextChunks.length}件
                </CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-white text-lg leading-relaxed">{systemAnswer}</p>
              </CardContent>
            </Card>
          )}

          {/* コンテキストチャンク（デバッグ用） */}
          {contextChunks.length > 0 && (
            <Card className="bg-slate-900/50 border-slate-700">
              <CardHeader>
                <CardTitle className="text-slate-300">参照情報（デバッグ用）</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {contextChunks.slice(0, 3).map((chunk, idx) => (
                    <div key={chunk.chunk_id} className="p-3 bg-slate-800/50 rounded border border-slate-700">
                      <div className="text-xs text-slate-500 mb-1">
                        Chunk #{idx + 1} | Score: {chunk.score.toFixed(3)}
                      </div>
                      <p className="text-sm text-slate-300 line-clamp-3">{chunk.text}</p>
                      {chunk.metadata.professor && (
                        <div className="text-xs text-slate-400 mt-1">
                          教員: {chunk.metadata.professor.join(', ')}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

        </div>
      </div>
    </div>
  );
}

