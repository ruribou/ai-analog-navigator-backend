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


@router.post("/transcription")
async def transcribe_audio(
    file: UploadFile = File(...),
    use_dict: bool = True,
    use_llm: bool = False
):
    """
    音声ファイルを文字起こし（faster-whisper + 校正パイプライン）
    
    Args:
        file: 音声ファイル（mp3, wav, m4a, flac, webm, ogg等）
        use_dict: 固有名詞辞書による正規化を使用するか（デフォルト: True）
        use_llm: LM Studio による校正を使用するか（デフォルト: False）
    
    Returns:
        JSONレスポンス: {
            "text": "...",  # 校正後のテキスト（校正なしの場合はWhisper生出力）
            "raw_text": "...",  # Whisper生出力
            "corrected_text": "...",  # 校正後のテキスト（校正ありの場合）
            "processing_time": 3.2,
            "whisper_time": 1.5,
            "dict_correction_enabled": true,
            "llm_correction_enabled": false
        }
    """
    import time
    
    # ファイルサイズチェック
    if file.size and file.size > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"ファイルサイズが大きすぎます。最大サイズ: {settings.MAX_FILE_SIZE / 1000000}MB"
        )
    
    # ファイル名チェック
    if not file.filename:
        raise HTTPException(status_code=400, detail="ファイル名が指定されていません")
    
    # サポートされているファイル形式をチェック
    file_extension = os.path.splitext(file.filename)[1].lower()
    
    # webm, oggも追加
    supported_formats = list(settings.SUPPORTED_AUDIO_FORMATS) + ['.webm', '.ogg']
    
    if file_extension not in supported_formats:
        raise HTTPException(
            status_code=400, 
            detail=f"サポートされていないファイル形式です。サポート形式: {', '.join(supported_formats)}"
        )
    
    # 一時ファイルに保存して処理
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
        try:
            start_time = time.time()
            
            # ファイルを一時保存
            content = await file.read()
            temp_file.write(content)
            temp_file.flush()
            
            logger.info(f"音声文字起こし開始: {file.filename} (use_dict={use_dict}, use_llm={use_llm})")
            
            # 新しいパイプラインで処理
            service = get_audio_service()
            result = await service.process_audio(
                temp_file.name,
                correct_text=(use_dict or use_llm),  # どちらかがTrueなら校正実行
                use_dict=use_dict,
                use_llm=use_llm
            )
            
            duration_sec = time.time() - start_time
            
            logger.info(f"音声文字起こし完了: 処理時間 {duration_sec:.2f}秒")
            
            # レスポンスを構築
            response = {
                "text": result["corrected_text"] or result["transcribed_text"],
                "raw_text": result["transcribed_text"],
                "processing_time": round(duration_sec, 2),
                "whisper_time": round(result.get("whisper_time", 0), 2),
                "dict_correction_enabled": use_dict,
                "llm_correction_enabled": use_llm
            }
            
            # 校正結果がある場合は追加
            if result["corrected_text"]:
                response["corrected_text"] = result["corrected_text"]
            
            return response
            
        except HTTPException:
            # HTTPExceptionはそのまま再発生
            raise
        except Exception as e:
            logger.error(f"音声文字起こしエラー: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"音声文字起こし中にエラーが発生しました: {str(e)}"
            )
        finally:
            # 一時ファイルを削除
            try:
                os.unlink(temp_file.name)
            except Exception as e:
                logger.warning(f"一時ファイル削除エラー: {e}")


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_and_correct(
    audio_file: UploadFile = File(...),
    correct_text: bool = True,
    use_dict: bool = True,
    use_llm: bool = False
):
    """
    音声ファイルを文字起こしし、オプションで文章校正を行う（新パイプライン対応）
    
    Args:
        audio_file: 音声ファイル（mp3, wav, m4a, flac等）
        correct_text: 文章校正を行うかどうか（デフォルト: True、後方互換性のため）
        use_dict: 固有名詞辞書による正規化を使用するか（デフォルト: True）
        use_llm: LM Studio による校正を使用するか（デフォルト: False）
    
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
            
            logger.info(f"音声処理開始: {audio_file.filename} (use_dict={use_dict}, use_llm={use_llm})")
            
            # 音声処理実行（新パイプライン）
            service = get_audio_service()
            result = await service.process_audio(
                temp_file.name,
                correct_text=correct_text,
                use_dict=use_dict,
                use_llm=use_llm
            )
            
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
            logger.error(f"音声処理エラー: {e}", exc_info=True)
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
