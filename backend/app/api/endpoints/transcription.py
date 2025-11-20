"""
音声文字起こしエンドポイント
"""
import os
import tempfile
import logging
from fastapi import APIRouter, File, UploadFile, HTTPException

from app.config import settings
from app.models.responses import TranscriptionResponse
from app.services.audio_processing_service import AudioProcessingService

logger = logging.getLogger(__name__)
router = APIRouter()

# サービス初期化（グローバル変数として）
audio_service = None


def get_audio_service() -> AudioProcessingService:
    """音声処理サービスを取得（遅延初期化）"""
    global audio_service
    if audio_service is None:
        logger.info("音声処理サービス初期化開始")
        audio_service = AudioProcessingService()
        audio_service.initialize()
        logger.info("音声処理サービス初期化完了")
    return audio_service


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_and_correct(
    audio_file: UploadFile = File(...),
    correct_text: bool = True
):
    """
    音声ファイルを文字起こしし、オプションで文章校正を行う
    
    Args:
        audio_file: 音声ファイル（mp3, wav, m4a, flac等）
        correct_text: 文章校正を行うかどうか（デフォルト: True）
    
    Returns:
        TranscriptionResponse: 文字起こし結果と校正結果
    """
    # ファイルサイズチェック
    if audio_file.size and audio_file.size > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"ファイルサイズが大きすぎます。最大サイズ: {settings.MAX_FILE_SIZE / 1000000}MB"
        )
    
    # ファイル名チェック
    if not audio_file.filename:
        raise HTTPException(status_code=400, detail="ファイル名が指定されていません")
    
    # サポートされているファイル形式をチェック
    file_extension = os.path.splitext(audio_file.filename)[1].lower()
    
    if file_extension not in settings.SUPPORTED_AUDIO_FORMATS:
        raise HTTPException(
            status_code=400, 
            detail=f"サポートされていないファイル形式です。サポート形式: {', '.join(settings.SUPPORTED_AUDIO_FORMATS)}"
        )
    
    # 一時ファイルに保存して処理
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
        try:
            # ファイルを一時保存
            content = await audio_file.read()
            temp_file.write(content)
            temp_file.flush()
            
            logger.info(f"音声処理開始: {audio_file.filename}")
            
            # 音声処理実行
            service = get_audio_service()
            result = await service.process_audio(temp_file.name, correct_text)
            
            logger.info(f"音声処理完了: 処理時間 {result['processing_time']:.2f}秒")
            
            return TranscriptionResponse(
                transcribed_text=result["transcribed_text"],
                corrected_text=result["corrected_text"],
                processing_time=result["processing_time"]
            )
            
        except HTTPException:
            # HTTPExceptionはそのまま再発生
            raise
        except Exception as e:
            logger.error(f"音声処理エラー: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"音声処理中にエラーが発生しました: {str(e)}"
            )
        finally:
            # 一時ファイルを削除
            try:
                os.unlink(temp_file.name)
            except Exception as e:
                logger.warning(f"一時ファイル削除エラー: {e}")
