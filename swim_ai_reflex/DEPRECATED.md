# DEPRECATION NOTICE

**This directory is deprecated as of 2026-01-08.**

## Migration Complete

AquaForge has migrated from Reflex to a standalone architecture:

- **Backend**: FastAPI at `swim_ai_reflex/backend/` (still active)
- **Frontend**: Next.js at `/frontend/` (new)

## Why Deprecated

Reflex components in this directory are no longer actively used:

- `components/*.py` → React components in `frontend/src/components/`
- `ui/*.py` → React pages in `frontend/src/app/`
- `state.py` → Zustand store in `frontend/src/lib/store.ts`

## Do Not Modify

Code in this directory is kept for reference only. All new development
should target the FastAPI backend and Next.js frontend.

## Startup Commands

```bash
# OLD (Reflex - deprecated)
reflex run

# NEW (FastAPI + Next.js)
start_dev.bat
```
