"""Result viewer component."""

import streamlit as st
import pandas as pd
import requests
from typing import Dict, Any, Optional


def render_results(response: Dict[str, Any]):
    """Render query results.
    
    Args:
        response: API response dictionary
    """
    if not response.get('success'):
        st.error(f"❌ Query Failed: {response.get('error', 'Unknown error')}")
        return
    
    # Success banner
    if response.get('cache_hit'):
        st.success("✅ Results retrieved from cache")
    else:
        st.success("✅ Query executed successfully")
    
    # Tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs(["Results", "Query Details", "Metadata", "Email"])
    
    with tab1:
        render_results_tab(response)
    
    with tab2:
        render_query_details_tab(response)
    
    with tab3:
        render_metadata_tab(response)
    
    with tab4:
        render_email_tab(response)


def render_results_tab(response: Dict[str, Any]):
    """Render results preview."""
    st.subheader("Query Results")
    
    metadata = response.get('metadata', {})
    s3_url = response.get('s3_url')
    
    # Metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Rows", metadata.get('row_count', 'N/A'))
    col2.metric("Columns", metadata.get('column_count', 'N/A'))
    col3.metric("Execution Time", f"{metadata.get('execution_time_seconds', 0):.2f}s")
    
    # Download button
    if s3_url:
        st.markdown(f"**Download URL:** `{s3_url}`")
        st.info("💡 Results are stored in S3. Use the download URL or check your email.")
    
    # TODO: Add preview if we implement presigned URL download
    st.info("📊 Full results are available via S3 download or email attachment")


def render_query_details_tab(response: Dict[str, Any]):
    """Render query analysis details."""
    st.subheader("Query Analysis")
    
    # Routing decision
    routing = response.get('routing_decision', {})
    if routing:
        st.markdown("**Router Agent Decision:**")
        
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"- **Requires SQL:** {routing.get('requires_sql', False)}")
            st.write(f"- **Requires Email:** {routing.get('requires_email', False)}")
        with col2:
            st.write(f"- **Complexity:** {routing.get('query_complexity', 'N/A')}")
            st.write(f"- **Tables:** {', '.join(routing.get('tables_involved', []))}")
        
        st.markdown(f"**Reasoning:** {routing.get('reasoning', 'N/A')}")
    
    # Generated SQL
    generated_sql = response.get('generated_sql')
    if generated_sql:
        st.markdown("**Generated SQL Query:**")
        st.code(generated_sql, language='sql')


def render_metadata_tab(response: Dict[str, Any]):
    """Render execution metadata."""
    st.subheader("Execution Metadata")
    
    metadata = response.get('metadata', {})
    
    # Display as table
    if metadata:
        df = pd.DataFrame([
            {"Metric": "Row Count", "Value": metadata.get('row_count', 'N/A')},
            {"Metric": "Column Count", "Value": metadata.get('column_count', 'N/A')},
            {"Metric": "Execution Time", "Value": f"{metadata.get('execution_time_seconds', 0):.2f}s"},
            {"Metric": "S3 Key", "Value": metadata.get('s3_key', 'N/A')},
            {"Metric": "Timestamp", "Value": response.get('timestamp', 'N/A')}
        ])
        st.table(df)
    
    # Columns
    columns = metadata.get('columns', [])
    if columns:
        st.markdown("**Result Columns:**")
        st.write(", ".join(columns))


def render_email_tab(response: Dict[str, Any]):
    """Render email status."""
    st.subheader("Email Delivery")
    
    routing = response.get('routing_decision', {})
    requires_email = routing.get('requires_email', False) if routing else False
    
    if requires_email:
        st.success("✅ Email delivery was requested and results were sent")
        st.info("Check your inbox for the results attachment")
    else:
        st.info("ℹ️ Email delivery was not requested for this query")
        st.markdown("To receive results via email, include phrases like:")
        st.markdown("- 'Email me...'")
        st.markdown("- 'Send me...'")
        st.markdown("- 'Mail the results...'")