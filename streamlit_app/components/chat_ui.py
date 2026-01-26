"""Chat interface component."""

import streamlit as st
from typing import Optional


def render_chat_interface() -> tuple:
    """Render chat interface for query input.
    
    Returns:
        Tuple of (query, user_email, enable_cache)
    """
    st.title("🤖 Agentic RAG Analytics")
    st.markdown("Ask questions about your data in natural language")
    
    # Query input
    query = st.text_area(
        "Enter your query:",
        height=100,
        placeholder="e.g., Show me top 10 customers by revenue in the West region"
    )
    
    # Options in columns
    col1, col2 = st.columns(2)
    
    with col1:
        user_email = st.text_input(
            "Email (optional - for results delivery):",
            placeholder="your.email@example.com"
        )
    
    with col2:
        enable_cache = st.checkbox("Use cached results", value=True)
    
    # Submit button
    submit = st.button("🚀 Execute Query", type="primary", width="stretch")
    
    return query, user_email if user_email else None, enable_cache, submit


def render_example_queries():
    """Render example queries sidebar."""
    st.sidebar.header("📝 Example Queries")
    
    examples = [
        "Show top 10 customers by revenue",
        "What are the high churn risk customers for December 2025?",
        "Forecast demand for Electronics category in Midwest",
        "Compare revenue across all regions for Q4 2025",
        "Email me the list of customers with failed payments",
        "Show best selling products by category",
        "What's the average order value by region?",
        "List customers who haven't ordered in 90 days"
    ]
    
    for example in examples:
        if st.sidebar.button(example, key=example):
            st.session_state['example_query'] = example
    
    return st.session_state.get('example_query', None)