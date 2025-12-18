"""
2段階クエリ補正効果測定スクリプト
擬似ASRテキストに対して、補正あり/なしでのRAG検索精度を比較
"""
import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import logging

# プロジェクトルートをPYTHONPATHに追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.evaluation.metrics import calculate_metrics, calculate_metrics_by_category
from app.services.rag_service import RAGService
from app.services.transcription_corrector import normalize_with_domain_terms

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CorrectionEvaluator:
    """2段階補正効果測定クラス"""

    def __init__(self):
        self.rag_service = RAGService()

    def apply_correction(
        self,
        text: str,
        use_dict: bool = False,
        use_llm: bool = False
    ) -> str:
        """補正を適用（同期版）"""
        if not use_dict and not use_llm:
            return text

        if use_dict and not use_llm:
            return normalize_with_domain_terms(text)

        # LLM使用時は非同期関数を呼び出す
        # この評価では辞書補正のみを主に扱う
        return normalize_with_domain_terms(text)

    async def search_with_strategy(
        self,
        query: str,
        strategy: str = "hybrid",
        top_k: int = 10
    ) -> List[str]:
        """指定した戦略で検索を実行"""
        if strategy == "dense":
            results = await self.rag_service.search_dense(query, top_k=top_k)
        elif strategy == "hybrid":
            results = await self.rag_service.search_hybrid(
                query, filters=None, top_k=top_k, alpha=0.6, beta=0.4
            )
        else:
            results = await self.rag_service.search_dense(query, top_k=top_k)

        return [r["chunk_id"] for r in results]

    def count_entity_matches(
        self,
        _original_query: str,
        corrected_query: str,
        expected_entities: List[str]
    ) -> Dict[str, Any]:
        """固有名詞の一致率を計算"""
        if not expected_entities:
            return {"total": 0, "matched": 0, "rate": 1.0}

        matched = 0
        for entity in expected_entities:
            if entity in corrected_query:
                matched += 1

        return {
            "total": len(expected_entities),
            "matched": matched,
            "rate": matched / len(expected_entities) if expected_entities else 1.0
        }


async def run_correction_evaluation():
    """補正効果測定のメイン処理"""
    eval_dir = Path(__file__).parent

    # 1. 評価データセット読み込み
    logger.info("評価データセットを読み込み中...")
    queries = []
    query_categories = {}

    eval_file = eval_dir / "correction_eval_set.jsonl"
    if not eval_file.exists():
        logger.error(f"評価データセットが見つかりません: {eval_file}")
        sys.exit(1)

    with open(eval_file) as f:
        for line in f:
            q = json.loads(line)
            queries.append(q)
            query_categories[q["id"]] = q["category"]

    logger.info(f"クエリ数: {len(queries)}問")

    # 2. ゴールドラベル読み込み
    logger.info("ゴールドラベルを読み込み中...")
    with open(eval_dir / "gold_labels.json") as f:
        gold_labels = json.load(f)

    logger.info(f"ゴールドラベル: {len(gold_labels)}件")

    # 3. 評価実行
    evaluator = CorrectionEvaluator()

    # 評価パターン定義
    patterns = {
        "no_correction": {"use_dict": False, "use_llm": False, "label": "補正なし（ベースライン）"},
        "dict_only": {"use_dict": True, "use_llm": False, "label": "辞書補正のみ"},
        # "full_correction": {"use_dict": True, "use_llm": True, "label": "2段階補正"}  # LLM必要時
    }

    all_results = {}
    entity_stats = {}

    for pattern_name, pattern_config in patterns.items():
        logger.info(f"\n{'='*60}")
        logger.info(f"=== 評価開始: {pattern_config['label']} ===")
        logger.info(f"{'='*60}")

        pattern_results = {}
        entity_matches = {"total": 0, "matched": 0}

        for idx, query_data in enumerate(queries, 1):
            qid = query_data["id"]
            original_query = query_data["query"]
            simulated_asr = query_data["simulated_asr"]
            expected_entities = query_data.get("expected_entities", [])

            logger.info(f"[{idx}/{len(queries)}] {qid}")
            logger.info(f"  正解クエリ: {original_query}")
            logger.info(f"  擬似ASR: {simulated_asr}")

            # 補正を適用
            corrected_query = evaluator.apply_correction(
                simulated_asr,
                use_dict=pattern_config["use_dict"],
                use_llm=pattern_config["use_llm"]
            )
            logger.info(f"  補正後: {corrected_query}")

            # 固有名詞マッチ率を計算
            entity_result = evaluator.count_entity_matches(
                original_query, corrected_query, expected_entities
            )
            entity_matches["total"] += entity_result["total"]
            entity_matches["matched"] += entity_result["matched"]

            if expected_entities:
                logger.info(f"  固有名詞: {entity_result['matched']}/{entity_result['total']}")

            # RAG検索を実行
            try:
                chunk_ids = await evaluator.search_with_strategy(
                    corrected_query, strategy="hybrid", top_k=10
                )
                pattern_results[qid] = chunk_ids

                if chunk_ids:
                    logger.info(f"  検索結果: {len(chunk_ids)}件, Top1={chunk_ids[0][:8]}...")
                else:
                    logger.warning("  検索結果: 0件")

            except Exception as e:
                logger.error(f"  検索エラー: {e}")
                pattern_results[qid] = []

        # メトリクス計算
        logger.info(f"\n{'='*60}")
        logger.info(f"=== メトリクス計算: {pattern_config['label']} ===")
        logger.info(f"{'='*60}")

        metrics = calculate_metrics(pattern_results, gold_labels, k_values=[5, 10])

        logger.info(f"Recall@5:  {metrics['recall@5']:.3f}")
        logger.info(f"Recall@10: {metrics['recall@10']:.3f}")
        logger.info(f"MRR@5:     {metrics['mrr@5']:.3f}")
        logger.info(f"MRR@10:    {metrics['mrr@10']:.3f}")

        # 固有名詞正解率
        entity_accuracy = (
            entity_matches["matched"] / entity_matches["total"]
            if entity_matches["total"] > 0 else 1.0
        )
        logger.info(f"固有名詞正解率: {entity_accuracy:.1%} ({entity_matches['matched']}/{entity_matches['total']})")

        # カテゴリ別メトリクス
        category_metrics = calculate_metrics_by_category(
            pattern_results, gold_labels, query_categories, k_values=[5, 10]
        )

        all_results[pattern_name] = {
            "label": pattern_config["label"],
            "overall": metrics,
            "by_category": category_metrics,
            "entity_accuracy": entity_accuracy,
            "entity_stats": entity_matches
        }
        entity_stats[pattern_name] = entity_matches

    # 4. 結果を保存
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = eval_dir / f"correction_eval_results_{timestamp}.json"

    with open(results_file, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": timestamp,
            "num_queries": len(queries),
            "patterns": list(patterns.keys()),
            "results": all_results
        }, f, indent=2, ensure_ascii=False)

    logger.info(f"\n結果を保存: {results_file}")

    # 5. サマリーテーブル表示
    print_summary_table(all_results)


