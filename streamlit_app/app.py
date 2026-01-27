"""Main Streamlit application."""

import streamlit as st
import requests
import os
from components.chat_ui import render_chat_interface, render_example_queries
from components.result_viewer import render_results

st.set_page_config(
    page_title="Agentic RAG Analytics",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

API_URL = os.getenv("API_URL", "http://localhost:8001")

if 'query_history' not in st.session_state:
    st.session_state['query_history'] = []

with st.sidebar:
    st.markdown("### Agentic RAG Analytics")
    st.markdown("---")
    
    example = render_example_queries()
    
    st.markdown("---")
    
    st.subheader("Settings")
    api_url = st.text_input("API URL", value=API_URL)
    
    st.markdown("---")
    
    st.subheader("Session Stats")
    st.metric("Queries Executed", len(st.session_state['query_history']))

query, user_email, enable_cache, submit = render_chat_interface()

if example:
    query = example

if submit and query:
    with st.spinner("Processing query..."):
        try:
            response = requests.post(
                f"{api_url}/query/",
                json={
                    "query": query,
                    "user_email": user_email,
                    "enable_cache": enable_cache
                },
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                
                st.session_state['query_history'].append({
                    'query': query,
                    'timestamp': result.get('timestamp'),
                    'success': result.get('success')
                })
                
                render_results(result)
            else:
                st.error(f"API Error: {response.status_code} - {response.text}")
        
        except requests.exceptions.Timeout:
            st.error("Request timeout. Query took too long to execute.")
        except requests.exceptions.ConnectionError:
            st.error(f"Cannot connect to API at {api_url}")
        except Exception as e:
            st.error(f"Unexpected error: {str(e)}")

if st.session_state['query_history']:
    with st.expander("Query History"):
        for i, item in enumerate(reversed(st.session_state['query_history'][-10:])):
            status = "✅" if item['success'] else "❌"
            st.markdown(f"{status} **{item['query'][:100]}...** - {item['timestamp']}")

st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray;'>
    Built with LangChain, FastAPI, Streamlit | Powered by GPT-4o & Claude Haiku
    </div>
    """,
    unsafe_allow_html=True
)