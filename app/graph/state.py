"""
State definition for the LangGraph workflow.
"""

from typing import TypedDict, Optional, List, Dict, Any


class QueryState(TypedDict):
    """State passed between nodes in the graph."""
    
    # Input
    query: str
    user_email: Optional[str]
    enable_cache: bool
    
    # Routing decision
    requires_sql: bool
    requires_email: bool
    tables_involved: List[str]
    query_complexity: str
    routing_reasoning: str
    
    # SQL generation
    generated_sql: Optional[str]
    sql_generation_error: Optional[str]
    sql_retry_count: int
    
    # Execution
    csv_s3_url: Optional[str]
    sql_s3_url: Optional[str]
    execution_metadata: Optional[Dict[str, Any]]
    execution_error: Optional[str]
    execution_retry_count: int
    
    # Final result
    success: bool
    error_message: Optional[str]
    cache_hit: bool


def build_initial_state(
    *,
    query: str,
    user_email: Optional[str],
    enable_cache: bool
) -> QueryState:
    """Create a fully-initialized state payload for graph executions."""

    return QueryState(
        query=query,
        user_email=user_email,
        enable_cache=enable_cache,
        requires_sql=True,
        requires_email=False,
        tables_involved=[],
        query_complexity="simple",
        routing_reasoning="",
        generated_sql=None,
        sql_generation_error=None,
        sql_retry_count=0,
        csv_s3_url=None,
        sql_s3_url=None,
        execution_metadata=None,
        execution_error=None,
        execution_retry_count=0,
        success=False,
        error_message=None,
        cache_hit=False,
    )