def print_summary_table(all_results: Dict[str, Dict]) -> None:
    """結果サマリーテーブルを表示（論文の表3形式）"""
    print("\n" + "=" * 90)
    print("2段階クエリ補正パイプライン評価結果（表3形式）")
    print("=" * 90)
    print(f"{'手法':<25} {'固有名詞正解率':>15} {'Recall@5':>12} {'MRR@5':>12} {'Recall@10':>12}")
    print("-" * 90)

    for results in all_results.values():
        label = results["label"]
        entity_acc = results["entity_accuracy"]
        metrics = results["overall"]
        print(f"{label:<25} {entity_acc:>14.1%} {metrics['recall@5']:>12.3f} "
              f"{metrics['mrr@5']:>12.3f} {metrics['recall@10']:>12.3f}")

    print("=" * 90)

    # 改善率表示
    if "no_correction" in all_results and "dict_only" in all_results:
        baseline = all_results["no_correction"]["overall"]
        improved = all_results["dict_only"]["overall"]

        print("\n=== 辞書補正による改善率 ===")
        for metric in ["recall@5", "mrr@5", "recall@10"]:
            if baseline[metric] > 0:
                improvement = (improved[metric] - baseline[metric]) / baseline[metric] * 100
                print(f"  {metric}: {improvement:+.1f}%")
            else:
                print(f"  {metric}: N/A (baseline=0)")

    # カテゴリ別表示
    print("\n" + "=" * 90)
    print("カテゴリ別 Recall@5 比較")
    print("=" * 90)

    # カテゴリを収集
    all_categories = set()
    for results in all_results.values():
        all_categories.update(results["by_category"].keys())

    print(f"{'手法':<25}", end="")
    for cat in sorted(all_categories):
        print(f"{cat:>15}", end="")
    print()
    print("-" * 90)

    for results in all_results.values():
        label = results["label"]
        print(f"{label:<25}", end="")
        for cat in sorted(all_categories):
            if cat in results["by_category"]:
                recall = results["by_category"][cat]["recall@5"]
                print(f"{recall:>15.3f}", end="")
            else:
                print(f"{'N/A':>15}", end="")
        print()

    print("=" * 90)


if __name__ == "__main__":
    try:
        asyncio.run(run_correction_evaluation())
    except KeyboardInterrupt:
        logger.info("\n評価を中断しました")
    except Exception as e:
        logger.error(f"評価実行エラー: {e}", exc_info=True)
        sys.exit(1)
