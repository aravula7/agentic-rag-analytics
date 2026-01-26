"""FastAPI application entry point."""

import os
os.environ["ANONYMIZED_TELEMETRY"] = "False"

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.models.schemas import HealthResponse
from app.routers import query_router

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Agentic RAG Analytics API",
    description="Multi-agent SQL query system with LangGraph",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(query_router)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint.
    
    Returns:
        HealthResponse with service status
    """
    services = {
        "database": "ok",  # TODO: Add actual health checks
        "redis": "ok",
        "chroma": "ok",
        "s3": "ok"
    }
    
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        services=services
    )


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Agentic RAG Analytics API",
        "version": "1.0.0",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True
    )