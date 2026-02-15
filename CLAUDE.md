# AquaForge - Claude AI Coding Assistant Context

## Project Overview

AquaForge is a swim meet optimization platform for competitive swimming teams.

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, Uvicorn (port 8001)
- **Frontend**: Next.js 16, React 19, TypeScript, Tailwind v4 (port 3000)
- **Optimizer**: Gurobi, Nash Equilibrium, Hungarian Algorithm
- **Testing**: pytest, Playwright

## Critical Rules

1. **Max 2 individual events per swimmer** (VISAA/VCAC rules)
2. **Relay 3 (400 FR) counts as 1 individual slot** at VCAC
3. **Diving counts as 1 individual slot**
4. **Grades 7-8 = Exhibition only** (no points)
5. Use team CODE "SST" not "Seton" in championship strategy

## Key Commands

```bash
# Backend
source .venv/bin/activate
python run_server.py --mode api

# Frontend
cd frontend && npm run dev

# Tests
python -m pytest tests/ -v

# Lint
ruff check . --fix && ruff format .
```

## Project Structure

```
/frontend/src/           - Next.js application
/swim_ai_reflex/backend/ - FastAPI backend
  /api/routers/          - API endpoints
  /services/             - Business logic
  /core/                 - Optimization, scoring
/.agent/                 - AI context and workflows
  /skills/               - Modular AI skills
  /workflows/            - Reusable workflows
  /context/              - Session state
```

## Available Workflows

- `/aquaforge-start` - Load context and begin session
- `/prism` - Multi-perspective problem solving
- `/ralph` - Iterative test-fix loop
- `/e2e-fix` - E2E debugging workflow
- `/delegate` - Auto-delegate to subagents

## Context Files

For detailed context, see:
- `.agent/memory/MEET_REGISTRY.md` - **Canonical meet details (venues, dates, rules) — check FIRST for any meet question**
- `.agent/CONTEXT_LOADER.md` - Quick reference
- `.agent/KNOWLEDGE_BASE.md` - Domain knowledge
- `.agent/skills/` - Task-specific skills

## Code Style

- Python: ruff format, type hints required
- TypeScript: prettier, strict mode
- Commits: conventional commits (feat:, fix:, docs:)
- Tests: pytest with descriptive names

## Current Sprint

VISAA State Swim & Dive Championships - Feb 12-14, 2026
(VCAC Championship Feb 7 — completed)
