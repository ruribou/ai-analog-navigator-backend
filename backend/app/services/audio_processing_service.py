"""
音声処理統合サービス（Whisper → 辞書正規化 → LLM校正パイプライン）
"""
import logging
import time
from typing import Dict, Any

from app.services.whisper_service import WhisperService
from app.services.lm_studio_service import LMStudioService
from app.services.transcription_corrector import correct_transcription

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
        correct_text: bool = True,
        use_dict: bool = True,
        use_llm: bool = False
    ) -> Dict[str, Any]:
        """音声ファイルを処理（文字起こし + 校正）
        
        Args:
            audio_file_path: 音声ファイルのパス
            correct_text: 校正を行うか（後方互換性のため）
            use_dict: 固有名詞辞書による正規化を使用するか
            use_llm: LM Studio による校正を使用するか
        
        Returns:
            処理結果の辞書
        """
        start_time = time.time()
        
        # Step 1: Whisper で文字起こし
        logger.info("Step 1: Whisper 文字起こし開始")
        whisper_start = time.time()
        transcribed_text = await self.whisper_service.transcribe(audio_file_path)
        whisper_time = time.time() - whisper_start
        logger.info(f"Whisper 完了: {len(transcribed_text)}文字, {whisper_time:.2f}秒")
        
        # Step 2: 校正処理（新パイプライン）
        corrected_text = None
        
        if correct_text and transcribed_text:
            # 新しい校正パイプラインを使用
            logger.info(f"Step 2: 校正開始 (use_dict={use_dict}, use_llm={use_llm})")
            correction_start = time.time()
            
            corrected_text = await correct_transcription(
                transcribed_text,
                use_dict=use_dict,
                use_llm=use_llm
            )
            
            correction_time = time.time() - correction_start
            logger.info(f"校正完了: {len(corrected_text)}文字, {correction_time:.2f}秒")
            
            # 変更があったかログ出力
            if corrected_text != transcribed_text:
                logger.info("=== 校正による変更 ===")
                logger.info(f"元: {transcribed_text}")
                logger.info(f"後: {corrected_text}")
        
        processing_time = time.time() - start_time
        
        return {
            "transcribed_text": transcribed_text,
            "corrected_text": corrected_text,
            "processing_time": processing_time,
            "whisper_time": whisper_time,
            "dict_correction_enabled": use_dict,
            "llm_correction_enabled": use_llm
        }
    
    async def process_audio_legacy(
        self, 
        audio_file_path: str, 
        correct_text: bool = True
    ) -> Dict[str, Any]:
        """旧形式の音声処理（後方互換性のため残す）
        
        LM Studioの旧校正ロジックを使用
        """
        start_time = time.time()
        
        # 文字起こし
        logger.info("文字起こし開始（Legacy）")
        transcribed_text = await self.whisper_service.transcribe(audio_file_path)
        logger.info(f"文字起こし完了: {len(transcribed_text)}文字")
        
        # 文章校正（オプション）
        corrected_text = None
        if correct_text and transcribed_text:
            logger.info("文章校正開始（Legacy）")
            corrected_text = await self.lm_studio_service.correct_text(transcribed_text)
            logger.info("文章校正完了")
        
        processing_time = time.time() - start_time
        
        return {
            "transcribed_text": transcribed_text,
            "corrected_text": corrected_text,
            "processing_time": processing_time
        }
