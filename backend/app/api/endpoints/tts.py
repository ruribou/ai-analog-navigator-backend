"""
Text-to-Speech API エンドポイント
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from typing import Optional
import logging

from app.services.tts_service import TTSService, SPEAKERS, DEFAULT_SPEAKER_ID

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tts", tags=["Text-to-Speech"])


class SynthesizeRequest(BaseModel):
    """音声合成リクエスト"""
    text: str = Field(..., description="読み上げるテキスト", max_length=1000)
    speaker_id: int = Field(DEFAULT_SPEAKER_ID, description="話者ID")
    speed_scale: float = Field(1.0, ge=0.5, le=2.0, description="話速")
    pitch_scale: float = Field(0.0, ge=-0.15, le=0.15, description="音高")
    intonation_scale: float = Field(1.0, ge=0.0, le=2.0, description="抑揚")
    volume_scale: float = Field(1.0, ge=0.0, le=2.0, description="音量")


class SpeakerInfo(BaseModel):
    """話者情報"""
    id: int
    name: str


@router.post("/synthesize", response_class=Response)
async def synthesize_speech(request: SynthesizeRequest):
    """
    テキストを音声に変換

    - **text**: 読み上げるテキスト（最大1000文字）
    - **speaker_id**: 話者ID（デフォルト: 3 = ずんだもん）
    - **speed_scale**: 話速（0.5〜2.0）
    - **pitch_scale**: 音高（-0.15〜0.15）
    - **intonation_scale**: 抑揚（0.0〜2.0）
    - **volume_scale**: 音量（0.0〜2.0）

    Returns:
        WAV形式の音声データ
    """
    try:
        logger.info(f"音声合成リクエスト: text={request.text[:50]}..., speaker_id={request.speaker_id}")

        tts_service = TTSService()
        audio_data = await tts_service.synthesize(
            text=request.text,
            speaker_id=request.speaker_id,
            speed_scale=request.speed_scale,
            pitch_scale=request.pitch_scale,
            intonation_scale=request.intonation_scale,
            volume_scale=request.volume_scale
        )

        return Response(
            content=audio_data,
            media_type="audio/wav",
            headers={
                "Content-Disposition": "inline; filename=speech.wav"
            }
        )

    except RuntimeError as e:
        logger.error(f"音声合成エラー: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"予期しないエラー: {e}")
        raise HTTPException(status_code=500, detail="音声合成に失敗しました")


@router.get("/synthesize")
async def synthesize_speech_get(
    text: str = Query(..., description="読み上げるテキスト", max_length=1000),
    speaker_id: int = Query(DEFAULT_SPEAKER_ID, description="話者ID"),
    speed_scale: float = Query(1.0, ge=0.5, le=2.0, description="話速")
):
    """
    テキストを音声に変換（GETメソッド版、シンプルなパラメータ）

    ブラウザから直接アクセスする場合に便利
    """
    request = SynthesizeRequest(
        text=text,
        speaker_id=speaker_id,
        speed_scale=speed_scale
    )
    return await synthesize_speech(request)


@router.get("/speakers", response_model=list[SpeakerInfo])
async def get_speakers():
    """
    利用可能な話者一覧を取得

    Returns:
        話者IDと名前のリスト
    """
    return [
        SpeakerInfo(id=speaker_id, name=name)
        for name, speaker_id in SPEAKERS.items()
    ]


@router.get("/health")
async def health_check():
    """
    VOICEVOXエンジンのヘルスチェック

    Returns:
        ステータス情報
    """
    tts_service = TTSService()
    is_healthy = await tts_service.health_check()

    if is_healthy:
        return {"status": "healthy", "engine": "VOICEVOX"}
    else:
        raise HTTPException(
            status_code=503,
            detail="VOICEVOXエンジンに接続できません"
        )
