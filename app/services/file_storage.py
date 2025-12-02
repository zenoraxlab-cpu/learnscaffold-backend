import os
import uuid
from fastapi import UploadFile
from app.config import UPLOAD_DIR

# Разрешённые расширения
ALLOWED_EXT = {".pdf", ".png", ".jpg", ".jpeg"}


async def save_upload_file(file: UploadFile):
    """
    Асинхронно сохраняет файл.
    Совместим с Uvicorn, Render, UploadFile.
    """
    filename = file.filename
    ext = os.path.splitext(filename)[1].lower()

    if ext not in ALLOWED_EXT:
        raise ValueError(f"Extension not allowed: {ext}")

    file_id = str(uuid.uuid4())[:8]
    saved_path = os.path.join(UPLOAD_DIR, f"{file_id}{ext}")

    # Создаём директорию, если её нет
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    try:
        # Асинхронно читаем файл
        content = await file.read()

        if not content or len(content) == 0:
            raise RuntimeError("Uploaded file is empty or unreadable")

        # Пишем на диск
        with open(saved_path, "wb") as buffer:
            buffer.write(content)

    except Exception as e:
        print("🔥 ERROR IN save_upload_file:", e)
        raise

    print(f"[FILE] Saved OK → {saved_path}")
    return file_id, saved_path
