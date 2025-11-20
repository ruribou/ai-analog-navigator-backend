"""
RAG（Retrieval-Augmented Generation）サービス
検索戦略: Dense, Prefilter+Dense, Hybrid (Dense+BM25)
"""
from typing import Dict, Any, List, Optional
import logging
from psycopg2.extras import DictCursor

from app.services.lm_studio_service import LMStudioService
from app.services.db_service import DBService

logger = logging.getLogger(__name__)


class RAGService:
    """RAG（Retrieval-Augmented Generation）サービス"""
    
    def __init__(self):
        self.lm_studio = LMStudioService()
        self.db_service = DBService()
    
    async def _get_query_embedding(self, query_text: str) -> List[float]:
        """
        クエリテキストを埋め込みベクトルに変換
        
        Args:
            query_text: クエリテキスト
        
        Returns:
            埋め込みベクトル (768次元)
        """
        embeddings = await self.lm_studio.generate_embeddings([query_text])
        return embeddings[0]
    
    async def search_dense(
        self, 
        query_text: str, 
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Dense検索（ベクトル類似度検索のみ）
        
        Args:
            query_text: 検索クエリ
            top_k: 取得件数
        
        Returns:
            検索結果のリスト
        """
        try:
            # 1. クエリをembedding化
            query_embedding = await self._get_query_embedding(query_text)
            
            # 2. ベクトル類似度検索
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
                            tags,
                            1 - (embedding <=> %s::vector) AS score
                        FROM chunks
                        ORDER BY embedding <=> %s::vector
                        LIMIT %s
                        """,
                        (query_embedding, query_embedding, top_k)
                    )
                    results = cur.fetchall()
                    
                    return [
                        {
                            "chunk_id": row["chunk_id"],
                            "text": row["text"],
                            "score": float(row["score"]),
                            "source_url": row["source_url"],
                            "metadata": {
                                "campus": row["campus"],
                                "department": row["department"],
                                "lab": row["lab"],
                                "professor": row["professor"],
                                "tags": row["tags"]
                            }
                        }
                        for row in results
                    ]
            finally:
                conn.close()
                
        except Exception as e:
            logger.error(f"Dense検索エラー: {e}")
            raise
    
    async def search_prefilter_dense(
        self,
        query_text: str,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Prefilter + Dense検索（メタデータフィルタ + ベクトル検索）
        
        Args:
            query_text: 検索クエリ
            filters: フィルタ条件 (department, professor, campus, lab等)
            top_k: 取得件数
        
        Returns:
            検索結果のリスト
        """
        try:
            # 1. クエリをembedding化
            query_embedding = await self._get_query_embedding(query_text)
            
            # 2. フィルタ条件を動的に構築
            where_clauses = []
            params = [query_embedding]
            
            if filters:
                if filters.get('department'):
                    where_clauses.append("department = %s")
                    params.append(filters['department'])
                
                if filters.get('professor'):
                    where_clauses.append("professor @> ARRAY[%s]")
                    params.append(filters['professor'])
                
                if filters.get('campus'):
                    where_clauses.append("campus = %s")
                    params.append(filters['campus'])
                
                if filters.get('lab'):
                    where_clauses.append("lab = %s")
                    params.append(filters['lab'])
            
            where_clause = " AND ".join(where_clauses) if where_clauses else "TRUE"
            
            # 3. フィルタ付きベクトル検索
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
                    params_with_vec = params + [query_embedding, top_k]
                    
                    cur.execute(query, params_with_vec)
                    results = cur.fetchall()
                    
                    return [
                        {
                            "chunk_id": row["chunk_id"],
                            "text": row["text"],
                            "score": float(row["score"]),
                            "source_url": row["source_url"],
                            "metadata": {
                                "campus": row["campus"],
                                "department": row["department"],
                                "lab": row["lab"],
                                "professor": row["professor"],
                                "tags": row["tags"]
                            }
                        }
                        for row in results
                    ]
            finally:
                conn.close()
                
        except Exception as e:
            logger.error(f"Prefilter+Dense検索エラー: {e}")
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
            
            # 1. Dense検索で候補を取得
            dense_results = await self._get_dense_candidates(
                query_text, filters, candidate_size
            )
            
            # 2. BM25検索で候補を取得
            bm25_results = await self._get_bm25_candidates(
                query_text, filters, candidate_size
            )
            
            # 3. スコア正規化と合成
            dense_scores = self._normalize_scores(dense_results)
            bm25_scores = self._normalize_scores(bm25_results)
            
            # 4. 両方のスコアをマージ
            merged_scores = {}
            
            # Denseスコアを追加
            for chunk_id, score in dense_scores.items():
                merged_scores[chunk_id] = alpha * score
            
            # BM25スコアを追加
            for chunk_id, score in bm25_scores.items():
                if chunk_id in merged_scores:
                    merged_scores[chunk_id] += beta * score
                else:
                    merged_scores[chunk_id] = beta * score
            
            # 5. スコア順にソートして上位k件を取得
            sorted_chunk_ids = sorted(
                merged_scores.keys(), 
                key=lambda x: merged_scores[x], 
                reverse=True
            )[:top_k]
            
            # 6. チャンク詳細を取得
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
                    chunk_details = {row["chunk_id"]: row for row in cur.fetchall()}
                
                # 7. ソート順に結果を組み立て
                results = []
                for chunk_id in sorted_chunk_ids:
                    if chunk_id in chunk_details:
                        row = chunk_details[chunk_id]
                        results.append({
                            "chunk_id": row["chunk_id"],
                            "text": row["text"],
                            "score": float(merged_scores[chunk_id]),
                            "source_url": row["source_url"],
                            "metadata": {
                                "campus": row["campus"],
                                "department": row["department"],
                                "lab": row["lab"],
                                "professor": row["professor"],
                                "tags": row["tags"]
                            }
                        })
                
                return results
            finally:
                conn.close()
                
        except Exception as e:
            logger.error(f"Hybrid検索エラー: {e}")
            raise
    
    async def _get_dense_candidates(
        self,
        query_text: str,
        filters: Optional[Dict[str, Any]],
        limit: int
    ) -> Dict[str, float]:
        """Dense検索で候補を取得（内部用）"""
        results = await self.search_prefilter_dense(query_text, filters, limit) \
            if filters else await self.search_dense(query_text, limit)
        return {r["chunk_id"]: r["score"] for r in results}
    
    async def _get_bm25_candidates(
        self,
        query_text: str,
        filters: Optional[Dict[str, Any]],
        limit: int
    ) -> Dict[str, float]:
        """BM25検索で候補を取得（内部用）"""
        try:
            # フィルタ条件を構築
            where_clauses = ["text_tsv @@ plainto_tsquery('simple', %s)"]
            params = [query_text]
            
            if filters:
                if filters.get('department'):
                    where_clauses.append("department = %s")
                    params.append(filters['department'])
                
                if filters.get('professor'):
                    where_clauses.append("professor @> ARRAY[%s]")
                    params.append(filters['professor'])
                
                if filters.get('campus'):
                    where_clauses.append("campus = %s")
                    params.append(filters['campus'])
                
                if filters.get('lab'):
                    where_clauses.append("lab = %s")
                    params.append(filters['lab'])
            
            where_clause = " AND ".join(where_clauses)
            
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
                        [query_text] + params + [limit]
                    )
                    results = cur.fetchall()
                    return {row["chunk_id"]: float(row["bm25_score"]) for row in results}
            finally:
                conn.close()
                
        except Exception as e:
            logger.error(f"BM25検索エラー: {e}")
            return {}
    
    def _normalize_scores(self, scores: Dict[str, float]) -> Dict[str, float]:
        """
        スコアを0〜1に正規化
        
        Args:
            scores: chunk_id -> score の辞書
        
        Returns:
            正規化されたスコア辞書
        """
        if not scores:
            return {}
        
        values = list(scores.values())
        min_score = min(values)
        max_score = max(values)
        
        # すべて同じスコアの場合
        if max_score == min_score:
            return {k: 1.0 for k in scores.keys()}
        
        # Min-Max正規化
        return {
            k: (v - min_score) / (max_score - min_score)
            for k, v in scores.items()
        }

    async def query_with_answer(
        self,
        query_text: str,
        strategy: str = "prefilter_dense",
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        クエリに対して検索 + 回答生成を実行
        
        Args:
            query_text: 検索クエリ
            strategy: 検索戦略 (dense, prefilter_dense, hybrid)
            filters: フィルタ条件
            top_k: 取得件数
        
        Returns:
            回答と使用したチャンク情報
        """
        try:
            # 1. 検索戦略に応じてチャンクを取得
            if strategy == "dense":
                chunks = await self.search_dense(query_text, top_k)
            elif strategy == "prefilter_dense":
                chunks = await self.search_prefilter_dense(query_text, filters, top_k)
            elif strategy == "hybrid":
                chunks = await self.search_hybrid(query_text, filters, top_k)
            else:
                raise ValueError(f"Unknown strategy: {strategy}")
            
            # 2. LLMで回答を生成
            answer = await self.lm_studio.generate_answer(query_text, chunks)
            
            # 3. 結果を返す
            return {
                "answer": answer,
                "used_strategy": strategy,
                "context_chunks": chunks
            }
        
        except Exception as e:
            logger.error(f"RAGクエリエラー: {e}")
            raise