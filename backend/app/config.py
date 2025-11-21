"""
設定ファイル
"""
import os
from typing import Optional

class Settings:
    """アプリケーション設定"""
    
    # Whisper設定 (faster-whisper)
    WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "large-v3")  # large-v3, medium, small, base
    WHISPER_DEVICE: str = os.getenv("WHISPER_DEVICE", "cuda")  # cuda or cpu
    WHISPER_COMPUTE_TYPE: str = os.getenv("WHISPER_COMPUTE_TYPE", "float16")  # float16, int8, int8_float16
    WHISPER_BEAM_SIZE: int = int(os.getenv("WHISPER_BEAM_SIZE", "5"))
    WHISPER_VAD_FILTER: bool = os.getenv("WHISPER_VAD_FILTER", "true").lower() == "true"
    WHISPER_INITIAL_PROMPT: str = os.getenv(
        "WHISPER_INITIAL_PROMPT",
        "ここは東京電機大学のオープンキャンパスです。"
        "理工学部、情報システムデザイン学系、神戸英利（かんべひでとし）、秋山、高橋、IoT、M2M、CPS などの専門用語や教員名が頻出します。"
        "ASR の誤認識を避けるため、固有名詞はできるだけ正しい表記を選んでください。"
    )
    
    # LM Studio設定
    # デフォルト: openai/gpt-oss-20b @ http://127.0.0.1:1234
    LM_STUDIO_BASE_URL: str = os.getenv("LM_STUDIO_BASE_URL", "http://127.0.0.1:1234/v1")
    LM_STUDIO_MODEL: str = os.getenv("LM_STUDIO_MODEL", "openai/gpt-oss-20b")
    LM_STUDIO_TIMEOUT: int = int(os.getenv("LM_STUDIO_TIMEOUT", "60"))  # 20Bモデルなので少し長めに
    
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
