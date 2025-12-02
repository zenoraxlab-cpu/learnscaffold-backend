from fastapi import APIRouter, UploadFile, File, HTTPException, status
from app.services.file_storage import save_upload_file
from app.utils.logger import logger

router = APIRouter()


@router.post("/")
async def upload_file(file: UploadFile = File(...)):
    logger.info("------------------------------------------------------------")
    logger.info("UPLOAD STARTED")
    logger.info(f"Filename: {file.filename}")
    logger.info(f"Content-Type: {file.content_type}")

    # Читаем несколько байтов для логов
    try:
        head = await file.read(64)
        logger.info(f"First 64 bytes: {head[:64]}")
        await file.seek(0)
    except Exception as e:
        logger.error(f"Failed to read file head: {e}", exc_info=True)

    # ----------------------------------------------------------
    # Проверяем пустое имя
    # ----------------------------------------------------------
    if not file.filename:
        logger.warning("Upload failed: empty filename")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty filename"
        )

    # ----------------------------------------------------------
    # Пробуем сохранить файл
    # ----------------------------------------------------------
    try:
        logger.info("Saving file...")
        file_id, saved_path = await save_upload_file(file)
        logger.info(f"File saved successfully: id={file_id}, path={saved_path}")

    except ValueError as e:
        logger.warning(f"Upload failed: invalid extension ({e})")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    except Exception as e:
        logger.error("UPLOAD FAILED WITH EXCEPTION", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error while saving file"
        )

    logger.info("UPLOAD COMPLETED OK")
    logger.info("------------------------------------------------------------")

    return {
        "status": "ok",
        "file_id": file_id,
        "filename": file.filename,
        "path": saved_path,
    }
