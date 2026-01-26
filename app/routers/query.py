"""Query endpoint router."""

import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.models.schemas import QueryRequest, QueryResponse, RoutingDecision, QueryMetadata
from app.config import settings
from app.utils.redis_cache import RedisCache
from app.utils.langfuse_tracker import LangfuseTracker

# Import agents
from agents.router_agent import RouterAgent
from agents.sql_agent import SQLAgent, SchemaRetriever
from agents.executor_agent import ExecutorAgent, S3Uploader
from agents.email_agent import EmailAgent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/query", tags=["query"])

# Initialize components (singleton pattern)
redis_cache = RedisCache(
    rest_url=settings.UPSTASH_REDIS_REST_URL,
    rest_token=settings.UPSTASH_REDIS_REST_TOKEN,
    ttl=settings.REDIS_CACHE_TTL
)

langfuse_tracker = LangfuseTracker(
    public_key=settings.LANGFUSE_PUBLIC_KEY or "",
    secret_key=settings.LANGFUSE_SECRET_KEY or "",
    host=settings.LANGFUSE_HOST
)

# Initialize agents
router_agent = RouterAgent(
    api_key=settings.OPENAI_API_KEY or "",
    model=settings.OPENAI_GENERAL_MODEL,
    max_tokens=settings.OPENAI_MAX_TOKENS
)

schema_retriever = SchemaRetriever(
    chroma_host=settings.CHROMA_HOST,
    chroma_port=settings.CHROMA_PORT,
    collection_name=settings.CHROMA_COLLECTION,
    embedding_model=settings.OPENAI_EMBEDDING_MODEL,
    openai_api_key=settings.OPENAI_API_KEY or "",
    persist_directory=settings.CHROMA_PERSIST_DIR
)

sql_agent = SQLAgent(
    anthropic_api_key=settings.ANTHROPIC_API_KEY or "",
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
    db_host=settings.DB_HOST or "",
    db_port=settings.DB_PORT,
    db_name=settings.DB_NAME or "",
    db_user=settings.DB_USER or "",
    db_password=settings.DB_PASSWORD or "",
    s3_uploader=s3_uploader,
    query_timeout=settings.QUERY_TIMEOUT
)

email_agent = EmailAgent(
    smtp_host=settings.SMTP_HOST,
    smtp_port=settings.SMTP_PORT,
    smtp_user=settings.SMTP_USER or "",
    smtp_password=settings.SMTP_PASSWORD or ""
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

    # Create Langfuse trace
    trace_id = langfuse_tracker.create_trace(request.query, request.user_email)

    try:
        # Check cache if enabled
        if request.enable_cache and settings.ENABLE_CACHE:
            cached = redis_cache.get(request.query)
            if cached:
                logger.info("Returning cached result")
                metadata_dict = cached.get('metadata', {})
                metadata = QueryMetadata(
                    row_count=metadata_dict.get('row_count', 0),
                    column_count=metadata_dict.get('column_count', 0),
                    execution_time_seconds=metadata_dict.get('execution_time_seconds', 0.0),
                    columns=metadata_dict.get('columns', []),
                    s3_key=metadata_dict.get('s3_key', cached.get('s3_url', ''))
                )
                return QueryResponse(
                    success=True,
                    query=request.query,
                    s3_url=cached.get('s3_url'),
                    metadata=metadata,
                    cache_hit=True
                )


        # Step 1: Router Agent
        routing_decision = router_agent.route(request.query)
        langfuse_tracker.track_router(trace_id, routing_decision)

        # Check if SQL is required
        if not routing_decision.get('requires_sql', False):
            error_msg = "Query does not require database access"
            langfuse_tracker.finalize_trace(trace_id, success=False, error=error_msg)
            return QueryResponse(
                success=False,
                query=request.query,
                routing_decision=RoutingDecision(**routing_decision),
                error=error_msg
            )

        # Step 2: SQL Agent (with retry logic)
        generated_sql = None
        execution_error = None

        for retry in range(settings.SQL_RETRY_MAX):
            try:
                # Generate SQL
                generated_sql = sql_agent.generate_sql(
                    query=request.query,
                    tables_involved=routing_decision.get('tables_involved'),
                    previous_sql=generated_sql if retry > 0 else None,
                    error=execution_error if retry > 0 else None
                )
                
                langfuse_tracker.track_sql_generation(
                    trace_id,
                    request.query,
                    generated_sql,
                    routing_decision.get('tables_involved', []),
                    retry_count=retry
                )

                # Validate SQL syntax
                if not sql_agent.validate_sql_syntax(generated_sql):
                    raise ValueError("Generated SQL failed validation")

                # Step 3: Executor Agent
                s3_url, metadata = executor_agent.execute_sql(generated_sql, request.query)
                
                langfuse_tracker.track_execution(trace_id, generated_sql, metadata, success=True)
                
                # Success - break retry loop
                break

            except Exception as e:
                execution_error = str(e)
                logger.warning(f"SQL execution attempt {retry + 1} failed: {e}")
                
                if retry == settings.SQL_RETRY_MAX - 1:
                    # Max retries reached
                    langfuse_tracker.track_execution(
                        trace_id, generated_sql or "N/A", {}, success=False, error=execution_error
                    )
                    langfuse_tracker.finalize_trace(trace_id, success=False, error=execution_error)
                    raise HTTPException(status_code=500, detail=f"Query execution failed: {execution_error}")

        # Step 4: Email Agent (if requested)
        if routing_decision.get('requires_email', False) and request.user_email:
            # Send email in background
            preview_df = executor_agent.get_row_preview(metadata['s3_key'], num_rows=10)
            background_tasks.add_task(
                email_agent.send_results,
                to_email=request.user_email,
                user_query=request.query,
                s3_url=s3_url,
                metadata=metadata,
                preview_df=preview_df
            )
            langfuse_tracker.track_email(trace_id, request.user_email, success=True)

        # Cache result
        if settings.ENABLE_CACHE:
            redis_cache.set(request.query, {
                's3_url': s3_url,
                'metadata': metadata
            })

        # Finalize trace
        langfuse_tracker.finalize_trace(trace_id, success=True)
        
        # Flush Langfuse events
        langfuse_tracker.flush()

        # Return response
        return QueryResponse(
            success=True,
            query=request.query,
            routing_decision=RoutingDecision(**routing_decision),
            generated_sql=generated_sql,
            s3_url=s3_url,
            metadata=QueryMetadata(**metadata),
            cache_hit=False
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        langfuse_tracker.finalize_trace(trace_id, success=False, error=str(e))
        langfuse_tracker.flush()
        raise HTTPException(status_code=500, detail=str(e))