"""
Query Router: orchestrates RouterAgent -> SQLAgent -> ExecutorAgent -> EmailAgent
Adds safe caching behavior (robust against Redis returning str/None/etc).
"""

import logging
from typing import Dict, Any, Optional, cast

from fastapi import APIRouter, HTTPException, BackgroundTasks

from app.config import settings
from app.models.schemas import QueryRequest, QueryResponse, RoutingDecision, QueryMetadata

from app.utils.redis_cache import RedisCache

from agents.router_agent import RouterAgent
from agents.sql_agent import SQLAgent, SchemaRetriever
from agents.executor_agent import ExecutorAgent, S3Uploader
from agents.email_agent import EmailAgent


logger = logging.getLogger(__name__)
router = APIRouter()

# ---- Initialize shared components (module-level singletons) ----
if settings.ENABLE_CACHE:
    redis_cache = RedisCache(
        rest_url=settings.UPSTASH_REDIS_REST_URL,
        rest_token=settings.UPSTASH_REDIS_REST_TOKEN,
        ttl=settings.REDIS_CACHE_TTL,
    )
else:
    redis_cache = None

router_agent = RouterAgent(
    api_key=settings.OPENAI_API_KEY,
    model=settings.OPENAI_GENERAL_MODEL,
)

schema_retriever = SchemaRetriever(
    collection_name=settings.CHROMA_COLLECTION,
    persist_directory=settings.CHROMA_PERSIST_DIR,
)

sql_agent = SQLAgent(
    anthropic_api_key=settings.ANTHROPIC_API_KEY,
    schema_retriever=schema_retriever,
    model=settings.ANTHROPIC_SQL_MODEL,
    max_tokens=settings.ANTHROPIC_MAX_TOKENS,
)

s3_uploader = S3Uploader(
    endpoint_url=settings.S3_ENDPOINT_URL,
    bucket_name=settings.S3_BUCKET_NAME,
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region=settings.AWS_REGION,
)

executor_agent = ExecutorAgent(
    db_host=settings.DB_HOST,
    db_port=settings.DB_PORT,
    db_name=settings.DB_NAME,
    db_user=settings.DB_USER,
    db_password=settings.DB_PASSWORD,
    s3_uploader=s3_uploader,
    query_timeout=30,
)

email_agent = EmailAgent(
    smtp_host=settings.SMTP_HOST,
    smtp_port=settings.SMTP_PORT,
    smtp_user=settings.SMTP_USER,
    smtp_password=settings.SMTP_PASSWORD,
)


def _normalize_query(q: Optional[str]) -> str:
    # Normalize whitespace so minor formatting doesn't create different cache keys.
    # (Also helps prevent “same result for different inputs” confusion)
    return " ".join((q or "").strip().split())


