from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class PointLoad(BaseModel):
    magnitude: float = Field(..., description="Load magnitude in kN (downward positive)", gt=0)
    position: float = Field(..., description="Position from left end (m)", ge=0)


class PointMoment(BaseModel):
    magnitude: float = Field(..., description="Moment in kNm (Clockwise positive)")
    position: float = Field(..., description="Position from left end (m)", ge=0)


class UDL(BaseModel):
    magnitude: float = Field(..., description="Uniform load intensity in kN/m", ge=0)
    start: float = Field(0.0, description="Start position from left end (m)", ge=0)
    end: float = Field(..., description="End position from left end (m)", gt=0)

    @field_validator("end")
    @classmethod
    def validate_end(cls, v: float, info) -> float:
        if "start" in info.data and v <= info.data["start"]:
            raise ValueError("UDL end position must be greater than start position")
        return v


class VaryingLoad(BaseModel):
    w1: float = Field(..., description="Start load intensity in kN/m", ge=0)
    w2: float = Field(..., description="End load intensity in kN/m", ge=0)
    start: float = Field(0.0, description="Start position from left end (m)", ge=0)
    end: float = Field(..., description="End position from left end (m)", gt=0)

    @field_validator("end")
    @classmethod
    def validate_end(cls, v: float, info) -> float:
        if "start" in info.data and v <= info.data["start"]:
            raise ValueError("Varying load end position must be greater than start position")
        return v


class Supports(BaseModel):
    support_a: float = Field(0.0, description="Position of left support R_A (m)", ge=0)
    support_b: float = Field(..., description="Position of right support R_B (m)", gt=0)

    @field_validator("support_b")
    @classmethod
    def validate_supports(cls, v: float, info) -> float:
        if "support_a" in info.data and v <= info.data["support_a"]:
            raise ValueError("Support B position must be greater than Support A position")
        return v


class BeamAnalysisRequest(BaseModel):
    length: float = Field(..., description="Total length of beam in meters", gt=0)
    supports: Optional[Supports] = None  # Defaults to simple supports at ends if None in calculations
    E: Optional[float] = Field(210e6, description="Modulus of Elasticity in kPa (default: 210 GPa)", gt=0)
    I: Optional[float] = Field(0.0001, description="Second Moment of Area in m^4", gt=0)
    point_loads: Optional[List[PointLoad]] = Field(default_factory=list)
    udls: Optional[List[UDL]] = Field(default_factory=list)  # Matches JS frontend payload key
    point_moments: Optional[List[PointMoment]] = Field(default_factory=list)
    varying_loads: Optional[List[VaryingLoad]] = Field(default_factory=list)
    num_points: int = Field(200, description="Points to plot SFD/BMD/Deflection", ge=20, le=1000)

    @field_validator("point_loads")
    @classmethod
    def validate_point_loads(cls, loads: List[PointLoad], info) -> List[PointLoad]:
        if "length" in info.data and loads:
            L = info.data["length"]
            for load in loads:
                if load.position > L:
                    raise ValueError(f"Point load at {load.position}m exceeds beam length of {L}m")
        return loads

    @field_validator("udls")
    @classmethod
    def validate_udls(cls, loads: List[UDL], info) -> List[UDL]:
        if "length" in info.data and loads:
            L = info.data["length"]
            for load in loads:
                if load.end > L:
                    raise ValueError(f"UDL end position at {load.end}m exceeds beam length of {L}m")
        return loads


class ReactionForces(BaseModel):
    R_A: float = Field(..., description="Left reaction (kN)")
    R_B: float = Field(..., description="Right reaction (kN)")


class CriticalValues(BaseModel):
    max_bending_moment: float = Field(..., description="Max bending moment magnitude (kNm)")
    max_shear_force: float = Field(..., description="Max shear force magnitude (kN)")
    max_deflection_mm: float = Field(..., description="Max deflection magnitude in mm")
    x_max_moment: float = Field(..., description="Location of max moment (m)")
    x_max_deflection: float = Field(..., description="Location of max deflection (m)")


class BeamAnalysisResponse(BaseModel):
    span: float
    reactions: ReactionForces
    critical_values: CriticalValues
    x_coords: List[float]
    shear_force: List[float]
    bending_moment: List[float]
    deflection_mm: List[float]