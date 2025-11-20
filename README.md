# AI Analog Navigator

音声文字起こしと文章校正のためのフルスタックアプリケーションです。
Whisper + LM Studio + pgvectorを使用したRAGシステムを搭載しています。

## 技術スタック

- **Frontend**: Next.js 16 (TypeScript, Tailwind CSS)
- **Backend**: FastAPI (Python 3.12)
- **Database**: PostgreSQL with pgvector extension
- **Vector Search**: pgvector
- **Containerization**: Docker & Docker Compose

## プロジェクト構造

モノレポ構造を採用し、フロントエンドとバックエンドを統合管理しています。

```
ai-analog-navigator/
├── frontend/              # Next.jsフロントエンド
│   ├── app/              # App Router
│   ├── public/           # 静的ファイル
│   ├── Dockerfile        # フロントエンド用Docker設定
│   ├── next.config.ts
│   ├── package.json
│   └── tsconfig.json
├── backend/               # FastAPIバックエンド
│   ├── app/              # メインアプリケーション
│   │   ├── main.py      # FastAPIアプリケーション
│   │   ├── config.py    # 設定管理
│   │   ├── api/         # APIエンドポイント
│   │   │   └── endpoints/
│   │   │       ├── health.py
│   │   │       └── transcription.py
│   │   ├── core/        # コア機能
│   │   │   ├── exceptions.py
│   │   │   └── middleware.py
│   │   ├── services/    # ビジネスロジック
│   │   │   ├── whisper_service.py
│   │   │   ├── lm_studio_service.py
│   │   │   ├── audio_processing_service.py
│   │   │   └── rag_service.py
│   │   └── models/      # Pydanticモデル
│   │       └── responses.py
│   ├── Dockerfile       # バックエンド用Docker設定
│   ├── pyproject.toml
│   └── uv.lock
├── docker-compose.yml    # Docker Compose設定
├── Makefile             # 開発用コマンド
└── README.md
```

## 必要な環境

- Docker Desktop
- Git

## クイックスタート

### 1. リポジトリのクローン

```bash
git clone <repository-url>
cd ai-analog-navigator
```

### 2. 環境変数の設定（オプション）

必要に応じて`.env`ファイルを作成してください：

```bash
# PostgreSQL Database Configuration
POSTGRES_DB=ai_navigator
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password

# Database URL for application
DATABASE_URL=postgresql://postgres:password@postgres:5432/ai_navigator
```

### 3. アプリケーションの起動

```bash
# 初回セットアップ（ビルド + 起動）
make setup
```

これだけで、すべてのサービスが起動し、以下のURLでアクセスできます：

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **PostgreSQL**: localhost:5432 (pgvector拡張付き)

### 4. 利用可能なコマンドの確認

```bash
# すべてのMakeコマンドを表示
make help
```

## Makeコマンド一覧

プロジェクトの操作を簡略化するため、Makefileを用意しています。

### 基本操作

```bash
# ヘルプを表示（全コマンド一覧）
make help

# 初回セットアップ（ビルド + 起動）
make setup

# 開発環境を起動（ログ表示付き）
make dev

# すべてのサービスを起動
make up

# すべてのサービスを停止
make down

# すべてのサービスを再起動
make restart
```

### ビルド関連

```bash
# イメージをビルド
make build

# キャッシュなしで完全リビルド
make rebuild

# サービス停止 + ボリューム削除
make clean

# サービス停止 + ボリューム削除 + イメージ削除
make clean-all
```

### 個別サービス操作

```bash
# フロントエンドのみ起動/停止/再起動
make start-frontend
make stop-frontend
make restart-frontend

# バックエンドAPIのみ起動/停止/再起動
make start-api
make stop-api
make restart-api

# データベースのみ起動/停止/再起動
make start-db
make stop-db
make restart-db
```

### ログ確認

```bash
# すべてのサービスのログを表示
make logs

# フロントエンドのログのみ表示
make logs-frontend

# バックエンドAPIのログのみ表示
make logs-api

# データベースのログのみ表示
make logs-db
```

### シェル接続

```bash
# フロントエンドコンテナに接続
make shell-frontend

# バックエンドAPIコンテナに接続
make shell-api

# データベースに接続（psql）
make shell-db
```

### ステータス確認

```bash
# サービスの状態を確認
make status
# または
make ps

# ヘルスチェック（各サービスの接続確認）
make health
```

## 各サービスについて

### Frontend (Next.js)

- **ポート**: 3000
- **技術**: Next.js 16, TypeScript, Tailwind CSS
- **ベースイメージ**: Node.js 24-alpine
- **ホットリロード**: 本番モード（開発モードが必要な場合は設定変更可能）

### Backend (FastAPI)

- **ポート**: 8000
- **技術**: FastAPI, Python 3.12, uv
- **主な機能**:
  - 音声文字起こし (Whisper)
  - 文章校正 (LM Studio連携)
  - RAG検索 (pgvector)
- **ホットリロード**: 有効（`--reload`オプション付き）

