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

app.include_router(upload.router, prefix="/upload", tags=["Upload"])
app.include_router(analyze.router, tags=["Analyze"])
app.include_router(generate.router, prefix="/generate", tags=["Generate"])
app.include_router(video.router, prefix="/video", tags=["Video"])
app.include_router(health.router, tags=["Health"])
app.include_router(studyplan.router, prefix="/studyplan", tags=["StudyPlan"])

# PDF GENERATION (POST /plan/pdf)
app.include_router(plan_pdf.router, prefix="/plan", tags=["Plan"])

# PDF DOWNLOAD (GET /plan/pdf/{task_id})
app.include_router(plan_download.router, prefix="/plan", tags=["Download"])

# ---------------------------------------------------------
# ROOT
# ---------------------------------------------------------
@app.get("/")
def root():
    return {"status": "ok", "service": "LearnScaffold backend"}
