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

### 3. Docker Composeでサービス起動

```bash
# すべてのサービスをビルド＆起動
docker compose up --build -d

# ログを確認
docker compose logs -f

# 特定のサービスのログを確認
docker compose logs -f frontend
docker compose logs -f api
docker compose logs -f postgres
```

### 4. アプリケーションへのアクセス

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **PostgreSQL**: localhost:5432 (pgvector拡張付き)

### 5. サービスの停止

```bash
# サービス停止
docker compose down

# データも含めて完全に削除
docker compose down -v
```

## 開発コマンド

### コンテナの管理

```bash
# サービスの状態確認
docker compose ps

# 特定のサービスを再起動
docker compose restart api
docker compose restart frontend

# コンテナに入る
docker compose exec api bash
docker compose exec frontend sh

# イメージを再ビルド
docker compose build --no-cache
```

### ログの確認

```bash
# 全サービスのログ
docker compose logs -f

# 最新50行のみ表示
docker compose logs --tail=50 api

# エラーログのみ抽出
docker compose logs api | grep ERROR
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

## トラブルシューティング

### ポートが既に使用されている

```bash
# 使用中のポートを確認
lsof -i :3000
lsof -i :8000
lsof -i :5432

# プロセスを終了してから再起動
docker compose down
docker compose up -d
```

### イメージのクリーンビルド

```bash
# すべて停止して削除
docker compose down -v

# イメージも削除
docker compose down --rmi all -v

# 再ビルド
docker compose up --build -d
```

### データベースのリセット

```bash
# ボリュームを削除（データが消えます）
docker compose down -v
docker compose up -d
```