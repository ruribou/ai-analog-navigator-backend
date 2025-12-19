"""
オフライン評価スクリプト
3種類の検索戦略（Dense, Prefilter+Dense, Hybrid）を評価
"""
import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
import logging

# プロジェクトルートをPYTHONPATHに追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.evaluation.metrics import calculate_metrics, calculate_metrics_by_category
from app.services.rag_service import RAGService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_evaluation():
    """評価実験のメイン処理"""
    eval_dir = Path(__file__).parent

    # 1. クエリセット読み込み
    logger.info("クエリセットを読み込み中...")
    queries = []
    query_categories = {}
    with open(eval_dir / "query_set.jsonl") as f:
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

    # 3. RAG Serviceインスタンス作成
    rag_service = RAGService()

    # 4. 各戦略で検索実行
    strategies = ["dense", "prefilter_dense", "hybrid"]
    all_results = {}
    all_strategy_results = {}

    for strategy in strategies:
        logger.info(f"\n{'='*60}")
        logger.info(f"=== 評価開始: {strategy} ===")
        logger.info(f"{'='*60}")

        strategy_results = {}

        for idx, query in enumerate(queries, 1):
            qid = query["id"]
            qtext = query["query"]

            try:
                logger.info(f"[{idx}/{len(queries)}] {qid}: {qtext}")

                # 戦略に応じて検索実行
                # Note: prefilter_dense は dense に統合
                if strategy in ("dense", "prefilter_dense"):
                    results = await rag_service.search_dense(
                        qtext, filters=None, top_k=10
                    )

                elif strategy == "hybrid":
                    results = await rag_service.search_hybrid(
                        qtext, filters=None, top_k=10, alpha=0.6, beta=0.4
                    )

                # チャンクIDのリストを保存
                chunk_ids = [r["chunk_id"] for r in results]
                strategy_results[qid] = chunk_ids

                # デバッグ情報
                if results:
                    logger.info(f"  → Top 3: {chunk_ids[:3]}")
                    logger.info(f"  → スコア: {[f'{r['score']:.3f}' for r in results[:3]]}")
                else:
                    logger.warning("  → 結果なし")

            except Exception as e:
                logger.error(f"  → エラー: {e}")
                strategy_results[qid] = []

        # 5. メトリクス計算
        logger.info(f"\n{'='*60}")
        logger.info(f"=== メトリクス計算: {strategy} ===")
        logger.info(f"{'='*60}")

        # 全体メトリクス
        metrics = calculate_metrics(
            strategy_results, gold_labels, k_values=[5, 10]
        )

        logger.info(f"Recall@5:  {metrics['recall@5']:.3f}")
        logger.info(f"Recall@10: {metrics['recall@10']:.3f}")
        logger.info(f"MRR@5:     {metrics['mrr@5']:.3f}")
        logger.info(f"MRR@10:    {metrics['mrr@10']:.3f}")

        # カテゴリ別メトリクス
        category_metrics = calculate_metrics_by_category(
            strategy_results, gold_labels, query_categories, k_values=[5, 10]
        )

        logger.info("\nカテゴリ別メトリクス:")
        for category, cat_metrics in category_metrics.items():
            logger.info(f"  {category}:")
            logger.info(f"    Recall@5: {cat_metrics['recall@5']:.3f}")
            logger.info(f"    MRR@5:    {cat_metrics['mrr@5']:.3f}")

        all_results[strategy] = {
            "overall": metrics,
            "by_category": category_metrics
        }
        all_strategy_results[strategy] = strategy_results

    # 6. 結果を保存
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = eval_dir / f"results_{timestamp}.json"

    with open(results_file, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": timestamp,
            "num_queries": len(queries),
            "strategies": strategies,
            "metrics": all_results,
            "raw_results": all_strategy_results
        }, f, indent=2, ensure_ascii=False)

    logger.info(f"\n{'='*60}")
    logger.info("=== 評価完了 ===")
    logger.info(f"{'='*60}")
    logger.info(f"結果を保存: {results_file}")

    # 7. サマリーテーブル表示
    print_summary_table(all_results)


def print_summary_table(all_results: dict):
    """結果サマリーテーブルを表示"""
    print("\n" + "="*80)
    print("戦略別総合スコア表")
    print("="*80)
    print(f"{'戦略':<20} {'Recall@5':>12} {'Recall@10':>12} {'MRR@5':>12} {'MRR@10':>12}")
    print("-"*80)

    for strategy, results in all_results.items():
        metrics = results["overall"]
        print(f"{strategy:<20} {metrics['recall@5']:>12.3f} {metrics['recall@10']:>12.3f} "
              f"{metrics['mrr@5']:>12.3f} {metrics['mrr@10']:>12.3f}")

    print("="*80)

    # カテゴリ別表示
    print("\n" + "="*80)
    print("カテゴリ別 Recall@5 比較")
    print("="*80)

    # カテゴリを収集
    all_categories = set()
    for results in all_results.values():
        all_categories.update(results["by_category"].keys())

    print(f"{'戦略':<20}", end="")
    for cat in sorted(all_categories):
        print(f"{cat:>15}", end="")
    print()
    print("-"*80)

    for strategy, results in all_results.items():
        print(f"{strategy:<20}", end="")
        for cat in sorted(all_categories):
            if cat in results["by_category"]:
                recall = results["by_category"][cat]["recall@5"]
                print(f"{recall:>15.3f}", end="")
            else:
                print(f"{'N/A':>15}", end="")
        print()

    print("="*80)


if __name__ == "__main__":
    try:
        asyncio.run(run_evaluation())
    except KeyboardInterrupt:
        logger.info("\n評価を中断しました")
    except Exception as e:
        logger.error(f"評価実行エラー: {e}", exc_info=True)
        sys.exit(1)
