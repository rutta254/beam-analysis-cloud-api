import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_root():
    """Tests the root endpoint (serves the frontend dashboard via FileResponse)."""
    response = client.get("/")
    assert response.status_code == 200
    # The root endpoint serves index.html, so we check for text/html content type
    assert "text/html" in response.headers.get("content-type", "")

def test_health_check():
    """Tests the dedicated system health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "Beam Analysis Cloud API"

def test_beam_analysis_endpoint():
    """Tests the beam statics analysis endpoint, validating nested critical values."""
    payload = {
        "length": 6.0,
        "point_load": 10.0,
        "point_load_location": 3.0,
        "udl": 5.0
    }
    response = client.post("/api/v1/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    # Verify presence of nested critical structural results
    assert "critical_values" in data
    assert "max_bending_moment" in data["critical_values"]
    assert "max_shear_force" in data["critical_values"]
    assert "max_deflection_mm" in data["critical_values"]

def test_design_element_endpoint():
    """Tests the multi-code structural element design engine endpoint."""
    payload = {
        "element_type": "beam",
        "design_code": "EN1992",  # Matches the DesignCode enum value expected by the API
        "length_m": 6.0,
        "dead_load_kN_m": 12.0,
        "live_load_kN_m": 8.0,
        "b_mm": 250.0,
        "d_mm": 450.0,
        "f_ck_MPa": 30.0,
        "f_yk_MPa": 500.0
    }
    response = client.post("/api/v1/design/element", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert data["design_code"] == "EN1992"
    assert "factored_load_kN_m" in data
    assert "M_u_kNm" in data
    assert "V_u_kN" in data
    assert "design_results" in data