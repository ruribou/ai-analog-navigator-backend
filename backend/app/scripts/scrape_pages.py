"""
固定URLからHTMLをスクレイピングするバッチスクリプト
"""
import requests
import time
import logging
from pathlib import Path
from typing import Dict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# スクレイピング対象URL
URLS = {
    "department_top": "https://www.dendai.ac.jp/about/undergraduate/rikougaku/rd/",
    "faculty_list": "https://www.dendai.ac.jp/about/undergraduate/rikougaku/rd/kyoin.html",
    "professor_s000773": "https://ra-data.dendai.ac.jp/tduhp/KgApp/k03/resid/S000773",
    "professor_s000301": "https://ra-data.dendai.ac.jp/tduhp/KgApp/k03/resid/S000301",
    "professor_s000438": "https://ra-data.dendai.ac.jp/tduhp/KgApp/k03/resid/S000438",
    "lab_kamlab": "https://www.kamlab.rd.dendai.ac.jp/about"
}

# 保存先ディレクトリ（プロジェクトルートからの相対パス）
OUTPUT_DIR = Path(__file__).parent.parent.parent.parent / "inputs" / "scraped"

# リトライ設定
MAX_RETRIES = 3
RETRY_DELAY = 2  # 秒
REQUEST_DELAY = 1  # 各リクエスト間の待機時間（秒）


def scrape_page(identifier: str, url: str) -> bool:
    """
    指定されたURLからHTMLを取得して保存する
    
    Args:
        identifier: ページ識別子（ファイル名に使用）
        url: スクレイピング対象URL
    
    Returns:
        成功した場合True、失敗した場合False
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
    }
    
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(f"[{identifier}] スクレイピング開始 (試行 {attempt}/{MAX_RETRIES}): {url}")
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # 文字エンコーディングを適切に設定
            if response.encoding is None or response.encoding == 'ISO-8859-1':
                response.encoding = response.apparent_encoding or 'utf-8'
            
            # HTMLを保存
            output_file = OUTPUT_DIR / f"{identifier}.html"
            output_file.write_text(response.text, encoding='utf-8')
            
            logger.info(f"[{identifier}] 保存成功: {output_file} ({len(response.text)} 文字)")
            return True
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"[{identifier}] HTTPエラー (試行 {attempt}/{MAX_RETRIES}): {e}")
            if response.status_code == 404:
                logger.error(f"[{identifier}] 404 Not Found - スキップします")
                return False
        except requests.exceptions.ConnectionError as e:
            logger.error(f"[{identifier}] 接続エラー (試行 {attempt}/{MAX_RETRIES}): {e}")
        except requests.exceptions.Timeout as e:
            logger.error(f"[{identifier}] タイムアウト (試行 {attempt}/{MAX_RETRIES}): {e}")
        except Exception as e:
            logger.error(f"[{identifier}] 予期しないエラー (試行 {attempt}/{MAX_RETRIES}): {e}")
        
        # リトライ前に待機
        if attempt < MAX_RETRIES:
            logger.info(f"[{identifier}] {RETRY_DELAY}秒後にリトライします...")
            time.sleep(RETRY_DELAY)
    
    logger.error(f"[{identifier}] {MAX_RETRIES}回の試行後も失敗しました")
    return False


def main():
    """
    メイン処理：全URLをスクレイピング
    """
    logger.info("=" * 60)
    logger.info("スクレイピングバッチ開始")
    logger.info("=" * 60)
    
    # 保存先ディレクトリが存在することを確認
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"保存先ディレクトリ: {OUTPUT_DIR}")
    
    # 統計情報
    success_count = 0
    failure_count = 0
    
    # 各URLをスクレイピング
    for identifier, url in URLS.items():
        result = scrape_page(identifier, url)
        
        if result:
            success_count += 1
        else:
            failure_count += 1
        
        # 次のリクエストまで待機（マナー）
        if identifier != list(URLS.keys())[-1]:  # 最後のページでなければ
            logger.info(f"次のリクエストまで {REQUEST_DELAY}秒待機...")
            time.sleep(REQUEST_DELAY)
    
    # 結果サマリー
    logger.info("=" * 60)
    logger.info(f"スクレイピング完了: 成功 {success_count}件 / 失敗 {failure_count}件")
    logger.info("=" * 60)
    
    return success_count, failure_count


if __name__ == "__main__":
    success, failure = main()
    exit(0 if failure == 0 else 1)

