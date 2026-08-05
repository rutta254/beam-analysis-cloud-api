from typing import List, Optional
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field, field_validator

app = FastAPI(
    title="Beam Analysis Cloud API",
    version="1.0.0",
    description="Engineered API for simply supported beam analysis"
)


# ==========================================
# 1. PYDANTIC SCHEMAS (Inputs & Outputs)
# ==========================================

class PointLoad(BaseModel):
    magnitude: float = Field(..., description="Load magnitude in kN", gt=0)
    position: float = Field(..., description="Position from left support (m)", ge=0)


class UDL(BaseModel):
    magnitude: float = Field(..., description="Load intensity in kN/m", gt=0)
    start: float = Field(0.0, description="Start position from left support (m)", ge=0)
    end: float = Field(..., description="End position from left support (m)", gt=0)

    @field_validator("end")
    @classmethod
    def validate_end(cls, v: float, info) -> float:
        if "start" in info.data and v <= info.data["start"]:
            raise ValueError("UDL end position must be greater than start position")
        return v


class BeamAnalysisRequest(BaseModel):
    length: float = Field(..., description="Total span of beam in meters", gt=0)
    point_loads: Optional[List[PointLoad]] = Field(default_factory=list)
    udls: Optional[List[UDL]] = Field(default_factory=list)
    num_points: int = Field(100, description="Points to plot SFD/BMD", ge=10, le=500)

    @field_validator("point_loads")
    @classmethod
    def validate_point_loads(cls, loads: List[PointLoad], info) -> List[PointLoad]:
        if "length" in info.data:
            L = info.data["length"]
            for load in loads:
                if load.position > L:
                    raise ValueError(f"Point load at {load.position}m exceeds span of {L}m")
        return loads

    @field_validator("udls")
    @classmethod
    def validate_udls(cls, udls: List[UDL], info) -> List[UDL]:
        if "length" in info.data:
            L = info.data["length"]
            for udl in udls:
                if udl.end > L:
                    raise ValueError(f"UDL end at {udl.end}m exceeds span of {L}m")
        return udls


class ReactionForces(BaseModel):
    R_A: float = Field(..., description="Left reaction (kN)")
    R_B: float = Field(..., description="Right reaction (kN)")


class CriticalValues(BaseModel):
    max_bending_moment: float = Field(..., description="Max bending moment (kNm)")
    max_shear_force: float = Field(..., description="Max shear force (kN)")
    x_max_moment: float = Field(..., description="Location of max moment (m)")


class BeamAnalysisResponse(BaseModel):
    span: float
    reactions: ReactionForces
    critical_values: CriticalValues
    x_coords: List[float]
    shear_force: List[float]
    bending_moment: List[float]


# ==========================================
# 2. CALCULATION ENGINE LOGIC
# ==========================================

def calculate_beam(req: BeamAnalysisRequest) -> BeamAnalysisResponse:
    L = req.length
    
    # Static Equilibrium calculations: Sum of Moments about A = 0
    total_moment_A = 0.0
    total_load = 0.0

    for p in req.point_loads:
        total_moment_A += p.magnitude * p.position
        total_load += p.magnitude

    for u in req.udls:
        w_len = u.end - u.start
        w_total = u.magnitude * w_len
        centroid = u.start + (w_len / 2.0)
        total_moment_A += w_total * centroid
        total_load += w_total

    R_B = total_moment_A / L
    R_A = total_load - R_B

    # Discretize span for SFD and BMD diagram generation
    step = L / (req.num_points - 1)
    x_coords = [round(i * step, 3) for i in range(req.num_points)]
    
    shear_force = []
    bending_moment = []

    for x in x_coords:
        V = R_A
        M = R_A * x

        # Subtract point load effects
        for p in req.point_loads:
            if x > p.position:
                V -= p.magnitude
                M -= p.magnitude * (x - p.position)

        # Subtract UDL effects
        for u in req.udls:
            if x > u.start:
                eff_end = min(x, u.end)
                covered = eff_end - u.start
                w_segment = u.magnitude * covered
                V -= w_segment
                M -= w_segment * (x - (u.start + covered / 2.0))

        shear_force.append(round(V, 3))
        bending_moment.append(round(M, 3))

    # Find critical values
    abs_moments = [abs(m) for m in bending_moment]
    max_M = max(abs_moments)
    max_M_pos = x_coords[abs_moments.index(max_M)]
    max_V = max(abs(v) for v in shear_force)

    return BeamAnalysisResponse(
        span=L,
        reactions=ReactionForces(R_A=round(R_A, 3), R_B=round(R_B, 3)),
        critical_values=CriticalValues(
            max_bending_moment=round(max_M, 3),
            max_shear_force=round(max_V, 3),
            x_max_moment=max_M_pos
        ),
        x_coords=x_coords,
        shear_force=shear_force,
        bending_moment=bending_moment
    )


# ==========================================
# 3. API ENDPOINTS
# ==========================================

@app.get("/")
def root():
    return {"status": "online", "message": "Beam Analysis API is running."}


@app.post(
    "/analyze",
    response_model=BeamAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze Simply Supported Beam"
)
def analyze(request: BeamAnalysisRequest):
    try:
        return calculate_beam(request)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )