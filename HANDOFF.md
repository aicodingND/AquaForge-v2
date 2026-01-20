# AquaForge.ai - Project Handoff Document

**Last Updated**: 2026-01-10  
**Status**: Active Development (Next.js + FastAPI Stack)

---

## 🎯 Project Overview

AquaForge.ai is a swim meet lineup optimization platform that uses game theory (Nash Equilibrium) and heuristic algorithms to generate optimal swimmer assignments for competitive swim meets.

**Tech Stack**:

- **Frontend**: Next.js 16 (React 19, TypeScript, Tailwind v4)
- **Backend**: FastAPI (Python 3.11+)
- **Optimization**: Custom Nash Equilibrium solver + Heuristic fallback
- **Data Processing**: Pandas, NumPy

---

## 📁 Project Structure

```
AquaForgeFinal/
├── frontend/                    # Next.js application
│   ├── src/
│   │   ├── app/                # Next.js app router pages
│   │   ├── components/         # React components
│   │   └── lib/                # Utilities, API client
│   └── package.json
│
├── swim_ai_reflex/             # Python backend package
│   ├── backend/
│   │   ├── api/                # FastAPI routers & models
│   │   │   ├── routers/        # Endpoints (optimization, data, export)
│   │   │   ├── models.py       # Pydantic schemas
│   │   │   └── main.py         # FastAPI app
│   │   ├── services/           # Business logic
│   │   │   ├── optimization_service.py
│   │   │   ├── data_service.py
│   │   │   └── export_service.py
│   │   └── utils/              # Helpers, file management
│   └── tests/                  # Backend tests
│
├── __ARCHIVE_REFLEX_APP__/     # Legacy Reflex UI (deprecated)
├── __DATA__/                   # Sample data & templates
├── docs/                       # Documentation
├── tests/                      # E2E tests
│
├── start_dev.bat               # 🚀 MAIN STARTUP SCRIPT
├── run_server.py               # Alternative runner (API-only, hybrid modes)
└── requirements.txt            # Python dependencies
```

---

## 🚀 Quick Start

### Running the Application

```bash
# Start both frontend and backend
.\start_dev.bat
```

This launches:

- **Frontend**: <http://localhost:3000>
- **Backend API**: <http://localhost:8001>
- **API Docs**: <http://localhost:8001/api/docs>

### Alternative: API-Only Mode

```bash
# Backend only (for mobile app development, etc.)
python run_server.py --mode api --port 8001 --reload
```

---

## 🔑 Key Components

### Backend API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/data/upload` | POST | Upload roster files (Excel/CSV) |
| `/api/optimize` | POST | Run lineup optimization |
| `/api/export/csv` | POST | Export results as CSV |
| `/api/data/events` | GET | List standard swim events |

### Core Services

1. **OptimizationService** (`optimization_service.py`)
   - Nash Equilibrium solver
   - Heuristic fallback for large datasets
   - Fatigue modeling

2. **DataService** (`data_service.py`)
   - Excel/CSV parsing
   - Data validation & cleaning
   - Roster management

3. **ExportService** (`export_service.py`)
   - CSV export
   - HTML/PDF generation

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run specific test suite
pytest tests/test_api.py -v

# Run with coverage
pytest --cov=swim_ai_reflex
```

---

## 📦 Dependencies

### Python (Backend)

- FastAPI + Uvicorn
- Pandas, NumPy
- Pydantic v2
- openpyxl (Excel support)

### Node.js (Frontend)

- Next.js 16
- React 19
- Axios (API client)
- Zustand (state management)
- Tailwind CSS v4

---

## 🗂️ Archive & Data Directories

### `__ARCHIVE_REFLEX_APP__/`

Contains the deprecated Reflex-based UI. **Not actively maintained**.  
See `__ARCHIVE_REFLEX_APP__/README.md` for details.

### `__DATA__/`

Sample roster files, templates, and test assets.  
Used by tests and documentation.

---

## 🔄 Recent Changes (2026-01-10)

1. **Architecture Migration**: Moved from Reflex to Next.js + FastAPI
2. **File Reorganization**: Archived legacy UI, organized data files
3. **Documentation**: Created handoff notes and README files

---

## 📝 Development Notes

### Adding New Features

1. **Backend**: Add router in `swim_ai_reflex/backend/api/routers/`
2. **Frontend**: Add page/component in `frontend/src/`
3. **Tests**: Add tests in `tests/` or `swim_ai_reflex/tests/`

### Common Tasks

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Node dependencies
cd frontend && npm install

# Run linting
ruff check swim_ai_reflex/

# Format code
ruff format swim_ai_reflex/
```

---

## 🐛 Known Issues

- None currently tracked

---

## 📞 Support

For questions or issues, refer to:

- API Documentation: <http://localhost:8001/api/docs>
- Project docs: `docs/` directory
- Archive notes: `__ARCHIVE_REFLEX_APP__/README.md`

---

**End of Handoff Document**
