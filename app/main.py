from fastapi import FastAPI, HTTPException, status
from fastapi.responses import Response

from app.schemas import BeamAnalysisRequest, BeamAnalysisResponse
from app.calculations import calculate_beam, generate_sfd_bmd_plot

app = FastAPI(
    title="Beam Analysis Cloud API",
    version="1.0.0",
    description="Engineered API for simply supported beam analysis"
)


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


@app.post(
    "/analyze/plot",
    response_class=Response,
    status_code=status.HTTP_200_OK,
    summary="Generate SFD and BMD Plots as PNG Image"
)
def analyze_and_plot(request: BeamAnalysisRequest):
    try:
        res = calculate_beam(request)
        img_bytes = generate_sfd_bmd_plot(res)
        return Response(content=img_bytes, media_type="image/png")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )