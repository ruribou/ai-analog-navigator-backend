"""
LM Studio文章校正サービス
"""
import requests
import logging

from app.config import settings
from app.core.exceptions import LMStudioError

logger = logging.getLogger(__name__)


class LMStudioService:
    """LM Studio文章校正サービス"""
    
    @staticmethod
    async def correct_text(text: str) -> str:
        """LM Studioを使用して文章を校正"""
        try:
            prompt = f"""以下の文章を自然で読みやすい日本語に校正してください。文法的な誤りを修正し、より適切な表現に変更してください。校正後の文章のみを出力してください。

元の文章：
{text}

校正後の文章："""

            payload = {
                "model": settings.LM_STUDIO_MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.3,
                "max_tokens": 1000
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
