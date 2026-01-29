# Agentic RAG Analytics

A multi-agent system that converts natural language questions into SQL queries, executes them against a PostgreSQL data warehouse, and delivers results via email. Built on a serverless architecture using Supabase, Upstash, and managed LLM APIs, with local ChromaDB for RAG-based schema retrieval.

## Architecture Overview

```
User Query (Streamlit / API)
         |
         v
  +------------------+
  |  FastAPI Server   |  POST /query/
  +------------------+
         |
         v
  +------------------+     Cache Hit?
  |  Upstash Redis   | ──────────────> Return cached result (<1s)
  +------------------+
         |  Cache Miss
         v
  +------------------+
  |  Router Agent    |  GPT-4o determines SQL/email requirements
  +------------------+
         |
         v
  +------------------+     ChromaDB
  |   SQL Agent      | <── Schema Retrieval (RAG)
  |  Claude Haiku    |     81 embedded chunks
  +------------------+
         |
         v
  +------------------+
  | Executor Agent   |  PostgreSQL (Supabase) -> CSV + SQL -> S3
  +------------------+
         |
         v
  +------------------+
  |  Email Agent     |  Background task: SMTP + CSV attachment
  +------------------+
```

**Serverless by design.** PostgreSQL, Redis, and object storage run as managed services (Supabase + Upstash). Only ChromaDB runs locally. No infrastructure to maintain beyond a single Docker container or local process.

## Features

- **Natural language to SQL** -- Ask questions in plain English, get executed query results
- **Multi-agent orchestration** -- Four specialized agents handle routing, SQL generation, execution, and delivery
- **Two-layer caching** -- Upstash Redis caches both generated SQL and full results (24h TTL)
- **RAG-powered schema retrieval** -- ChromaDB vector search provides relevant table context to the SQL agent
- **Dual file storage** -- Both CSV results and SQL query files uploaded to S3 with date-based organization
- **Email delivery** -- HTML emails with data preview tables and CSV attachments, sent as background tasks
- **Automatic retry and regeneration** -- Up to 3 attempts for SQL generation and execution, with error context fed back for correction
- **SQL safety** -- Read-only database connections, SELECT-only validation, forbidden keyword blocking, 30-second query timeout
- **Observability** -- Langfuse tracing on Router Agent, SQL Agent, and the main endpoint via `@observe` decorators
- **Cost-optimized model selection** -- GPT-4o for routing decisions, Claude Haiku for SQL generation (20x cheaper)

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| API | FastAPI 0.128.0 | REST endpoint, background tasks |
| Frontend | Streamlit 1.53.1 | Interactive query interface |
| Router Agent | OpenAI GPT-4o | Query analysis, routing decisions |
| SQL Agent | Anthropic Claude Haiku | SQL generation from natural language |
| Embeddings | OpenAI text-embedding-3-small | Schema vector embeddings |
| Vector DB | ChromaDB 0.4.24 | Local schema retrieval (RAG) |
| Database | Supabase PostgreSQL | Data warehouse |
| Cache | Upstash Redis (REST API) | Two-layer query/result caching |
| Object Storage | Supabase Storage (S3-compatible) | CSV and SQL file storage |
| Monitoring | Langfuse | Agent tracing, cost tracking |
| Email | Gmail SMTP | Result delivery with attachments |

## Project Structure

