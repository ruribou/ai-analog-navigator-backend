"""
設定ファイル
"""
import os
from typing import Optional

class Settings:
    """アプリケーション設定"""
    
    # Whisper設定
    WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "base")  # tiny, base, small, medium, large
    
    # LM Studio設定
    LM_STUDIO_BASE_URL: str = os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")
    LM_STUDIO_MODEL: str = os.getenv("LM_STUDIO_MODEL", "local-model")
    LM_STUDIO_TIMEOUT: int = int(os.getenv("LM_STUDIO_TIMEOUT", "30"))
    
    # ファイルアップロード設定
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "50000000"))  # 50MB
    SUPPORTED_AUDIO_FORMATS: set = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".wma"}
    
    # 将来のRAG設定用
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")
    VECTOR_DIMENSION: int = int(os.getenv("VECTOR_DIMENSION", "1536"))
    
    # ログ設定
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # CORS設定
    CORS_ORIGINS: list = os.getenv("CORS_ORIGINS", "*").split(",")

settings = Settings()
