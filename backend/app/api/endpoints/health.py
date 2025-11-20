"""
ヘルスチェックエンドポイント
"""
from fastapi import APIRouter

from app.config import settings
from app.models.responses import HealthResponse
from app.services.lm_studio_service import LMStudioService

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    ヘルスチェックエンドポイント
    
    Returns:
        HealthResponse: システムの健康状態
        - healthy: 全サービス正常
        - degraded: 一部サービス利用不可（Whisperのみ動作）
        - unhealthy: 主要サービス利用不可
    """
    # LM Studioの状態確認
    lm_studio_available = await LMStudioService.check_model_availability()
    
    # ステータス決定
    if lm_studio_available:
        status = "healthy"
    else:
        status = "degraded"  # Whisperは動作するが、LM Studioが利用不可
    
    return HealthResponse(
        status=status,
        whisper_model=settings.WHISPER_MODEL,
        lm_studio_url=settings.LM_STUDIO_BASE_URL,
        lm_studio_model=settings.LM_STUDIO_MODEL,
        lm_studio_available=lm_studio_available,
        supported_formats=list(settings.SUPPORTED_AUDIO_FORMATS)
    )