```
agentic-rag-analytics/
|-- agents/
|   |-- router_agent/
|   |   |-- __init__.py
|   |   |-- router.py              # GPT-4o routing with @observe
|   |   +-- prompts.py             # System prompt, user template
|   |-- sql_agent/
|   |   |-- __init__.py
|   |   |-- generator.py           # Claude Haiku SQL generation with @observe
|   |   |-- retriever.py           # ChromaDB schema retrieval
|   |   +-- prompts.py             # SQL generation/regeneration prompts
|   |-- executor_agent/
|   |   |-- __init__.py
|   |   |-- executor.py            # SQL execution, CSV/SQL file creation
|   |   +-- s3_uploader.py         # Supabase Storage (S3-compatible) uploads
|   +-- email_agent/
|       |-- __init__.py
|       |-- sender.py              # SMTP email with attachments
|       +-- templates.py           # HTML and plain text email templates
|-- app/
|   |-- __init__.py
|   |-- main.py                    # FastAPI entry point, CORS, health check
|   |-- config.py                  # Pydantic v2 settings from .env
|   |-- routers/
|   |   +-- query.py               # POST /query/ orchestration endpoint
|   |-- models/
|   |   +-- schemas.py             # Pydantic request/response models
|   +-- utils/
|       +-- redis_cache.py         # Upstash Redis REST API client
|-- streamlit_app/
|   |-- app.py                     # Main Streamlit application
|   |-- components/
|   |   |-- chat_ui.py             # Query input, example queries
|   |   +-- result_viewer.py       # Tabbed result display
|   +-- pages/
|       +-- analytics.py           # Analytics dashboard (placeholder)
|-- schema/
|   +-- source/                    # 9 markdown files documenting tables
|       |-- customers.md
|       |-- products.md
|       |-- orders.md
|       |-- order_items.md
|       |-- subscriptions.md
|       |-- churn_predictions.md
|       |-- forecast_predictions.md
|       |-- relationships.md
|       +-- analytics_patterns.md
|-- notebooks/
|   +-- generate_embeddings.ipynb  # Schema embedding generation
|-- embeddings/                    # ChromaDB persistent storage (gitignored)
|-- tests/
|   |-- conftest.py                # 30+ shared fixtures
|   |-- test_agents/               # Unit tests for all 4 agents
|   |-- test_api/                  # Endpoint tests
|   |-- test_utils/                # Cache and config tests
|   +-- integration/               # End-to-end pipeline tests
|-- k8s/
|   |-- configmap.yaml
|   |-- deployment.yaml
|   +-- service.yaml
|-- docker-compose.yml
|-- Dockerfile.api
|-- Dockerfile.streamlit
|-- requirements.txt
|-- pytest.ini
+-- .env.example
```

## Prerequisites

