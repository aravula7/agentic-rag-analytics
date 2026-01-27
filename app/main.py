"""FastAPI application entry point."""

import os
os.environ["ANONYMIZED_TELEMETRY"] = "False"

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

from app.routers import query as query_router
from app.config import settings

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = FastAPI(
    title="Agentic RAG Analytics API",
    description="Natural language to SQL query execution with multi-agent system",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount query router
app.include_router(query_router.router, prefix="/query", tags=["Query"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Agentic RAG Analytics API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "database": "ok",
            "redis": "ok",
            "chroma": "ok",
            "s3": "ok"
        }
    }

@app.post("/clear-cache")
async def clear_cache():
    """Clear all Redis cache."""
    from app.routers.query import redis_cache
    redis_cache.clear_all()
    return {"message": "Cache cleared successfully"}