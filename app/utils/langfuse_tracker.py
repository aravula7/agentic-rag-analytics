"""Langfuse monitoring utility - Dummy implementation for testing."""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class LangfuseTracker:
    """Langfuse tracker - Disabled for testing."""

    def __init__(
        self,
        public_key: str,
        secret_key: str,
        host: str = "https://us.cloud.langfuse.com"
    ):
        """Initialize Langfuse tracker (disabled)."""
        logger.warning("Langfuse tracking is DISABLED for testing")
        self.enabled = False

    def create_trace(self, query: str, user_email: Optional[str] = None) -> str:
        """Create a new trace (no-op)."""
        return "test-trace-id"

    def track_router(self, trace_id: str, routing_decision: Dict[str, Any]):
        """Track Router Agent (no-op)."""
        pass

    def track_sql_generation(
        self,
        trace_id: str,
        query: str,
        generated_sql: str,
        tables_involved: list,
        retry_count: int = 0
    ):
        """Track SQL Agent (no-op)."""
        pass

    def track_execution(
        self,
        trace_id: str,
        sql: str,
        metadata: Dict[str, Any],
        success: bool = True,
        error: Optional[str] = None
    ):
        """Track Executor Agent (no-op)."""
        pass

    def track_email(
        self,
        trace_id: str,
        to_email: str,
        success: bool = True,
        error: Optional[str] = None
    ):
        """Track Email Agent (no-op)."""
        pass

    def finalize_trace(self, trace_id: str, success: bool, error: Optional[str] = None):
        """Finalize trace (no-op)."""
        pass

    def flush(self):
        """Flush events (no-op)."""
        pass