- Python 3.11.9
- [Supabase](https://supabase.com) account (PostgreSQL database + Storage)
- [Upstash](https://upstash.com) account (serverless Redis)
- [OpenAI](https://platform.openai.com) API key
- [Anthropic](https://console.anthropic.com) API key
- Gmail account with [app-specific password](https://support.google.com/accounts/answer/185833)
- [Langfuse](https://langfuse.com) account (optional, for observability)

## Installation

### 1. Clone and set up the environment

```bash
git clone https://github.com/your-username/agentic-rag-analytics.git
cd agentic-rag-analytics
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
# Edit .env with your credentials
```

All required variables are documented in `.env.example`. Key settings:

| Variable | Description |
|----------|-------------|
| `DB_HOST` | Supabase PostgreSQL host (`db.xxxxx.supabase.co`) |
| `S3_ENDPOINT_URL` | Supabase Storage endpoint (`https://xxxxx.supabase.co`) |
| `UPSTASH_REDIS_REST_URL` | Upstash Redis REST URL |
| `UPSTASH_REDIS_REST_TOKEN` | Upstash Redis REST token |
| `OPENAI_API_KEY` | OpenAI API key (for GPT-4o + embeddings) |
| `ANTHROPIC_API_KEY` | Anthropic API key (for Claude Haiku) |
| `ANTHROPIC_SQL_MODEL` | `claude-3-5-haiku-20241022` |
| `SMTP_USER` | Gmail address |
| `SMTP_PASSWORD` | Gmail app-specific password |
| `LANGFUSE_PUBLIC_KEY` | Langfuse public key (optional) |
| `LANGFUSE_SECRET_KEY` | Langfuse secret key (optional) |

### 3. Generate schema embeddings

This step is required before the first run. It creates 81 vector chunks from 9 schema documentation files.

```bash
# Start ChromaDB
chroma run --path ./embeddings --port 8082

# In another terminal, run the embedding notebook
jupyter notebook notebooks/generate_embeddings.ipynb
```

Follow the notebook cells to embed all schema files into the `agentic_rag_analytics_schema` collection. One-time cost: approximately $0.02.

### 4. Verify setup

```bash
# ChromaDB should be running on port 8082
curl http://localhost:8082/api/v1/heartbeat
```

## Running the Application

### Local development (three terminals)

```bash
# Terminal 1: ChromaDB
chroma run --path ./embeddings --port 8082

# Terminal 2: FastAPI
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

# Terminal 3: Streamlit
streamlit run streamlit_app/app.py --server.port 8501
```

Access the application:
- Streamlit UI: http://localhost:8501
- API docs: http://localhost:8001/docs
- Health check: http://localhost:8001/health

### Docker

```bash
docker-compose up -d
```

This starts three containers:
- `rag-chromadb` -- ChromaDB on port 8082
- `rag-api` -- FastAPI on port 8001
- `rag-streamlit` -- Streamlit on port 8501

External services (Supabase PostgreSQL, Upstash Redis, Supabase Storage) are accessed via environment variables. Only ChromaDB runs locally.

## Usage

### Streamlit interface

Open http://localhost:8501 and type a natural language query. Optionally provide an email address for result delivery. The interface shows:
- Routing decision details
- Generated SQL
- Result preview table
- Download links for CSV and SQL files
- Execution metadata (row count, columns, timing)

### API

```bash
# Basic query
curl -X POST http://localhost:8001/query/ \
  -H "Content-Type: application/json" \
  -d '{"query": "Show top 10 customers by total revenue"}'

# Query with email delivery
curl -X POST http://localhost:8001/query/ \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Show high churn risk customers for December 2025",
    "user_email": "analyst@company.com"
  }'

# Query with caching disabled
curl -X POST http://localhost:8001/query/ \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Compare revenue by region for Q4 2025",
    "enable_cache": false
  }'

# Health check
curl http://localhost:8001/health
```

### Example queries

- "Show top 10 customers by total revenue"
- "Email me high churn risk customers for December 2025"
- "Compare revenue by region for Q4 2025"
- "What are the best selling products by category?"
- "List customers with more than 3 failed payments in the last 30 days"
- "Show monthly subscription revenue trends"

## Database Schema

Seven tables across three categories:

**Dimension tables:**
- `customers` -- Customer profiles (region, state, email)
- `products` -- Product catalog (SKU, category, base price)

**Fact tables:**
- `orders` -- Order headers with timestamps
- `order_items` -- Line items with quantity and unit price
- `subscriptions` -- Subscription events (plan, status, billing cycle)

**Analytics tables:**
- `churn_predictions` -- ML model outputs (probability, flag, snapshot month)
- `forecast_predictions` -- Demand forecasts by product and region

Schema documentation is maintained in 9 markdown files under `schema/source/`, including relationship definitions and common analytics patterns. These files are embedded into ChromaDB for RAG-based retrieval.

## Caching Strategy

The system implements two-layer caching through Upstash Redis (REST API) to minimize redundant LLM calls and database queries.

**How it works:**

| Execution | What happens | Latency |
|-----------|-------------|---------|
| First (cold) | Route -> Generate SQL -> Execute -> Upload -> Cache result | 10-15s |
| Second (warm) | Retrieve SQL from cache -> Execute -> Cache result | 3-5s |
| Repeated (hot) | Return cached result directly | <1s |

Cache keys are generated by normalizing the query (lowercase, collapse whitespace) and hashing with SHA-256. The prefix `result_v2` namespaces result entries.

**Cache safety:** When retrieving a cached entry, the system verifies the stored query matches the requested query. Mismatched or non-dict entries are deleted and recomputed. This prevents hash collisions from returning incorrect results.

**TTL:** 24 hours (86,400 seconds), configurable via `REDIS_CACHE_TTL`.

**Bypass:** Set `enable_cache: false` in the request to skip caching.

## Cost Optimization

### Model selection rationale

| Agent | Model | Input / Output cost (per 1M tokens) | Rationale |
|-------|-------|--------------------------------------|-----------|
| Router | GPT-4o | $2.50 / $10.00 | Best structured JSON output |
| SQL Generator | Claude Haiku | $0.80 / $4.00 | Excellent SQL ability at a fraction of GPT-4o cost |
| Embeddings | text-embedding-3-small | $0.02 | Cost-effective for schema retrieval |

### Per-query cost estimates

- Uncached query: $0.01 - $0.03
- With 50% cache hit rate: $0.005 - $0.015 average
- Monthly estimate (10K queries): $50 - $150

The two-layer cache reduces API calls by 60-80% in typical usage patterns.

## Monitoring and Observability

### Langfuse integration

The system uses Langfuse for tracing agent execution:

- `@observe(name="router_agent")` on `RouterAgent.route()`
- `@observe(name="sql_agent")` on `SQLAgent.generate_sql()`
- OpenAI calls are traced automatically via the `langfuse.openai` wrapper
- Anthropic calls are not traced (no Langfuse wrapper available for the Anthropic SDK)

### Metrics available in Langfuse dashboard

- Agent-level latency breakdown
- Token usage per model
- Cost attribution per query
- Error rates and stack traces
- Cache hit rates (via logged metadata)

Dashboard: https://us.cloud.langfuse.com

## Testing

178 tests covering all agents, utilities, API endpoints, and end-to-end flows. All external services are mocked -- no real API calls during testing.

```
tests/
|-- conftest.py                    # 30+ shared fixtures
|-- test_agents/
|   |-- test_router_agent.py       # 16 tests: routing, JSON parsing, markdown stripping
|   |-- test_sql_agent.py          # 24 tests: generation, validation, schema retrieval
|   |-- test_executor_agent.py     # 24 tests: execution, S3 upload, file cleanup
|   +-- test_email_agent.py        # 15 tests: delivery, attachments, preview tables
|-- test_api/
|   |-- test_query_endpoint.py     # 18 tests: pipeline, retries, caching, validation
|   +-- test_health_endpoint.py    # 13 tests: health, root, CORS, OpenAPI
|-- test_utils/
|   |-- test_redis_cache.py        # 28 tests: key generation, normalization, hit/miss
|   +-- test_config.py             # 15 tests: defaults, env loading, all config sections
+-- integration/
    +-- test_end_to_end.py         # 13 tests: full pipeline, retry, caching, models
```

### Running tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run a specific file
python -m pytest tests/test_agents/test_router_agent.py -v

# Run with coverage
python -m pytest tests/ --cov=app --cov=agents --cov-report=term-missing

# Exclude integration tests
python -m pytest tests/ -v -m "not integration"
```

All 178 tests pass in under 15 seconds.

## Deployment

### Docker Compose

```bash
docker-compose up -d
```

Three services are orchestrated with health checks and dependency ordering:
- ChromaDB starts first (healthcheck: heartbeat API)
- API starts after ChromaDB is healthy
- Streamlit starts after API is healthy

### Kubernetes

Manifests in `k8s/` provide production-grade deployment:

- **ConfigMap** (`configmap.yaml`) -- Non-sensitive configuration
- **Deployment** (`deployment.yaml`) -- 2 API replicas, 1 ChromaDB with 5Gi PVC, 1 Streamlit
- **Service** (`service.yaml`) -- ClusterIP for internal services, LoadBalancer for Streamlit

Resource limits:
- API: 512Mi request / 1Gi limit
- Streamlit: 256Mi request / 512Mi limit
- ChromaDB: 5Gi persistent volume

## Troubleshooting

### ChromaDB

| Symptom | Solution |
|---------|----------|
| Collection not found | Run `notebooks/generate_embeddings.ipynb` to create embeddings |
| Connection refused on 8082 | Start ChromaDB: `chroma run --path ./embeddings --port 8082` |
| Telemetry warnings in logs | Harmless; already disabled via `ANONYMIZED_TELEMETRY=False` |

### Redis cache

| Symptom | Solution |
|---------|----------|
| Stale results | Set `enable_cache: false` in request, or wait for 24h TTL |
| Cache errors in logs | Verify `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN` |
| Non-dict cache entries | System auto-deletes invalid entries on next request |

### SQL generation

| Symptom | Solution |
|---------|----------|
| Empty SQL output | Check `ANTHROPIC_API_KEY` quota and validity |
| Wrong tables referenced | Verify schema embeddings match current database |
| `created_at` flagged as forbidden | Known: substring match catches `CREATE` in `created_at`. Does not affect query execution (validation is advisory) |

### Email delivery

| Symptom | Solution |
|---------|----------|
| Authentication failed | Use a Gmail app-specific password, not your account password |
| Connection refused | Verify `SMTP_HOST=smtp.gmail.com` and `SMTP_PORT=587` |
| No attachment | CSV must be uploaded to S3 before email is sent (happens automatically) |

### Langfuse

| Symptom | Solution |
|---------|----------|
| No traces visible | Verify `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` in `.env` |
| Missing Anthropic traces | Expected: no Langfuse wrapper exists for the Anthropic SDK |
| Wrong region | Ensure `LANGFUSE_BASE_URL` matches your account region (US vs EU) |
