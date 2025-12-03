import os
import uuid
import tempfile
from typing import Any

import yt_dlp
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl
from openai import OpenAI

# OpenAI client (expects OPENAI_API_KEY in environment)
client = OpenAI()

router = APIRouter()


class VideoURLRequest(BaseModel):
    url: HttpUrl


@router.post("/analyze_url")
async def analyze_video_url(payload: VideoURLRequest) -> dict[str, Any]:
    """
    Downloads audio from a video URL using yt-dlp, sends it to Whisper,
    and returns transcription text.
    """
    url = str(payload.url)

    # Temporary audio file
    tmp_dir = tempfile.gettempdir()
    audio_id = str(uuid.uuid4())
    audio_path = os.path.join(tmp_dir, f"{audio_id}.m4a")

    # Download best audio stream
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

    # Transcribe with Whisper
    try:
        with open(audio_path, "rb") as f:
            transcript = client.audio.transcriptions.create(
                model="gpt-4o-mini-transcribe",
                file=f,
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ASR failed: {e}")
    finally:
        # Remove temp file
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

