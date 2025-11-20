# AI Analog Navigator Backend

これは研究のバックエンドリポジトリです。
Pgvector + PostgreSQLを使用したRAGシステムのバックエンドAPIです。

## 技術スタック

- **Backend**: FastAPI (Python 3.12)
- **Database**: PostgreSQL with pgvector extension
- **Vector Search**: pgvector
- **Containerization**: Docker & Docker Compose

## プロジェクト構造

このプロジェクトはモノレポ構造を採用しており、将来的にフロントエンド（Next.js想定）を追加できるようになっています。

```
ai-analog-navigator/
├── backend/                # バックエンドアプリケーション
│   ├── app/               # メインアプリケーション
│   │   ├── main.py       # FastAPIアプリケーション
│   │   ├── config.py     # 設定管理
│   │   ├── api/          # APIエンドポイント
│   │   │   └── endpoints/
│   │   │       ├── health.py
│   │   │       └── transcription.py
│   │   ├── core/         # コア機能
│   │   │   ├── exceptions.py
│   │   │   └── middleware.py
│   │   ├── services/     # ビジネスロジック
│   │   │   ├── whisper_service.py
│   │   │   ├── lm_studio_service.py
│   │   │   ├── audio_processing_service.py
│   │   │   └── rag_service.py
│   │   └── models/       # Pydanticモデル
│   │       └── responses.py
│   ├── main.py           # エントリーポイント
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── uv.lock
├── docker-compose.yml     # Docker設定（ルート）
├── Makefile              # 開発用コマンド（ルート）
├── .gitignore
└── README.md
```

## 必要な環境

- Docker Desktop
- Python 3.12.12 (ローカル開発用)
- uv 0.9.5 (ローカル開発用)

## Docker環境での起動

### 1. 環境変数の設定（オプション）

必要に応じて`.env`ファイルを作成してください：

```bash
# PostgreSQL Database Configuration
POSTGRES_DB=ai_navigator
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password

# Database URL for application
DATABASE_URL=postgresql://postgres:password@postgres:5432/ai_navigator
```

### 2. Docker Composeでサービス起動

```bash
# すべてのサービスを起動
docker compose up -d

# ログを確認
docker compose logs -f

# 特定のサービスのログを確認
docker compose logs -f api
docker compose logs -f postgres
```

### 3. サービスの確認

- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **PostgreSQL**: localhost:5432 (pgvector拡張付き)

### 4. サービスの停止

```bash
# サービス停止
docker compose down

# データも削除する場合
docker compose down -v
```

## ローカル開発環境

### Makefileを使用（推奨）
```bash
# ローカル環境セットアップ
make local-setup

# ローカルでAPI起動
make local-run
```

### 手動セットアップ
```bash
# backendディレクトリに移動
cd backend

# 依存関係インストール
uv sync

# 開発用依存関係も含める場合
uv sync --extra test

# 起動
uv run main.py
```