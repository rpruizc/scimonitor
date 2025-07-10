# DLMonitor API 2.0

Modern FastAPI backend for the DLMonitor deep learning research monitoring platform.

## 🚀 Features

- **FastAPI Framework**: Modern, fast, and auto-documented API
- **Async/Await**: Fully asynchronous with excellent performance
- **Type Hints**: Complete type safety with Pydantic models
- **Auto Documentation**: Interactive API docs at `/docs`
- **Health Checks**: Comprehensive monitoring endpoints
- **Docker Ready**: Multi-stage Dockerfile for production
- **Environment Config**: Pydantic Settings for configuration
- **Structured Logging**: JSON logging with contextual information
- **Error Tracking**: Sentry integration for production monitoring

## 📋 Prerequisites

- Python 3.11+
- Redis (for caching and sessions)
- PostgreSQL 15+ (for data storage)
- Docker & Docker Compose (recommended)

## 🛠️ Quick Start

### Using Docker Compose (Recommended)

1. **Clone and navigate to the API directory:**
   ```bash
   cd dlmonitor_api
   ```

2. **Create environment file:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start all services:**
   ```bash
   docker-compose up -d
   ```

4. **Check the API:**
   - API: http://localhost:8000
   - Docs: http://localhost:8000/docs
   - Health: http://localhost:8000/api/v1/health

### Local Development

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Start Redis and PostgreSQL** (using Docker):
   ```bash
   docker-compose up -d db redis
   ```

3. **Run the development server:**
   ```bash
   python run.py
   ```

## 📁 Project Structure

```
dlmonitor_api/
├── app/
│   ├── api/
│   │   └── v1/
│   │       └── endpoints/
│   │           └── health.py          # Health check endpoints
│   ├── core/
│   │   └── settings.py                # Application configuration
│   ├── db/                           # Database models and utilities
│   ├── models/                       # SQLAlchemy models
│   ├── schemas/                      # Pydantic schemas
│   └── main.py                       # FastAPI application
├── tests/                            # Test suite
├── Dockerfile                        # Production container
├── docker-compose.yml               # Development environment
├── requirements.txt                 # Python dependencies
└── run.py                          # Development server runner
```

## 🔧 Configuration

All configuration is handled through environment variables using Pydantic Settings:

### Core Settings
- `ENVIRONMENT`: development/staging/production
- `DEBUG`: Enable debug mode
- `SECRET_KEY`: JWT signing secret
- `HOST`: Server host (default: 0.0.0.0)
- `PORT`: Server port (default: 8000)

### Database
- `DATABASE_URL`: PostgreSQL connection string
- `DATABASE_ECHO`: Log SQL queries

### Redis
- `REDIS_URL`: Redis connection string

### External APIs
- `OPENAI_API_KEY`: OpenAI API key for AI features
- `ANTHROPIC_API_KEY`: Anthropic API key for AI features
- `TWITTER_BEARER_TOKEN`: Twitter API bearer token
- `REDDIT_CLIENT_ID`: Reddit API client ID
- `REDDIT_CLIENT_SECRET`: Reddit API client secret
- `GITHUB_TOKEN`: GitHub API token

### Monitoring
- `SENTRY_DSN`: Sentry error tracking DSN
- `LOG_LEVEL`: Logging level (DEBUG/INFO/WARNING/ERROR)

## 🏥 Health Checks

The API provides comprehensive health monitoring:

- **Basic Health**: `GET /api/v1/health`
- **Detailed Health**: `GET /api/v1/health/detailed`
- **Readiness Probe**: `GET /api/v1/health/readiness`
- **Liveness Probe**: `GET /api/v1/health/liveness`

## 🐳 Docker Commands

### Development
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop all services
docker-compose down

# Rebuild API container
docker-compose build api
```

### Production
```bash
# Build production image
docker build -t dlmonitor-api:latest .

# Run production container
docker run -p 8000:8000 -e ENVIRONMENT=production dlmonitor-api:latest
```

## 🧪 Testing

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run tests
pytest

# Run with coverage
pytest --cov=app tests/
```

## 📝 API Documentation

When running the application, visit:
- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## 🔄 Development Workflow

1. **Start services**: `docker-compose up -d`
2. **Make changes**: Edit code with hot-reload enabled
3. **Test endpoints**: Use `/docs` for interactive testing
4. **Check health**: Monitor `/api/v1/health/detailed`
5. **View logs**: `docker-compose logs -f api`

## 🚀 Deployment

### Environment Variables
Create appropriate `.env` files for each environment:

**Production Checklist:**
- [ ] Set strong `SECRET_KEY`
- [ ] Configure production `DATABASE_URL`
- [ ] Set `ENVIRONMENT=production`
- [ ] Configure `SENTRY_DSN`
- [ ] Set up external API keys
- [ ] Configure CORS origins
- [ ] Enable health check monitoring

### Container Registry
```bash
# Tag for registry
docker tag dlmonitor-api:latest your-registry/dlmonitor-api:v2.0.0

# Push to registry
docker push your-registry/dlmonitor-api:v2.0.0
```

## 🤝 Contributing

1. Follow the existing code structure
2. Add type hints to all functions
3. Write tests for new features
4. Update documentation
5. Ensure health checks pass

## 📄 License

This project is part of the DLMonitor platform. 