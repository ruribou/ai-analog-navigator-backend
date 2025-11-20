"""
スクレイプ結果をDBに登録するインジェストバッチ
"""
import asyncio
import logging
from pathlib import Path
import sys

# パスを追加（app モジュールをインポートできるように）
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.db_service import DBService
from app.services.lm_studio_service import LMStudioService
from app.scripts.utils.parsers import parse_page
from app.scripts.utils.chunker import chunk_text

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# HTMLファイルが保存されているディレクトリ
SCRAPED_DIR = Path(__file__).parent.parent.parent.parent / "inputs" / "scraped"

# URL マッピング（ファイル名 → URL）
URL_MAPPING = {
    "department_top": "https://www.dendai.ac.jp/about/undergraduate/rikougaku/rd/",
    "faculty_list": "https://www.dendai.ac.jp/about/undergraduate/rikougaku/rd/kyoin.html",
    "professor_s000773": "https://ra-data.dendai.ac.jp/tduhp/KgApp/k03/resid/S000773",
    "professor_s000301": "https://ra-data.dendai.ac.jp/tduhp/KgApp/k03/resid/S000301",
    "professor_s000438": "https://ra-data.dendai.ac.jp/tduhp/KgApp/k03/resid/S000438",
    "lab_kamlab": "https://www.kamlab.rd.dendai.ac.jp/about"
}


async def ingest_page(html_path: Path, url: str) -> bool:
    """
    1ページをインジェスト
    
    Args:
        html_path: HTMLファイルのパス
        url: ソースURL
    
    Returns:
        成功した場合True、失敗した場合False
    """
    try:
        logger.info("=" * 60)
        logger.info(f"インジェスト開始: {html_path.name}")
        logger.info(f"URL: {url}")
        
        # 1. HTMLファイル読み込み
        html = html_path.read_text(encoding='utf-8')
        logger.info(f"HTMLファイル読み込み完了: {len(html)} 文字")
        
        # 2. パース
        parsed_data = parse_page(html, url)
        title = parsed_data['title']
        text = parsed_data['text']
        sections = parsed_data['sections']
        metadata = parsed_data['metadata']
        
        logger.info(f"パース完了: タイトル='{title}'")
        logger.info(f"テキスト長: {len(text)} 文字")
        logger.info(f"セクション数: {len(sections)}")
        
        if not text:
            logger.warning(f"テキストが空です。スキップします: {url}")
            return False
        
        # 3. チャンク生成
        chunks = chunk_text(
            text=text,
            sections=sections,
            chunk_size_tokens=400,
            overlap_tokens=80
        )
        logger.info(f"チャンク生成完了: {len(chunks)}個")
        
        if not chunks:
            logger.warning(f"チャンクが生成されませんでした。スキップします: {url}")
            return False
        
        # 4. 埋め込み生成
        chunk_texts = [chunk['text'] for chunk in chunks]
        logger.info("埋め込み生成開始...")
        embeddings = await LMStudioService.generate_embeddings(chunk_texts, batch_size=32)
        logger.info(f"埋め込み生成完了: {len(embeddings)}個")
        
        if len(embeddings) != len(chunks):
            logger.error(f"チャンク数と埋め込み数が一致しません: {len(chunks)} != {len(embeddings)}")
            return False
        
        # 5. documents テーブルに登録
        source_type = 'school_hp' if 'dendai.ac.jp' in url else 'lab_hp'
        doc_id = DBService.insert_document(
            url=url,
            title=title,
            text=text,
            source_type=source_type,
            meta=metadata
        )
        logger.info(f"ドキュメント登録完了: doc_id={doc_id}")
        
        # 6. chunks テーブルに一括登録
        embedding_model = "text-embedding-nomic-embed-text-v1.5"
        embedding_dim = LMStudioService.get_embedding_dim()
        
        chunks_data = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_data = {
                'chunk_index': i,
                'text': chunk['text'],
                'token_count': chunk['token_count'],
                'heading_path': [h['text'] if isinstance(h, dict) else str(h) for h in chunk.get('heading_path', [])],
                'tags': metadata.get('tags', []),
                'campus': metadata.get('campus'),
                'building': metadata.get('building'),
                'department': metadata.get('department'),
                'lab': metadata.get('lab'),
                'professor': metadata.get('professor', []),
                'source_url': url,
                'embedding': embedding,
                'embedding_model': embedding_model,
                'embedding_dim': embedding_dim
            }
            chunks_data.append(chunk_data)
        
        inserted_count = DBService.insert_chunks(doc_id, chunks_data)
        logger.info(f"チャンク登録完了: {inserted_count}件")
        
        logger.info(f"インジェスト成功: {html_path.name}")
        return True
        
    except Exception as e:
        logger.error(f"インジェストエラー ({html_path.name}): {e}", exc_info=True)
        return False


async def main():
    """
    メイン処理：全ページをインジェスト
    """
    logger.info("=" * 60)
    logger.info("インジェストバッチ開始")
    logger.info("=" * 60)
    
    # スクレイプされたHTMLファイルを検索
    html_files = list(SCRAPED_DIR.glob("*.html"))
    
    if not html_files:
        logger.error(f"HTMLファイルが見つかりません: {SCRAPED_DIR}")
        return 0, 0
    
    logger.info(f"対象ファイル数: {len(html_files)}")
    
    # 統計情報
    success_count = 0
    failure_count = 0
    
    # 各HTMLファイルをインジェスト
    for html_file in html_files:
        # ファイル名からURLを取得
        identifier = html_file.stem
        url = URL_MAPPING.get(identifier)
        
        if not url:
            logger.warning(f"URLマッピングが見つかりません: {identifier}")
            failure_count += 1
            continue
        
        # インジェスト実行
        result = await ingest_page(html_file, url)
        
        if result:
            success_count += 1
        else:
            failure_count += 1
    
    # 結果サマリー
    logger.info("=" * 60)
    logger.info(f"インジェスト完了: 成功 {success_count}件 / 失敗 {failure_count}件")
    logger.info("=" * 60)
    
    return success_count, failure_count


if __name__ == "__main__":
    success, failure = asyncio.run(main())
    exit(0 if failure == 0 else 1)

