"""
LM Studio LLMサービス（校正・回答生成）
"""
import re
import logging

import requests

from app.config import settings

logger = logging.getLogger(__name__)


class LMStudioService:
    """LM Studio LLMサービス"""

    @staticmethod
    async def check_model_availability() -> bool:
        """LM Studioのモデルが利用可能かチェック"""
        try:
            response = requests.get(
                f"{settings.LM_STUDIO_BASE_URL}/models",
                timeout=5
            )
            if response.status_code == 200:
                models = response.json()
                available_models = [
                    model.get("id", "") for model in models.get("data", [])
                ]
                logger.info(f"利用可能なモデル: {available_models}")
                return settings.LM_STUDIO_MODEL in available_models
            return False
        except Exception as e:
            logger.error(f"LM Studioモデル確認エラー: {e}")
            return False

    @staticmethod
    async def correct_text(text: str) -> str:
        """LM Studioを使用して文章を校正"""
        try:
            system_prompt = """あなたは日本語文章校正の専門家です。音声認識で生成されたテキストを、自然で読みやすい日本語に校正することが得意です。

校正の方針：
1. 文法的な誤りを修正
2. 適切な句読点を追加
3. 自然な日本語表現に変更
4. 元の意味を保持
5. 簡潔で分かりやすい文章にする

校正後の文章のみを出力してください。"""

            user_prompt = f"""以下の音声認識テキストを校正してください：

{text}"""

            payload = {
                "model": settings.LM_STUDIO_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.2,
                "max_tokens": 2000,
                "top_p": 0.9,
                "frequency_penalty": 0.1,
                "presence_penalty": 0.1
            }

            response = requests.post(
                f"{settings.LM_STUDIO_BASE_URL}/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=settings.LM_STUDIO_TIMEOUT
            )

            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"].strip()
            else:
                logger.error(
                    f"LM Studio API エラー: {response.status_code} - {response.text}"
                )
                return text

        except requests.exceptions.RequestException as e:
            logger.error(f"LM Studio接続エラー: {e}")
            return text
        except Exception as e:
            logger.error(f"文章校正エラー: {e}")
            return text

    @staticmethod
    async def generate_answer(query: str, context_chunks: list[dict]) -> str:
        """
        コンテキストチャンクを使ってクエリに対する回答を生成

        Args:
            query: ユーザーの質問
            context_chunks: 検索で取得したコンテキストチャンク（text, metadata含む）

        Returns:
            生成された回答テキスト
        """
        try:
            context_text = "\n\n".join([
                f"[情報源 {i+1}]\n{_clean_text(chunk['text'])}"
                for i, chunk in enumerate(context_chunks)
            ])

            system_prompt = """あなたは東京電機大学のオープンキャンパスAIナビゲーターです。
与えられた情報源を基に、来場者の質問に対して正確で分かりやすい回答を提供してください。

回答の方針：
1. 情報源に基づいた正確な回答をする
2. 分かりやすく、親しみやすい表現を使う
3. 情報源に記載がない内容は推測しない
4. 必要に応じて具体的な情報（研究室名、教授名など）を含める
5. 簡潔にまとめる（200文字程度を目安）

フォーマット指示：
- HTMLタグ（<br>, <div>など）やマークダウン記号（**, ##など）は除去し、自然な日本語で回答する
- 複数の項目を説明する場合は、「〜、〜、〜といった分野です」のように自然な文章にまとめる
- 箇条書きが必要な場合は「まず〜、次に〜、さらに〜」のように文章で表現する
- 読みやすい段落構成を意識する"""

            user_prompt = f"""以下の情報源を基に、質問に答えてください。

【情報源】
{context_text}

【質問】
{query}

【回答】"""

            payload = {
                "model": settings.LM_STUDIO_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 500,
                "top_p": 0.9
            }

            response = requests.post(
                f"{settings.LM_STUDIO_BASE_URL}/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=settings.LM_STUDIO_TIMEOUT
            )

            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"].strip()
            else:
                logger.error(
                    f"LM Studio API エラー: {response.status_code} - {response.text}"
                )
                return "申し訳ございません。現在、回答を生成できません。"

        except requests.exceptions.RequestException as e:
            logger.error(f"LM Studio接続エラー: {e}")
            return "申し訳ございません。現在、システムに接続できません。"
        except Exception as e:
            logger.error(f"回答生成エラー: {e}")
            return "申し訳ございません。回答の生成中にエラーが発生しました。"


def _clean_text(text: str) -> str:
    """
    テキストからHTMLタグやマークダウン記号を除去して整形

    Args:
        text: 元のテキスト

    Returns:
        整形されたテキスト
    """
    # HTMLタグを除去
    text = re.sub(r'<[^>]+>', ' ', text)
    # マークダウンの強調記号を除去
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # **bold**
    text = re.sub(r'\*([^*]+)\*', r'\1', text)      # *italic*
    # マークダウンの見出し記号を除去
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
    # 連続する空白を1つに
    text = re.sub(r'\s+', ' ', text)
    # 前後の空白を削除
    return text.strip()
