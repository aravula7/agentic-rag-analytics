"""Pydantic models for API schemas."""

from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


class QueryRequest(BaseModel):
    """Request model for query execution."""
    query: str
    user_email: Optional[EmailStr] = None
    enable_cache: bool = True


class RoutingDecision(BaseModel):
    """Router agent decision."""
    requires_sql: bool
    requires_email: bool
    tables_involved: List[str]
    query_complexity: str
    reasoning: str


class QueryMetadata(BaseModel):
    """Query execution metadata."""
    row_count: int
    column_count: int
    execution_time_seconds: float
    columns: List[str]
    csv_s3_key: str
    csv_s3_url: str
    sql_s3_key: str
    sql_s3_url: str
    timestamp: str


class QueryResponse(BaseModel):
    """Response model for query execution."""
    success: bool
    query: str
    routing_decision: Optional[RoutingDecision] = None
    generated_sql: Optional[str] = None
    s3_url: Optional[str] = None
    metadata: Optional[QueryMetadata] = None
    error: Optional[str] = None
    cache_hit: bool = False
    timestamp: str = datetime.utcnow().isoformat()


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    timestamp: str
    services: dict