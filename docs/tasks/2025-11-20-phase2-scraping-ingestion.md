# Task: Phase 2 スクレイピング & インジェスト実装

- **Source plan:** `docs/plans/phase2_ingestion_plan_jp_existing_impl.md`
- **Status:** Completed
- **Created:** 2025-11-20
- **Completed:** 2025-11-20
- **Assignee:** AI Assistant

---

## Summary

Phase 2 では、オープンキャンパスAIナビゲーションシステムにおける **データ収集パイプライン** を実装します。

具体的には、東京電機大学の学系紹介・教員情報・研究室ページから情報をスクレイピングし、テキスト正規化 → チャンク分割 → 埋め込み生成 → ベクトルDB登録 までの一連の処理を行うバッチスクリプトを構築します。

Phase 1 で構築した PostgreSQL + pgvector を活用し、既存の FastAPI 実装（特に `lm_studio_service.py`）を最大限再利用することで、効率的な実装を目指します。

### ゴール
- 5つの固定URLからデータを取得し、`documents` / `chunks` テーブルに登録
- 既存サービス層（`lm_studio_service.py`）を再利用した埋め込み生成
- CLI から再実行可能なバッチスクリプト（`python -m app.scripts.scrape_pages` など）
- 手動SQLでベクトル近傍検索が動作することを確認

### 非ゴール
- クローリング（固定URLのみ対象）
- FastAPI エンドポイントとしての実装（Phase 3で対応）
- 検索精度の評価・最適化（Phase 3で対応）

### 成功基準
1. `documents` テーブルに5ページ分のレコードが登録される
2. `chunks` テーブルにチャンク+埋め込み+メタデータが登録される
3. SQLでの近傍検索で「神戸 英利」「IoT」などのクエリで適切なチャンクが返る
4. スクリプトがエラーなく再実行可能

---

## Proposed Steps

### ステップ1: 環境準備とディレクトリ構成

**目的:** バッチスクリプト用のディレクトリ構造を整備する

**作業内容:**
1. 以下のディレクトリを作成
   ```
   backend/app/scripts/
   backend/app/scripts/utils/
   inputs/scraped/
   ```

2. 必要な依存パッケージを確認・追加（`pyproject.toml`）
   - `requests` (スクレイピング)
   - `beautifulsoup4` (HTML解析)
   - `lxml` (パーサ)
   - `tiktoken` (トークンカウント)
   - `psycopg2-binary` または `asyncpg` (DB接続)

3. `.gitignore` に `inputs/scraped/` を追加

**成果物:**
- ディレクトリ構造
- 更新された `pyproject.toml`

---

### ステップ2: DB接続サービスの実装

**目的:** documents / chunks テーブルへのCRUD操作を共通化する

**作業内容:**
1. `backend/app/services/db_service.py` を作成
2. 以下の関数を実装
   - `get_db_connection()`: DB接続取得
   - `insert_document(url, title, text, metadata)`: documentsテーブルへの挿入
   - `insert_chunks(document_id, chunks_data)`: chunksテーブルへのbulk挿入
   - `check_document_exists(url)`: 重複チェック

3. トランザクション管理を実装（1ページ単位でコミット）

4. 環境変数からDB接続情報を取得（`app/config.py` を活用）

**成果物:**
- `backend/app/services/db_service.py`

**注意点:**
- Phase 1 で作成したテーブルスキーマ（`backend/migrations/001_init_vector_db.sql`）に準拠
- エラーハンドリング（接続失敗、重複など）を適切に行う

---

### ステップ3: スクレイピングバッチの実装

**目的:** 固定URLからHTMLを取得し、ローカルに保存する

**作業内容:**
1. `backend/app/scripts/scrape_pages.py` を作成

2. 対象URL定数を定義
   ```python
   URLS = {
       "department_top": "https://www.dendai.ac.jp/about/undergraduate/rikougaku/rd/",
       "faculty_list": "https://www.dendai.ac.jp/about/undergraduate/rikougaku/rd/kyoin.html",
       "professor_s000773": "https://ra-data.dendai.ac.jp/tduhp/KgApp/k03/resid/S000773",
       "professor_s000301": "https://ra-data.dendai.ac.jp/tduhp/KgApp/k03/resid/S000301",
       "professor_s000438": "https://ra-data.dendai.ac.jp/tduhp/KgApp/k03/resid/S000438",
       "lab_kamlab": "https://www.kamlab.rd.dendai.ac.jp/about"
   }
   ```

