import traceback
from fastapi import Request
from fastapi.responses import JSONResponse

async def log_exceptions(request: Request, call_next):
    try:
        return await call_next(request)

    except Exception as e:
        # ↓↓↓ Это критично — именно print попадает в Render Logs ↓↓↓
        print("=== GLOBAL ERROR ===")
        print(f"Path: {request.url.path}")
        print(traceback.format_exc())

        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )
