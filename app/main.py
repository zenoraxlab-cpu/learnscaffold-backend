from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import upload, analyze, generate, video, health, studyplan, plan_pdf
from app.utils.logger import logger
from app.utils.error_handler import log_exceptions

app = FastAPI(
    title="AI StudyPlan Generator API",
    version="0.1.0",
)

# ---------------------------------------------------------------
# Middleware: логирование ошибок всех запросов
# ---------------------------------------------------------------
app.middleware("http")(log_exceptions)

# ---------------------------------------------------------------
# CORS (разрешим фронтенду подключаться)
# ---------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # позже можно ограничить доменом
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------
# Лог запуска
# ---------------------------------------------------------------
logger.info("Backend started")

# ---------------------------------------------------------------
# Подключаем роуты
# ---------------------------------------------------------------
app.include_router(upload.router, prefix="/upload", tags=["Upload"])
app.include_router(analyze.router, prefix="/analyze", tags=["Analyze"])
app.include_router(generate.router, prefix="/generate", tags=["Generate"])
app.include_router(video.router, prefix="/video", tags=["Video"])
app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(studyplan.router, prefix="/studyplan", tags=["StudyPlan"])
app.include_router(plan_pdf.router, prefix="/plan", tags=["Plan"])
