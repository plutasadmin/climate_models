from fastapi.testclient import TestClient
from app.app import app

client = TestClient(app)

def test_health_check():
    """Test health check endpoint"""
    response = client.get("/model/filestore/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
