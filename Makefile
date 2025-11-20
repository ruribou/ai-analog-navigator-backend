.PHONY: help setup dev build up down restart clean rebuild \
        logs logs-api logs-frontend logs-db \
        shell-api shell-frontend shell-db \
        status ps health \
        start-api start-frontend start-db \
        stop-api stop-frontend stop-db \
        restart-api restart-frontend restart-db

# デフォルトターゲット
help: ## ヘルプを表示
	@echo "==================== AI Analog Navigator ===================="
	@echo ""
	@echo "利用可能なコマンド:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "============================================================="

# セットアップ・起動
setup: ## 初回セットアップ（ビルド + 起動）
	@echo "🚀 初回セットアップを開始します..."
	docker compose up --build -d
	@echo "✅ セットアップ完了！"
	@echo ""
	@echo "📱 Frontend: http://localhost:3000"
	@echo "🔧 Backend API: http://localhost:8000"
	@echo "📚 API Docs: http://localhost:8000/docs"
	@echo "🗄️  PostgreSQL: localhost:5432"
	@echo ""
	@echo "ログを確認: make logs"

dev: ## 開発環境を起動（ログ表示付き）
	docker compose up

# Docker操作
build: ## すべてのDockerイメージをビルド
	docker compose build

rebuild: ## キャッシュなしで完全リビルド
	docker compose build --no-cache

up: ## すべてのサービスを起動（バックグラウンド）
	docker compose up -d

down: ## すべてのサービスを停止
	docker compose down

restart: ## すべてのサービスを再起動
	docker compose restart

clean: ## サービスを停止してボリュームも削除
	docker compose down -v
	@echo "⚠️  データベースのデータも削除されました"

clean-all: ## サービス、ボリューム、イメージをすべて削除
	docker compose down -v --rmi all
	@echo "⚠️  すべてのデータとイメージが削除されました"

# 個別サービス起動
start-api: ## バックエンドAPIのみ起動
	docker compose up -d api

start-frontend: ## フロントエンドのみ起動
	docker compose up -d frontend

start-db: ## データベースのみ起動
	docker compose up -d postgres

# 個別サービス停止
stop-api: ## バックエンドAPIを停止
	docker compose stop api

stop-frontend: ## フロントエンドを停止
	docker compose stop frontend

stop-db: ## データベースを停止
	docker compose stop postgres

# 個別サービス再起動
restart-api: ## バックエンドAPIを再起動
	docker compose restart api

restart-frontend: ## フロントエンドを再起動
	docker compose restart frontend

restart-db: ## データベースを再起動
	docker compose restart postgres

# ログ確認
logs: ## すべてのサービスのログを表示
	docker compose logs -f

logs-api: ## バックエンドAPIのログを表示
	docker compose logs -f api

logs-frontend: ## フロントエンドのログを表示
	docker compose logs -f frontend

logs-db: ## データベースのログを表示
	docker compose logs -f postgres

# シェル接続
shell-api: ## バックエンドAPIコンテナにシェル接続
	docker compose exec api bash

shell-frontend: ## フロントエンドコンテナにシェル接続
	docker compose exec frontend sh

shell-db: ## データベースに接続
	docker compose exec postgres psql -U postgres -d ai_navigator

# ステータス確認
status: ## サービスの状態を確認
	docker compose ps

ps: ## サービスの状態を確認（statusのエイリアス）
	docker compose ps

health: ## ヘルスチェック
	@echo "🏥 ヘルスチェックを実行中..."
	@echo ""
	@echo "📱 Frontend (http://localhost:3000):"
	@curl -s -o /dev/null -w "  Status: %{http_code}\n" http://localhost:3000 || echo "  ❌ 接続できません"
	@echo ""
	@echo "🔧 Backend API (http://localhost:8000):"
	@curl -s -o /dev/null -w "  Status: %{http_code}\n" http://localhost:8000 || echo "  ❌ 接続できません"
	@echo ""
	@echo "🗄️  PostgreSQL (localhost:5432):"
	@docker compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1 && echo "  ✅ 接続OK" || echo "  ❌ 接続できません"

