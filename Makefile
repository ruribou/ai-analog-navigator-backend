.PHONY: help build up down restart logs logs-api logs-db shell-api shell-db clean status

# デフォルトターゲット
help: ## ヘルプを表示
	@echo "利用可能なコマンド:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

# Docker関連コマンド
build: ## Dockerイメージをビルド
	docker compose build

up: ## サービスを起動（バックグラウンド）
	docker compose up -d

down: ## サービスを停止
	docker compose down

restart: ## サービスを再起動
	docker compose restart

clean: ## サービスを停止してボリュームも削除
	docker compose down -v

# ログ関連
logs: ## 全サービスのログを表示
	docker compose logs -f

logs-api: ## APIサービスのログを表示
	docker compose logs -f api

logs-db: ## データベースのログを表示
	docker compose logs -f postgres

# シェル接続
shell-api: ## APIコンテナにシェル接続
	docker compose exec api bash

shell-db: ## データベースに接続
	docker compose exec postgres psql -U postgres -d ai_navigator

# 開発関連
dev: ## 開発環境を起動（ログ表示付き）
	docker compose up

status: ## サービスの状態を確認
	docker compose ps

# 初期セットアップ
setup: build up ## 初回セットアップ（ビルド + 起動）
	@echo "セットアップ完了！"
	@echo "API: http://localhost:8000"
	@echo "API Docs: http://localhost:8000/docs"

# ローカル開発環境
local-setup: ## ローカル開発環境のセットアップ
	uv venv --python=3.12.12
	uv add -r requirements.txt

local-run: ## ローカルでAPIを起動
	uv run main.py
