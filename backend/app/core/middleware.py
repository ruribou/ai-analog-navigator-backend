"""
ミドルウェア設定
"""
import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

logger = logging.getLogger(__name__)


class MetricsMiddleware(BaseHTTPMiddleware):
    """リクエスト応答時間を計測するミドルウェア"""

    # 計測対象のエンドポイントプレフィックス
    TRACKED_PREFIXES = ["/api/"]

    async def dispatch(self, request: Request, call_next) -> Response:
        # 計測対象外のエンドポイントはスキップ
        if not any(request.url.path.startswith(p) for p in self.TRACKED_PREFIXES):
            return await call_next(request)

        start_time = time.perf_counter()

        response = await call_next(request)

        # 応答時間を計算
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # メトリクス記録（遅延インポートで循環参照回避）
        try:
            from app.services.metrics_service import get_metrics_service
            metrics_service = get_metrics_service()
            metrics_service.record_request(
                endpoint=request.url.path,
                method=request.method,
                latency_ms=elapsed_ms,
                status_code=response.status_code
            )
        except Exception as e:
            logger.warning(f"メトリクス記録エラー: {e}")

        # レスポンスヘッダーに応答時間を追加
        response.headers["X-Response-Time-Ms"] = f"{elapsed_ms:.2f}"

        return response


def setup_middleware(app: FastAPI) -> None:
    """ミドルウェアの設定"""

    # メトリクス計測ミドルウェア
    app.add_middleware(MetricsMiddleware)

    # CORS設定
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
