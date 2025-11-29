import os
import uuid
from typing import Tuple
from fastapi import UploadFile
from app.config import UPLOAD_DIR, ALLOWED_EXTENSIONS
from app.utils.logger import logger


def get_extension(filename: str) -> str:
    return os.path.splitext(filename)[1].lower()


def is_allowed_extension(filename: str) -> bool:
    ext = get_extension(filename)
    return ext in ALLOWED_EXTENSIONS


def save_upload_file(file: UploadFile) -> Tuple[str, str]:
    """
    Сохраняет загруженный файл в UPLOAD_DIR.
    Возвращает (file_id, saved_path).
    """
    ext = get_extension(file.filename)
    if not is_allowed_extension(file.filename):
        raise ValueError(f"File extension not allowed: {ext}")

    file_id = str(uuid.uuid4())
    safe_name = f"{file_id}{ext}"
    save_path = os.path.join(UPLOAD_DIR, safe_name)

    logger.info(f"Saving file: original={file.filename}, id={file_id}, path={save_path}")

    with open(save_path, "wb") as buffer:
        content = file.file.read()
        buffer.write(content)

    logger.info(f"File saved successfully: {save_path}")

    return file_id, save_path
