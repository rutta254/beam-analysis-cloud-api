from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware

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
    "http://localhost:3000",       # React / Next.js local dev
    "http://localhost:5173",       # Vite local dev
    "http://127.0.0.1:5173",
    "https://your-frontend-domain.vercel.app",  # Production frontend (replace with actual domain)
    "*"                            # Allow all origins (useful during early testing)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,             # Origins allowed to send requests
    allow_credentials=True,
    allow_methods=["*"],               # Allow all HTTP methods (GET, POST, OPTIONS, etc.)
    allow_headers=["*"],               # Allow all headers (Content-Type, Authorization, etc.)
)

# -------------------------------------------------------------
# Endpoints
# -------------------------------------------------------------
@app.get("/")
def read_root():
    return {"status": "healthy", "service": "Beam Analysis Cloud API"}

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