# Agentic RAG Analytics

Natural language to SQL query execution system using a multi-agent architecture with LangGraph. The system converts user questions into SQL queries, executes them against a PostgreSQL database, and delivers results via email or web interface.

## Architecture Overview

### Multi-Agent System
- **Router Agent**: Analyzes queries using GPT-4o to determine SQL requirements and email delivery needs
- **SQL Agent**: Generates SQL queries using Claude 3.5 Haiku with RAG-based schema retrieval
- **Executor Agent**: Executes queries safely with timeout protection and stores results in cloud storage
- **Email Agent**: Delivers formatted results with CSV attachments via SMTP

### Technology Stack

**Backend:**
- FastAPI for REST API
- LangGraph for agent orchestration
- ChromaDB for schema embeddings (local)
- OpenAI GPT-4o for routing and embeddings
- Anthropic Claude 3.5 Haiku for SQL generation

**Storage:**
- Supabase PostgreSQL for data warehouse
- Supabase Storage (S3-compatible) for result files
- Upstash Redis for two-layer caching (SQL + results)

**Frontend:**
- Streamlit for web interface

**Monitoring:**
- Langfuse for agent tracing and cost tracking

## Features

### Core Capabilities
- Natural language to SQL conversion
- Multi-table query support with automatic JOIN generation
- Query result caching (24-hour TTL)
- SQL query caching for instant regeneration
- Email delivery with CSV attachments
- Real-time query execution tracking
- Secure read-only database access

### Supported Query Types
- Revenue analytics and aggregations
- Customer lifetime value calculations
- Churn risk analysis
- Demand forecasting
- Multi-region comparisons
- Time-series analysis

## Project Structure
```
agentic-rag-analytics/
├── agents/
│   ├── router_agent/          # GPT-4o routing logic
│   ├── sql_agent/             # Claude Haiku SQL generation + RAG
│   ├── executor_agent/        # Query execution + S3 upload
│   └── email_agent/           # Email delivery
├── app/
│   ├── routers/               # FastAPI endpoints
│   ├── utils/                 # Redis cache, Langfuse tracker
│   ├── models/                # Pydantic schemas
│   ├── config.py              # Environment configuration
│   └── main.py                # FastAPI application
├── streamlit_app/             # Web interface
├── schema/
│   └── source/                # Database schema documentation (9 files)
├── embeddings/                # ChromaDB vector store (gitignored)
├── notebooks/                 # Embedding generation notebook
├── tests/                     # Unit and integration tests
├── .env.example               # Environment variables template
├── requirements.txt           # Python dependencies
└── README.md
```

## Prerequisites

- Python 3.11.9
- Supabase account (PostgreSQL + Storage)
- Upstash account (Redis)
- OpenAI API key
- Anthropic API key
- Gmail account with app password (for email delivery)
- Langfuse account (optional, for monitoring)

## Installation

### 1. Clone Repository
```bash
git clone https://github.com/yourusername/agentic-rag-analytics.git
cd agentic-rag-analytics
```

### 2. Create Virtual Environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
```bash
# Copy template
cp .env.example .env

# Edit .env with your credentials
notepad .env  # Windows
nano .env     # macOS/Linux
```

Required variables:
- Database: `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- Supabase Storage: `S3_ENDPOINT_URL`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
- Upstash Redis: `UPSTASH_REDIS_REST_URL`, `UPSTASH_REDIS_REST_TOKEN`
- OpenAI: `OPENAI_API_KEY`
- Anthropic: `ANTHROPIC_API_KEY`
- Email: `SMTP_USER`, `SMTP_PASSWORD`
- Langfuse (optional): `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`

### 5. Generate Schema Embeddings

**Option A: Run Jupyter Notebook**
```bash
cd notebooks
jupyter notebook generate_embeddings.ipynb
# Run all cells
# Download embeddings/ folder to project root
```

**Option B: Use Pre-generated Embeddings**
```bash
# If you have embeddings.zip
unzip embeddings.zip
```

## Running the Application

### Local Development (No Docker)

**Terminal 1: ChromaDB**
```bash
chroma run --path ./embeddings --port 8082
```

**Terminal 2: FastAPI Backend**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

**Terminal 3: Streamlit Frontend**
```bash
streamlit run streamlit_app/app.py --server.port 8501
```

### Access Points
- API Documentation: http://localhost:8001/docs
- Health Check: http://localhost:8001/health
- Streamlit UI: http://localhost:8501

## Usage

### Via Streamlit UI

1. Open http://localhost:8501
2. Enter natural language query (e.g., "Show top 10 customers by revenue")
3. Optionally provide email for delivery
4. Click "Execute Query"
5. View results and download CSV

### Via API
```bash
curl -X POST http://localhost:8001/query/ \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Show top 10 customers by revenue",
    "user_email": "your@email.com",
    "enable_cache": true
  }'
