"""
VOICEVOX Text-to-Speech サービス
"""
import logging
import httpx

logger = logging.getLogger(__name__)

# VOICEVOX Engine URL (Docker Compose内からアクセス)
VOICEVOX_BASE_URL = "http://voicevox:50021"

# 話者ID一覧（よく使うもの）
SPEAKERS = {
    "四国めたん（ノーマル）": 2,
    "四国めたん（あまあま）": 0,
    "四国めたん（ツンツン）": 6,
    "ずんだもん（ノーマル）": 3,
    "ずんだもん（あまあま）": 1,
    "ずんだもん（ツンツン）": 7,
    "春日部つむぎ": 8,
    "雨晴はう": 10,
    "波音リツ": 9,
    "玄野武宏": 11,
    "白上虎太郎": 12,
    "青山龍星": 13,
    "冥鳴ひまり": 14,
    "九州そら": 16,
}

DEFAULT_SPEAKER_ID = 3  # ずんだもん（ノーマル）


class TTSService:
    """VOICEVOX Text-to-Speech サービス"""

    def __init__(self, base_url: str = VOICEVOX_BASE_URL):
        self.base_url = base_url

    async def synthesize(
        self,
        text: str,
        speaker_id: int = DEFAULT_SPEAKER_ID,
        speed_scale: float = 1.0,
        pitch_scale: float = 0.0,
        intonation_scale: float = 1.0,
        volume_scale: float = 1.0
    ) -> bytes:
        """
        テキストを音声に変換

        Args:
            text: 読み上げるテキスト
            speaker_id: 話者ID
            speed_scale: 話速（0.5〜2.0、デフォルト1.0）
            pitch_scale: 音高（-0.15〜0.15、デフォルト0.0）
            intonation_scale: 抑揚（0.0〜2.0、デフォルト1.0）
            volume_scale: 音量（0.0〜2.0、デフォルト1.0）

        Returns:
            WAV形式の音声データ（bytes）
        """
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                # 1. 音声合成用のクエリを作成
                logger.info(f"音声合成クエリ作成: speaker={speaker_id}, text={text[:50]}...")

                query_response = await client.post(
                    f"{self.base_url}/audio_query",
                    params={"text": text, "speaker": speaker_id}
                )
                query_response.raise_for_status()
                audio_query = query_response.json()

                # パラメータを調整
                audio_query["speedScale"] = speed_scale
                audio_query["pitchScale"] = pitch_scale
                audio_query["intonationScale"] = intonation_scale
                audio_query["volumeScale"] = volume_scale

                # 2. 音声を合成
                logger.info("音声合成中...")
                synthesis_response = await client.post(
                    f"{self.base_url}/synthesis",
                    params={"speaker": speaker_id},
                    json=audio_query
                )
                synthesis_response.raise_for_status()

                audio_data = synthesis_response.content
                logger.info(f"音声合成完了: {len(audio_data)} bytes")

                return audio_data

        except httpx.ConnectError as e:
            logger.error(f"VOICEVOX接続エラー: {e}")
            raise RuntimeError("VOICEVOXエンジンに接続できません。サービスが起動しているか確認してください。")
        except httpx.HTTPStatusError as e:
            logger.error(f"VOICEVOX APIエラー: {e.response.status_code} - {e.response.text}")
            raise RuntimeError(f"音声合成に失敗しました: {e.response.text}")
        except Exception as e:
            logger.error(f"音声合成エラー: {e}")
            raise

    async def get_speakers(self) -> list:
        """
        利用可能な話者一覧を取得

        Returns:
            話者情報のリスト
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/speakers")
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"話者一覧取得エラー: {e}")
            raise

    async def health_check(self) -> bool:
        """
        VOICEVOXエンジンのヘルスチェック

        Returns:
            True: 正常, False: 異常
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/version")
                return response.status_code == 200
        except Exception:
            return False
