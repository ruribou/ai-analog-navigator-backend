"""
検索APIエンドポイント
Dense / Prefilter+Dense / Hybrid 検索戦略をサポート
"""
from functools import lru_cache
import logging

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Literal, Any

from app.services.rag_service import RAGService

logger = logging.getLogger(__name__)

router = APIRouter()


@lru_cache
def get_rag_service() -> RAGService:
    """
    RAGサービスを取得（シングルトン）

    lru_cacheにより初回呼び出し時のみ初期化され、
    以降はキャッシュされたインスタンスを返す。
    """
    logger.info("RAGサービス初期化")
    return RAGService()


# ============================================================================
# Request/Response Models
# ============================================================================

class SearchRequest(BaseModel):
    """検索リクエスト"""
    query: str = Field(..., min_length=1, description="検索クエリ")
    strategy: Literal["dense", "prefilter_dense", "hybrid"] = Field(
        default="dense",
        description="検索戦略 (dense: ベクトル検索のみ, prefilter_dense: フィルタ+ベクトル検索, hybrid: ベクトル+BM25)"
    )
    filters: Optional[Dict[str, str]] = Field(
        default=None,
        description="メタデータフィルタ (department, professor, campus, lab等)",
        examples=[{"department": "理工学部", "professor": "神戸 英利"}]
    )
    top_k: int = Field(
        default=10,
        ge=1,
        le=50,
        description="取得件数 (1〜50)"
    )
    alpha: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Hybrid時のDense検索の重み (0.0〜1.0)"
    )
    beta: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="Hybrid時のBM25検索の重み (0.0〜1.0)"
    )


class SearchResultItem(BaseModel):
    """検索結果アイテム"""
    chunk_id: str = Field(..., description="チャンクID")
    text: str = Field(..., description="チャンクのテキスト")
    score: float = Field(..., description="スコア（0〜1）")
    source_url: Optional[str] = Field(None, description="ソースURL")
    metadata: Dict[str, Any] = Field(..., description="メタデータ (campus, department, lab, professor, tags)")


class SearchResponse(BaseModel):
    """検索レスポンス"""
    strategy: str = Field(..., description="使用した検索戦略")
    query: str = Field(..., description="検索クエリ")
    results: List[SearchResultItem] = Field(..., description="検索結果リスト")
    total: int = Field(..., description="結果件数")


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/search", response_model=SearchResponse)
async def search(
    request: SearchRequest,
    rag_service: RAGService = Depends(get_rag_service)
):
    """
    検索エンドポイント

    3種類の検索戦略をサポート:
    - **dense**: ベクトル検索のみ（意味検索）
    - **prefilter_dense**: メタデータフィルタ + ベクトル検索
    - **hybrid**: Dense + BM25（キーワード検索）のスコア合成

    ## 使用例

    ### Dense検索
    ```json
    {
      "query": "神戸先生の研究内容を教えて",
      "strategy": "dense",
      "top_k": 5
    }
    ```

    ### Prefilter + Dense
    ```json
    {
      "query": "IoTの研究",
      "strategy": "prefilter_dense",
      "filters": {"department": "理工学部"},
      "top_k": 5
    }
    ```

    ### Hybrid
    ```json
    {
      "query": "機械学習を使った研究",
      "strategy": "hybrid",
      "alpha": 0.6,
      "beta": 0.4,
      "top_k": 10
    }
    ```
    """
    try:
        logger.info(f"検索リクエスト: strategy={request.strategy}, query={request.query}")

        # 戦略に応じて検索実行
        # Note: prefilter_dense は dense に統合（後方互換のため残す）
        if request.strategy in ("dense", "prefilter_dense"):
            results = await rag_service.search_dense(
                request.query,
                filters=request.filters,
                top_k=request.top_k
            )

        elif request.strategy == "hybrid":
            results = await rag_service.search_hybrid(
                request.query,
                request.filters,
                request.top_k,
                request.alpha,
                request.beta
            )

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown strategy: {request.strategy}"
            )

        logger.info(f"検索完了: {len(results)}件")

        return SearchResponse(
            strategy=request.strategy,
            query=request.query,
            results=results,
            total=len(results)
        )

    except Exception as e:
        logger.error(f"検索エラー: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"検索処理中にエラーが発生しました: {str(e)}"
        )
