"""Tests for the health check endpoint."""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """Test cases for the /health endpoint."""

    @pytest.fixture
    def test_client(self):
        """Create test client."""
        with patch.dict('os.environ', {
            'ENABLE_CACHE': 'false',
            'OPENAI_API_KEY': 'test-key',
            'ANTHROPIC_API_KEY': 'test-key',
        }):
            from app.main import app
            client = TestClient(app)
            yield client

    def test_health_check_returns_200(self, test_client):
        """Test that health check returns 200 OK."""
        response = test_client.get("/health")

        assert response.status_code == 200

    def test_health_check_returns_status(self, test_client):
        """Test that health check returns status field."""
        response = test_client.get("/health")
        data = response.json()

        assert "status" in data
        assert data["status"] == "healthy"

    def test_health_check_returns_version(self, test_client):
        """Test that health check returns version."""
        response = test_client.get("/health")
        data = response.json()

        assert "version" in data
        assert data["version"] == "1.0.0"

    def test_health_check_returns_timestamp(self, test_client):
        """Test that health check returns timestamp."""
        response = test_client.get("/health")
        data = response.json()

        assert "timestamp" in data
        # Timestamp should be ISO format
        assert "T" in data["timestamp"]


class TestRootEndpoint:
    """Test cases for the root endpoint."""

    @pytest.fixture
    def test_client(self):
        """Create test client."""
        with patch.dict('os.environ', {
            'ENABLE_CACHE': 'false',
            'OPENAI_API_KEY': 'test-key',
            'ANTHROPIC_API_KEY': 'test-key',
        }):
            from app.main import app
            client = TestClient(app)
            yield client

    def test_root_returns_200(self, test_client):
        """Test that root endpoint returns 200 OK."""
        response = test_client.get("/")

        assert response.status_code == 200

    def test_root_returns_message(self, test_client):
        """Test that root endpoint returns welcome message."""
        response = test_client.get("/")
        data = response.json()

        assert "message" in data
        assert "Agentic RAG Analytics API" in data["message"]

    def test_root_returns_version(self, test_client):
        """Test that root endpoint returns version."""
        response = test_client.get("/")
        data = response.json()

        assert "version" in data
        assert data["version"] == "1.0.0"

    def test_root_returns_docs_link(self, test_client):
        """Test that root endpoint returns docs link."""
        response = test_client.get("/")
        data = response.json()

        assert "docs" in data
        assert data["docs"] == "/docs"


class TestDocsEndpoint:
    """Test cases for the OpenAPI docs endpoint."""

    @pytest.fixture
    def test_client(self):
        """Create test client."""
        with patch.dict('os.environ', {
            'ENABLE_CACHE': 'false',
            'OPENAI_API_KEY': 'test-key',
            'ANTHROPIC_API_KEY': 'test-key',
        }):
            from app.main import app
            client = TestClient(app)
            yield client

    def test_docs_endpoint_accessible(self, test_client):
        """Test that /docs endpoint is accessible."""
        response = test_client.get("/docs")

        # FastAPI serves HTML for /docs
        assert response.status_code == 200

    def test_openapi_json_accessible(self, test_client):
        """Test that OpenAPI JSON is accessible."""
        response = test_client.get("/openapi.json")

        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "paths" in data

    def test_openapi_includes_query_endpoint(self, test_client):
        """Test that OpenAPI spec includes query endpoint."""
        response = test_client.get("/openapi.json")
        data = response.json()

        assert "/query/" in data["paths"]

    def test_openapi_includes_health_endpoint(self, test_client):
        """Test that OpenAPI spec includes health endpoint."""
        response = test_client.get("/openapi.json")
        data = response.json()

        assert "/health" in data["paths"]


class TestCORSMiddleware:
    """Test cases for CORS middleware."""

    @pytest.fixture
    def test_client(self):
        """Create test client."""
        with patch.dict('os.environ', {
            'ENABLE_CACHE': 'false',
            'OPENAI_API_KEY': 'test-key',
            'ANTHROPIC_API_KEY': 'test-key',
        }):
            from app.main import app
            client = TestClient(app)
            yield client

    def test_cors_allows_all_origins(self, test_client):
        """Test that CORS allows all origins."""
        response = test_client.options(
            "/health",
            headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "GET"
            }
        )

        # With allow_credentials=True, Starlette echoes the request origin
        # instead of returning the literal '*'
        origin = response.headers.get("access-control-allow-origin")
        assert origin in ("*", "https://example.com")

    def test_cors_allows_all_methods(self, test_client):
        """Test that CORS allows all methods."""
        response = test_client.options(
            "/query/",
            headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "POST"
            }
        )

        # Should allow POST method
        assert response.status_code in [200, 204]
