import os
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.schemas import BeamAnalysisRequest, BeamAnalysisResponse
from app.calculations import calculate_beam, generate_sfd_bmd_plot

app = FastAPI(
    title="Beam Analysis Cloud API",
    description="Structural analysis API for simply supported and overhanging beams.",
    version="1.0.0"
)

# -------------------------------------------------------------
# CORS Middleware Configuration
# -------------------------------------------------------------
origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------
# Static Files & UI Serving
# -------------------------------------------------------------
# Resolves path to app/frontend regardless of working directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

@app.get("/", response_class=FileResponse)
def read_root():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"status": "healthy", "service": "Beam Analysis Cloud API", "note": "index.html not found in app/frontend"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "Beam Analysis Cloud API"}

# -------------------------------------------------------------
# API Endpoints
# -------------------------------------------------------------
@app.post("/api/v1/analyze", response_model=BeamAnalysisResponse)
def analyze_beam_endpoint(payload: BeamAnalysisRequest):
    try:
        return calculate_beam(payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/analyze/plot", response_class=Response)
def analyze_beam_plot_endpoint(payload: BeamAnalysisRequest):
    try:
        res = calculate_beam(payload)
        image_bytes = generate_sfd_bmd_plot(res)
        return Response(content=image_bytes, media_type="image/png")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))