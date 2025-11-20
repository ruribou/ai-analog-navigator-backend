"""
Whisper音声文字起こしサービス
"""
import whisper
import logging
from fastapi import HTTPException

from app.config import settings
from app.core.exceptions import WhisperModelError, AudioProcessingError

logger = logging.getLogger(__name__)


class WhisperService:
    """Whisper音声文字起こしサービス"""
    
    def __init__(self):
        self.model = None
    
    def load_model(self):
        """Whisperモデルを読み込み"""
        try:
            logger.info(f"Whisperモデル '{settings.WHISPER_MODEL}' を読み込み中...")
            self.model = whisper.load_model(settings.WHISPER_MODEL)
            logger.info("Whisperモデルの読み込み完了")
        except Exception as e:
            logger.error(f"Whisperモデル読み込みエラー: {e}")
            raise WhisperModelError(f"Whisperモデルの読み込みに失敗しました: {str(e)}")
    
    async def transcribe(self, audio_file_path: str) -> str:
        """音声ファイルを文字起こし"""
        if self.model is None:
            raise HTTPException(status_code=503, detail="Whisperモデルが読み込まれていません")
        
        try:
            result = self.model.transcribe(audio_file_path)
            return result["text"].strip()
        except Exception as e:
            logger.error(f"文字起こしエラー: {e}")
            raise AudioProcessingError(f"文字起こし処理でエラーが発生しました: {str(e)}")
