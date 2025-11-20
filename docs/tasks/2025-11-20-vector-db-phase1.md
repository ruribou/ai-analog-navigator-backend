# Task: Phase 1 ベクトルDB（PostgreSQL + pgvector）構築

- Source plan: docs/plans/vector-db.md
- Status: Completed
- Created: 2025-11-20
- Completed: 2025-11-20

## Summary

Docker上のPostgreSQLでpgvectorを有効化し、RAG用のベクトルDB基盤を構築する。documents（原文メタ管理）とchunks（ベクトル保存本体）の2テーブルを作成し、HNSWインデックスによる高速ANN検索を実現する。

**Phase Goal:**
ベクトルを保存して検索できるDB基盤の完成

**Out of Scope:**
- スクレイピング/チャンク生成/embedding生成の実装
- 検索API（Next.js側）の実装
- 評価実験/ハイブリッド検索

## Proposed Steps

### Step 1: Docker環境確認とpgvector有効化 [P1-A1]

**作業内容:**
1. `docker-compose.yml` の確認（`pgvector/pgvector:pg16`など）
2. `docker compose up -d` でDB起動
3. psql接続確認
4. `CREATE EXTENSION IF NOT EXISTS vector;` を実行
5. vector extensionの有効化確認

**確認方法:**
```sql
SELECT extname FROM pg_extension WHERE extname='vector';
```

**受け入れ条件:**
- DBコンテナが正常起動し、再起動でデータが保持される（volume確認）
- vector extensionが1行返る

### Step 2: documentsテーブル作成 [P1-A2]

**作業内容:**
スクレイプ元ページ単位の管理用テーブルを作成。

**DDL:**
```sql
CREATE TABLE IF NOT EXISTS documents (
  doc_id          UUID PRIMARY KEY,
  source_url      TEXT NOT NULL,
  source_type     TEXT NOT NULL,  -- school_hp / lab_hp / pdf / news
  title           TEXT,
  lang            TEXT DEFAULT 'ja',
  fetched_at      TIMESTAMPTZ NOT NULL,
  updated_at      TIMESTAMPTZ,
  content_hash    TEXT NOT NULL,
  status          TEXT NOT NULL DEFAULT 'active', -- active / superseded / error
  meta            JSONB DEFAULT '{}'::jsonb
);

CREATE UNIQUE INDEX IF NOT EXISTS documents_source_url_uq ON documents(source_url);
CREATE INDEX IF NOT EXISTS documents_status_idx ON documents(status);
```

**受け入れ条件:**
- DDLが通る
- `source_url` 重複で二重登録されない
- `status='active'` のみをWHEREで高速に引ける

### Step 3: chunksテーブル作成 [P1-A3]

**作業内容:**
検索対象チャンクと埋め込みを保持するメインテーブルを作成。

**DDL:**
```sql
CREATE TABLE IF NOT EXISTS chunks (
  chunk_id        UUID PRIMARY KEY,
  doc_id          UUID NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
  chunk_index     INT NOT NULL,
  text            TEXT NOT NULL,
  token_count     INT,
  heading_path    TEXT[],
  tags            TEXT[],

  campus          TEXT,
  building        TEXT,
  department      TEXT,
  lab             TEXT,
  professor       TEXT[],

  validity_start  DATE,
  validity_end    DATE,

  source_url      TEXT NOT NULL,

  embedding       VECTOR(768) NOT NULL, -- 現在: text-embedding-nomic-embed-text-v1.5
  embedding_model TEXT NOT NULL,       -- モデル名を明示的に保存
  embedding_dim   INT NOT NULL,        -- 実際の次元数を保存（モデル切り替え時の検証用）
  version         INT NOT NULL DEFAULT 1,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS chunks_doc_order_uq ON chunks(doc_id, chunk_index);

CREATE INDEX IF NOT EXISTS chunks_campus_idx ON chunks(campus);
CREATE INDEX IF NOT EXISTS chunks_building_idx ON chunks(building);
CREATE INDEX IF NOT EXISTS chunks_department_idx ON chunks(department);
CREATE INDEX IF NOT EXISTS chunks_lab_idx ON chunks(lab);

CREATE INDEX IF NOT EXISTS chunks_professor_gin ON chunks USING gin(professor);
CREATE INDEX IF NOT EXISTS chunks_tags_gin ON chunks USING gin(tags);

CREATE INDEX IF NOT EXISTS chunks_validity_idx ON chunks(validity_start, validity_end);
```

