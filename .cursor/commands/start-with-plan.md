# start-with-plan

## 目的
`docs/tasks/`にある実装方針Markdownを起点に、必要な実装と検証を自走するための指示セットです。

## 引数
`/start-with-plan <docs/tasks/.../task.md>`

## 実行フロー
1. 指定ファイルが`docs/tasks/`配下に存在するか確認し、開けない場合はユーザーへ修正を依頼する。
2. Taskドキュメントから以下を抽出して要約する:
   - Source plan
   - Status
   - Proposed steps
   - Verification
3. 各ステップを作業タスクに分解し、Todoや実施順を明示する（必要なら`todo_write`利用）。
4. 承認済みであることをユーザーに確認し、未承認なら先に承認を得る。
5. 実装開始前に必ず新しい作業ブランチを作成する。
   - 作業ツリーがクリーンか確認し、`git checkout -b <feature-name>`でブランチを切る。
   - ブランチ名は`feature/<task-slug>`や`chore/<task-slug>`などTaskに紐づくものを提案し、ユーザーの同意を得る。
6. コード実装を開始し、ステップごとに
   - 対象ファイルの確認/編集
   - テスト・Lint・実行結果
   - 追加で生じた課題
   を報告する。
7. すべてのステップを完了したら、Verificationに記載されたチェックを実施し、結果をまとめる。
8. 必要に応じてTaskドキュメントの`Status`や`Verification`の更新内容を提案する。

## 注意事項
- Taskの範囲外に踏み出す場合は必ずユーザーへ相談する。
- 実装ログを簡潔にまとめ、ファイルパスやコマンドはバッククォートで示す。
- 完了後はPull Request作成や次アクションを提案する。

