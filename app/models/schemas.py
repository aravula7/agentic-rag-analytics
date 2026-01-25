"""Pydantic schemas for API."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class QueryRequest(BaseModel):
    """Request model for query endpoint."""
    
    query: str = Field(..., description="Natural language query", min_length=1)
    user_email: Optional[str] = Field(None, description="Email for results delivery")
    enable_cache: bool = Field(True, description="Use cached results if available")


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
    s3_key: str


class QueryResponse(BaseModel):
    """Response model for query endpoint."""
    
    success: bool
    query: str
    routing_decision: Optional[RoutingDecision] = None
    generated_sql: Optional[str] = None
    s3_url: Optional[str] = None
    metadata: Optional[QueryMetadata] = None
    error: Optional[str] = None
    cache_hit: bool = False
    timestamp: datetime = Field(default_factory=datetime.now)


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str
    version: str
    timestamp: datetime = Field(default_factory=datetime.now)
    services: Dict[str, str] = Field(default_factory=dict)