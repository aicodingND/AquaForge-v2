---
description: Quick system health check - validates backend, frontend, tests, and lint
---

# System Health Check Workflow 🏥

Run this to quickly validate the entire AquaForge system state.

---

## How to Invoke

- `/health`
- "Check system health"
- "Is everything working?"

---

## Health Checks

// turbo
### 1. Backend Health

```bash
cd /Users/mpage1/Desktop/AquaForge/AquaForge_v1.0.0-next_2026-01-10
source .venv/bin/activate 2>/dev/null || true
python -c "from swim_ai_reflex.backend.api.main import api_app; print('✅ Backend imports OK')" 2>&1
```

// turbo
### 2. Frontend Health

```bash
cd /Users/mpage1/Desktop/AquaForge/AquaForge_v1.0.0-next_2026-01-10/frontend
npm run build --dry-run 2>/dev/null || npm run lint 2>&1 | head -5
echo "✅ Frontend check complete"
```

// turbo
### 3. Quick Test (Smoke Test)

```bash
cd /Users/mpage1/Desktop/AquaForge/AquaForge_v1.0.0-next_2026-01-10
source .venv/bin/activate 2>/dev/null || true
python -m pytest tests/ -x -q --tb=no 2>&1 | tail -5
```

// turbo
### 4. Lint Check

```bash
cd /Users/mpage1/Desktop/AquaForge/AquaForge_v1.0.0-next_2026-01-10
ruff check . --statistics 2>&1 | tail -3
```

---

## Health Dashboard Output

After running checks, present:

```
┌─────────────────────────────────────────┐
│          AquaForge Health Check         │
├─────────────────────────────────────────┤
│ Backend:    ✅ OK / ❌ FAIL             │
│ Frontend:   ✅ OK / ❌ FAIL             │
│ Tests:      ✅ 117/130 passing          │
│ Lint:       ✅ Clean / ⚠️ X issues      │
│ Last Commit: [hash] - [message]         │
├─────────────────────────────────────────┤
│ Sprint: VCAC Championship               │
│ Days Left: 19                           │
│ Blockers: None / [list]                 │
└─────────────────────────────────────────┘
```

---

## Quick Fixes

If health check fails, suggest:

| Issue         | Command                             |
| ------------- | ----------------------------------- |
| Lint errors   | `/lint-fix` or `ruff check . --fix` |
| Test failures | `/ralph` for iterative fix          |
| Import errors | Check dependency installation       |
| Type errors   | `pyright swim_ai_reflex/`           |

---

// turbo-all
