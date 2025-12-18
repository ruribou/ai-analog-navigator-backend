"""
E2Eパフォーマンス評価スクリプト
各コンポーネントの応答時間を計測し、統計情報を出力
"""
import asyncio
import json
import sys
import statistics
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging
import httpx

# プロジェクトルートをPYTHONPATHに追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 設定
BASE_URL = "http://localhost:8000"
TIMEOUT = 120.0  # 秒


class E2EPerformanceEvaluator:
    """E2Eパフォーマンス評価クラス"""

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.results: Dict[str, List[float]] = {
            "rag_query": [],
            "tts": [],
            "e2e_text_to_speech": [],  # RAG + TTS
        }

    async def measure_rag_query(
        self,
        client: httpx.AsyncClient,
        query: str,
        strategy: str = "hybrid"
    ) -> Dict[str, Any]:
        """RAGクエリのレイテンシを計測"""
        payload = {
            "query": query,
            "strategy": strategy,
            "top_k": 5
        }

        start = asyncio.get_event_loop().time()
        response = await client.post(
            f"{self.base_url}/api/rag_query",
            json=payload,
            timeout=TIMEOUT
        )
        elapsed_ms = (asyncio.get_event_loop().time() - start) * 1000

        if response.status_code == 200:
            data = response.json()
            return {
                "success": True,
                "latency_ms": elapsed_ms,
                "answer_length": len(data.get("answer", "")),
                "context_count": len(data.get("context_chunks", []))
            }
        else:
            return {
                "success": False,
                "latency_ms": elapsed_ms,
                "error": response.text
            }

    async def measure_tts(
        self,
        client: httpx.AsyncClient,
        text: str
    ) -> Dict[str, Any]:
        """TTS（音声合成）のレイテンシを計測"""
        payload = {
            "text": text,
            "speaker_id": 3,  # ずんだもん
            "speed_scale": 1.0
        }

        start = asyncio.get_event_loop().time()
        response = await client.post(
            f"{self.base_url}/api/tts/synthesize",
            json=payload,
            timeout=TIMEOUT
        )
        elapsed_ms = (asyncio.get_event_loop().time() - start) * 1000

        if response.status_code == 200:
            return {
                "success": True,
                "latency_ms": elapsed_ms,
                "audio_size_bytes": len(response.content)
            }
        else:
            return {
                "success": False,
                "latency_ms": elapsed_ms,
                "error": response.text
            }

    async def measure_e2e_text_to_speech(
        self,
        client: httpx.AsyncClient,
        query: str
    ) -> Dict[str, Any]:
        """E2E（RAG→TTS）のレイテンシを計測"""
        total_start = asyncio.get_event_loop().time()

        # Step 1: RAGクエリ
        rag_result = await self.measure_rag_query(client, query)
        if not rag_result["success"]:
            return {
                "success": False,
                "error": f"RAGクエリ失敗: {rag_result.get('error', 'unknown')}"
            }

        # Step 2: TTS
        # 回答テキストを取得（長すぎる場合は切り詰め）
        answer_text = rag_result.get("answer_length", 0)

        # RAGの回答を再取得（実際のテキストが必要）
        rag_response = await client.post(
            f"{self.base_url}/api/rag_query",
            json={"query": query, "strategy": "hybrid", "top_k": 5},
            timeout=TIMEOUT
        )
        answer = rag_response.json().get("answer", "")[:500]  # 最大500文字

        tts_result = await self.measure_tts(client, answer)

        total_elapsed_ms = (asyncio.get_event_loop().time() - total_start) * 1000

        return {
            "success": tts_result["success"],
            "total_latency_ms": total_elapsed_ms,
            "rag_latency_ms": rag_result["latency_ms"],
            "tts_latency_ms": tts_result["latency_ms"],
            "answer_length": len(answer),
            "audio_size_bytes": tts_result.get("audio_size_bytes", 0)
        }

    async def run_evaluation(
        self,
        queries: List[str],
        iterations: int = 3
    ) -> Dict[str, Any]:
        """評価を実行"""
        logger.info(f"E2E評価開始: {len(queries)}クエリ x {iterations}回")

        all_results = {
            "rag_query": [],
            "tts": [],
            "e2e": []
        }

        async with httpx.AsyncClient() as client:
            # ヘルスチェック
            try:
                health_resp = await client.get(f"{self.base_url}/health")
                if health_resp.status_code != 200:
                    raise Exception("APIサーバーが起動していません")
            except Exception as e:
                logger.error(f"ヘルスチェック失敗: {e}")
                raise

            for iteration in range(1, iterations + 1):
                logger.info(f"\n=== イテレーション {iteration}/{iterations} ===")

                for idx, query in enumerate(queries, 1):
                    logger.info(f"[{idx}/{len(queries)}] {query[:50]}...")

                    # RAGクエリ計測
                    rag_result = await self.measure_rag_query(client, query)
                    if rag_result["success"]:
                        all_results["rag_query"].append(rag_result["latency_ms"])
                        logger.info(f"  RAG: {rag_result['latency_ms']:.0f}ms")

                    # TTS計測（短いテキストで）
                    tts_result = await self.measure_tts(
                        client,
                        "これはテスト用の音声合成です。"
                    )
                    if tts_result["success"]:
                        all_results["tts"].append(tts_result["latency_ms"])
                        logger.info(f"  TTS: {tts_result['latency_ms']:.0f}ms")

                    # E2E計測
                    e2e_result = await self.measure_e2e_text_to_speech(client, query)
                    if e2e_result["success"]:
                        all_results["e2e"].append(e2e_result["total_latency_ms"])
                        logger.info(f"  E2E: {e2e_result['total_latency_ms']:.0f}ms")

                    # レート制限対策
                    await asyncio.sleep(0.5)

        return all_results

    @staticmethod
    def calculate_statistics(latencies: List[float]) -> Dict[str, float]:
        """統計情報を計算"""
        if not latencies:
            return {}

        def percentile(data: List[float], p: float) -> float:
            sorted_data = sorted(data)
            k = (len(sorted_data) - 1) * p / 100
            f = int(k)
            c = f + 1 if f + 1 < len(sorted_data) else f
            return sorted_data[f] + (sorted_data[c] - sorted_data[f]) * (k - f)

        return {
            "count": len(latencies),
            "mean": round(statistics.mean(latencies), 2),
            "median": round(statistics.median(latencies), 2),
            "stdev": round(statistics.stdev(latencies), 2) if len(latencies) > 1 else 0,
            "p95": round(percentile(latencies, 95), 2),
            "p99": round(percentile(latencies, 99), 2),
            "min": round(min(latencies), 2),
            "max": round(max(latencies), 2)
        }


