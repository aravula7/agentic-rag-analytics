"""Main Streamlit application."""

import streamlit as st
import requests
import os
from components.chat_ui import render_chat_interface, render_example_queries
from components.result_viewer import render_results

# Page configuration
st.set_page_config(
    page_title="Agentic RAG Analytics",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API endpoint
API_URL = os.getenv("API_URL", "http://localhost:8001")

# Initialize session state
if 'query_history' not in st.session_state:
    st.session_state['query_history'] = []

# Sidebar
with st.sidebar:
    st.image("https://via.placeholder.com/150x50?text=RAG+Analytics", use_container_width=True)
    st.markdown("---")
    
    # Example queries
    example = render_example_queries()
    
    st.markdown("---")
    
    # Settings
    st.subheader("⚙️ Settings")
    api_url = st.text_input("API URL", value=API_URL)
    
    st.markdown("---")
    
    # Stats
    st.subheader("📈 Session Stats")
    st.metric("Queries Executed", len(st.session_state['query_history']))

# Main content
query, user_email, enable_cache, submit = render_chat_interface()

# Pre-fill with example if selected
if example:
    query = example

# Execute query
if submit and query:
    with st.spinner("🔄 Processing query..."):
        try:
            # Call API
            response = requests.post(
                f"{api_url}/query/",
                json={
                    "query": query,
                    "user_email": user_email,
                    "enable_cache": enable_cache
                },
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Add to history
                st.session_state['query_history'].append({
                    'query': query,
                    'timestamp': result.get('timestamp'),
                    'success': result.get('success')
                })
                
                # Render results
                render_results(result)
            else:
                st.error(f"❌ API Error: {response.status_code} - {response.text}")
        
        except requests.exceptions.Timeout:
            st.error("❌ Request timeout. Query took too long to execute.")
        except requests.exceptions.ConnectionError:
            st.error(f"❌ Cannot connect to API at {api_url}")
        except Exception as e:
            st.error(f"❌ Unexpected error: {str(e)}")

# Query history
if st.session_state['query_history']:
    with st.expander("📜 Query History"):
        for i, item in enumerate(reversed(st.session_state['query_history'][-10:])):
            status = "✅" if item['success'] else "❌"
            st.markdown(f"{status} **{item['query'][:100]}...** - {item['timestamp']}")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray;'>
    Built with LangChain, FastAPI, Streamlit | Powered by GPT-4o & Claude Haiku
    </div>
    """,
    unsafe_allow_html=True
)