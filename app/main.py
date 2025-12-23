from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import upload
from app.routes import analyze
from app.routes import generate
from app.routes import video
from app.routes import health
from app.routes import studyplan
from app.routes import plan_pdf
from app.routes import plan_download



app = FastAPI(
    title="LearnScaffold Backend",
    description="API for document analysis and study plan generation",
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# ROUTERS
# ---------------------------------------------------------

# Все корректно:
app.include_router(upload.router, prefix="/upload", tags=["Upload"])

# Анализ — ПРАВИЛЬНО:
app.include_router(analyze.router, tags=["Analyze"])

# Генерация
app.include_router(generate.router, prefix="/generate", tags=["Generate"])

# Видео
app.include_router(video.router, prefix="/video", tags=["Video"])

# Health — БЕЗ prefix! 
# И В ФАЙЛЕ health.py ОБЯЗАТЕЛЬНО ДОЛЖНО БЫТЬ @router.get("/healthz")
app.include_router(health.router, tags=["Health"])

# Старые эндпоинты
app.include_router(studyplan.router, prefix="/studyplan", tags=["StudyPlan"])

# PDF
app.include_router(plan_pdf.router, prefix="/plan", tags=["Plan"])

# Download
app.include_router(plan_download.router, prefix="/plan")



# ---------------------------------------------------------
# ROOT
# ---------------------------------------------------------
@app.get("/")
def root():
    return {"status": "ok", "service": "LearnScaffold backend"}
