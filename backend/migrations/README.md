# Database Migrations

このディレクトリにはPostgreSQL + pgvectorのマイグレーションSQLファイルが含まれています。

## マイグレーション一覧

### 001_init_vector_db.sql

**作成日:** 2025-11-20  
**目的:** ベクトルDB基盤の初期セットアップ

**内容:**
- pgvector extensionの有効化
- `documents` テーブル作成（原文メタ管理）
- `chunks` テーブル作成（ベクトル保存本体）
- 各種インデックス作成（BTree, GIN, HNSW）

**実行方法:**
```bash
# PostgreSQLコンテナを起動
docker compose up -d postgres

# マイグレーション実行
docker exec -i ai-navigator-postgres psql -U postgres -d ai_navigator < backend/migrations/001_init_vector_db.sql
```

**確認方法:**
```bash
# pgvector extensionの確認
docker exec ai-navigator-postgres psql -U postgres -d ai_navigator -c "SELECT extname FROM pg_extension WHERE extname='vector';"

# テーブル構造の確認
docker exec ai-navigator-postgres psql -U postgres -d ai_navigator -c "\d documents"
docker exec ai-navigator-postgres psql -U postgres -d ai_navigator -c "\d chunks"
```

## テストスクリプト

### test_vector_search.sql

**目的:** ベクトルDB機能の疎通テスト

**実行内容:**
1. ✅ 基本的なINSERT/SELECT
2. ✅ ベクトル類似度検索（コサイン距離）
3. ✅ プリフィルタ + ベクトル検索
4. ✅ 配列カラムの検索（GINインデックス）
5. ✅ CASCADE DELETE（外部キー制約）

**実行方法:**
```bash
docker exec -i ai-navigator-postgres psql -U postgres -d ai_navigator < backend/migrations/test_vector_search.sql
```

## データベース接続情報

デフォルト設定（`docker-compose.yml` より）:
- **Host:** localhost
- **Port:** 5432
- **Database:** ai_navigator
- **User:** postgres
- **Password:** password

環境変数で変更可能:
```bash
POSTGRES_DB=ai_navigator
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
```

## スキーマ概要

### documents テーブル

原文ドキュメントのメタデータを管理。

- `doc_id` (UUID): 主キー
- `source_url` (TEXT): ソースURL（ユニーク制約）
- `source_type` (TEXT): ドキュメント種別（CHECK制約: 'school_hp' | 'lab_hp' | 'pdf' | 'news'）
- `title`, `lang`, `fetched_at`, `updated_at`: メタデータ
- `content_hash` (TEXT): 差分更新用ハッシュ
- `status` (TEXT): ステータス（CHECK制約: 'active' | 'superseded' | 'error'）
- `meta` (JSONB): 拡張用メタデータ

### chunks テーブル

検索対象チャンクとembeddingを保存。

**基本フィールド:**
- `chunk_id` (UUID): 主キー
- `doc_id` (UUID): documents への外部キー（CASCADE DELETE）
- `chunk_index` (INT): チャンク順序
- `text` (TEXT): チャンク本文
- `token_count`, `heading_path`, `tags`: メタデータ

**プリフィルタ用フィールド:**
- `campus`, `building`, `department`, `lab`, `professor`
- `validity_start`, `validity_end`: 有効期間

**Embedding フィールド:**
- `embedding` (VECTOR(768)): ベクトル（768次元）
- `embedding_model` (TEXT): モデル名（例: "nomic-embed-text-v1.5"）
- `embedding_dim` (INT): 実際の次元数（CHECK制約: 768固定）
- `version` (INT): バージョン管理用

### インデックス戦略

**BTree インデックス:**
- `documents(source_url)` - ユニーク制約
- `documents(status)` - ステータスフィルタ用
- `chunks(campus/building/department/lab)` - 単一カラムフィルタ用

**GIN インデックス:**
- `chunks(professor)` - 配列検索用
- `chunks(tags)` - 配列検索用

**HNSW インデックス:**
- `chunks(embedding)` - ベクトル類似度検索用
  - `m=16`, `ef_construction=128`
  - `vector_cosine_ops` (コサイン距離)

## Embedding モデル管理

### 現在のモデル

- **モデル名:** `text-embedding-nomic-embed-text-v1.5`
- **次元数:** 768
- **距離関数:** cosine

### モデル切り替え戦略

将来的に別のembeddingモデルに切り替える場合:

**オプションA: バージョン管理（推奨）**
```sql
-- 新モデルでchunksを追加
INSERT INTO chunks (
  ...
  embedding_model = 'new-model-name',
  embedding_dim = 1024,  -- 新モデルの次元数
  version = 2  -- バージョンをインクリメント
);

-- 検索時にモデルを指定
WHERE embedding_model = 'new-model-name' AND version = 2
```

**オプションB: テーブル分割**
- モデルごとに chunks テーブルを分ける
- スキーマ管理は複雑になるが、次元数を最適化できる

詳細は `docs/tasks/2025-11-20-vector-db-phase1.md` を参照。

## トラブルシューティング

### pgvector extensionがない

```bash
# Dockerイメージの確認
docker compose config | grep image

# pgvector/pgvector:pg16 であることを確認
```

### テーブルが作成されない

```bash
# ログ確認
docker compose logs postgres

# マイグレーション再実行
docker exec -i ai-navigator-postgres psql -U postgres -d ai_navigator < backend/migrations/001_init_vector_db.sql
```

### ベクトル検索が遅い

```bash
# HNSW インデックスの確認
docker exec ai-navigator-postgres psql -U postgres -d ai_navigator -c "\d chunks"

# chunks_embedding_hnsw が存在することを確認
```

HNSWパラメータのチューニング:
- `m`: グラフの接続数（デフォルト: 16）
- `ef_construction`: 構築時の探索幅（デフォルト: 128）

詳細は [pgvector documentation](https://github.com/pgvector/pgvector) を参照。

