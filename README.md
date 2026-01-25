# Agentic RAG Analytics

Multi-agent SQL query system using LangGraph to interact with PostgreSQL analytics warehouse.

## 🎯 Project Overview

This project demonstrates a production-ready agentic RAG system that converts natural language questions into SQL queries, executes them, and delivers results via email. Built with a focus on separation of concerns, each agent has a single responsibility in the pipeline.

### Agent Architecture
```
User Query
    ↓
Router Agent (GPT-4o)
    ├─→ Determines if SQL is required
    ├─→ Determines if email is required
    └─→ Identifies relevant tables/predictions
    ↓
SQL Agent (Claude Haiku 4)
    ├─→ Retrieves relevant schema from Chroma embeddings
    ├─→ Generates PostgreSQL query
    └─→ NO execution (generation only)
    ↓
Executor Agent (psycopg2)
    ├─→ Executes SQL query
    ├─→ Writes results to CSV
    └─→ Uploads CSV to S3/MinIO
    ↓
Email Agent (Gmail/SES)
    ├─→ Reads CSV from S3/MinIO
    ├─→ Formats email with results
    └─→ Sends via SMTP
```

## 🏗️ Architecture Components

### Agents (LangGraph)

**Router Agent** (`agents/router_agent/`)
- **LLM**: OpenAI GPT-4o
- **Responsibility**: Planning only - decides query requirements
- **No database access**: Pure reasoning layer

**SQL Agent** (`agents/sql_agent/`)
- **LLM**: Anthropic Claude Haiku 4 (`claude-haiku-4-20250514`)
- **Responsibility**: SQL generation only
- **RAG**: Retrieves schema context from Chroma embeddings
- **No execution**: Returns SQL string

**Executor Agent** (`agents/executor_agent/`)
- **Technology**: psycopg2 (Python PostgreSQL driver)
- **Responsibility**: Execute SQL, write CSV, upload to S3
- **Retry Logic**: SQL Agent regenerates on error (max 3 attempts)
- **Deterministic**: No LLM reasoning

**Email Agent** (`agents/email_agent/`)
- **Technology**: Python SMTP (Gmail) / AWS SES (production)
- **Responsibility**: Read CSV from S3, format and send email
- **No database access**: Works only with S3 artifacts

### Backend (FastAPI)

- **API Endpoints** (`app/routers/query.py`): POST /query endpoint
- **Redis Caching** (`app/utils/redis_cache.py`): Caches S3 paths by query hash
- **Langfuse Tracking** (`app/utils/langfuse_tracker.py`): Monitors all 4 agents separately
- **Pydantic Models** (`app/models/schemas.py`): Request/response validation

### Frontend (Streamlit)

- **Chat Interface** (`streamlit_app/components/chat_ui.py`): Natural language query input
- **Result Viewer** (`streamlit_app/components/result_viewer.py`): Display SQL, results, agent reasoning
- **Analytics Dashboard** (`streamlit_app/pages/analytics.py`): Query history, cache hit rates

### Schema Embeddings

**Structured Markdown Files** (`schema/source/`)
- One file per table (customers, products, orders, etc.)
- Relationships file for join patterns
- Analytics patterns file for common query concepts
- **Embedding Model**: OpenAI `text-embedding-3-small`
- **Vector DB**: Chroma DB
- **Generation**: One-time in Colab, loaded at startup

### Storage

**PostgreSQL** (Supabase - development, RDS - production)
- Clean normalized tables (customers, products, orders, order_items, subscriptions)
- ML prediction tables (churn_predictions, forecast_predictions)

**MinIO** (local) / **S3** (production)
- CSV query results
- Email attachments
- Report artifacts

**Redis**
- Cache S3 paths by query hash
- 24-hour TTL
- 99% hit rate target after warmup

**Chroma DB**
- Schema embeddings
- Persistent storage in `./embeddings/`

## 🚀 Quick Start

### Prerequisites

- Python 3.11.9
- Docker Desktop
- MinIO (local S3-compatible storage)
- PostgreSQL access (Supabase)
- OpenAI API key
- Anthropic API key
- Langfuse account

### 1. Clone and Setup
```bash
git clone https://github.com/YOUR_USERNAME/agentic-rag-analytics.git
cd agentic-rag-analytics

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
# Copy environment template
copy .env.example .env  # Windows
cp .env.example .env    # Linux/Mac

# Edit .env with your credentials
# - Database: Supabase connection details
# - S3/MinIO: MinIO local endpoint
# - LLM APIs: OpenAI and Anthropic keys
# - Redis, Chroma, Langfuse settings
```

### 3. Start MinIO (Local Development)

**Option A: Docker (Recommended)**
```bash
docker-compose up minio minio-client -d
```

**Option B: Manual**
```bash
# Start MinIO server
minio.exe server C:\minio\data --console-address ":9001"

# Access console: http://localhost:9001
# Login: minioadmin / minioadmin
# Create bucket: rag-reports
```

### 4. Generate Schema Embeddings (One-Time)

