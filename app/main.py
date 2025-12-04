from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import upload
from app.routes import analyze
from app.routes import generate
from app.routes import video
from app.routes import health
from app.routes import studyplan
from app.routes import plan_pdf

from app.config import ALLOWED_ORIGINS


app = FastAPI(
    title="LearnScaffold Backend",
    description="API for document analysis and study plan generation",
    version="1.0.0",
)


# ---------------------------------------------------------
# CORS
# ---------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# ROUTERS
# ---------------------------------------------------------

# File upload
app.include_router(upload.router, prefix="/upload", tags=["Upload"])

# Document analysis
app.include_router(analyze.router, prefix="/analyze", tags=["Analyze"])

# Study plan generation (FIX — prefix must be empty so /generate/ works!)
app.include_router(generate.router, prefix="", tags=["Generate"])

# Video analysis (video-to-text, video plans)
app.include_router(video.router, prefix="/video", tags=["Video"])

# Health check
app.include_router(health.router, prefix="/health", tags=["Health"])

# StudyPlan older endpoints (legacy)
app.include_router(studyplan.router, prefix="/studyplan", tags=["StudyPlan"])

# PDF export
app.include_router(plan_pdf.router, prefix="/plan", tags=["Plan"])


# ---------------------------------------------------------
# ROOT ENDPOINT
# ---------------------------------------------------------
@app.get("/")
def root():
    return {"status": "ok", "service": "LearnScaffold backend"}
