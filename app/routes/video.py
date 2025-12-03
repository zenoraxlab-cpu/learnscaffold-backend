import os
import uuid
import tempfile
from typing import Any

import yt_dlp
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl
from openai import OpenAI

client = OpenAI()
router = APIRouter()


class VideoURLRequest(BaseModel):
    url: HttpUrl


@router.post("/analyze_url")
async def analyze_video_url(payload: VideoURLRequest) -> dict[str, Any]:
    url = str(payload.url)

    tmp_dir = tempfile.gettempdir()
    audio_id = str(uuid.uuid4())
    audio_path = os.path.join(tmp_dir, f"{audio_id}.m4a")

    try:
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": audio_path,
            "quiet": True,
            "no_warnings": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to download audio: {e}")

    if not os.path.exists(audio_path):
        raise HTTPException(status_code=500, detail="Audio file was not created")

    try:
        with open(audio_path, "rb") as f:
            transcript = client.audio.transcriptions.create(
                model="gpt-4o-mini-transcribe",
                file=f,
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ASR failed: {e}")
    finally:
        try:
            if os.path.exists(audio_path):
                os.remove(audio_path)
        except Exception:
            pass

    text = getattr(transcript, "text", "")
    if not text:
        raise HTTPException(status_code=500, detail="Empty transcript received")

    return {
        "status": "success",
        "mode": "video_url",
        "source_url": url,
        "text": text,
        "length": len(text),
    }
