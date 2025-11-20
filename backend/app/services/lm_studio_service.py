"""
LM Studio文章校正サービス
"""
import requests
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class LMStudioService:
    """LM Studio文章校正サービス"""
    
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
                available_models = [model.get("id", "") for model in models.get("data", [])]
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
            # システムプロンプトで役割を明確に定義
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
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ],
                "temperature": 0.2,  # より一貫した校正のため低めに設定
                "max_tokens": 2000,  # 20Bモデルなので余裕を持って
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
                logger.error(f"LM Studio API エラー: {response.status_code} - {response.text}")
                return text  # エラーの場合は元のテキストを返す
                
        except requests.exceptions.RequestException as e:
            logger.error(f"LM Studio接続エラー: {e}")
            return text  # エラーの場合は元のテキストを返す
        except Exception as e:
            logger.error(f"文章校正エラー: {e}")
            return text  # エラーの場合は元のテキストを返す