3. スクレイピング処理を実装
   - `requests.get()` でHTML取得
   - `inputs/scraped/{識別子}.html` に保存
   - アクセス間に `time.sleep(1)` を挿入（マナー）
   - エラーハンドリング（404、タイムアウトなど）

4. CLIから実行可能に
   ```bash
   python -m app.scripts.scrape_pages
   ```

**成果物:**
- `backend/app/scripts/scrape_pages.py`
- `inputs/scraped/*.html` (5〜6ファイル)

**注意点:**
- User-Agentヘッダーを適切に設定
- リトライロジックを実装（3回まで）

---

### ステップ4: テキスト正規化モジュールの実装

**目的:** HTMLから本文テキストを抽出し、RAG向きにクリーンアップする

**作業内容:**
1. `backend/app/scripts/utils/clean_text.py` を作成

2. 正規化関数を実装
   ```python
   def clean_html_text(html: str) -> str:
       """HTMLから本文テキストを抽出・正規化"""
       # <script>, <style> の除去
       # ヘッダー・フッター・ナビの削除
       # 連続空白・改行の統一
       # 短すぎる場合はNone返却（200文字未満）
   ```

3. BeautifulSoup を使った不要要素の削除
   - `<script>`, `<style>`, `<nav>`, `<footer>` など
   - class/id ベースのフィルタリング（サイト固有）

4. テキスト正規化
   - 連続空白 → 単一スペース
   - 連続改行 → 最大2改行
   - 全角・半角の統一（任意）

**成果物:**
- `backend/app/scripts/utils/clean_text.py`

**検証:**
- サンプルHTMLで正しくテキスト抽出できることを確認
- 最低文字数チェックが動作することを確認

---

### ステップ5: ページ種別パーサの実装

**目的:** ページ種別ごとにタイトル・本文・メタデータを抽出する

**作業内容:**
1. `backend/app/scripts/utils/parsers.py` を作成

2. 各ページ種別のパーサ関数を実装
   ```python
   def parse_department_top(html: str, url: str) -> dict:
       """学系トップページのパース"""
       # タイトル、本文、tags=["department_overview"]
   
   def parse_faculty_list(html: str, url: str) -> dict:
       """教員一覧ページのパース"""
       # タイトル、本文、tags=["faculty_list", "lab_list"]
   
   def parse_professor_detail(html: str, url: str) -> dict:
       """教員詳細ページのパース"""
       # タイトル、教員名、専門分野、研究キーワード
       # tags=["faculty_profile", "research_topic"]
   
   def parse_lab_about(html: str, url: str) -> dict:
       """研究室ページのパース"""
       # タイトル、研究室名、指導教員、研究内容
       # tags=["lab", "research_theme"]
   ```

3. 共通メタデータの付与
   - `campus = "hatoyama"`
   - `department = "理工学部"`

4. URLパターンマッチングによる自動振り分け関数
   ```python
   def parse_page(html: str, url: str) -> dict:
       """URLに応じて適切なパーサを呼び出す"""
   ```

**成果物:**
- `backend/app/scripts/utils/parsers.py`

**検証:**
- 各ページでタイトル・メタデータが正しく抽出されることを確認

---

### ステップ6: チャンク分割モジュールの実装

**目的:** heading-aware なチャンク分割を実装する

**作業内容:**
1. `backend/app/scripts/utils/chunker.py` を作成

2. チャンク分割関数を実装
   ```python
   def chunk_text(
       text: str,
       heading_structure: list[dict],
       chunk_size_tokens: int = 400,
       overlap_tokens: int = 80
   ) -> list[dict]:
       """テキストをチャンクに分割"""
       # heading_path を保持しながら分割
       # overlap を考慮
   ```

3. tiktoken を使ったトークンカウント
   - モデル: `cl100k_base` (OpenAI互換)

4. heading_path の構築
   - 例: `["研究室概要", "研究内容"]`
   - チャンクのコンテキスト情報として保存

5. チャンクメタデータの構造
   ```python
   {
       "text": "チャンク本文",
       "heading_path": ["見出し1", "見出し2"],
       "chunk_index": 0,
       "token_count": 387
   }
   ```

**成果物:**
- `backend/app/scripts/utils/chunker.py`

**検証:**
- サンプルテキストでチャンクサイズ・overlapが期待通りか確認

---

### ステップ7: 埋め込み生成機能の拡張

