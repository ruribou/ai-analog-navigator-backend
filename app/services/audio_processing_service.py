"""
音声処理統合サービス
"""
import logging
import time
from typing import Dict, Any

from app.services.whisper_service import WhisperService
from app.services.lm_studio_service import LMStudioService

logger = logging.getLogger(__name__)


class AudioProcessingService:
    """音声処理統合サービス"""
    
    def __init__(self):
        self.whisper_service = WhisperService()
        self.lm_studio_service = LMStudioService()
    
    def initialize(self):
        """サービス初期化"""
        self.whisper_service.load_model()
    
    async def process_audio(
        self, 
        audio_file_path: str, 
        correct_text: bool = True
    ) -> Dict[str, Any]:
        """音声ファイルを処理（文字起こし + 校正）"""
        start_time = time.time()
        
        # 文字起こし
        logger.info("文字起こし開始")
        transcribed_text = await self.whisper_service.transcribe(audio_file_path)
        logger.info(f"文字起こし完了: {len(transcribed_text)}文字")
        
        # 文章校正（オプション）
        corrected_text = None
        if correct_text and transcribed_text:
            logger.info("文章校正開始")
            corrected_text = await self.lm_studio_service.correct_text(transcribed_text)
            logger.info("文章校正完了")
        
        processing_time = time.time() - start_time
        
        return {
            "transcribed_text": transcribed_text,
            "corrected_text": corrected_text,
            "processing_time": processing_time
        }
