"""
APIレスポンスモデル
"""
from pydantic import BaseModel
from typing import Optional


class TranscriptionResponse(BaseModel):
    """音声文字起こしレスポンス"""
    transcribed_text: str
    corrected_text: Optional[str] = None
    processing_time: Optional[float] = None


class ErrorResponse(BaseModel):
    """エラーレスポンス"""
    error: str
    detail: Optional[str] = None


class HealthResponse(BaseModel):
    """ヘルスチェックレスポンス"""
    status: str  # "healthy", "degraded", "unhealthy"
    whisper_model: str
    lm_studio_url: str
    lm_studio_model: Optional[str] = None
    lm_studio_available: Optional[bool] = None
    supported_formats: list
