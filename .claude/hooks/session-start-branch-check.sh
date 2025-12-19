#!/bin/bash
# SessionStart Hook: develop/main ブランチでの作業を防止

set -e

# 現在のブランチを取得
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")

# Git リポジトリでない場合はスキップ
if [ -z "$CURRENT_BRANCH" ]; then
  exit 0
fi

# develop または main ブランチの場合は警告
if [ "$CURRENT_BRANCH" = "develop" ] || [ "$CURRENT_BRANCH" = "main" ]; then
  cat << EOF
{
  "decision": "Proceed",
  "feedback": "[Warning] 現在のブランチ: **$CURRENT_BRANCH**

開発作業は feature ブランチでおこなってください。

以下のいずれかを実行してください：
1. 既存の feature ブランチに切り替え: \`git checkout feature/xxx\`
2. 新しい feature ブランチを作成: \`git checkout -b feature/[description]\`

作業を続ける場合は、まずブランチを切り替えてください。"
}
EOF
  exit 0
fi

# feature/bugfix ブランチの場合は正常
exit 0