# Python 3.12をベースイメージとして使用
FROM python:3.12-slim

# 作業ディレクトリを設定
WORKDIR /app

# システムの依存関係をインストール
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# uvをインストール
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Pythonの依存関係をコピー
COPY pyproject.toml uv.lock ./

# 依存関係をインストール
RUN uv sync --frozen --no-dev

# アプリケーションのソースコードをコピー
COPY . .

# ポート8000を公開
EXPOSE 8000

# アプリケーションを起動
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
