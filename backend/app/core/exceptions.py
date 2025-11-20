"""
カスタム例外とエラーハンドラー
"""
import logging
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from app.models.responses import ErrorResponse
from app.config import settings

logger = logging.getLogger(__name__)


class AudioProcessingError(Exception):
    """音声処理エラー"""
    pass


class WhisperModelError(Exception):
    """Whisperモデルエラー"""
    pass


class LMStudioError(Exception):
    """LM Studioエラー"""
    pass


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """HTTPエラーハンドラー"""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            detail=f"Status Code: {exc.status_code}"
        ).dict()
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """一般的なエラーハンドラー"""
    logger.error(f"予期しないエラー: {exc}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="内部サーバーエラーが発生しました",
            detail=str(exc) if settings.LOG_LEVEL == "DEBUG" else None
        ).dict()
    )
