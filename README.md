# Agentic RAG Analytics

SQL agent system with LangGraph for querying ML warehouse.

## Components
- **Agents**: LangGraph orchestration (SQL, Report, Email agents)
- **App**: FastAPI backend
- **Streamlit**: Chat interface
- **Embeddings**: Schema documentation (Chroma DB)

## Agent Flow
User Query → Orchestrator → SQL Agent (GPT-4o/3.5) → Report Agent (Claude) → Email Agent

## Setup
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

copy .env.example .env
# Configure OpenAI, Anthropic, Langfuse keys

docker-compose up -d
```

## Monitoring
- Langfuse: Track agent steps, latencies, token usage
- Redis: 99% cache hit rate after warmup