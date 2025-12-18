"""
メトリクスエンドポイント
応答時間の統計情報を取得
"""
from fastapi import APIRouter
from typing import Dict, Any
import logging

from app.services.metrics_service import get_metrics_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/metrics", tags=["Metrics"])


@router.get("", response_model=Dict[str, Any])
async def get_metrics():
    """
    現在のセッションのメトリクス統計を取得

    Returns:
        {
            "count": リクエスト数,
            "latency": {
                "mean": 平均(ms),
                "median": 中央値(ms),
                "p95": 95パーセンタイル(ms),
                "p99": 99パーセンタイル(ms),
                "min": 最小(ms),
                "max": 最大(ms)
            },
            "success_rate": 成功率(%),
            "by_endpoint": エンドポイント別の統計
        }
    """
    metrics_service = get_metrics_service()
    stats = metrics_service.get_current_stats()

    logger.info(f"メトリクス取得: {stats.get('count', 0)}リクエスト")

    return stats


@router.get("/files")
async def list_metrics_files():
    """
    保存されているメトリクスファイル一覧を取得

    Returns:
        {
            "files": [ファイル名のリスト]
        }
    """
    metrics_service = get_metrics_service()
    files = metrics_service.list_metrics_files()

    return {
        "files": [f.name for f in files],
        "current_file": metrics_service.metrics_file.name
    }


@router.delete("")
async def reset_metrics():
    """
    現在のセッションのメトリクスをリセット（新しいファイルで開始）

    Returns:
        {
            "message": "メトリクスをリセットしました",
            "new_file": 新しいファイル名
        }
    """
    from app.services.metrics_service import MetricsService
    global _metrics_service

    # 新しいセッションを開始
    from app.services import metrics_service as ms_module
    ms_module._metrics_service = MetricsService()

    return {
        "message": "メトリクスをリセットしました",
        "new_file": ms_module._metrics_service.metrics_file.name
    }
