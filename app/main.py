import os
from enum import Enum
from typing import Optional
from fastapi import FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from app.schemas import BeamAnalysisRequest, BeamAnalysisResponse
from app.calculations import calculate_beam, generate_sfd_bmd_plot
from app.design_codes import design_rc_beam_flexure, DesignCode

app = FastAPI(
    title="Beam Analysis Cloud API",
    description="Production-ready API for structural beam calculations, design verification, and diagram generation.",
    version="2.0.0",
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
        "version": "2.0.0",
        "environment": os.getenv("ENVIRONMENT", "production")
    }

# -------------------------------------------------------------
# 4. Statics & Plotting Endpoints
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

# -------------------------------------------------------------
# 5. Multi-Code Structural Element Design Endpoint
# -------------------------------------------------------------
class DesignRequest(BaseModel):
    element_type: str = Field(default="beam", description="Element type: beam, slab")
    design_code: DesignCode = Field(default=DesignCode.EUROCODE2, description="EN1992, BS8110, or ACI318")
    length_m: float = Field(default=6.0, gt=0, description="Span length in meters")
    dead_load_kN_m: float = Field(default=12.0, ge=0, description="Characteristic dead load Gk (kN/m)")
    live_load_kN_m: float = Field(default=8.0, ge=0, description="Characteristic live load Qk (kN/m)")
    b_mm: float = Field(default=250.0, gt=0, description="Section width in mm")
    d_mm: float = Field(default=450.0, gt=0, description="Effective depth in mm")
    f_ck_MPa: float = Field(default=30.0, gt=0, description="Concrete compressive strength (f_ck or f_c') in MPa")
    f_yk_MPa: float = Field(default=500.0, gt=0, description="Steel yield strength (f_yk or f_y) in MPa")

@app.post(
    "/api/v1/design/element",
    summary="Design Structural Element",
    tags=["Design Engine"]
)
def design_element_endpoint(payload: DesignRequest):
    """Performs factored load combination, statics analysis, and cross-section reinforcement design."""
    try:
        # 1. Factored load combinations based on selected design standard
        if payload.design_code == DesignCode.EUROCODE2:
            w_u = (1.35 * payload.dead_load_kN_m) + (1.50 * payload.live_load_kN_m)
        elif payload.design_code == DesignCode.BS8110:
            w_u = (1.40 * payload.dead_load_kN_m) + (1.60 * payload.live_load_kN_m)
        elif payload.design_code == DesignCode.ACI318:
            w_u = (1.20 * payload.dead_load_kN_m) + (1.60 * payload.live_load_kN_m)
        else:
            w_u = (1.35 * payload.dead_load_kN_m) + (1.50 * payload.live_load_kN_m)

        # 2. Beam Statics (Simply Supported UDL case)
        L = payload.length_m
        M_u = (w_u * (L ** 2)) / 8.0  # Max bending moment in kN·m
        V_u = (w_u * L) / 2.0         # Max shear force in kN

        # 3. Calculate reinforcement requirements
        design_res = design_rc_beam_flexure(
            M_u=M_u,
            b=payload.b_mm,
            d=payload.d_mm,
            f_ck=payload.f_ck_MPa,
            f_yk=payload.f_yk_MPa,
            code=payload.design_code
        )

        return {
            "element_type": payload.element_type,
            "design_code": payload.design_code,
            "factored_load_kN_m": round(w_u, 2),
            "M_u_kNm": round(M_u, 2),
            "V_u_kN": round(V_u, 2),
            "design_results": design_res
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Design calculation error: {str(e)}"
        )