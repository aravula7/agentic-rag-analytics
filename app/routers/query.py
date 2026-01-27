"""Query router for natural language to SQL execution."""

import logging
import os

# Set Langfuse credentials before any imports that use it
os.environ.setdefault("LANGFUSE_PUBLIC_KEY", os.getenv("LANGFUSE_PUBLIC_KEY", ""))
os.environ.setdefault("LANGFUSE_SECRET_KEY", os.getenv("LANGFUSE_SECRET_KEY", ""))
os.environ.setdefault("LANGFUSE_HOST", os.getenv("LANGFUSE_HOST", "https://us.cloud.langfuse.com"))

from typing import Any, Dict, cast
from fastapi import APIRouter, HTTPException, BackgroundTasks
from datetime import datetime

from app.models.schemas import QueryRequest, QueryResponse, RoutingDecision, QueryMetadata
from app.config import settings
from app.utils.redis_cache import RedisCache

from agents.router_agent import RouterAgent
from agents.sql_agent import SQLAgent, SchemaRetriever
from agents.executor_agent import ExecutorAgent, S3Uploader
from agents.email_agent import EmailAgent

logger = logging.getLogger(__name__)

router = APIRouter()

redis_cache = RedisCache(
    rest_url=settings.UPSTASH_REDIS_REST_URL,
    rest_token=settings.UPSTASH_REDIS_REST_TOKEN,
    ttl=settings.REDIS_CACHE_TTL
)

router_agent = RouterAgent(
    api_key=settings.OPENAI_API_KEY,
    model=settings.OPENAI_GENERAL_MODEL
)

schema_retriever = SchemaRetriever(
    chroma_host=settings.CHROMA_HOST,
    chroma_port=settings.CHROMA_PORT,
    collection_name=settings.CHROMA_COLLECTION,
    openai_api_key=settings.OPENAI_API_KEY,
    embedding_model=settings.OPENAI_EMBEDDING_MODEL
)

sql_agent = SQLAgent(
    anthropic_api_key=settings.ANTHROPIC_API_KEY,
    schema_retriever=schema_retriever,
    model=settings.ANTHROPIC_SQL_MODEL,
    max_tokens=settings.ANTHROPIC_MAX_TOKENS
)

s3_uploader = S3Uploader(
    endpoint_url=settings.S3_ENDPOINT_URL,
    bucket_name=settings.S3_BUCKET_NAME,
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region=settings.AWS_REGION
)

executor_agent = ExecutorAgent(
    db_host=settings.DB_HOST,
    db_port=settings.DB_PORT,
    db_name=settings.DB_NAME,
    db_user=settings.DB_USER,
    db_password=settings.DB_PASSWORD,
    s3_uploader=s3_uploader,
    query_timeout=settings.QUERY_TIMEOUT
)

email_agent = EmailAgent(
    smtp_host=settings.SMTP_HOST,
    smtp_port=settings.SMTP_PORT,
    smtp_user=settings.SMTP_USER,
    smtp_password=settings.SMTP_PASSWORD
)


