import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Cloud-Native Structural Beam Analysis API is running!"}

def test_beam_analysis_endpoint():
    payload = {
        "length": 6.0,
        "point_load": 10.0,
        "point_load_location": 3.0,
        "udl": 5.0
    }
    response = client.post("/api/v1/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "max_bending_moment" in data
    assert "max_shear_force" in data

def test_design_element_endpoint():
    payload = {
        "length": 6.0,
        "dead_load": 10.0,
        "live_load": 15.0,
        "width": 300,
        "depth": 500,
        "f_ck": 30,
        "f_yk": 500,
        "code_standard": "BS_EN_1992"
    }
    response = client.post("/api/v1/design/element", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["design_code"] == "BS_EN_1992"
    assert "required_rebar_area_mm2" in data