"""
Node functions for the LangGraph workflow.
Each node takes State and returns updates to State.
"""

import json
import logging
import re
from typing import Any, Dict, Optional

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI

from app.config import settings
from app.graph.state import QueryState
from agents.router_agent.prompts import ROUTER_SYSTEM_PROMPT, USER_QUERY_TEMPLATE
from agents.sql_agent import SchemaRetriever
from agents.sql_agent.prompts import SQL_GENERATION_SYSTEM_PROMPT, SQL_REGENERATION_TEMPLATE
from agents.executor_agent import ExecutorAgent, S3Uploader
from agents.email_agent import EmailAgent

logger = logging.getLogger(__name__)


def _coerce_content(raw_content: Any) -> str:
    """Normalize LangChain message content into a plain string."""
    if isinstance(raw_content, str):
        return raw_content

    if isinstance(raw_content, list):
        parts = []
        for chunk in raw_content:
            if isinstance(chunk, dict) and "text" in chunk:
                parts.append(str(chunk["text"]))
            elif hasattr(chunk, "text"):
                parts.append(str(chunk.text))  # type: ignore[attr-defined]
            else:
                parts.append(str(chunk))
        return "".join(parts)

    return str(raw_content)


# Initialize shared components (module-level)
schema_retriever = SchemaRetriever(
    chroma_host=settings.CHROMA_HOST,
    chroma_port=settings.CHROMA_PORT,
    collection_name=settings.CHROMA_COLLECTION,
    embedding_model=settings.OPENAI_EMBEDDING_MODEL,
    openai_api_key=settings.OPENAI_API_KEY,
    persist_directory=settings.CHROMA_PERSIST_DIR,
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
    query_timeout=settings.QUERY_TIMEOUT,
)

email_agent = EmailAgent(
    smtp_host=settings.SMTP_HOST,
    smtp_port=settings.SMTP_PORT,
    smtp_user=settings.SMTP_USER,
    smtp_password=settings.SMTP_PASSWORD,
)


def router_node(state: QueryState) -> Dict[str, Any]:
    """
    Router node: Analyze query and determine routing decision.
    Uses LangChain ChatOpenAI for automatic token/cost tracking.
    """
    logger.info(f"Router node: Processing query: {state['query'][:100]}...")
    
    # Use LangChain's ChatOpenAI for automatic tracing
    openai_kwargs: Dict[str, Any] = {
        "model_name": settings.OPENAI_GENERAL_MODEL,
        "temperature": 0.0,
        "openai_api_key": settings.OPENAI_API_KEY,
        "max_tokens": settings.OPENAI_MAX_TOKENS,
    }
    llm = ChatOpenAI(**openai_kwargs)
    
    messages = [
        SystemMessage(content=ROUTER_SYSTEM_PROMPT),
        HumanMessage(content=USER_QUERY_TEMPLATE.format(query=state["query"]))
    ]
    
    try:
        response = llm.invoke(messages)
        decision_text = _coerce_content(response.content)

        # Clean markdown if present
        decision_text = re.sub(r"^```json\s*", "", decision_text)
        decision_text = re.sub(r"\s*```$", "", decision_text)
        decision_text = decision_text.strip()

        decision = json.loads(decision_text)
        requires_sql = decision.get("requires_sql", True)
        requires_email = decision.get("requires_email", False)

        logger.info(f"Routing decision: {decision}")

        updates: Dict[str, Any] = {
            "requires_sql": requires_sql,
            "requires_email": requires_email,
            "tables_involved": decision.get("tables_involved") or [],
            "query_complexity": decision.get("query_complexity", "simple"),
            "routing_reasoning": decision.get("reasoning", ""),
        }

        if not requires_sql:
            updates["success"] = False
            updates["error_message"] = "Query does not require database access per router decision."

        return updates

    except Exception as e:
        logger.error(f"Router error: {e}")
        error_msg = f"Router error: {e}"
        return {
            "requires_sql": True,
            "requires_email": False,
            "tables_involved": [],
            "query_complexity": "simple",
            "routing_reasoning": f"Error: {str(e)}",
            "success": False,
            "error_message": error_msg,
        }


