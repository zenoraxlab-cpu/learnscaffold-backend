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
    and returns the transcribed text.
    """

    video_url = payload.url

    try:
        # Temporary file for audio
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
            temp_audio_path = tmp_file.name

        # Download audio
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": temp_audio_path,
            "quiet": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])

        # Send audio to Whisper (OpenAI)
        with open(temp_audio_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )

        os.remove(temp_audio_path)

        return {
            "status": "success",
            "transcript": transcript.text,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