### Database (PostgreSQL + pgvector)

- **ポート**: 5432
- **拡張機能**: pgvector (ベクトル検索用)
- **永続化**: `postgres_data`ボリューム

## 開発ワークフロー例

### 日常的な開発

```bash
# 1. サービス起動
make up

# 2. ログを確認しながら開発
make logs

# 3. コード変更後、特定のサービスを再起動
make restart-api        # バックエンドのみ
make restart-frontend   # フロントエンドのみ

# 4. 終了時
make down
```

### デバッグ

```bash
# ヘルスチェックで問題を確認
make health

# 特定のサービスのログを確認
make logs-api
make logs-frontend

# コンテナに入って直接確認
make shell-api
make shell-frontend
```

### クリーンな環境で再起動

```bash
# データを保持して再起動
make down
make rebuild
make up

# データも含めて完全にクリーン
make clean-all
make setup
```

## トラブルシューティング

### サービスが起動しない

```bash
# サービスの状態を確認
make status

# ログでエラーを確認
make logs

# ヘルスチェックを実行
make health
```

### ポートが既に使用されている

```bash
# 使用中のポートを確認
lsof -i :3000
lsof -i :8000
lsof -i :5432

# サービスを停止して再起動
make down
make up
```

### イメージやキャッシュの問題

```bash
# キャッシュなしで完全リビルド
make rebuild

# 完全にクリーンアップしてから再セットアップ
make clean-all
make setup
```

### データベースの問題

```bash
# データベースのログを確認
make logs-db

# データベースに直接接続して確認
make shell-db

# データベースをリセット（データが消えます）
make clean
make up
```

### コンテナ内で直接作業したい

```bash
# 各コンテナに入る
make shell-frontend  # フロントエンド
make shell-api       # バックエンド
make shell-db        # データベース
```

---

## Phase 2: データインジェスト機能

Phase 2 では、オープンキャンパス向けの学系情報・教員情報・研究室情報をスクレイピングし、PostgreSQL + pgvector に登録する機能を実装しました。

### 実装機能

1. **スクレイピングバッチ** (`backend/app/scripts/scrape_pages.py`)
   - 固定URLからHTMLを取得
   - リトライロジック、エラーハンドリング実装
   - `inputs/scraped/` に保存

2. **テキスト正規化** (`backend/app/scripts/utils/clean_text.py`)
   - HTMLから本文テキスト抽出
   - 不要要素の削除、連続空白・改行の統一

3. **ページ種別パーサ** (`backend/app/scripts/utils/parsers.py`)
   - 学系トップ、教員一覧、教員詳細、研究室ページに対応
   - メタデータ抽出（campus, department, professor, lab, tags）

4. **チャンク分割** (`backend/app/scripts/utils/chunker.py`)
   - heading-aware なチャンク分割
   - チャンクサイズ: 400トークン、オーバーラップ: 80トークン
   - tiktoken を使用したトークンカウント

5. **埋め込み生成** (`backend/app/services/lm_studio_service.py`)
   - LM Studio の embedding API 連携
   - モデル: `text-embedding-nomic-embed-text-v1.5` (768次元)
   - バッチ処理（32件/バッチ）

6. **DB接続サービス** (`backend/app/services/db_service.py`)
   - documents / chunks テーブルへのCRUD操作
   - トランザクション管理、エラーハンドリング

7. **インジェストバッチ** (`backend/app/scripts/ingest_to_db.py`)
   - スクレイプ → パース → チャンク化 → 埋め込み生成 → DB登録の統合処理

### 使用方法

#### 1. スクレイピング実行

```bash
cd backend
source .venv/bin/activate
python -m app.scripts.scrape_pages
```

#### 2. インジェスト実行

```bash
cd backend
source .venv/bin/activate
export DATABASE_URL="postgresql://postgres:password@localhost:5432/ai_navigator"
python -m app.scripts.ingest_to_db
```

#### 3. ベクトル検索テスト

```bash
cd backend
source .venv/bin/activate
export DATABASE_URL="postgresql://postgres:password@localhost:5432/ai_navigator"
python -m app.scripts.test_vector_search
```

### 登録データ

- **documents**: 6件（学系トップ、教員一覧、教員詳細×3、研究室ページ）
- **chunks**: 370件（チャンク+埋め込みベクトル+メタデータ）
- **メタデータ**: campus, department, professor, lab, tags

### ベクトル検索例

```sql
-- 「神戸 英利」で検索
SELECT chunk_id, text, campus, department, lab, professor,
       1 - (embedding <=> '[query_embedding]'::vector) AS similarity_score
FROM chunks
ORDER BY embedding <=> '[query_embedding]'::vector
LIMIT 10;
```

### 検証結果

詳細な検証結果は `docs/tasks/phase2_verification_results.md` を参照してください。

- ✅ スクレイピング成功: 6件
- ✅ インジェスト成功: 6件 (370チャンク)
- ✅ ベクトル検索動作確認済み
- ✅ メタデータ適切に付与

---

## ライセンス

MIT