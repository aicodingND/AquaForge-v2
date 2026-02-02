---
description: One-command lint fix for entire project
---

# Lint Auto-Fix Workflow 🧹

Fix all linting and formatting issues across the project.

---

## How to Invoke

- `/lint-fix`
- "Fix linting"
- "Clean up code"

---

## Workflow Steps

// turbo
### Step 1: Python - Ruff Check & Fix

```bash
cd /Users/mpage1/Desktop/AquaForge/AquaForge_v1.0.0-next_2026-01-10
source .venv/bin/activate 2>/dev/null || true
ruff check . --fix --show-fixes
```

// turbo
### Step 2: Python - Ruff Format

```bash
cd /Users/mpage1/Desktop/AquaForge/AquaForge_v1.0.0-next_2026-01-10
ruff format .
```

// turbo
### Step 3: Frontend - ESLint

```bash
cd /Users/mpage1/Desktop/AquaForge/AquaForge_v1.0.0-next_2026-01-10/frontend
npm run lint -- --fix 2>/dev/null || echo "ESLint complete"
```

// turbo
### Step 4: Frontend - Prettier

```bash
cd /Users/mpage1/Desktop/AquaForge/AquaForge_v1.0.0-next_2026-01-10/frontend
npx prettier --write "src/**/*.{ts,tsx,css}" 2>/dev/null || echo "Prettier complete"
```

---

## Summary Output

```
┌─────────────────────────────────────────┐
│            Lint Fix Summary             │
├─────────────────────────────────────────┤
│ Python (ruff):                          │
│   Fixed: X issues                       │
│   Remaining: Y issues                   │
│                                         │
│ TypeScript (ESLint):                    │
│   Fixed: X issues                       │
│   Remaining: Y issues                   │
│                                         │
│ Formatting (prettier):                  │
│   Formatted: X files                    │
└─────────────────────────────────────────┘
```

---

## Common Issues

| Error Type         | Auto-Fix         | Manual Fix      |
| ------------------ | ---------------- | --------------- |
| Unused imports     | ✅ ruff removes   | -               |
| Missing type hints | ❌                | Add manually    |
| Line too long      | ✅ ruff reformats | -               |
| Unused variables   | ⚠️ commented      | Remove or use   |
| Any type           | ❌                | Add proper type |

---

// turbo-all
