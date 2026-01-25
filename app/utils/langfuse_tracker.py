"""Langfuse monitoring utility."""

import logging
from typing import Optional, Dict, Any
from langfuse import Langfuse
from datetime import datetime

logger = logging.getLogger(__name__)


class LangfuseTracker:
    """Langfuse tracker for agent monitoring."""

    def __init__(
        self,
        public_key: str,
        secret_key: str,
        host: str = "https://cloud.langfuse.com"
    ):
        """Initialize Langfuse tracker.
        
        Args:
            public_key: Langfuse public key
            secret_key: Langfuse secret key
            host: Langfuse host URL
        """
        self.client = Langfuse(
            public_key=public_key,
            secret_key=secret_key,
            host=host
        )
        logger.info("LangfuseTracker initialized")

    def create_trace(self, query: str, user_email: Optional[str] = None) -> Any:
        """Create a new trace for a query.
        
        Args:
            query: User query
            user_email: User email (optional)
            
        Returns:
            Langfuse trace object
        """
        return self.client.trace(
            name="query_execution",
            input={"query": query},
            user_id=user_email,
            metadata={"timestamp": datetime.now().isoformat()}
        )

    def track_router(self, trace: Any, routing_decision: Dict[str, Any]):
        """Track Router Agent execution.
        
        Args:
            trace: Langfuse trace object
            routing_decision: Router decision dict
        """
        trace.span(
            name="router_agent",
            input={"query": trace.input.get("query")},
            output=routing_decision,
            metadata={"agent": "router", "model": "gpt-4o"}
        )

    def track_sql_generation(
        self,
        trace: Any,
        query: str,
        generated_sql: str,
        tables_involved: list,
        retry_count: int = 0
    ):
        """Track SQL Agent execution.
        
        Args:
            trace: Langfuse trace object
            query: User query
            generated_sql: Generated SQL
            tables_involved: List of tables
            retry_count: Number of retries
        """
        trace.span(
            name="sql_agent",
            input={"query": query, "tables": tables_involved},
            output={"sql": generated_sql},
            metadata={
                "agent": "sql_generator",
                "model": "claude-haiku-4",
                "retry_count": retry_count
            }
        )

    def track_execution(
        self,
        trace: Any,
        sql: str,
        metadata: Dict[str, Any],
        success: bool = True,
        error: Optional[str] = None
    ):
        """Track Executor Agent execution.
        
        Args:
            trace: Langfuse trace object
            sql: SQL query
            metadata: Execution metadata
            success: Whether execution succeeded
            error: Error message if failed
        """
        output = metadata if success else {"error": error}
        trace.span(
            name="executor_agent",
            input={"sql": sql},
            output=output,
            metadata={
                "agent": "executor",
                "success": success,
                "execution_time": metadata.get('execution_time_seconds', 0)
            }
        )

    def track_email(
        self,
        trace: Any,
        to_email: str,
        success: bool = True,
        error: Optional[str] = None
    ):
        """Track Email Agent execution.
        
        Args:
            trace: Langfuse trace object
            to_email: Recipient email
            success: Whether email sent successfully
            error: Error message if failed
        """
        trace.span(
            name="email_agent",
            input={"to_email": to_email},
            output={"success": success, "error": error},
            metadata={"agent": "email_sender"}
        )

    def finalize_trace(self, trace: Any, success: bool, error: Optional[str] = None):
        """Finalize trace with final status.
        
        Args:
            trace: Langfuse trace object
            success: Overall success status
            error: Error message if failed
        """
        trace.update(
            output={"success": success, "error": error},
            metadata={"completed_at": datetime.now().isoformat()}
        )