def sql_generator_node(state: QueryState) -> Dict[str, Any]:
    """
    SQL Generator node: Generate SQL query using Claude with RAG.
    Uses LangChain ChatAnthropic for automatic token/cost tracking.
    """
    logger.info(f"SQL Generator node: Generating SQL for query: {state['query'][:100]}...")
    
    # Retrieve schema context
    tables = state.get("tables_involved") or []
    if tables:
        schema_context = schema_retriever.get_table_context(tables)
    else:
        schema_context = schema_retriever.retrieve(state["query"])
    
    # Build prompt
    if state.get("generated_sql") and state.get("sql_generation_error"):
        # Regeneration after error
        user_prompt = SQL_REGENERATION_TEMPLATE.format(
            query=state["query"],
            schema_context=schema_context,
            previous_sql=state["generated_sql"],
            error=state["sql_generation_error"]
        )
    else:
        user_prompt = f"Schema Context:\n{schema_context}\n\nUser Query: {state['query']}"
    
    # Use LangChain's ChatAnthropic for automatic tracing
    anthropic_kwargs: Dict[str, Any] = {
        "model": settings.ANTHROPIC_SQL_MODEL,
        "max_tokens": settings.ANTHROPIC_MAX_TOKENS,
        "temperature": 0.0,
        "anthropic_api_key": settings.ANTHROPIC_API_KEY,
    }
    llm = ChatAnthropic(**anthropic_kwargs)
    
    messages = [
        SystemMessage(content=SQL_GENERATION_SYSTEM_PROMPT),
        HumanMessage(content=user_prompt)
    ]
    
    try:
        response = llm.invoke(messages)
        sql_query = _coerce_content(response.content).strip()

        # Clean SQL
        sql_query = sql_query.replace("```sql", "").replace("```", "").strip()

        logger.info(f"Generated SQL: {sql_query[:100]}...")

        return {
            "generated_sql": sql_query,
            "sql_generation_error": None,
            "error_message": None,
        }

    except Exception as e:
        logger.error(f"SQL generation error: {e}")
        error_message = f"SQL generation error: {e}"
        return {
            "sql_generation_error": str(e),
            "sql_retry_count": state.get("sql_retry_count", 0) + 1,
            "success": False,
            "error_message": error_message,
        }


def executor_node(state: QueryState) -> Dict[str, Any]:
    """
    Executor node: Execute SQL and upload results to S3.
    """
    logger.info(f"Executor node: Executing SQL...")
    
    generated_sql = state.get("generated_sql")
    if not generated_sql:
        error_message = "No SQL to execute"
        return {
            "success": False,
            "error_message": error_message,
            "execution_error": error_message,
        }
    
    try:
        csv_url, metadata = executor_agent.execute_sql(
            generated_sql,
            state["query"]
        )
        
        logger.info(f"SQL executed successfully. CSV URL: {csv_url}")
        
        return {
            "csv_s3_url": csv_url,
            "sql_s3_url": metadata.get("sql_s3_url"),
            "execution_metadata": metadata,
            "execution_error": None,
            "execution_retry_count": state.get("execution_retry_count", 0),
            "sql_generation_error": None,
            "success": True,
            "error_message": None,
        }
        
    except Exception as e:
        logger.error(f"Execution error: {e}")
        error_message = str(e)
        return {
            "execution_error": error_message,
            "execution_retry_count": state.get("execution_retry_count", 0) + 1,
            "success": False,
            "error_message": error_message,
            "sql_generation_error": error_message,
        }


def email_node(state: QueryState) -> Dict[str, Any]:
    """
    Email node: Send results via email (runs as last step if needed).
    """
    logger.info(f"Email node: Sending results to {state.get('user_email')}...")
    
    user_email = state.get("user_email")
    if not user_email:
        logger.warning("No email address provided, skipping email")
        return {}
    
    csv_s3_url = state.get("csv_s3_url")
    execution_metadata = state.get("execution_metadata")
    if not csv_s3_url or not execution_metadata:
        logger.warning("Missing CSV URL or execution metadata, skipping email")
        return {}
    
    try:
        # Get preview and attachment path
        preview_df = None
        attachment_path = None
        
        csv_s3_key = execution_metadata.get("csv_s3_key")
        if csv_s3_key:
            preview_df = executor_agent.get_row_preview(csv_s3_key, num_rows=30)
            attachment_path = executor_agent.get_full_csv_path(csv_s3_key)
        
        # Send email
        email_agent.send_results(
            to_email=user_email,
            user_query=state["query"],
            s3_url=csv_s3_url,
            metadata=execution_metadata,
            preview_df=preview_df,
            csv_attachment_path=attachment_path,
        )
        
        logger.info("Email sent successfully")
        return {}
        
    except Exception as e:
        logger.error(f"Email error: {e}")
        return {
            "error_message": f"Email delivery failed: {e}",
            "success": False,
        }
