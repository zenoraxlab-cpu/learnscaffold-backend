import os
import uuid
from app.config import UPLOAD_DIR

# Разрешённые расширения
ALLOWED_EXT = {".pdf", ".png", ".jpg", ".jpeg"}


def save_upload_file(file):
    filename = file.filename
    ext = os.path.splitext(filename)[1].lower()

    # Проверка расширения
    if ext not in ALLOWED_EXT:
        raise ValueError(f"Extension not allowed: {ext}")

    file_id = str(uuid.uuid4())[:8]
    saved_path = os.path.join(UPLOAD_DIR, f"{file_id}{ext}")

    print(f"[FILE] Saving upload: name={filename}, ext={ext}, id={file_id}")

    # Основная правка — читаем и пишем вручную
    try:
        content = file.file.read()

        if not content or len(content) == 0:
            raise RuntimeError("Uploaded file is empty or unreadable")

        with open(saved_path, "wb") as buffer:
            buffer.write(content)

    except Exception as e:
        print("🔥 ERROR INSIDE save_upload_file():", e)
        raise

    print(f"[FILE] Saved OK → {saved_path}")
    return file_id, saved_path