@router.post("/", response_model=QueryResponse)
def run_query(request: QueryRequest, background_tasks: BackgroundTasks) -> QueryResponse:
    """
    Main query endpoint.
    """
    normalized_query = _normalize_query(request.query)
    logger.info(f"Received query: {normalized_query[:120]}...")

    try:
        # Step 1: Result cache (safe)
        if request.enable_cache and settings.ENABLE_CACHE and redis_cache is not None:
            cached_result = redis_cache.get_result(normalized_query)

            # Redis/Upstash sometimes returns strings/None/etc depending on JSON commands.
            # Only accept dict payloads that match the same query.
            if isinstance(cached_result, dict):
                cached_query = _normalize_query(str(cached_result.get("query", "")))
                if cached_query == normalized_query:
                    logger.info("Returning cached result")
                    return QueryResponse(
                        success=True,
                        query=normalized_query,
                        routing_decision=RoutingDecision(**cast(Dict[str, Any], cached_result.get("routing_decision", {}))),
                        generated_sql=cached_result.get("sql"),
                        s3_url=cached_result.get("s3_url"),
                        metadata=QueryMetadata(**cast(Dict[str, Any], cached_result.get("metadata", {}))),
                        cache_hit=True,
                    )
                else:
                    # Wrong payload for this query => delete and proceed as miss
                    logger.warning("Cache payload query mismatch; deleting cached entry and recomputing")
                    redis_cache.delete(normalized_query)

            elif cached_result is not None:
                # Non-dict junk in cache (str/None/etc) => delete and proceed
                logger.warning(f"Cache returned non-dict payload ({type(cached_result)}). Deleting and recomputing.")
                redis_cache.delete(normalized_query)

        # Step 2: Router Agent
        routing_decision = router_agent.route(normalized_query)

        if not routing_decision.get("requires_sql", False):
            error_msg = "Query does not require database access"
            return QueryResponse(
                success=False,
                query=normalized_query,
                routing_decision=RoutingDecision(**routing_decision),
                error=error_msg,
            )


        # Step 3: SQL Agent
        generated_sql: Optional[str] = None
        sql_error: Optional[str] = None

        if not generated_sql:
            for retry in range(settings.SQL_RETRY_MAX):
                try:
                    generated_sql = sql_agent.generate_sql(
                        query=normalized_query,
                        tables_involved=routing_decision.get("tables_involved"),
                        previous_sql=generated_sql if retry > 0 else None,
                        error=sql_error if retry > 0 else None,
                    )
                    break

                except Exception as e:
                    sql_error = str(e)
                    logger.warning(f"SQL generation attempt {retry + 1} failed: {e}")

                    if retry == settings.SQL_RETRY_MAX - 1:
                        raise HTTPException(status_code=500, detail=f"SQL generation failed: {sql_error}")

        if not generated_sql:
            raise HTTPException(status_code=500, detail="SQL generation failed")

        # Step 4: Execute SQL (+ regen on DB error)
        exec_error: Optional[str] = None
        csv_url: Optional[str] = None
        metadata: Dict[str, Any] = {}

        for retry in range(settings.SQL_RETRY_MAX):
            try:
                csv_url, metadata = executor_agent.execute_sql(generated_sql, normalized_query)
                break

            except Exception as e:
                exec_error = str(e)
                logger.warning(f"SQL execution attempt {retry + 1} failed: {e}")

                if retry < settings.SQL_RETRY_MAX - 1:
                    # Regenerate SQL based on DB error
                    generated_sql = sql_agent.generate_sql(
                        query=normalized_query,
                        tables_involved=routing_decision.get("tables_involved"),
                        previous_sql=generated_sql,
                        error=exec_error,
                    )
                    continue

                raise HTTPException(status_code=500, detail=f"SQL execution failed: {exec_error}")

        if not csv_url:
            raise HTTPException(status_code=500, detail="SQL execution failed (no output url)")


        # Step 5: Email (optional)
        if routing_decision.get("requires_email", False) and request.user_email:
            to_email = request.user_email

            # preview + attachment
            preview_df = None
            attachment_path = None

            # metadata should include csv_s3_key/sql_s3_url depending on executor implementation
            csv_s3_key = metadata.get("csv_s3_key")
            if isinstance(csv_s3_key, str) and csv_s3_key:
                preview_df = executor_agent.get_row_preview(csv_s3_key, num_rows=30)
                attachment_path = executor_agent.get_full_csv_path(csv_s3_key)

            background_tasks.add_task(
                email_agent.send_results,
                to_email=to_email,
                user_query=normalized_query,
                s3_url=csv_url,
                metadata=metadata,
                preview_df=preview_df,
                csv_attachment_path=attachment_path,
            )

        # Step 6: Store result cache
        if request.enable_cache and settings.ENABLE_CACHE and redis_cache is not None:
            payload = {
                "query": normalized_query,
                "routing_decision": routing_decision,
                "sql": generated_sql,
                "s3_url": csv_url,
                "metadata": metadata,
            }
            redis_cache.set_result(normalized_query, payload)

        return QueryResponse(
            success=True,
            query=normalized_query,
            routing_decision=RoutingDecision(**routing_decision),
            generated_sql=generated_sql,
            s3_url=csv_url,
            metadata=QueryMetadata(**metadata),
            cache_hit=False,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unhandled error while processing query: {e}")
        raise HTTPException(status_code=500, detail=str(e))
