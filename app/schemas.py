from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


# ==========================================
# Load Inputs
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


# ==========================================
# Main Request Model
# ==========================================

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


# ==========================================
# Output Models
# ==========================================

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