**目的:** 既存の `lm_studio_service.py` に埋め込み生成機能を追加

**作業内容:**
1. `backend/app/services/lm_studio_service.py` を確認

2. 埋め込み生成関数を追加（または既存機能を確認）
   ```python
   async def generate_embeddings(
       texts: list[str],
       batch_size: int = 32
   ) -> list[list[float]]:
       """テキスト配列から埋め込みベクトルを生成"""
       # LM Studio の embedding API を呼び出す
       # バッチ処理を実装
   ```

3. 埋め込み次元数の取得機能
   ```python
   def get_embedding_dim() -> int:
       """使用中の埋め込みモデルの次元数を返す"""
   ```

4. エラーハンドリング
   - LM Studio 未起動
   - タイムアウト
   - レート制限

**成果物:**
- 更新された `backend/app/services/lm_studio_service.py`

**検証:**
- テストテキストで埋め込みが生成されることを確認
- 次元数が取得できることを確認

---

### ステップ8: インジェストバッチの実装

**目的:** スクレイプ結果をDBに登録する統合バッチ

**作業内容:**
1. `backend/app/scripts/ingest_to_db.py` を作成

2. メイン処理フローを実装
   ```python
   async def ingest_page(html_path: str, url: str):
       """1ページをインジェストする"""
       # 1. HTMLファイル読み込み
       # 2. パース（parsers.py）
       # 3. テキスト正規化（clean_text.py）
       # 4. チャンク分割（chunker.py）
       # 5. 埋め込み生成（lm_studio_service）
       # 6. documents 登録（db_service）
       # 7. chunks bulk insert（db_service）
   
   async def main():
       """全ページをインジェスト"""
       for html_file in glob("inputs/scraped/*.html"):
           await ingest_page(html_file, ...)
   ```

3. トランザクション管理
   - 1ページ単位でコミット
   - エラー時はロールバック、ログ記録して次へ

4. 進捗表示・ログ出力
   - tqdm またはシンプルなプログレス表示
   - 成功/失敗をログファイルに記録

5. CLIから実行可能に
   ```bash
   python -m app.scripts.ingest_to_db
   ```

**成果物:**
- `backend/app/scripts/ingest_to_db.py`

**注意点:**
- 重複チェック（同じURLを再登録しない）
- 既存データの扱い（上書き or スキップ）

---

### ステップ9: 手動検証とデバッグ

**目的:** 登録されたデータの品質を確認する

**作業内容:**
1. PostgreSQL に接続してデータを確認
   ```bash
   psql -U postgres -d opencampus_navigator
   ```

2. documents テーブルの確認
   ```sql
   SELECT doc_id, url, title, campus, department 
   FROM documents;
   ```

3. chunks テーブルの確認
   ```sql
   SELECT chunk_id, text, heading_path, campus, department, tags
   FROM chunks
   LIMIT 10;
   ```

4. ベクトル近傍検索のテスト
   ```sql
   -- 「神戸 英利」のクエリ埋め込みを生成（別途スクリプトで）
   -- qvec に埋め込みベクトルを設定
   SELECT chunk_id, text, campus, department,
          1 - (embedding <=> :qvec) AS score
   FROM chunks
   ORDER BY embedding <=> :qvec
   LIMIT 10;
   ```

5. メタデータの確認
   - `campus`, `department`, `professor`, `lab`, `tags` が期待通りか
   - 「IoT」「情報システムデザイン学系」などでフィルタリングできるか

6. デバッグが必要な項目のリストアップ
   - テキストが正しく抽出されていない箇所
   - チャンク分割が不自然な箇所
   - メタデータの不備

**成果物:**
- 検証結果レポート（`docs/tasks/phase2_verification_results.md`）
- 修正が必要な箇所のリスト

---

### ステップ10: ドキュメント整備と最終確認

**目的:** 実装の完了とドキュメント整備

**作業内容:**
1. README の更新
   - Phase 2 の実装内容を追記
   - バッチスクリプトの実行方法を記載

2. 各スクリプトに docstring を追加
   - 目的、引数、戻り値、使用例

3. 実行手順書の作成（`docs/tasks/phase2_execution_guide.md`）
   ```markdown
   # Phase 2 実行手順
   
   ## 前提条件
   - PostgreSQL + pgvector が起動している
   - LM Studio が起動している
   
   ## 実行コマンド
   1. スクレイピング: `python -m app.scripts.scrape_pages`
   2. インジェスト: `python -m app.scripts.ingest_to_db`
   
   ## トラブルシューティング
   ...
   ```

4. 完了条件の最終確認
   - [ ] 5ページが documents テーブルに登録されている
   - [ ] chunks テーブルにチャンク+埋め込みが登録されている
   - [ ] ベクトル近傍検索が動作する
   - [ ] スクリプトが再実行可能

5. Phase 3 へのハンドオフ準備
   - 残課題のリストアップ
   - 改善提案の記録

**成果物:**
- 更新された README.md
- `docs/tasks/phase2_execution_guide.md`
- 完了レポート

---

## Verification

### 機能検証
- [ ] `python -m app.scripts.scrape_pages` が正常に完了する
- [ ] `inputs/scraped/` に5〜6個のHTMLファイルが保存される
- [ ] `python -m app.scripts.ingest_to_db` が正常に完了する
- [ ] documents テーブルに5レコードが登録される
- [ ] chunks テーブルに複数のチャンクが登録される
- [ ] 各チャンクに embedding ベクトルが含まれる

### データ品質検証
- [ ] テキストが適切に正規化されている（不要なタグがない）
- [ ] チャンクサイズが400トークン前後である
- [ ] heading_path が適切に保持されている
- [ ] メタデータ（campus, department, tags）が正しく付与されている

### 検索機能検証
- [ ] SQLでベクトル近傍検索が実行できる
- [ ] 「神戸 英利」クエリで関連チャンクが返る
- [ ] 「IoT」クエリで関連チャンクが返る
- [ ] メタデータフィルタ（campus, department）が機能する

### 運用性検証
- [ ] スクリプトが再実行可能（冪等性）
- [ ] エラー時のログが適切に記録される
- [ ] 実行時間が許容範囲内（全体で5分以内）

---

## Dependencies & Prerequisites

### 技術的前提条件
- Phase 1 完了（PostgreSQL + pgvector のセットアップ済み）
- LM Studio が起動しており、埋め込みモデルがロード済み
- Python 3.11+
- 必要なパッケージ（requests, beautifulsoup4, tiktoken, psycopg2-binary）

### 外部依存
- 対象URLが正常にアクセス可能である
- LM Studio の embedding API が利用可能である

---

## Risks & Mitigations

### リスク1: スクレイピング失敗
- **原因:** 対象サイトの構造変更、ネットワークエラー
- **対策:** リトライロジック、エラーハンドリング、ログ記録

### リスク2: LM Studio 接続失敗
- **原因:** LM Studio 未起動、モデル未ロード
- **対策:** 事前チェック、明確なエラーメッセージ

### リスク3: チャンク品質の問題
- **原因:** HTML構造の複雑さ、見出し抽出の失敗
- **対策:** ページ種別ごとのカスタムパーサ、手動検証フェーズ

### リスク4: DB接続・性能問題
- **原因:** 大量データの一括挿入
- **対策:** bulk insert の活用、トランザクション単位の調整

---

## Open Questions

1. **埋め込みモデルの選定**
   - LM Studio で利用する具体的なモデルは？（例: `nomic-embed-text-v1.5`）
   - 次元数は？（768? 1024?）

2. **重複データの扱い**
   - 同じURLを再実行した場合、上書き or スキップ？
   - バージョン管理は必要か？

3. **HTML構造の詳細**
   - 各ページのHTML構造は事前調査済みか？
   - CSSセレクタの特定は必要か？

4. **チャンク分割の調整**
   - 400トークンで問題ない？
   - 実際のページで試して調整が必要？

---

## Next Steps (Phase 3 Preview)

Phase 2 完了後、以下を実装予定：

1. **RAG パイプライン実装**
   - `rag_service.py` の拡張
   - ベクトル検索 → LLM生成 → 音声合成

2. **検索戦略の比較**
   - Dense のみ
   - Prefilter + Dense
   - Hybrid（Dense + BM25）

3. **評価実験**
   - Recall@k, nDCG, MRR
   - チャンクサイズ・overlap のアブレーション

4. **FastAPI エンドポイント化**
   - `/api/v1/query` エンドポイント
   - ストリーミングレスポンス

---

## References

- Phase 2 計画書: `docs/plans/phase2_ingestion_plan_jp_existing_impl.md`
- Phase 1 実装: `backend/migrations/001_init_vector_db.sql`
- 既存サービス: `backend/app/services/lm_studio_service.py`