**Run in Google Colab:**
```python
# Upload schema/source/*.md files to Colab
# Run embedding notebook (provided separately)
# Download embeddings/ folder
# Place in project root
```

### 5. Start Services
```bash
# Start all services
docker-compose up -d

# Verify services
docker ps

# Expected services:
# - rag_minio (ports 9000, 9001)
# - rag_redis (port 6380)
# - rag_chroma (port 8082)
# - rag_fastapi (port 8001)
# - rag_streamlit (port 8501)
```

### 6. Access Application

- **Streamlit UI**: http://localhost:8501
- **FastAPI Docs**: http://localhost:8001/docs
- **MinIO Console**: http://localhost:9001
- **Chroma Admin**: http://localhost:8082

## 📊 Example Queries
```
"Show me top 10 customers by revenue in the West region"
"What are the high churn risk customers for December 2025?"
"Forecast demand for Electronics category in Midwest for next month"
"Compare revenue across all regions for Q4 2025"
```

## 🧪 Testing
```bash
# Run tests
pytest tests/

# Test individual agents
pytest tests/test_agents.py::test_router_agent
pytest tests/test_agents.py::test_sql_agent
pytest tests/test_agents.py::test_executor_agent
```

## 📦 Deployment

### Kubernetes (Demonstration Only)
```bash
# Apply K8s templates (NOT for production deployment)
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

# Note: K8s files are for portfolio demonstration
# Actual deployment target is AWS ECS Fargate
```

### AWS ECS Fargate (Future)

- Replace MinIO with S3
- Replace Gmail with SES
- Replace Supabase with RDS PostgreSQL
- Use AWS Secrets Manager for credentials
- Deploy FastAPI and Streamlit as ECS services

### Agent Configuration

**SQL Retry Logic**
- Max retries: 3
- Error-based regeneration: SQL Agent receives error message
- Timeout: 30 seconds per query

**Cache Strategy**
- Cache key: MD5 hash of user query
- TTL: 24 hours
- Invalidation: Manual or on schema changes

## 📈 Monitoring

### Langfuse Dashboard

Track all agents separately:
- Router Agent: Planning decisions
- SQL Agent: Query generation, retrieval context, retries
- Executor Agent: Execution time, result size
- Email Agent: Delivery success

### Redis Cache Metrics

- Hit rate: Target 99% after warmup
- Cache size: Monitor memory usage
- Eviction policy: LRU

## 🛠️ Development

### Adding New Tables

1. Create schema file in `schema/source/table_name.md`
2. Update `relationships.md` with new joins
3. Regenerate embeddings in Colab
4. Update `analytics_patterns.md` with new query patterns

### Testing New Queries
```bash
# Use FastAPI directly
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Show top 5 products by revenue"}'
```

## 📝 Project Structure
```
agentic-rag-analytics/
├── agents/
│   ├── router_agent/       # GPT-4o planning
│   ├── sql_agent/          # Claude Haiku SQL generation
│   ├── executor_agent/     # psycopg2 execution
│   └── email_agent/        # SMTP email delivery
├── app/
│   ├── routers/            # FastAPI endpoints
│   ├── utils/              # Redis, Langfuse utilities
│   └── models/             # Pydantic schemas
├── streamlit_app/
│   ├── components/         # Reusable UI components
│   └── pages/              # Multi-page app
├── schema/
│   └── source/             # Structured .md files for embeddings
├── embeddings/             # Chroma DB (gitignored)
├── config/                 # Service configurations
├── k8s/                    # Kubernetes templates (demo)
├── tests/                  # Unit and integration tests
├── docker-compose.yml      # Local development
├── requirements.txt        # Python dependencies
└── README.md
```

## 🎓 Key Design Decisions

### Why Separate SQL Generation from Execution?
- **Testability**: SQL can be validated without database access
- **Security**: SQL Agent has no database credentials
- **Debugging**: Inspect generated SQL before execution
- **Retry Logic**: Regenerate SQL based on execution errors

### Why psycopg2 Instead of Spark?
- **Latency**: Sub-second response vs. 2-5 second JVM startup
- **Simplicity**: No cluster management, pure Python
- **Cost**: No Spark driver/executor overhead
- **Use Case**: Analytics queries on normalized tables, not big data ETL

### Why Claude Haiku for SQL?
- **Cost**: 20x cheaper than GPT-4o
- **Quality**: Excellent SQL generation capabilities
- **Speed**: Lower latency than larger models
- **Budget**: Preserves OpenAI credits for planning/orchestration

### Why Chroma for Embeddings?
- **Simplicity**: Single-node vector DB, no cluster
- **Python Native**: Easy integration
- **Persistent**: Disk-backed storage
- **Lightweight**: Perfect for schema documentation scale

## 🤝 Contributing

This is a portfolio project. Contributions are not currently accepted, but feedback is welcome!

## 📄 License

MIT License - See LICENSE file for details

## 📧 Contact

For questions or interview discussions, contact: [your_email@example.com]

---

**Built with:** Python 3.11 • LangChain • FastAPI • Streamlit • PostgreSQL • Redis • MinIO • Chroma • Langfuse