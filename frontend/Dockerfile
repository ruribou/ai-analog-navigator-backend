# Node.js 24をベースイメージとして使用
FROM node:24-alpine AS base

# 依存関係のインストールステージ
FROM base AS deps
WORKDIR /app

# package.jsonとpackage-lock.jsonをコピー
COPY package.json package-lock.json* ./
RUN npm ci

# ビルドステージ
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# 環境変数を設定（本番ビルド用）
ENV NEXT_TELEMETRY_DISABLED 1

# Next.jsアプリケーションをビルド
RUN npm run build

# 本番実行ステージ
FROM base AS runner
WORKDIR /app

ENV NODE_ENV production
ENV NEXT_TELEMETRY_DISABLED 1

# 非rootユーザーを作成
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# 必要なファイルをコピー
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

# ポート3000を公開
EXPOSE 3000

ENV PORT 3000
ENV HOSTNAME "0.0.0.0"

# アプリケーションを起動
CMD ["node", "server.js"]

