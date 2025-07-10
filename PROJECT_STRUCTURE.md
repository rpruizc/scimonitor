# DLMonitor Project Structure

This repository contains both the **legacy Flask application** and the **new FastAPI backend** during the modernization transition.

## 📁 Directory Structure

```
dlmonitor/
├── dlmonitor/                    # 🔴 Legacy Flask Application
│   ├── webapp/                   # Old web interface
│   ├── sources/                  # Data fetching (ArXiv, Twitter)
│   ├── db_models.py             # Legacy SQLAlchemy models
│   └── ...
├── dlmonitor_api/               # 🟢 New FastAPI Backend
│   ├── app/                     # Modern FastAPI application
│   │   ├── api/v1/              # API endpoints
│   │   ├── core/                # Configuration
│   │   └── main.py              # FastAPI app
│   ├── requirements.txt         # Modern dependencies
│   ├── Dockerfile               # Container setup
│   └── docker-compose.yml       # Development environment
├── requirements.txt             # 🔴 Legacy Flask dependencies
├── specs.md                     # Modernization roadmap
└── README.md                    # Original project documentation
```

## 🔄 Development Approach

### Current State (EPIC 1 - Foundation)
- **Legacy App**: Still functional but outdated (Flask 0.12.2)
- **New API**: Modern FastAPI backend being built
- **Coexistence**: Both apps can run simultaneously during transition

### Dependencies

| Component | File | Purpose |
|-----------|------|---------|
| **Legacy Flask** | `requirements.txt` | Old Flask app in `dlmonitor/` folder |
| **New FastAPI** | `dlmonitor_api/requirements.txt` | Modern backend in `dlmonitor_api/` folder |

## 🚀 Quick Start

### Legacy Flask App
```bash
# Install legacy dependencies
pip install -r requirements.txt

# Run legacy app (if needed)
PYTHONPATH="." python dlmonitor/webapp/app.py
```

### New FastAPI Backend
```bash
# Navigate to new backend
cd dlmonitor_api

# Install modern dependencies  
pip install -r requirements.txt

# Run with Docker (recommended)
docker-compose up -d

# Or run directly
python run.py
```

## 🎯 Migration Timeline

### Phase 1: Foundation ✅ (Current)
- [x] FastAPI backend structure
- [x] Modern dependencies
- [x] Docker setup
- [x] Health checks

### Phase 2: Core Features (Next)
- [ ] Database migration to SQLAlchemy 2.0
- [ ] API endpoints
- [ ] Authentication system

### Phase 3: Feature Parity
- [ ] Data source integrations
- [ ] AI-powered features
- [ ] Frontend migration

### Phase 4: Legacy Deprecation
- [ ] Remove old Flask app
- [ ] Single requirements.txt
- [ ] Production deployment

## 🧪 Testing Both Apps

During development, you can run both applications:

- **Legacy Flask**: http://localhost:5000 (or configured port)
- **New FastAPI**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## 📝 Development Guidelines

1. **New features** → Build in `dlmonitor_api/`
2. **Bug fixes** → Fix in legacy app only if critical
3. **Dependencies** → Use appropriate requirements.txt file
4. **Testing** → Test both apps during transition
5. **Documentation** → Update both READMEs as needed

## 🏁 End State

Eventually, the project structure will become:

```
dlmonitor/
├── backend/                     # FastAPI backend
├── frontend/                    # Next.js frontend  
├── requirements.txt             # Single modern dependencies file
├── docker-compose.yml           # Full-stack development
└── README.md                    # Unified documentation
```

The legacy Flask app and its dependencies will be completely removed once the migration is complete. 