import pytest
from fastapi.testclient import TestClient
from app.app import app  # Import your FastAPI app

@pytest.fixture
def client():
    return TestClient(app)


