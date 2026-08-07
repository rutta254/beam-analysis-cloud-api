import os
from fastapi import FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from app.schemas import BeamAnalysisRequest, BeamAnalysisResponse
from app.calculations import calculate_beam, generate_sfd_bmd_plot

app = FastAPI(
    title="Beam Analysis Cloud API",
    description="Production-ready API for structural beam calculations and diagram generation.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# -------------------------------------------------------------
# 1. Flexible CORS Middleware Configuration
# -------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows Vercel, rutta.com, localhost, and any frontend client
    allow_credentials=True,
    allow_methods=["*"],  # Allows GET, POST, OPTIONS, etc.
    allow_headers=["*"],  # Allows all incoming headers
)

# -------------------------------------------------------------
# 2. Static File & Frontend Routing
# -------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

@app.get("/", response_class=FileResponse, include_in_schema=False)
def read_root():
    """Serves the main frontend dashboard."""
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"error": "Frontend entry point (index.html) not found in app/frontend."}
    )

# -------------------------------------------------------------
# 3. Dedicated Production Health Check
# -------------------------------------------------------------
@app.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="API Health & Readiness Check",
    tags=["System"]
)
def health_check():
    """Endpoint for Render or external uptime monitors."""
    return {
        "status": "healthy",
        "service": "Beam Analysis Cloud API",
        "version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "production")
    }

# -------------------------------------------------------------
# 4. API Endpoints
# -------------------------------------------------------------
@app.post(
    "/api/v1/analyze",
    response_model=BeamAnalysisResponse,
    summary="Analyze Beam Statics",
    tags=["Analysis"]
)
def analyze_beam_endpoint(payload: BeamAnalysisRequest):
    """Calculates reactions, maximum shear force, bending moments, and deflections."""
    try:
        return calculate_beam(payload)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Structural Computation Error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during beam calculation."
        )

@app.post(
    "/api/v1/analyze/plot",
    response_class=Response,
    summary="Generate SFD/BMD Plot Image",
    tags=["Analysis"]
)
def analyze_beam_plot_endpoint(payload: BeamAnalysisRequest):
    """Generates a 3-panel PNG plot (SFD, BMD, Deflection)."""
    try:
        res = calculate_beam(payload)
        image_bytes = generate_sfd_bmd_plot(res)
        return Response(content=image_bytes, media_type="image/png")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Plot Generation Error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate beam analysis plot."
        )