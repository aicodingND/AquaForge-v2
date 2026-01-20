# AquaForge Full-Stack Migration Guide

This document outlines the path to migrating from Reflex to a modern, optimal full-stack architecture.

## Current Architecture

```
┌─────────────────────────────────────────────────────┐
│                 CURRENT: Reflex                      │
├─────────────────────────────────────────────────────┤
│  Frontend (React-like)  ←→  Backend (Python State)  │
│         Port 3000              Port 8000            │
│  - Tightly coupled                                  │
│  - State sync via WebSocket                         │
│  - Limited frontend flexibility                     │
└─────────────────────────────────────────────────────┘
```

## Target Architecture

```
┌─────────────────────────────────────────────────────┐
│              TARGET: FastAPI + Next.js               │
├─────────────────────────────────────────────────────┤
│  Next.js Frontend    ←──REST API──→   FastAPI       │
│     Port 3000                         Port 8001     │
│  - Independent                                      │
│  - Full React ecosystem                             │
│  - Better SEO (SSR/SSG)                            │
│  - Scalable separately                             │
└─────────────────────────────────────────────────────┘
```

## Migration Phases

### Phase 1: API Layer (✅ COMPLETE)
- [x] Create standalone FastAPI application
- [x] Define Pydantic models for validation
- [x] Create API routers for all services
- [x] Add unified server runner
- [x] Configure CORS for frontend access

### Phase 2: API Stabilization (CURRENT)
- [ ] Add comprehensive API tests
- [ ] Document all endpoints (OpenAPI)
- [ ] Add authentication/authorization
- [ ] Performance optimization (caching, connection pooling)
- [ ] Error handling standardization

### Phase 3: Frontend Preparation
- [ ] Create Next.js project structure
- [ ] Set up API client (axios/fetch wrapper)
- [ ] Port UI components to React
- [ ] Implement state management (Zustand/Redux)
- [ ] Add TailwindCSS for styling

### Phase 4: Feature Parity
- [ ] File upload interface
- [ ] Team data display
- [ ] Optimization controls
- [ ] Results visualization
- [ ] Export functionality

### Phase 5: Advanced Features
- [ ] Real-time updates (WebSocket or SSE)
- [ ] Progressive Web App (PWA)
- [ ] Offline support
- [ ] Mobile responsiveness
- [ ] Analytics dashboard

### Phase 6: Production Cutover
- [ ] A/B testing setup
- [ ] Feature flags
- [ ] Gradual traffic migration
- [ ] Monitoring and alerting
- [ ] Documentation update

## Directory Structure (Target)

```
AquaForge/
├── backend/                    # FastAPI Backend
│   ├── app/
│   │   ├── api/
│   │   │   ├── routers/
│   │   │   │   ├── optimization.py
│   │   │   │   ├── data.py
│   │   │   │   ├── export.py
│   │   │   │   └── analytics.py
│   │   │   ├── models.py
│   │   │   └── deps.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   └── events.py
│   │   ├── services/
│   │   │   ├── optimization_service.py
│   │   │   ├── data_service.py
│   │   │   └── export_service.py
│   │   └── main.py
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/                   # Next.js Frontend
│   ├── src/
│   │   ├── app/               # App Router
│   │   │   ├── page.tsx
│   │   │   ├── layout.tsx
│   │   │   ├── upload/
│   │   │   ├── optimize/
│   │   │   └── results/
│   │   ├── components/
│   │   │   ├── ui/
│   │   │   ├── forms/
│   │   │   └── charts/
│   │   ├── lib/
│   │   │   ├── api.ts
│   │   │   └── utils.ts
│   │   └── hooks/
│   ├── public/
│   ├── package.json
│   └── Dockerfile
│
├── docker-compose.yml          # Orchestration
├── .env.example
└── README.md
```

## API Endpoints (Current)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/v1/optimize` | POST | Run optimization |
| `/api/v1/optimize/preview` | POST | Preview optimization |
| `/api/v1/optimize/backends` | GET | List backends |
| `/api/v1/data/upload` | POST | Upload team file |
| `/api/v1/data/team` | POST | Submit team JSON |
| `/api/v1/data/events` | GET | List events |
| `/api/v1/export` | POST | Export results |
| `/api/v1/analytics/compare` | POST | Compare teams |

## Running the Application

### Current (Reflex)
```bash
python run_server.py --mode reflex
# or
reflex run
```

### API Only (Development)
```bash
python run_server.py --mode api --reload
# Access: http://localhost:8001/api/docs
```

### Hybrid Mode
```bash
python run_server.py --mode hybrid
# Reflex: http://localhost:3000
# FastAPI: http://localhost:8001
```

### Quick Launch (Windows)
```cmd
launch.bat
```

## Technology Recommendations

### Backend (FastAPI) ✅
- **FastAPI**: High-performance, modern Python API
- **Pydantic**: Data validation
- **SQLAlchemy**: Database ORM (future)
- **Celery/ARQ**: Background tasks (future)
- **Redis**: Caching (future)

### Frontend (Next.js) 🔄 Planned
- **Next.js 14+**: React framework with App Router
- **TypeScript**: Type safety
- **TailwindCSS**: Utility-first styling
- **Shadcn/ui**: Component library
- **Zustand**: State management
- **React Query**: Data fetching
- **Recharts**: Visualization

### DevOps
- **Docker**: Containerization
- **GitHub Actions**: CI/CD
- **Railway/Render**: Hosting
- **Sentry**: Error tracking

## Next Steps

1. **Test the API**: Run `python run_server.py --mode api` and visit http://localhost:8001/api/docs
2. **Review endpoints**: Ensure all needed functionality is exposed via API
3. **Add tests**: Create pytest tests for all API endpoints
4. **Start frontend**: Initialize Next.js project when ready

## Notes

- The current Reflex app continues to work unchanged
- FastAPI runs on a separate port (8001)
- Both can run simultaneously in hybrid mode
- Migration can be gradual - no big bang required
