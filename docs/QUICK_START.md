# AquaForge Quick Start

Get AquaForge running in minutes with this quick start guide.

## Prerequisites

- Python 3.11+
- Node.js 20+
- Gurobi license (optional, AquaOptimizer works without it)

## Backend Setup

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start backend server
python run_server.py --mode api
```

Backend will run on: http://localhost:8001

## Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend will run on: http://localhost:3000

## Run Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_e2e_standard.py -v

# Run with coverage
python -m pytest tests/ --cov=swim_ai_reflex --cov-report=html
```

## Access Points

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8001
- **API Docs**: http://localhost:8001/docs (Swagger UI)
- **API ReDoc**: http://localhost:8001/redoc

## Key Features

### Championship Scoring
- **VCAC Rules**: Max 2 individual events per swimmer
- **Relay 3 (400 FR)**: Counts as 1 individual slot at VCAC
- **Diving**: Counts as 1 individual slot
- **Exhibition**: Grades 7-8 are exhibition only (no points)
- **Team Code**: Use "SST" for Seton Swimming Team

### Optimization Engines
- **Gurobi**: Exact optimization (requires license)
- **AquaOptimizer**: Custom heuristic optimizer (no license required)
- **Automatic Fallback**: System automatically uses AquaOptimizer if Gurobi unavailable

### Data Format
See [CSV Template Guide](CSV_TEMPLATE_GUIDE.md) for detailed upload format specifications.

## Common Commands

```bash
# Backend linting
ruff check . --fix && ruff format .

# Type checking
pyright swim_ai_reflex/backend/

# Frontend linting
cd frontend && npm run lint

# Build frontend for production
cd frontend && npm run build

# Run championship backtest
python scripts/championship_backtest.py
```

## Troubleshooting

### Backend won't start
- Verify Python 3.11+ is installed: `python --version`
- Check virtual environment is activated
- Ensure port 8001 is available

### Frontend won't start
- Verify Node.js 20+ is installed: `node --version`
- Delete `node_modules` and reinstall: `rm -rf node_modules && npm install`
- Check port 3000 is available

### Gurobi license issues
- AquaOptimizer will automatically be used as fallback
- Check Gurobi license with: `gurobi_cl --license`
- See [Optimizer Deep Dive](OPTIMIZER_DEEP_DIVE.md) for details

### Data upload errors
- Verify CSV format matches [CSV Template Guide](CSV_TEMPLATE_GUIDE.md)
- Check file encoding is UTF-8
- Ensure all required columns are present
- See [Data Pipeline Audit](DATA_PIPELINE_AUDIT_2026-01-16.md) for common issues

## Next Steps

1. Review [Championship Strategy Specification](CHAMPIONSHIP_STRATEGY_SPECIFICATION.md) for VCAC/VISAA optimization
2. Check [API Reference](API_REFERENCE.md) for integration details
3. See [Optimization Strategies Guide](OPTIMIZATION_STRATEGIES_GUIDE.md) for advanced optimization
4. Consult [Dev Environment Setup](DEV_ENVIRONMENT_SETUP.md) for detailed development configuration

## Current Sprint

**VCAC Championship Preparation - February 7, 2026**

See [VCAC Championship Feb 7, 2026](VCAC_CHAMPIONSHIP_FEB7_2026.md) for championship-specific details.
