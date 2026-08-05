from fastapi import FastAPI
from pydantic import BaseModel
from app.calculations import analyze_simply_supported_beam

app = FastAPI(
    title="Cloud-Native Structural Beam Analysis API",
    description="API for validating beam calculations under point loads.",
    version="1.0.0"
)

# Input validation schema
class BeamAnalysisRequest(BaseModel):
    length: float       # Length in meters
    point_load: float   # Load in kN

@app.get("/")
def read_root():
    return {"message": "Beam Analysis API is running locally!"}

@app.post("/analyze")
def analyze_beam(data: BeamAnalysisRequest):
    results = analyze_simply_supported_beam(data.length, data.point_load)
    return {
        "success": True,
        "data": results
    }