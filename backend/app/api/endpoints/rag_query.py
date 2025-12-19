"""
RAGクエリエンドポイント
検索 + 回答生成の統合エンドポイント
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Literal, Any
import logging

from app.services.rag_service import RAGService

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class RAGQueryRequest(BaseModel):
    """RAGクエリリクエスト"""
    query: str = Field(..., min_length=1, description="検索クエリ")
    strategy: Literal["dense", "prefilter_dense", "hybrid"] = Field(
        default="prefilter_dense",
        description="検索戦略"
    )
    filters: Optional[Dict[str, str]] = Field(
        default=None,
        description="メタデータフィルタ"
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="取得件数 (1〜20)"
    )


class ContextChunk(BaseModel):
    """コンテキストチャンク"""
    chunk_id: str = Field(..., description="チャンクID")
    text: str = Field(..., description="チャンクテキスト")
    score: float = Field(..., description="スコア")
    source_url: Optional[str] = Field(None, description="ソースURL")
    metadata: Dict[str, Any] = Field(..., description="メタデータ")


class RAGQueryResponse(BaseModel):
    """RAGクエリレスポンス"""
    answer: str = Field(..., description="生成された回答")
    used_strategy: str = Field(..., description="使用した検索戦略")
    context_chunks: List[ContextChunk] = Field(..., description="使用したコンテキストチャンク")


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/rag_query", response_model=RAGQueryResponse)
async def rag_query(request: RAGQueryRequest):
    """
    RAGクエリエンドポイント

    クエリテキストを受け取り、検索 + LLM回答生成を実行します。

    ## 使用例

    ```json
    {
      "query": "神戸先生の研究内容を教えてください",
      "strategy": "prefilter_dense",
      "filters": {"department": "理工学部"},
      "top_k": 5
    }
    ```
    """
    try:
        logger.info(f"RAGクエリリクエスト: strategy={request.strategy}, query={request.query}")

        # RAG Serviceインスタンスを作成
        rag_service = RAGService()

        # 検索 + 回答生成を実行
        result = await rag_service.query_with_answer(
            query_text=request.query,
            strategy=request.strategy,
            filters=request.filters,
            top_k=request.top_k
        )

        logger.info(f"RAGクエリ完了: {len(result['context_chunks'])}件のチャンクを使用")

        return RAGQueryResponse(
            answer=result["answer"],
            used_strategy=result["used_strategy"],
            context_chunks=result["context_chunks"]
        )

    except Exception as e:
        logger.error(f"RAGクエリエラー: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"RAGクエリ処理中にエラーが発生しました: {str(e)}"
        )
