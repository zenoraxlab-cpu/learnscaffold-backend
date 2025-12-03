import os
import uuid
import tempfile
from typing import Any

import yt_dlp
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl
from openai import OpenAI

# Клиент OpenAI. Берёт ключ из переменной окружения OPENAI_API_KEY
client = OpenAI()

router = APIRouter()


# ---------------------------
# Pydantic-модели запросов
# ---------------------------

class VideoURLRequest(BaseModel):
    url: HttpUrl


class VideoPlanRequest(BaseModel):
    url: HttpUrl
    target_days: int | None = None  # на будущее, под генерацию плана


# ---------------------------
# Вспомогательные функции
# ---------------------------

def _download_audio_from_url(url: str) -> str:
    """
    Скачивает только аудиодорожку по URL с помощью yt-dlp.
    Возвращает путь к временному аудиофайлу.
    """
    tmp_dir = tempfile.gettempdir()
    audio_id = str(uuid.uuid4())
    audio_path = os.path.join(tmp_dir, f"{audio_id}.m4a")

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": audio_path,
        "quiet": True,
        "no_warnings": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to download audio: {e}")

    if not os.path.exists(audio_path):
        raise HTTPException(status_code=500, detail="Audio file not created")

    return audio_path


def _transcribe_audio_file(audio_path: str) -> str:
    """
    Отправляет аудиофайл в Whisper API (OpenAI) и возвращает текст.
    Всегда старается удалить временный файл.
    """
    try:
        with open(audio_path, "rb") as f:
            # Самая надёжная модель для транскриба сейчас — whisper-1
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ASR failed: {e}")
    finally:
        # Пытаемся удалить временный файл, но не падаем, если не получилось
        try:
            if os.path.exists(audio_path):
                os.remove(audio_path)
        except Exception:
            pass

    text = getattr(transcript, "text", "") or ""
    if not text:
        raise HTTPException(status_code=500, detail="Empty transcript from ASR")

    return text


# ---------------------------
# Публичные эндпоинты
# ---------------------------

@router.post("/analyze_url")
async def analyze_video_url(payload: VideoURLRequest) -> dict[str, Any]:
    """
    БАЗОВЫЙ ЭНДПОИНТ.
    Принимает URL видео (YouTube, Vimeo и др.),
    скачивает ТОЛЬКО аудиодорожку, отправляет
