from fastapi.testclient import TestClient
from app.app import app

client = TestClient(app)

def test_root_endpoint():
    """Test if the root ("/") endpoint returns the correct welcome message."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {
        "message": "Welcome to the Risk Analyzer API. Go to /model/docs for Swagger UI."
    }

def test_docs_available():
    """Test if Swagger UI documentation is accessible."""
    response = client.get("/model/docs")
    assert response.status_code == 200

def test_redoc_available():
    """Test if ReDoc documentation is accessible."""
    response = client.get("/model/redoc")
    assert response.status_code == 200

def test_openapi_schema():
    """Test if OpenAPI JSON schema is accessible."""
    response = client.get("/model/openapi.json")
    assert response.status_code == 200

def test_routes_registered():
    """Ensure all expected routes are registered in the app."""
    routes = [route.path for route in app.routes]

    print("Registered routes:", routes)  # Debugging: Print actual registered routes

    assert "/model/filestore/health" in routes  # Health Check Route
    assert "/model/calculate_risk" in routes  # Risk Analysis Route
    assert "/model/calculate_risk/stream" in routes  # Risk Analysis SSE Route
    assert "/model/update_weather_data" in routes  # Weather Data Route (fixed)
