"""SQL Agent for generating SQL queries."""

import logging
import re
from typing import Optional, List

from anthropic import Anthropic
from anthropic.types import TextBlock
from langfuse import observe

logger = logging.getLogger(__name__)

from .retriever import SchemaRetriever
from .prompts import SQL_GENERATION_SYSTEM_PROMPT, SQL_REGENERATION_TEMPLATE


class SQLAgent:
    """SQL generation agent using Claude with RAG."""

    def __init__(
        self,
        anthropic_api_key: str,
        schema_retriever: SchemaRetriever,
        model: str = "claude-3-5-haiku-20241022",
        max_tokens: int = 1000
    ):
        """Initialize SQL Agent."""
        self.client = Anthropic(api_key=anthropic_api_key)
        self.schema_retriever = schema_retriever
        self.model = model
        self.max_tokens = max_tokens
        logger.info(f"SQLAgent initialized with model: {model}")

    @observe(name="sql_agent")  # This creates the observation!
    def generate_sql(
        self,
        query: str,
        tables_involved: Optional[List[str]] = None,
        previous_sql: Optional[str] = None,
        error: Optional[str] = None
    ) -> str:
        """Generate SQL query."""
        logger.info(f"Generating SQL for query: {query[:100]}...")

        # Retrieve schema context
        if tables_involved:
            schema_context = self.schema_retriever.get_table_context(tables_involved)
        else:
            schema_context = self.schema_retriever.retrieve(query)

        logger.info(f"Retrieved context for tables: {tables_involved or 'all'}")

        # Build prompt
        if previous_sql and error:
            logger.info("Regenerating SQL after error")
            user_prompt = SQL_REGENERATION_TEMPLATE.format(
                query=query,
                schema_context=schema_context,
                previous_sql=previous_sql,
                error=error
            )
        else:
            user_prompt = f"Schema Context:\n{schema_context}\n\nUser Query: {query}"

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=0.0,
                messages=[
                    {"role": "user", "content": user_prompt}
                ],
                system=SQL_GENERATION_SYSTEM_PROMPT
            )

            content_block = response.content[0]
            if not isinstance(content_block, TextBlock):
                raise ValueError(f"Unexpected response type: {type(content_block)}")
            sql_query = content_block.text.strip()

            # Clean SQL
            sql_query = sql_query.replace("```sql", "").replace("```", "").strip()

            logger.info(f"Generated SQL: {sql_query[:100]}...")
            return sql_query

        except Exception as e:
            logger.error(f"SQL Agent error: {e}")
            raise

    def validate_sql_syntax(self, sql: str) -> bool:
        """Validate SQL syntax."""
        sql_upper = sql.upper().strip()

        if not sql_upper.startswith("SELECT"):
            logger.error("SQL must start with SELECT")
            return False

        forbidden_keywords = ["DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "CREATE", "TRUNCATE"]
        for keyword in forbidden_keywords:
            if keyword in sql_upper:
                logger.error(f"SQL contains forbidden keyword: {keyword}")
                return False

        return True