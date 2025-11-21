"""
音声認識テキストの校正サービス
"""
import json
import re
import logging
from pathlib import Path
from typing import Dict, Optional

from app.services.lm_studio_service import LMStudioService

logger = logging.getLogger(__name__)


def load_domain_terms() -> Dict[str, str]:
    """domain_terms.json を読み込み
    
    Returns:
        固有名詞辞書 {誤認識パターン: 正しい表記}
    """
    try:
        terms_path = Path(__file__).parent.parent / "data" / "domain_terms.json"
        
        if not terms_path.exists():
            logger.warning(f"固有名詞辞書が見つかりません: {terms_path}")
            return {}
        
        with open(terms_path, "r", encoding="utf-8") as f:
            domain_dict = json.load(f)
        
        logger.info(f"固有名詞辞書を読み込みました: {len(domain_dict)} エントリ")
        return domain_dict
        
    except Exception as e:
        logger.error(f"固有名詞辞書の読み込みエラー: {e}")
        return {}


def normalize_with_domain_terms(text: str, domain_dict: Optional[Dict[str, str]] = None) -> str:
    """辞書に基づいてテキストを正規化
    
    Args:
        text: 正規化対象のテキスト
        domain_dict: 固有名詞辞書 {誤認識パターン: 正しい表記}
                     None の場合は自動読み込み
    
    Returns:
        正規化されたテキスト
    
    Example:
        >>> normalize_with_domain_terms("こうべ先生の研究", {"こうべ": "神戸"})
        "神戸先生の研究"
    """
    if domain_dict is None:
        domain_dict = load_domain_terms()
    
    if not domain_dict:
        logger.debug("固有名詞辞書が空のため、正規化をスキップします")
        return text
    
    normalized_text = text
    
    # 辞書を長い順にソート（部分一致の競合を避けるため）
    sorted_terms = sorted(domain_dict.items(), key=lambda x: len(x[0]), reverse=True)
    
    replacements_made = []
    
    for wrong_term, correct_term in sorted_terms:
        # 完全一致または単語境界での置換
        pattern = re.compile(re.escape(wrong_term), re.IGNORECASE)
        
        if pattern.search(normalized_text):
            normalized_text = pattern.sub(correct_term, normalized_text)
            replacements_made.append(f"{wrong_term} → {correct_term}")
    
    if replacements_made:
        logger.info(f"固有名詞を正規化しました: {', '.join(replacements_made)}")
    else:
        logger.debug("置換する固有名詞が見つかりませんでした")
    
    return normalized_text


# LM Studio 校正用プロンプトテンプレート
CORRECTION_PROMPT_TEMPLATE = """あなたは日本語の音声認識テキストの校正モデルです。
以下の raw_text は Whisper による音声認識結果です。

誤変換された単語や固有名詞を正しい日本語に修正してください。
ただし、要約や文章構造の変更は行わず、「元の発話に忠実な校正」を行ってください。

raw_text:
{text}

校正結果:"""


async def correct_with_llm(raw_text: str, use_llm: bool = True) -> str:
    """LM Studio を使ってテキストを校正
    
    Args:
        raw_text: 校正対象のテキスト
        use_llm: LLM による校正を使用するか（False の場合は辞書のみ）
    
    Returns:
        校正されたテキスト
    """
    # まず辞書による正規化を実行
    normalized_text = normalize_with_domain_terms(raw_text)
    
    # LLM 校正を使用しない場合は辞書正規化のみで終了
    if not use_llm:
        logger.info("辞書正規化のみを実行（LLM校正はスキップ）")
        return normalized_text
    
    try:
        logger.info("LM Studio による校正を開始します")
        
        # プロンプトを構築
        prompt = CORRECTION_PROMPT_TEMPLATE.format(text=normalized_text)
        
        # LM Studio サービスを使用
        lm_service = LMStudioService()
        
        # 校正を実行
        corrected_text = await lm_service.generate_completion(
            prompt=prompt,
            max_tokens=500,
            temperature=0.3,  # 創造性を抑えて忠実な校正
            system_message="あなたは音声認識テキストを校正する専門家です。元の発話に忠実に、誤字や誤変換のみを修正してください。"
        )
        
        logger.info(f"LM Studio 校正完了: {len(corrected_text)} 文字")
        logger.debug(f"校正前: {normalized_text}")
        logger.debug(f"校正後: {corrected_text}")
        
        return corrected_text.strip()
        
    except Exception as e:
        logger.warning(f"LM Studio 校正でエラーが発生しました（辞書正規化結果を返します）: {e}")
        return normalized_text


async def correct_transcription(
    raw_text: str,
    use_dict: bool = True,
    use_llm: bool = False
) -> str:
    """音声認識テキストを校正する統合関数
    
    Args:
        raw_text: 音声認識結果（Whisper の生出力）
        use_dict: 固有名詞辞書による正規化を使用するか
        use_llm: LM Studio による校正を使用するか
    
    Returns:
        校正されたテキスト
    """
    logger.info(f"テキスト校正を開始: use_dict={use_dict}, use_llm={use_llm}")
    
    # 辞書のみ使用
    if use_dict and not use_llm:
        return normalize_with_domain_terms(raw_text)
    
    # LLM使用（辞書も内部で使用される）
    if use_llm:
        return await correct_with_llm(raw_text, use_llm=True)
    
    # 両方使用しない場合は元のテキストを返す
    logger.debug("校正をスキップします（use_dict=False, use_llm=False）")
    return raw_text

