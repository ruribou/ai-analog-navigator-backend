"""
応答時間メトリクス収集・集計サービス
"""
import json
import logging
import statistics
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from threading import Lock

logger = logging.getLogger(__name__)


@dataclass
class RequestMetric:
    """リクエストメトリクス"""
    timestamp: str
    endpoint: str
    method: str
    latency_ms: float
    status_code: int
    extra: Optional[Dict[str, Any]] = None


class MetricsService:
    """メトリクス収集・集計サービス"""

    def __init__(self, metrics_dir: Optional[Path] = None):
        if metrics_dir is None:
            metrics_dir = Path(__file__).parent.parent / "evaluation" / "metrics"
        self.metrics_dir = metrics_dir
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

        # 現在のセッションファイル
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.metrics_file = self.metrics_dir / f"metrics_{session_id}.jsonl"

        logger.info(f"MetricsService initialized: {self.metrics_file}")

    def record(self, metric: RequestMetric) -> None:
        """メトリクスを記録"""
        with self._lock:
            with open(self.metrics_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(metric), ensure_ascii=False) + "\n")

    def record_request(
        self,
        endpoint: str,
        method: str,
        latency_ms: float,
        status_code: int,
        extra: Optional[Dict[str, Any]] = None
    ) -> None:
        """リクエストメトリクスを記録（便利メソッド）"""
        metric = RequestMetric(
            timestamp=datetime.now().isoformat(),
            endpoint=endpoint,
            method=method,
            latency_ms=latency_ms,
            status_code=status_code,
            extra=extra
        )
        self.record(metric)

    def load_metrics(self, file_path: Optional[Path] = None) -> List[RequestMetric]:
        """メトリクスファイルを読み込み"""
        if file_path is None:
            file_path = self.metrics_file

        metrics = []
        if file_path.exists():
            with open(file_path, encoding="utf-8") as f:
                for line in f:
                    data = json.loads(line.strip())
                    metrics.append(RequestMetric(**data))
        return metrics

    def calculate_stats(
        self,
        metrics: List[RequestMetric],
        endpoint_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """統計情報を計算

        Returns:
            {
                "count": リクエスト数,
                "latency": {
                    "mean": 平均,
                    "median": 中央値,
                    "p95": 95パーセンタイル,
                    "p99": 99パーセンタイル,
                    "min": 最小,
                    "max": 最大
                },
                "success_rate": 成功率,
                "by_endpoint": エンドポイント別の統計
            }
        """
        if endpoint_filter:
            metrics = [m for m in metrics if m.endpoint == endpoint_filter]

        if not metrics:
            return {"count": 0, "latency": {}, "success_rate": 0.0}

        latencies = [m.latency_ms for m in metrics]
        successful = [m for m in metrics if 200 <= m.status_code < 300]

        def percentile(data: List[float], p: float) -> float:
            """パーセンタイル計算"""
            if not data:
                return 0.0
            sorted_data = sorted(data)
            k = (len(sorted_data) - 1) * p / 100
            f = int(k)
            c = f + 1 if f + 1 < len(sorted_data) else f
            return sorted_data[f] + (sorted_data[c] - sorted_data[f]) * (k - f)

        # エンドポイント別の集計
        by_endpoint: Dict[str, List[float]] = {}
        for m in metrics:
            if m.endpoint not in by_endpoint:
                by_endpoint[m.endpoint] = []
            by_endpoint[m.endpoint].append(m.latency_ms)

        endpoint_stats = {}
        for endpoint, ep_latencies in by_endpoint.items():
            endpoint_stats[endpoint] = {
                "count": len(ep_latencies),
                "mean": round(statistics.mean(ep_latencies), 2),
                "median": round(statistics.median(ep_latencies), 2),
                "p95": round(percentile(ep_latencies, 95), 2),
                "min": round(min(ep_latencies), 2),
                "max": round(max(ep_latencies), 2),
            }

        return {
            "count": len(metrics),
            "latency": {
                "mean": round(statistics.mean(latencies), 2),
                "median": round(statistics.median(latencies), 2),
                "p95": round(percentile(latencies, 95), 2),
                "p99": round(percentile(latencies, 99), 2),
                "min": round(min(latencies), 2),
                "max": round(max(latencies), 2),
            },
            "success_rate": round(len(successful) / len(metrics) * 100, 2),
            "by_endpoint": endpoint_stats
        }

    def get_current_stats(self) -> Dict[str, Any]:
        """現在のセッションの統計を取得"""
        metrics = self.load_metrics()
        return self.calculate_stats(metrics)

    def list_metrics_files(self) -> List[Path]:
        """メトリクスファイル一覧を取得"""
        return sorted(self.metrics_dir.glob("metrics_*.jsonl"))


# シングルトンインスタンス
_metrics_service: Optional[MetricsService] = None


def get_metrics_service() -> MetricsService:
    """MetricsServiceのシングルトンを取得"""
    global _metrics_service
    if _metrics_service is None:
        _metrics_service = MetricsService()
    return _metrics_service


class Timer:
    """コンテキストマネージャで処理時間を計測"""

    def __init__(self):
        self.start_time: float = 0
        self.end_time: float = 0
        self.elapsed_ms: float = 0

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, *args):
        self.end_time = time.perf_counter()
        self.elapsed_ms = (self.end_time - self.start_time) * 1000
