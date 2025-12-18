# AI Analog Navigator

音声文字起こしと文章校正のためのフルスタックアプリケーション。Whisper + LM Studio + pgvectorを使用したRAGシステムを搭載。

## 技術スタック

- **Frontend**: Next.js 16 (React 19, TypeScript, Tailwind CSS 4)
- **Backend**: FastAPI (Python 3.12, uv)
- **Database**: PostgreSQL with pgvector extension
- **Containerization**: Docker & Docker Compose

## プロジェクト構造

```
ai-analog-navigator/
├── frontend/               # Next.js App Router
│   ├── app/                # ページ・コンポーネント
│   └── package.json
├── backend/                # FastAPIアプリケーション
│   ├── app/
│   │   ├── main.py         # エントリーポイント
│   │   ├── api/endpoints/  # APIエンドポイント
│   │   └── services/       # ビジネスロジック
│   └── pyproject.toml
├── docker-compose.yml
└── Makefile
```

## 開発環境

### 必要なツール
- Docker Desktop
- LM Studio（ローカルLLM）

### 起動方法

```bash
# 初回セットアップ
make setup

# 通常起動
make up

# ログ確認付き起動
make dev
```

### サービスURL
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- PostgreSQL: localhost:5432

## よく使うコマンド

```bash
# ビルド・起動
make build          # イメージビルド
make up             # 起動
make down           # 停止
make restart        # 再起動
make rebuild        # キャッシュなしリビルド

# ログ確認
make logs           # 全サービス
make logs-api       # バックエンドのみ
make logs-frontend  # フロントエンドのみ

# 個別サービス操作
make restart-api
make restart-frontend

# デバッグ
make status         # サービス状態確認
make health         # ヘルスチェック
make shell-api      # バックエンドコンテナに接続
make shell-frontend # フロントエンドコンテナに接続
make shell-db       # PostgreSQLに接続

# クリーンアップ
make clean          # ボリューム削除
make clean-all      # イメージも削除
```

## バックエンド開発

### 主要なサービス
- `whisper_service.py` - 音声文字起こし（faster-whisper使用）
- `lm_studio_service.py` - LM Studio連携（文章校正）
- `rag_service.py` - RAG検索（pgvector）
- `audio_processing_service.py` - 音声ファイル処理

### テスト実行

```bash
# コンテナ内で実行
make shell-api
pytest
```

## フロントエンド開発

### コマンド（コンテナ内）

```bash
make shell-frontend
npm run lint
npm run build
```

## 注意事項

- ホットリロード: バックエンドは有効、フロントエンドは本番モード
- コード変更後は `make restart-api` または `make restart-frontend` で反映
- データベースリセットは `make clean && make up`
