"""
データベース接続・CRUD操作サービス
"""
import psycopg2
import psycopg2.extras
import logging
from typing import Optional, List, Dict, Any
from uuid import uuid4
from datetime import datetime
import hashlib
import json

from app.config import settings

logger = logging.getLogger(__name__)


class DBService:
    """PostgreSQL + pgvector データベースサービス"""

    @staticmethod
    def get_connection():
        """DB接続を取得"""
        if not settings.DATABASE_URL:
            raise ValueError("DATABASE_URL が設定されていません")

        try:
            conn = psycopg2.connect(settings.DATABASE_URL)
            return conn
        except Exception as e:
            logger.error(f"DB接続エラー: {e}")
            raise

    @staticmethod
    def check_document_exists(url: str) -> Optional[str]:
        """
        ドキュメントが既に存在するかチェック

        Args:
            url: ソースURL

        Returns:
            存在する場合はdoc_id、存在しない場合はNone
        """
        conn = None
        try:
            conn = DBService.get_connection()
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT doc_id FROM documents WHERE source_url = %s",
                    (url,)
                )
                result = cur.fetchone()
                return str(result[0]) if result else None
        except Exception as e:
            logger.error(f"ドキュメント存在チェックエラー: {e}")
            return None
        finally:
            if conn:
                conn.close()

    @staticmethod
    def insert_document(
        url: str,
        title: str,
        text: str,
        source_type: str = "school_hp",
        meta: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        documentsテーブルにレコードを挿入

        Args:
            url: ソースURL
            title: タイトル
            text: 本文テキスト
            source_type: ソースタイプ ('school_hp', 'lab_hp', 'pdf', 'news')
            meta: メタデータ（JSONB）

        Returns:
            doc_id (UUID文字列)
        """
        conn = None
        try:
            # コンテンツハッシュを生成
            content_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()

            doc_id = str(uuid4())
            fetched_at = datetime.now()

            conn = DBService.get_connection()
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO documents
                    (doc_id, source_url, source_type, title, lang, fetched_at,
                     content_hash, status, meta)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (source_url)
                    DO UPDATE SET
                        title = EXCLUDED.title,
                        content_hash = EXCLUDED.content_hash,
                        updated_at = EXCLUDED.fetched_at,
                        meta = EXCLUDED.meta
                    RETURNING doc_id
                    """,
                    (
                        doc_id,
                        url,
                        source_type,
                        title,
                        'ja',
                        fetched_at,
                        content_hash,
                        'active',
                        json.dumps(meta or {})
                    )
                )
                result = cur.fetchone()
                returned_doc_id = str(result[0])
                conn.commit()
                logger.info(f"ドキュメント登録成功: {returned_doc_id} ({url})")
                return returned_doc_id
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"ドキュメント登録エラー: {e}")
            raise
        finally:
            if conn:
                conn.close()

    @staticmethod
    def insert_chunks(
        doc_id: str,
        chunks_data: List[Dict[str, Any]]
    ) -> int:
        """
        chunksテーブルに複数レコードをbulk insert

        Args:
            doc_id: ドキュメントID
            chunks_data: チャンクデータのリスト
                各要素は以下のキーを持つ辞書:
                - chunk_index: int
                - text: str
                - token_count: int
                - heading_path: List[str]
                - tags: List[str]
                - campus: str
                - building: str (optional)
                - department: str
                - lab: str (optional)
                - professor: List[str] (optional)
                - source_url: str
                - embedding: List[float]
                - embedding_model: str
                - embedding_dim: int

        Returns:
            挿入されたレコード数
        """
        conn = None
        try:
            conn = DBService.get_connection()
            with conn.cursor() as cur:
                # bulk insertの準備
                insert_values = []
                for chunk in chunks_data:
                    chunk_id = str(uuid4())
                    insert_values.append((
                        chunk_id,
                        doc_id,
                        chunk['chunk_index'],
                        chunk['text'],
                        chunk.get('token_count'),
                        chunk.get('heading_path', []),
                        chunk.get('tags', []),
                        chunk.get('campus'),
                        chunk.get('building'),
                        chunk.get('department'),
                        chunk.get('lab'),
                        chunk.get('professor', []),
                        chunk.get('validity_start'),
                        chunk.get('validity_end'),
                        chunk['source_url'],
                        chunk['embedding'],
                        chunk['embedding_model'],
                        chunk['embedding_dim'],
                        1  # version
                    ))

                # bulk insert実行
                psycopg2.extras.execute_batch(
                    cur,
                    """
                    INSERT INTO chunks
                    (chunk_id, doc_id, chunk_index, text, token_count,
                     heading_path, tags, campus, building, department, lab, professor,
                     validity_start, validity_end, source_url,
                     embedding, embedding_model, embedding_dim, version)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    insert_values
                )

                conn.commit()
                inserted_count = len(insert_values)
                logger.info(f"チャンク登録成功: {inserted_count}件 (doc_id={doc_id})")
                return inserted_count
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"チャンク登録エラー: {e}")
            raise
        finally:
            if conn:
                conn.close()

    @staticmethod
    def delete_chunks_by_doc_id(doc_id: str) -> int:
        """
        指定されたdoc_idのチャンクを削除（再登録時用）

        Args:
            doc_id: ドキュメントID

        Returns:
            削除されたレコード数
        """
        conn = None
        try:
            conn = DBService.get_connection()
            with conn.cursor() as cur:
                cur.execute("DELETE FROM chunks WHERE doc_id = %s", (doc_id,))
                deleted_count = cur.rowcount
                conn.commit()
                logger.info(f"チャンク削除: {deleted_count}件 (doc_id={doc_id})")
                return deleted_count
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"チャンク削除エラー: {e}")
            raise
        finally:
            if conn:
                conn.close()
