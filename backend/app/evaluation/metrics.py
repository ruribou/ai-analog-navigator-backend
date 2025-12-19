"""
評価指標計算モジュール
Recall@k, MRR@k の計算
"""
from typing import List, Dict, Set


def recall_at_k(retrieved: List[str], relevant: Set[str], k: int) -> float:
    """
    Recall@k: Top k件の中に正解が1つでも含まれるか

    Args:
        retrieved: 検索結果のチャンクIDリスト（順序付き）
        relevant: 正解チャンクIDの集合
        k: 上位k件を評価

    Returns:
        1.0（正解あり）または 0.0（正解なし）
    """
    if not relevant:
        return 0.0

    top_k = set(retrieved[:k])
    return 1.0 if len(top_k & relevant) > 0 else 0.0


def mrr_at_k(retrieved: List[str], relevant: Set[str], k: int) -> float:
    """
    MRR@k: 最初の正解が出現した順位の逆数

    Args:
        retrieved: 検索結果のチャンクIDリスト（順序付き）
        relevant: 正解チャンクIDの集合
        k: 上位k件を評価

    Returns:
        正解出現順位の逆数（1位=1.0, 2位=0.5, ...）、出現しない場合は0.0
    """
    if not relevant:
        return 0.0

    for i, chunk_id in enumerate(retrieved[:k], 1):
        if chunk_id in relevant:
            return 1.0 / i
    return 0.0


def calculate_metrics(
    results: Dict[str, List[str]],
    gold_labels: Dict[str, List[str]],
    k_values: List[int] = [5, 10]
) -> Dict:
    """
    全クエリに対する平均メトリクスを計算

    Args:
        results: {query_id: [chunk_id, ...]} の辞書
        gold_labels: {query_id: [relevant_chunk_id, ...]} の辞書
        k_values: 評価するkの値のリスト

    Returns:
        平均メトリクスの辞書 {"recall@5": 0.8, "mrr@5": 0.65, ...}
    """
    metrics = {f"recall@{k}": [] for k in k_values}
    metrics.update({f"mrr@{k}": [] for k in k_values})

    for query_id, retrieved in results.items():
        relevant = set(gold_labels.get(query_id, []))
        for k in k_values:
            metrics[f"recall@{k}"].append(recall_at_k(retrieved, relevant, k))
            metrics[f"mrr@{k}"].append(mrr_at_k(retrieved, relevant, k))

    # 平均を計算
    avg_metrics = {
        key: sum(values) / len(values) if values else 0.0
        for key, values in metrics.items()
    }
    return avg_metrics


def calculate_metrics_by_category(
    results: Dict[str, List[str]],
    gold_labels: Dict[str, List[str]],
    query_categories: Dict[str, str],
    k_values: List[int] = [5, 10]
) -> Dict[str, Dict]:
    """
    カテゴリ別に平均メトリクスを計算

    Args:
        results: {query_id: [chunk_id, ...]} の辞書
        gold_labels: {query_id: [relevant_chunk_id, ...]} の辞書
        query_categories: {query_id: category} の辞書
        k_values: 評価するkの値のリスト

    Returns:
        カテゴリ別メトリクスの辞書
    """
    # カテゴリごとに結果を分類
    category_results = {}
    for query_id, retrieved in results.items():
        category = query_categories.get(query_id, "unknown")
        if category not in category_results:
            category_results[category] = {}
        category_results[category][query_id] = retrieved

    # カテゴリごとにメトリクスを計算
    category_metrics = {}
    for category, cat_results in category_results.items():
        category_metrics[category] = calculate_metrics(
            cat_results, gold_labels, k_values
        )

    return category_metrics