@router.post("/", response_model=QueryResponse)
async def execute_query(request: QueryRequest, background_tasks: BackgroundTasks):
    """Execute a natural language query.
    
    Args:
        request: QueryRequest with query and optional email
        background_tasks: FastAPI background tasks
        
    Returns:
        QueryResponse with results or error
    """
    logger.info(f"Received query: {request.query[:100]}...")

    try:
        # Step 1: Check result cache if enabled
        if request.enable_cache and settings.ENABLE_CACHE:
            cached_result = redis_cache.get_result(request.query)
            if cached_result:
                logger.info("Returning cached result")
                
                return QueryResponse(
                    success=True,
                    query=request.query,
                    routing_decision=RoutingDecision(**cached_result.get('routing_decision', {})),
                    generated_sql=cached_result.get('sql'),
                    s3_url=cached_result.get('s3_url'),
                    metadata=QueryMetadata(**cast(Dict[str, Any], cached_result.get('metadata', {}))),
                    cache_hit=True
                )

        # Step 2: Router Agent
        routing_decision = router_agent.route(request.query)

        if not routing_decision.get('requires_sql', False):
            error_msg = "Query does not require database access"
            
            return QueryResponse(
                success=False,
                query=request.query,
                routing_decision=RoutingDecision(**routing_decision),
                error=error_msg
            )

        # Step 3: SQL Agent with two-layer caching
        generated_sql = None
        execution_error = None
        
        # Check SQL cache first
        if request.enable_cache and settings.ENABLE_CACHE:
            cached_sql = redis_cache.get_sql(request.query)
            if cached_sql:
                generated_sql = cached_sql
                logger.info("Using cached SQL query")
        
        # Generate SQL if not cached
        if not generated_sql:
            for retry in range(settings.SQL_RETRY_MAX):
                try:
                    generated_sql = sql_agent.generate_sql(
                        query=request.query,
                        tables_involved=routing_decision.get('tables_involved'),
                        previous_sql=generated_sql if retry > 0 else None,
                        error=execution_error if retry > 0 else None
                    )

                    if not sql_agent.validate_sql_syntax(generated_sql):
                        raise ValueError("Generated SQL failed validation")

                    # Cache the generated SQL
                    if settings.ENABLE_CACHE:
                        redis_cache.set_sql(request.query, generated_sql)
                    
                    break

                except Exception as e:
                    execution_error = str(e)
                    logger.warning(f"SQL generation attempt {retry + 1} failed: {e}")
                    
                    if retry == settings.SQL_RETRY_MAX - 1:
                        raise HTTPException(
                            status_code=500, 
                            detail=f"SQL generation failed: {execution_error}"
                        )

        # Step 4: Executor Agent with retry logic
        if generated_sql is None:
            raise HTTPException(status_code=500, detail="SQL generation failed")

        for retry in range(settings.SQL_RETRY_MAX):
            try:
                csv_url, metadata = executor_agent.execute_sql(generated_sql, request.query)
                
                break

            except Exception as e:
                execution_error = str(e)
                logger.warning(f"SQL execution attempt {retry + 1} failed: {e}")
                
                if retry < settings.SQL_RETRY_MAX - 1:
                    # Regenerate SQL based on error
                    try:
                        generated_sql = sql_agent.generate_sql(
                            query=request.query,
                            tables_involved=routing_decision.get('tables_involved'),
                            previous_sql=generated_sql,
                            error=execution_error
                        )
                    except Exception as gen_error:
                        logger.error(f"SQL regeneration failed: {gen_error}")
                        continue
                else:
                    # Max retries reached
                    raise HTTPException(
                        status_code=500, 
                        detail=f"Query execution failed: {execution_error}"
                    )

        # Step 5: Email Agent if requested
        if routing_decision.get('requires_email', False) and request.user_email:
            # Get full CSV path for attachment
            csv_local_path = executor_agent.get_full_csv_path(metadata['csv_s3_key'])
            
            # Get preview for email body
            preview_df = executor_agent.get_row_preview(metadata['csv_s3_key'], num_rows=10)
            
            # Send email in background
            background_tasks.add_task(
                email_agent.send_results,
                to_email=request.user_email,
                user_query=request.query,
                s3_url=csv_url,
                metadata=metadata,
                preview_df=preview_df,
                csv_attachment_path=csv_local_path
            )

        # Step 6: Cache result with SQL included
        if settings.ENABLE_CACHE:
            redis_cache.set_result(request.query, {
                'routing_decision': routing_decision,
                's3_url': csv_url,
                'metadata': metadata,
                'sql': generated_sql
            })

        # Return response
        return QueryResponse(
            success=True,
            query=request.query,
            routing_decision=RoutingDecision(**routing_decision),
            generated_sql=generated_sql,
            s3_url=csv_url,
            metadata=QueryMetadata(**metadata),
            cache_hit=False
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=str(e))