**受け入れ条件:**
- DDLが通る
- doc単位でchunksを削除できる
- tags/professor/campus等でWHEREフィルタできる

### Step 4: HNSWインデックス作成 [P1-A4]

**作業内容:**
高速な近傍検索のためのHNSWインデックスを作成。

**DDL:**
```sql
CREATE INDEX IF NOT EXISTS chunks_embedding_hnsw
  ON chunks USING hnsw (embedding vector_cosine_ops)
  WITH (m=16, ef_construction=128);
```

**受け入れ条件:**
- `\d chunks` で `chunks_embedding_hnsw` が確認できる
- `ORDER BY embedding <=> :qvec LIMIT 5` が動作する
- 1000件規模のinsert後もsearchが実行できる

### Step 5: ベクトルDB疎通テスト [P1-A5]

**作業内容:**
最小データでの保存→検索フローを検証。

**テスト手順:**
1. documentsにダミーdocを1件insert
2. chunksにダミーchunkを数件insert（embeddingはランダムでも可）
3. cosine検索SQLでtop_kが返ることを確認
4. prefilter列でWHERE絞り込みできることを確認

**検索SQL例:**
```sql
SELECT chunk_id, 1 - (embedding <=> :qvec) AS score
FROM chunks
WHERE campus = 'main'  -- prefilterテスト
ORDER BY embedding <=> :qvec
LIMIT 5;
```

**受け入れ条件:**
- insert→selectが通る
- `embedding <=> :qvec` で近傍検索が返る
- `WHERE campus='main'` のような絞り込みが効く

## Verification

### Phase 1 完了条件

- [x] pgvector有効化済みのPostgresがDocker上で安定稼働
- [x] documents / chunks / HNSW index を作成完了
- [x] ダミーデータで保存→検索→prefilterが通る

### 技術的確認事項

- [x] DBコンテナの再起動でデータが保持される
- [x] vector extensionが有効
- [x] documentsテーブルのユニーク制約が機能
- [x] chunksテーブルの外部キー制約（CASCADE）が機能
- [x] HNSWインデックスが作成され、ANN検索が動作
- [x] prefilter用インデックス（BTree/GiN）が効いている

## Implementation Notes

### 接続情報
- 接続情報（user/pass/db）は `.env` or docker-compose.ymlに合わせる

### embedding次元数とモデル管理
- **現在のモデル**: `text-embedding-nomic-embed-text-v1.5` (768次元)
- **柔軟性のための設計**:
  - `embedding_model` カラムでモデル名を保存（例: "nomic-embed-text-v1.5"）
  - `embedding_dim` カラムで実際の次元数を保存（768）
  - モデル切り替え時は新バージョンとして chunks を追加し、`version` カラムで管理
  - 異なるモデルを並行運用する場合は、検索時に `WHERE embedding_model = :model` でフィルタ可能

### HNSWパラメータ
- 初期値: m=16, ef_construction=128
- データ量・検索精度要件に応じてチューニング可能

## Model Flexibility Strategy

将来的な複数モデル比較のための戦略:

### 1. モデル切り替えアプローチ

**オプションA: バージョン管理による並行運用**
- 同じdoc_idに対して異なる `embedding_model` + `version` の組み合わせで複数のchunksを保存
- 検索時に使用モデルを指定: `WHERE embedding_model = 'nomic-embed-text-v1.5'`
- 比較実験時は両モデルで検索して精度を測定

**オプションB: テーブル分割**
- モデルごとに chunks テーブルを分ける（chunks_nomic, chunks_openai等）
- VECTOR型の次元数をモデルに最適化できる
- ただし、スキーマ管理が複雑になる

**推奨**: オプションA（柔軟性とスキーマのシンプルさのバランス）

### 2. モデル切り替え時の移行手順

1. 新モデルで全documentsを再処理
2. `version` をインクリメントして新chunksをINSERT
3. 新旧両バージョンで検索精度を比較
4. 新モデルが優位なら、古いバージョンのchunksを削除

### 3. 設定管理

embeddingサービス側で以下を環境変数/設定ファイルで管理:
```python
EMBEDDING_MODEL = "text-embedding-nomic-embed-text-v1.5"
EMBEDDING_DIM = 768
EMBEDDING_VERSION = 1
```

## Next Actions

1. docker-compose.ymlの確認・修正（必要に応じて）
2. マイグレーションファイルまたはinit.sqlの作成
3. Step 1から順次実行
4. 各Stepの受け入れ条件を満たすことを確認
5. Phase 1完了後、Phase 2（スクレイピング/embedding生成）へ

