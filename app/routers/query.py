"""
Query router: LangGraph orchestration with Langfuse tracing.
"""

import logging
from typing import Dict, Any, Optional, cast

from fastapi import APIRouter, HTTPException
from langfuse.langchain import CallbackHandler

from app.config import settings
from app.models.schemas import QueryRequest, QueryResponse, RoutingDecision, QueryMetadata
from app.utils.redis_cache import RedisCache
from app.graph import workflow_graph, QueryState, build_initial_state

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize Redis cache (module-level)
if settings.ENABLE_CACHE:
    redis_cache = RedisCache(
        rest_url=settings.UPSTASH_REDIS_REST_URL,
        rest_token=settings.UPSTASH_REDIS_REST_TOKEN,
        ttl=settings.REDIS_CACHE_TTL,
    )
else:
    redis_cache = None


def _normalize_query(q: Optional[str]) -> str:
    """Normalize whitespace for consistent cache keys."""
    return " ".join((q or "").strip().split())


@router.post("/", response_model=QueryResponse)
def run_query(request: QueryRequest) -> QueryResponse:
    """
    Main query endpoint using LangGraph workflow.
    """
    normalized_query = _normalize_query(request.query)
    logger.info(f"Received query: {normalized_query[:120]}...")

    try:
        # Step 1: Check result cache
        if request.enable_cache and settings.ENABLE_CACHE and redis_cache is not None:
            cached_result = redis_cache.get_result(normalized_query)

            if isinstance(cached_result, dict):
                cached_query = _normalize_query(str(cached_result.get("query", "")))
                if cached_query == normalized_query:
                    logger.info("Returning cached result")
                    return QueryResponse(
                        success=True,
                        query=normalized_query,
                        routing_decision=RoutingDecision(**cached_result.get("routing_decision", {})),
                        generated_sql=cached_result.get("sql"),
                        s3_url=cached_result.get("s3_url"),
                        metadata=QueryMetadata(**cached_result.get("metadata", {})),
                        cache_hit=True,
                    )
                else:
                    logger.warning("Cache payload query mismatch; deleting and recomputing")
                    redis_cache.delete(normalized_query)

            elif cached_result is not None:
                logger.warning(f"Cache returned non-dict payload ({type(cached_result)}). Deleting.")
                redis_cache.delete(normalized_query)

        # Step 2: Initialize Langfuse handler for tracing
        langfuse_handler = CallbackHandler()
        
        # Step 3: Build initial state
        initial_state = build_initial_state(
            query=normalized_query,
            user_email=request.user_email,
            enable_cache=request.enable_cache,
        )

        # Step 4: Invoke LangGraph workflow with Langfuse tracing
        logger.info("Invoking LangGraph workflow...")
        final_state = cast(
            QueryState,
            workflow_graph.invoke(
                initial_state,
                config={"callbacks": [langfuse_handler]}
            ),
        )

        logger.info(f"Workflow completed. Success: {final_state.get('success')}")

        # Step 5: Check for workflow failure
        if not final_state.get("success"):
            error_msg = final_state.get("error_message", "Workflow failed")
            logger.error(f"Workflow error: {error_msg}")
            raise HTTPException(status_code=500, detail=error_msg)

        # Step 6: Extract results
        csv_url = final_state.get("csv_s3_url")
        if not csv_url:
            raise HTTPException(status_code=500, detail="No CSV URL generated")

        execution_metadata = final_state.get("execution_metadata")
        if not isinstance(execution_metadata, dict):
            raise HTTPException(status_code=500, detail="Missing execution metadata")
        metadata_payload: Dict[str, Any] = execution_metadata
        query_metadata = QueryMetadata(**metadata_payload)

        # Step 7: Cache result
        if request.enable_cache and settings.ENABLE_CACHE and redis_cache is not None:
            routing_decision = {
                "requires_sql": final_state.get("requires_sql", False),
                "requires_email": final_state.get("requires_email", False),
                "tables_involved": final_state.get("tables_involved", []),
                "query_complexity": final_state.get("query_complexity", "simple"),
                "reasoning": final_state.get("routing_reasoning", ""),
            }
            
            cache_payload = {
                "query": normalized_query,
                "routing_decision": routing_decision,
                "sql": final_state.get("generated_sql"),
                "s3_url": csv_url,
                "metadata": query_metadata.model_dump(),
            }
            redis_cache.set_result(normalized_query, cache_payload)

        # Step 8: Return response
        return QueryResponse(
            success=True,
            query=normalized_query,
            routing_decision=RoutingDecision(
                requires_sql=final_state.get("requires_sql", False),
                requires_email=final_state.get("requires_email", False),
                tables_involved=final_state.get("tables_involved", []),
                query_complexity=final_state.get("query_complexity", "simple"),
                reasoning=final_state.get("routing_reasoning", ""),
            ),
            generated_sql=final_state.get("generated_sql"),
            s3_url=csv_url,
            metadata=query_metadata,
            cache_hit=False,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unhandled error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
