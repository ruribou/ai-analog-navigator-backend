"""
ベクトル近傍検索のテストスクリプト
"""
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.db_service import DBService
from app.services.embedding_service import EmbeddingService

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_search(query: str, top_k: int = 10):
    """
    クエリテキストでベクトル近傍検索を実行

    Args:
        query: 検索クエリ
        top_k: 取得する結果数
    """
    logger.info("=" * 60)
    logger.info(f"検索クエリ: {query}")
    logger.info("=" * 60)

    # 1. クエリの埋め込み生成
    logger.info("クエリの埋め込み生成中...")
    embeddings = await EmbeddingService.generate([query])
    query_embedding = embeddings[0]
    logger.info(f"埋め込み生成完了 (次元数: {len(query_embedding)})")

    # 2. ベクトル近傍検索
    conn = None
    try:
        conn = DBService.get_connection()
        with conn.cursor() as cur:
            # pgvectorの cosine distance演算子 (<=>)を使用
            cur.execute(
                """
                SELECT
                    chunk_id,
                    text,
                    campus,
                    department,
                    lab,
                    professor,
                    tags,
                    1 - (embedding <=> %s::vector) AS similarity_score
                FROM chunks
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (query_embedding, query_embedding, top_k)
            )

            results = cur.fetchall()

            # 結果表示
            logger.info(f"\n検索結果: {len(results)}件\n")
            for i, row in enumerate(results, 1):
                chunk_id, text, campus, department, lab, professor, tags, score = row
                logger.info(f"--- 結果 {i} (スコア: {score:.4f}) ---")
                logger.info(f"Campus: {campus}, Department: {department}")
                if lab:
                    logger.info(f"Lab: {lab}")
                if professor:
                    logger.info(f"Professor: {professor}")
                if tags:
                    logger.info(f"Tags: {tags}")
                logger.info(f"Text: {text[:200]}...")
                logger.info("")

    except Exception as e:
        logger.error(f"検索エラー: {e}", exc_info=True)
    finally:
        if conn:
            conn.close()


async def main():
    """
    メイン処理：複数のクエリでテスト
    """
    test_queries = [
        "神戸 英利",
        "IoT",
        "情報システムデザイン学系",
        "研究室",
        "組み込みシステム"
    ]

    for query in test_queries:
        await test_search(query, top_k=5)
        logger.info("\n" + "=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
