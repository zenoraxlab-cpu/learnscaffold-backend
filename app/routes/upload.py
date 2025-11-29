from fastapi import APIRouter, UploadFile, File, HTTPException, status
from app.services.file_storage import save_upload_file
from app.utils.logger import logger

router = APIRouter()


@router.post("/")
async def upload_file(file: UploadFile = File(...)):
    logger.info(f"Upload request received: filename={file.filename}, content_type={file.content_type}")

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty filename"
        )

    try:
        file_id, saved_path = save_upload_file(file)
    except ValueError as e:
        logger.warning(f"Upload failed (bad extension): {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Upload failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error while saving file"
        )

    return {
        "status": "ok",
        "file_id": file_id,
        "filename": file.filename,
        "path": saved_path,
    }
