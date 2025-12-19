"""
RAG（Retrieval-Augmented Generation）サービス
検索戦略: Dense, Prefilter+Dense, Hybrid (Dense+BM25)
"""
from typing import Dict, Any, List, Optional, Tuple
import logging
from psycopg2.extras import DictCursor

from app.services.lm_studio_service import LMStudioService
from app.services.embedding_service import EmbeddingService
from app.services.db_service import DBService

logger = logging.getLogger(__name__)


class RAGService:
    """RAG（Retrieval-Augmented Generation）サービス"""

    def __init__(self):
        self.lm_studio = LMStudioService()
        self.embedding = EmbeddingService()
        self.db_service = DBService()

    # ========== ヘルパーメソッド ==========

    def _build_filter_clause(
        self,
        filters: Optional[Dict[str, Any]]
    ) -> Tuple[str, List[Any]]:
        """
        フィルタ条件からWHERE句とパラメータを構築

        Args:
            filters: フィルタ条件 (department, professor, campus, lab)

        Returns:
            (WHERE句文字列, パラメータリスト)
        """
        if not filters:
            return "TRUE", []

        clauses = []
        params = []

        if filters.get('department'):
            clauses.append("department = %s")
            params.append(filters['department'])

        if filters.get('professor'):
            clauses.append("professor @> ARRAY[%s]")
            params.append(filters['professor'])

        if filters.get('campus'):
            clauses.append("campus = %s")
            params.append(filters['campus'])

        if filters.get('lab'):
            clauses.append("lab = %s")
            params.append(filters['lab'])

        return " AND ".join(clauses) if clauses else "TRUE", params

    def _format_chunk_result(
        self,
        row: Dict[str, Any],
        score: float
    ) -> Dict[str, Any]:
        """
        DBの行データを統一フォーマットに変換

        Args:
            row: DictCursorの行
            score: スコア

        Returns:
            統一フォーマットの検索結果
        """
        return {
            "chunk_id": row["chunk_id"],
            "text": row["text"],
            "score": float(score),
            "source_url": row["source_url"],
            "metadata": {
                "campus": row["campus"],
                "department": row["department"],
                "lab": row["lab"],
                "professor": row["professor"],
                "tags": row["tags"]
            }
        }

    async def _get_query_embedding(self, query_text: str) -> List[float]:
        """クエリテキストを埋め込みベクトルに変換"""
        embeddings = await self.embedding.generate([query_text])
        return embeddings[0]

    # ========== 検索メソッド ==========

    async def search_dense(
        self,
        query_text: str,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Dense検索（ベクトル類似度検索）

        Args:
            query_text: 検索クエリ
            filters: フィルタ条件（オプション）
            top_k: 取得件数

        Returns:
            検索結果のリスト
        """
        try:
            query_embedding = await self._get_query_embedding(query_text)
            where_clause, filter_params = self._build_filter_clause(filters)

            conn = self.db_service.get_connection()
            try:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    query = f"""
                        SELECT
                            chunk_id::text,
                            text,
                            campus,
                            department,
                            lab,
                            professor,
                            source_url,
                            tags,
                            1 - (embedding <=> %s::vector) AS score
                        FROM chunks
                        WHERE {where_clause}
                        ORDER BY embedding <=> %s::vector
                        LIMIT %s
                    """
                    params = [query_embedding] + filter_params + [query_embedding, top_k]
                    cur.execute(query, params)

                    return [
                        self._format_chunk_result(row, row["score"])
                        for row in cur.fetchall()
                    ]
            finally:
                conn.close()

        except Exception as e:
            logger.error(f"Dense検索エラー: {e}")
            raise

    async def search_hybrid(
        self,
        query_text: str,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 10,
        alpha: float = 0.6,
        beta: float = 0.4,
        candidate_multiplier: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Hybrid検索（Dense + BM25のスコア合成）

        Args:
            query_text: 検索クエリ
            filters: フィルタ条件（オプション）
            top_k: 取得件数
            alpha: Dense検索の重み
            beta: BM25検索の重み
            candidate_multiplier: 候補取得の倍率

        Returns:
            検索結果のリスト
        """
        try:
            candidate_size = top_k * candidate_multiplier

            # 1. Dense/BM25で候補を取得
            dense_results = await self._get_dense_candidates(
                query_text, filters, candidate_size
            )
            bm25_results = await self._get_bm25_candidates(
                query_text, filters, candidate_size
            )

            # 2. スコア正規化と合成
            dense_scores = self._normalize_scores(dense_results)
            bm25_scores = self._normalize_scores(bm25_results)

            merged_scores = {}
            for chunk_id, score in dense_scores.items():
                merged_scores[chunk_id] = alpha * score
            for chunk_id, score in bm25_scores.items():
                merged_scores[chunk_id] = merged_scores.get(chunk_id, 0) + beta * score

            # 3. 上位k件を取得
            sorted_chunk_ids = sorted(
                merged_scores.keys(),
                key=lambda x: merged_scores[x],
                reverse=True
            )[:top_k]

            if not sorted_chunk_ids:
                return []

            # 4. チャンク詳細を取得して結果を組み立て
            conn = self.db_service.get_connection()
            try:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute(
                        """
                        SELECT
                            chunk_id::text,
                            text,
                            campus,
                            department,
                            lab,
                            professor,
                            source_url,
                            tags
                        FROM chunks
                        WHERE chunk_id::text = ANY(%s)
                        """,
                        (sorted_chunk_ids,)
                    )
                    chunk_map = {row["chunk_id"]: row for row in cur.fetchall()}

                return [
                    self._format_chunk_result(chunk_map[cid], merged_scores[cid])
                    for cid in sorted_chunk_ids
                    if cid in chunk_map
                ]
            finally:
                conn.close()

        except Exception as e:
            logger.error(f"Hybrid検索エラー: {e}")
            raise

    # ========== 内部検索メソッド ==========

    async def _get_dense_candidates(
        self,
        query_text: str,
        filters: Optional[Dict[str, Any]],
        limit: int
    ) -> Dict[str, float]:
        """Dense検索で候補を取得（内部用）"""
        results = await self.search_dense(query_text, filters, limit)
        return {r["chunk_id"]: r["score"] for r in results}

    async def _get_bm25_candidates(
        self,
        query_text: str,
        filters: Optional[Dict[str, Any]],
        limit: int
    ) -> Dict[str, float]:
        """BM25検索で候補を取得（内部用）"""
        try:
            where_clause, filter_params = self._build_filter_clause(filters)

            # BM25用のtsquery条件を追加
            if where_clause == "TRUE":
                where_clause = "text_tsv @@ plainto_tsquery('simple', %s)"
            else:
                where_clause = f"text_tsv @@ plainto_tsquery('simple', %s) AND {where_clause}"

            conn = self.db_service.get_connection()
            try:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute(
                        f"""
                        SELECT
                            chunk_id::text,
                            ts_rank_cd(text_tsv, plainto_tsquery('simple', %s)) AS bm25_score
                        FROM chunks
                        WHERE {where_clause}
                        ORDER BY bm25_score DESC
                        LIMIT %s
                        """,
                        [query_text, query_text] + filter_params + [limit]
                    )
                    return {
                        row["chunk_id"]: float(row["bm25_score"])
                        for row in cur.fetchall()
                    }
            finally:
                conn.close()

        except Exception as e:
            logger.error(f"BM25検索エラー: {e}")
            return {}

    def _normalize_scores(self, scores: Dict[str, float]) -> Dict[str, float]:
        """スコアを0〜1にMin-Max正規化"""
        if not scores:
            return {}

        values = list(scores.values())
        min_score, max_score = min(values), max(values)

        if max_score == min_score:
            return {k: 1.0 for k in scores}

        return {
            k: (v - min_score) / (max_score - min_score)
            for k, v in scores.items()
        }

    # ========== 回答生成 ==========

    async def query_with_answer(
        self,
        query_text: str,
        strategy: str = "dense",
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        クエリに対して検索 + 回答生成を実行

        Args:
            query_text: 検索クエリ
            strategy: 検索戦略 (dense, hybrid)
            filters: フィルタ条件
            top_k: 取得件数

        Returns:
            回答と使用したチャンク情報
        """
        try:
            # Note: prefilter_dense は dense に統合（後方互換）
            if strategy in ("dense", "prefilter_dense"):
                chunks = await self.search_dense(query_text, filters, top_k)
            elif strategy == "hybrid":
                chunks = await self.search_hybrid(query_text, filters, top_k)
            else:
                raise ValueError(f"Unknown strategy: {strategy}")

            answer = await self.lm_studio.generate_answer(query_text, chunks)

            return {
                "answer": answer,
                "used_strategy": strategy,
                "context_chunks": chunks
            }

        except Exception as e:
            logger.error(f"RAGクエリエラー: {e}")
            raise
