"""
Whisper音声文字起こしサービス (faster-whisper版)
"""
import logging
from faster_whisper import WhisperModel
from fastapi import HTTPException

from app.config import settings
from app.core.exceptions import WhisperModelError, AudioProcessingError

logger = logging.getLogger(__name__)


class WhisperService:
    """Whisper音声文字起こしサービス (faster-whisper使用)"""

    def __init__(self):
        self.model = None

    def load_model(self):
        """Whisperモデルを読み込み"""
        try:
            logger.info(f"faster-whisper モデル '{settings.WHISPER_MODEL}' を読み込み中...")
            logger.info(f"デバイス: {settings.WHISPER_DEVICE}, Compute Type: {settings.WHISPER_COMPUTE_TYPE}")

            self.model = WhisperModel(
                settings.WHISPER_MODEL,
                device=settings.WHISPER_DEVICE,
                compute_type=settings.WHISPER_COMPUTE_TYPE
            )
            logger.info("Whisperモデルの読み込み完了")
        except Exception as e:
            logger.error(f"Whisperモデル読み込みエラー: {e}")
            raise WhisperModelError(f"Whisperモデルの読み込みに失敗しました: {str(e)}")

    async def transcribe(self, audio_file_path: str) -> str:
        """音声ファイルを文字起こし

        Args:
            audio_file_path: 音声ファイルのパス

        Returns:
            文字起こし結果のテキスト
        """
        if self.model is None:
            raise HTTPException(status_code=503, detail="Whisperモデルが読み込まれていません")

        try:
            logger.info(f"音声ファイルを文字起こし中: {audio_file_path}")

            # VADパラメータ
            vad_parameters = {
                "threshold": 0.5,
                "min_speech_duration_ms": 250,
                "min_silence_duration_ms": 2000
            }

            # faster-whisper で文字起こし実行
            segments, info = self.model.transcribe(
                audio_file_path,
                language="ja",  # 日本語を強制
                task="transcribe",  # 翻訳ではなく文字起こし
                temperature=0.0,  # 決定論的な出力（安定性重視）
                beam_size=settings.WHISPER_BEAM_SIZE,  # ビームサーチで精度向上
                vad_filter=settings.WHISPER_VAD_FILTER,  # VAD（音声区間検出）を有効化
                vad_parameters=vad_parameters if settings.WHISPER_VAD_FILTER else None,
                initial_prompt=settings.WHISPER_INITIAL_PROMPT  # ドメイン固有のプロンプト
            )

            # セグメントを結合してテキスト化
            text_segments = [segment.text for segment in segments]
            result_text = " ".join(text_segments).strip()

            logger.info(f"文字起こし完了: {len(text_segments)} セグメント, {len(result_text)} 文字")
            logger.debug(f"認識言語: {info.language}, 確率: {info.language_probability:.2f}")

            return result_text

        except Exception as e:
            logger.error(f"文字起こしエラー: {e}")
            raise AudioProcessingError(f"文字起こし処理でエラーが発生しました: {str(e)}")