def print_results_table(results: Dict[str, Dict[str, float]]) -> None:
    """結果テーブルを表示"""
    print("\n" + "=" * 80)
    print("E2Eパフォーマンス評価結果")
    print("=" * 80)
    print(f"{'コンポーネント':<20} {'回数':>8} {'平均(ms)':>10} {'中央値':>10} "
          f"{'P95':>10} {'P99':>10} {'最小':>10} {'最大':>10}")
    print("-" * 80)

    for component, stats in results.items():
        if stats:
            print(f"{component:<20} {stats['count']:>8} {stats['mean']:>10.0f} "
                  f"{stats['median']:>10.0f} {stats['p95']:>10.0f} "
                  f"{stats['p99']:>10.0f} {stats['min']:>10.0f} {stats['max']:>10.0f}")

    print("=" * 80)


async def main():
    """メイン処理"""
    eval_dir = Path(__file__).parent

    # テストクエリ（既存のquery_setから読み込み）
    queries = []
    query_file = eval_dir / "query_set.jsonl"

    if query_file.exists():
        with open(query_file) as f:
            for line in f:
                q = json.loads(line)
                queries.append(q["query"])
        logger.info(f"クエリセット読み込み: {len(queries)}問")
    else:
        # デフォルトクエリ
        queries = [
            "神戸先生はどんな研究をしていますか？",
            "IoTの研究をしている研究室はどこですか？",
            "機械学習を学べる研究室を教えてください",
            "セキュリティの研究について教えてください",
            "自然言語処理の研究室はありますか？"
        ]
        logger.info(f"デフォルトクエリ使用: {len(queries)}問")

    # 評価実行
    evaluator = E2EPerformanceEvaluator()

    try:
        raw_results = await evaluator.run_evaluation(
            queries=queries[:10],  # 最初の10クエリで評価
            iterations=2  # 2回繰り返し
        )
    except Exception as e:
        logger.error(f"評価実行エラー: {e}")
        sys.exit(1)

    # 統計計算
    stats_results = {}
    for component, latencies in raw_results.items():
        stats_results[component] = evaluator.calculate_statistics(latencies)

    # 結果表示
    print_results_table(stats_results)

    # 結果保存
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = eval_dir / f"perf_results_{timestamp}.json"

    with open(results_file, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": timestamp,
            "config": {
                "queries_count": len(queries[:10]),
                "iterations": 2
            },
            "statistics": stats_results,
            "raw_latencies": raw_results
        }, f, indent=2, ensure_ascii=False)

    logger.info(f"\n結果を保存: {results_file}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n評価を中断しました")
    except Exception as e:
        logger.error(f"評価実行エラー: {e}", exc_info=True)
        sys.exit(1)
