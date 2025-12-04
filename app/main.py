from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import (
    upload,
    analyze,
    generate,
    video,
    health,
    studyplan,
    plan_pdf,
)

from app.utils.logger import logger
from app.utils.error_handler import log_exceptions


# -------------------------------------------------------------------
# FastAPI application
# -------------------------------------------------------------------
app = FastAPI(
    debug=True,
    title="AI StudyPlan Generator API",
    version="0.1.0",
)

# -------------------------------------------------------------------
# Global error logging middleware
# -------------------------------------------------------------------
app.middleware("http")(log_exceptions)

# -------------------------------------------------------------------
# CORS settings
# -------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],     # можно ограничить позже
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.info("Backend started")


# -------------------------------------------------------------------
# Routers
# -------------------------------------------------------------------
app.include_router(upload.router,    prefix="/upload",   tags=["Upload"])
app.include_router(analyze.router,   prefix="/analyze",  tags=["Analyze"])
app.include_router(generate.router,  prefix="/generate", tags=["Generate"])
app.include_router(video.router,     prefix="/video",    tags=["Video"])
app.include_router(health.router,    prefix="/health",   tags=["Health"])
app.include_router(studyplan.router, prefix="/studyplan",tags=["StudyPlan"])
app.include_router(plan_pdf.router,  prefix="/plan",     tags=["Plan"])


# -------------------------------------------------------------------
# Root endpoint
# -------------------------------------------------------------------
@app.get("/")
async def root():
    return {
        "status": "ok",
        "message": "AI StudyPlan Generator API is running",
        "version": "0.1.0",
    }
