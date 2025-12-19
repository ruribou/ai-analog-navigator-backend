"""
音声文字起こしエンドポイント
"""
import os
import tempfile
import logging
from functools import lru_cache

from fastapi import APIRouter, File, UploadFile, HTTPException, Depends

from app.config import settings
from app.models.responses import TranscriptionResponse
from app.services.audio_processing_service import AudioProcessingService

logger = logging.getLogger(__name__)
router = APIRouter()


@lru_cache
def get_audio_service() -> AudioProcessingService:
    """
    音声処理サービスを取得（シングルトン）

    lru_cacheにより初回呼び出し時のみ初期化され、
    以降はキャッシュされたインスタンスを返す。
    """
    logger.info("音声処理サービス初期化開始")
    service = AudioProcessingService()
    service.initialize()
    logger.info("音声処理サービス初期化完了")
    return service


def _validate_audio_file(file: UploadFile, extra_formats: list[str] | None = None):
    """
    音声ファイルのバリデーション

    Args:
        file: アップロードされたファイル
        extra_formats: 追加でサポートする形式

    Raises:
        HTTPException: バリデーションエラー時
    """
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
    supported_formats = list(settings.SUPPORTED_AUDIO_FORMATS)
    if extra_formats:
        supported_formats.extend(extra_formats)

    if file_extension not in supported_formats:
        raise HTTPException(
            status_code=400,
            detail=f"サポートされていないファイル形式です。サポート形式: {', '.join(supported_formats)}"
        )

    return file_extension


@router.post("/transcription")
async def transcribe_audio(
    file: UploadFile = File(...),
    use_dict: bool = True,
    use_llm: bool = False,
    service: AudioProcessingService = Depends(get_audio_service)
):
    """
    音声ファイルを文字起こし（faster-whisper + 校正パイプライン）

    Args:
        file: 音声ファイル（mp3, wav, m4a, flac, webm, ogg等）
        use_dict: 固有名詞辞書による正規化を使用するか（デフォルト: True）
        use_llm: LM Studio による校正を使用するか（デフォルト: False）

    Returns:
        JSONレスポンス
    """
    import time

    file_extension = _validate_audio_file(file, extra_formats=['.webm', '.ogg'])

    with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
        try:
            start_time = time.time()

            content = await file.read()
            temp_file.write(content)
            temp_file.flush()

            logger.info(
                f"音声文字起こし開始: {file.filename} (use_dict={use_dict}, use_llm={use_llm})"
            )

            result = await service.process_audio(
                temp_file.name,
                correct_text=(use_dict or use_llm),
                use_dict=use_dict,
                use_llm=use_llm
            )

            duration_sec = time.time() - start_time
            logger.info(f"音声文字起こし完了: 処理時間 {duration_sec:.2f}秒")

            response = {
                "text": result["corrected_text"] or result["transcribed_text"],
                "raw_text": result["transcribed_text"],
                "processing_time": round(duration_sec, 2),
                "whisper_time": round(result.get("whisper_time", 0), 2),
                "dict_correction_enabled": use_dict,
                "llm_correction_enabled": use_llm
            }

            if result["corrected_text"]:
                response["corrected_text"] = result["corrected_text"]

            return response

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"音声文字起こしエラー: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"音声文字起こし中にエラーが発生しました: {str(e)}"
            )
        finally:
            try:
                os.unlink(temp_file.name)
            except Exception as e:
                logger.warning(f"一時ファイル削除エラー: {e}")


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_and_correct(
    audio_file: UploadFile = File(...),
    correct_text: bool = True,
    use_dict: bool = True,
    use_llm: bool = False,
    service: AudioProcessingService = Depends(get_audio_service)
):
    """
    音声ファイルを文字起こしし、オプションで文章校正を行う

    Args:
        audio_file: 音声ファイル（mp3, wav, m4a, flac等）
        correct_text: 文章校正を行うかどうか（デフォルト: True）
        use_dict: 固有名詞辞書による正規化を使用するか（デフォルト: True）
        use_llm: LM Studio による校正を使用するか（デフォルト: False）

    Returns:
        TranscriptionResponse: 文字起こし結果と校正結果
    """
    file_extension = _validate_audio_file(audio_file)

    with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
        try:
            content = await audio_file.read()
            temp_file.write(content)
            temp_file.flush()

            logger.info(
                f"音声処理開始: {audio_file.filename} (use_dict={use_dict}, use_llm={use_llm})"
            )

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
            raise
        except Exception as e:
            logger.error(f"音声処理エラー: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"音声処理中にエラーが発生しました: {str(e)}"
            )
        finally:
            try:
                os.unlink(temp_file.name)
            except Exception as e:
                logger.warning(f"一時ファイル削除エラー: {e}")
