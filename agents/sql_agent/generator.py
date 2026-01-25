"""SQL Agent implementation using Claude Haiku."""

import logging
from typing import Dict, Any, Optional
from anthropic import Anthropic
from .retriever import SchemaRetriever
from .prompts import (
    SQL_GENERATION_SYSTEM_PROMPT,
    SQL_GENERATION_USER_TEMPLATE,
    SQL_REGENERATION_TEMPLATE
)

logger = logging.getLogger(__name__)


class SQLAgent:
    """SQL Agent for generating PostgreSQL queries using Claude Haiku."""

    def __init__(
        self,
        anthropic_api_key: str,
        schema_retriever: SchemaRetriever,
        model: str = "claude-haiku-4-20250514",
        max_tokens: int = 1000
    ):
        """Initialize SQL Agent.
        
        Args:
            anthropic_api_key: Anthropic API key
            schema_retriever: SchemaRetriever instance for RAG
            model: Anthropic model to use
            max_tokens: Maximum tokens in response
        """
        self.client = Anthropic(api_key=anthropic_api_key)
        self.retriever = schema_retriever
        self.model = model
        self.max_tokens = max_tokens
        logger.info(f"SQLAgent initialized with model: {model}")

    def generate_sql(
        self,
        query: str,
        tables_involved: Optional[list] = None,
        previous_sql: Optional[str] = None,
        error: Optional[str] = None
    ) -> str:
        """Generate SQL query from natural language.
        
        Args:
            query: User's natural language query
            tables_involved: List of tables from Router Agent (optional)
            previous_sql: Previous SQL that failed (for regeneration)
            error: Error message from failed execution (for regeneration)
            
        Returns:
            PostgreSQL SELECT query string
        """
        logger.info(f"Generating SQL for query: {query[:100]}...")

        # Retrieve relevant schema context
        if tables_involved:
            schema_context = self.retriever.get_table_context(tables_involved)
        else:
            schema_context = self.retriever.retrieve(query, top_k=5)
        
        if not schema_context:
            logger.warning("No schema context retrieved, using empty context")
            schema_context = "No schema context available"

        # Build user message
        if previous_sql and error:
            # Regeneration after error
            user_message = SQL_REGENERATION_TEMPLATE.format(
                error=error,
                previous_sql=previous_sql,
                query=query,
                schema_context=schema_context
            )
            logger.info("Regenerating SQL after error")
        else:
            # Initial generation
            user_message = SQL_GENERATION_USER_TEMPLATE.format(
                query=query,
                schema_context=schema_context
            )

        try:
            # Call Claude API
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=SQL_GENERATION_SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": user_message}
                ],
                temperature=0.0  # Deterministic SQL generation
            )

            # Extract SQL from response
            sql_query = response.content[0].text.strip()
            
            # Clean up SQL (remove markdown if present)
            if sql_query.startswith("```sql"):
                sql_query = sql_query.replace("```sql\n", "").replace("\n```", "")
            elif sql_query.startswith("```"):
                sql_query = sql_query.replace("```\n", "").replace("\n```", "")
            
            # Ensure query ends with semicolon
            if not sql_query.endswith(";"):
                sql_query += ";"
            
            logger.info(f"Generated SQL: {sql_query[:200]}...")
            return sql_query

        except Exception as e:
            logger.error(f"SQL Agent error: {e}")
            raise

    def validate_sql_syntax(self, sql: str) -> bool:
        """Basic SQL syntax validation.
        
        Args:
            sql: SQL query string
            
        Returns:
            True if basic syntax checks pass
        """
        # Basic checks
        sql_upper = sql.upper().strip()
        
        # Must start with SELECT
        if not sql_upper.startswith("SELECT"):
            logger.error("SQL must start with SELECT")
            return False
        
        # Must not contain forbidden keywords
        forbidden = ["INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER", "TRUNCATE"]
        for keyword in forbidden:
            if keyword in sql_upper:
                logger.error(f"SQL contains forbidden keyword: {keyword}")
                return False
        
        return True