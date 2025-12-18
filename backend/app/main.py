"""
FastAPIアプリケーションのメインファイル
"""
import logging
from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse

from app.config import settings
from app.core.middleware import setup_middleware
from app.core.exceptions import http_exception_handler, general_exception_handler
from app.api.endpoints import health, transcription, search, rag_query, tts

# ログ設定
logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL))
logger = logging.getLogger(__name__)

# FastAPIアプリケーション作成
app = FastAPI(
    title="AI Analog Navigator Backend",
    description="音声文字起こしと文章校正のためのAPI",
    version="0.1.0"
)

# ミドルウェア設定
setup_middleware(app)

# エラーハンドラー設定
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# ルーター設定
app.include_router(health.router, tags=["health"])
app.include_router(transcription.router, prefix="/api", tags=["transcription"])
app.include_router(search.router, prefix="/api", tags=["search"])
app.include_router(rag_query.router, prefix="/api", tags=["rag"])
app.include_router(tts.router, prefix="/api", tags=["tts"])


@app.get("/", response_class=PlainTextResponse)
async def root():
    """ルートエンドポイント"""
    return "AI Analog Navigator Backend API"


@app.on_event("startup")
async def startup_event():
    """アプリケーション起動時の初期化"""
    logger.info("アプリケーション起動開始")
    logger.info("アプリケーション起動完了")
