"""
ヘルスチェックエンドポイント
"""
from fastapi import APIRouter

from app.config import settings
from app.models.responses import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """ヘルスチェックエンドポイント"""
    return HealthResponse(
        status="healthy",
        whisper_model=settings.WHISPER_MODEL,
        lm_studio_url=settings.LM_STUDIO_BASE_URL,
        supported_formats=list(settings.SUPPORTED_AUDIO_FORMATS)
    )
