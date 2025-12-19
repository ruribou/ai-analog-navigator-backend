"""
埋め込みベクトル生成サービス
"""
import logging

import requests

from app.config import settings

logger = logging.getLogger(__name__)

# nomic-embed-text-v1.5 の次元数
EMBEDDING_DIM = 768
EMBEDDING_MODEL = "text-embedding-nomic-embed-text-v1.5"


class EmbeddingService:
    """埋め込みベクトル生成サービス"""

    @staticmethod
    async def generate(
        texts: list[str],
        batch_size: int = 32
    ) -> list[list[float]]:
        """
        テキスト配列から埋め込みベクトルを生成

        Args:
            texts: 埋め込み生成対象のテキスト配列
            batch_size: バッチサイズ

        Returns:
            埋め込みベクトルのリスト

        Raises:
            EmbeddingError: 埋め込み生成に失敗した場合
        """
        all_embeddings = []

        try:
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                logger.info(
                    f"埋め込み生成中: {i+1}-{min(i+batch_size, len(texts))} / {len(texts)}"
                )

                payload = {
                    "input": batch,
                    "model": EMBEDDING_MODEL
                }

                response = requests.post(
                    f"{settings.LM_STUDIO_BASE_URL}/embeddings",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=60
                )

                if response.status_code == 200:
                    result = response.json()
                    for item in result.get("data", []):
                        all_embeddings.append(item["embedding"])
                else:
                    logger.error(
                        f"埋め込み生成エラー: {response.status_code} - {response.text}"
                    )
                    raise EmbeddingError(
                        f"埋め込み生成失敗: {response.status_code}"
                    )

            logger.info(f"埋め込み生成完了: {len(all_embeddings)}件")
            return all_embeddings

        except requests.exceptions.RequestException as e:
            logger.error(f"埋め込みAPI接続エラー: {e}")
            raise EmbeddingError(f"埋め込みAPI接続失敗: {e}") from e

    @staticmethod
    def get_dim() -> int:
        """
        使用中の埋め込みモデルの次元数を返す

        Returns:
            埋め込み次元数
        """
        return EMBEDDING_DIM


class EmbeddingError(Exception):
    """埋め込み生成エラー"""
    pass
