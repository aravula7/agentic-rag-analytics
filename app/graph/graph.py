"""
LangGraph workflow definition.
"""

import logging
from typing import Union

from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph

from app.config import settings
from app.graph.state import QueryState
from app.graph.nodes import router_node, sql_generator_node, executor_node, email_node

logger = logging.getLogger(__name__)

EdgeTarget = Union[str, object]


def should_generate_sql(state: QueryState) -> EdgeTarget:
    """Conditional edge: Check if SQL generation is needed."""
    if state.get("requires_sql"):
        return "sql_generator"
    return END


def should_retry_sql(state: QueryState) -> EdgeTarget:
    """Conditional edge: Check if SQL generation should retry."""
    if state.get("sql_generation_error"):
        if state.get("sql_retry_count", 0) < settings.SQL_RETRY_MAX:
            logger.info(f"Retrying SQL generation (attempt {state.get('sql_retry_count', 0) + 1})")
            return "sql_generator"
        logger.error("SQL generation retries exhausted; ending workflow.")
        return END
    return "executor"


def should_retry_execution(state: QueryState) -> EdgeTarget:
    """Conditional edge: Check if execution should retry with SQL regeneration."""
    if state.get("execution_error"):
        if state.get("execution_retry_count", 0) < settings.SQL_RETRY_MAX:
            logger.info(
                "Retrying execution with SQL regeneration "
                f"(attempt {state.get('execution_retry_count', 0) + 1})"
            )
            return "sql_generator"
        logger.error("Execution retries exhausted; ending workflow.")
        return END

    if state.get("requires_email") and state.get("user_email") and state.get("success"):
        return "email"

    return END


def create_graph() -> CompiledStateGraph[QueryState, None, QueryState, QueryState]:
    """
    Create and compile the LangGraph workflow.
    
    Graph structure:
    START -> router -> [sql_generator (with retry)] -> executor (with retry) -> [email] -> END
    """
    # Create graph
    graph_builder = StateGraph(QueryState)
    
    # Add nodes
    graph_builder.add_node("router", router_node)
    graph_builder.add_node("sql_generator", sql_generator_node)
    graph_builder.add_node("executor", executor_node)
    graph_builder.add_node("email", email_node)
    
    # Add edges
    graph_builder.add_edge(START, "router")
    graph_builder.add_conditional_edges("router", should_generate_sql)
    graph_builder.add_conditional_edges("sql_generator", should_retry_sql)
    graph_builder.add_conditional_edges("executor", should_retry_execution)
    graph_builder.add_edge("email", END)

    # Compile
    graph = graph_builder.compile()
    
    logger.info("LangGraph workflow compiled successfully")
    return graph


# Create singleton graph instance
workflow_graph = create_graph()