```

### Example Queries
```
Show top 10 customers by revenue
What are the high churn risk customers for December 2025?
Compare revenue across all regions for Q4 2025
Email me the list of customers with failed payments
Show best selling products by category
What is the average order value by region?
List customers who have not ordered in 90 days
```

## Database Schema

### Dimension Tables
- **customers**: Customer master data with demographics
- **products**: Product catalog with pricing

### Fact Tables
- **orders**: Order transactions
- **order_items**: Line-item details
- **subscriptions**: Subscription events and status

### Analytics Tables
- **churn_predictions**: ML-based churn risk scores
- **forecast_predictions**: Demand forecasting results

## Caching Strategy

### Two-Layer Cache
1. **SQL Cache**: Stores generated SQL queries (key: query hash)
2. **Result Cache**: Stores execution results and metadata (key: query hash)

### Cache Behavior
- First execution: Generate SQL, execute, cache both
- Second execution: Retrieve SQL from cache, execute, cache result
- Third+ execution: Retrieve result directly from cache
- TTL: 24 hours for both layers

### Cache Performance
- Cold query: 10-15 seconds (full pipeline)
- Warm query (SQL cached): 3-5 seconds (execution only)
- Hot query (result cached): <1 second (instant retrieval)

## Cost Optimization

### Model Selection
- **Routing**: GPT-4o ($2.50/$10.00 per 1M tokens)
- **SQL Generation**: Claude 3.5 Haiku ($0.80/$4.00 per 1M tokens)
- **Embeddings**: text-embedding-3-small ($0.02 per 1M tokens)

### Estimated Costs
- Per query (uncached): $0.01-0.03
- Per 1000 queries with 50% cache hit: $5-15
- Monthly (10K queries): $50-150

## Monitoring

### Langfuse Integration
- Agent-level tracing (Router, SQL, Executor, Email)
- Token usage tracking per model
- Latency measurements
- Error tracking and retry counts
- Cost attribution by query

### Metrics Dashboard
Access Langfuse dashboard at https://cloud.langfuse.com to view:
- Query success/failure rates
- Average execution time per agent
- Cache hit rates
- API cost breakdown
- Query complexity distribution

## Testing
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_agents.py

# Run with coverage
pytest --cov=app --cov=agents
```

## Deployment

### Docker Deployment

**Build Images:**
```bash
docker build -f Dockerfile.api -t rag-analytics-api .
docker build -f Dockerfile.streamlit -t rag-analytics-streamlit .
```

**Run Containers:**
```bash
docker-compose up -d
```

### Production Considerations
- Use production database with connection pooling
- Enable HTTPS/TLS for API endpoints
- Implement rate limiting
- Set up log aggregation (e.g., CloudWatch)
- Use secrets manager for credentials (e.g., AWS Secrets Manager)
- Configure autoscaling based on load
- Set up database read replicas for high traffic

## Troubleshooting

### Common Issues

**ChromaDB Connection Failed**
```bash
# Ensure ChromaDB is running
chroma run --path ./embeddings --port 8082

# Check embeddings exist
ls embeddings/
```

**Redis Cache Errors**
```bash
# Clear cache via API
curl -X POST http://localhost:8001/clear-cache

# Verify Upstash credentials in .env
```

**SQL Generation Errors**
- Check Anthropic API key and quota
- Verify schema files exist in schema/source/
- Review Langfuse trace for error details

**Email Delivery Failed**
- Verify Gmail app password (not regular password)
- Enable "Less secure app access" if needed
- Check SMTP settings in .env

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/your-feature`)
3. Commit changes (`git commit -m 'Add feature'`)
4. Push to branch (`git push origin feature/your-feature`)
5. Open Pull Request

## License

MIT License - see LICENSE file for details

## Acknowledgments

- LangChain for agent orchestration framework
- Anthropic for Claude API
- OpenAI for GPT and embedding models
- Supabase for managed PostgreSQL and storage
- Upstash for serverless Redis
- Langfuse for monitoring and tracing

## Contact

For questions or support, please open an issue on GitHub.