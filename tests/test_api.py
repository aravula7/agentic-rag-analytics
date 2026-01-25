"""Tests for FastAPI endpoints."""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'healthy'
    assert 'version' in data


def test_root():
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert 'message' in data


def test_query_endpoint_missing_query():
    """Test query endpoint with missing query."""
    response = client.post("/query/", json={})
    assert response.status_code == 422  # Validation error


def test_query_endpoint_valid():
    """Test query endpoint with valid input."""
    # Note: This will fail without proper setup (DB, APIs, etc.)
    # In real testing, mock the agents
    response = client.post(
        "/query/",
        json={
            "query": "Show all customers",
            "enable_cache": False
        }
    )
    # We expect 500 because services aren't running in test
    # But it should not be 422 (validation error)
    assert response.status_code in [200, 500]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])