# ⚡ AquaForge Context Loader (Tier 0)

**Purpose**: Minimal always-loaded context for token optimization. Load additional tiers on-demand.

---

## 🎯 Current Sprint

**VCAC Championship** - Feb 7, 2026 (~19 days)  
**VISAA States** - Feb 12-14, 2026 (~24 days)

---

## ⚠️ Critical Constraints (ALWAYS REMEMBER)

```
┌────────────────────────────────────────────────────────┐
│ MAX 2 INDIVIDUAL EVENTS per swimmer                    │
│ RELAY 3 (400 FR) COUNTS AS 1 INDIVIDUAL SLOT (VCAC)   │
│ DIVING COUNTS AS 1 INDIVIDUAL SLOT                     │
│ GRADES 7-8 = EXHIBITION ONLY (no points)               │
│ USE TEAM CODE "SST" not "Seton" in championship        │
└────────────────────────────────────────────────────────┘
```

---

## 📂 Context Tiers

| Tier  | File                | Load When                              |
| ----- | ------------------- | -------------------------------------- |
| **0** | This file           | Always (auto)                          |
| **1** | `KNOWLEDGE_BASE.md` | `/aquaforge-start` or domain questions |
| **2** | `REFERENCE.md`      | Historical lookups, changelog          |
| **3** | `skills/*`          | Task-specific (auto or manual)         |

---

## 🛠️ Available Skills (12 Total)

### Auto-Load via Smart-Loader

| Trigger Keywords                      | Skill                   |
| ------------------------------------- | ----------------------- |
| scoring, points, place, X-0           | `scoring-validator`     |
| test, TDD, coverage, pytest           | `test-generator`        |
| review, code review, bugs             | `code-reviewer`         |
| E2E, Playwright, browser test         | `e2e-debugger`          |
| championship, VCAC, multi-team        | `championship-mode`     |
| API, endpoint, FastAPI, Pydantic      | `api-docs`              |
| psych sheet, roster, times, SwimCloud | `data-validator`        |
| optimizer, lineup, Gurobi, Nash       | `optimization-reviewer` |
| remember, decision, history           | `project-memory`        |
| scrape, browser automation            | `browser-automation`    |
| parallel, multi-agent, orchestrate    | `multi-agent`           |

**Core**: `smart-loader` (auto-detects and loads appropriate skill)

---

## 🔄 Available Workflows (8 Total)

| Command            | Purpose                                 |
| ------------------ | --------------------------------------- |
| `/aquaforge-start` | Load context, review focus              |
| `/health-check`    | Validate backend, frontend, tests, lint |
| `/auto-commit`     | Generate conventional commit messages   |
| `/lint-fix`        | Fix all linting issues                  |
| `/delegate`        | Route tasks to subagents                |
| `/prism`           | Multi-perspective problem solving       |
| `/ralph`           | Iterative test-fix loop                 |
| `/e2e-fix`         | Debug E2E test failures                 |

---

## 🏃 Quick Commands

```bash
# Backend
source .venv/bin/activate && python run_server.py --mode api

# Frontend  
cd frontend && npm run dev

# Tests
python -m pytest tests/ -v

# Lint Fix
ruff check . --fix && ruff format .
```

---

## 🔒 Quality Safeguards

1. **Never guess domain facts** - Load KNOWLEDGE_BASE.md
2. **Auto-escalate context** - Load skill when task detected
3. **Verify before commit** - Run tests and lint
4. **Ask, don't assume** - Clarify ambiguous requests

---

## 📍 Current Focus

View: `.agent/context/current_focus.md`

**Last Session**: Token optimization, 12 skills, 8 workflows created

---

_Tier 0 Context | ~3KB | Auto-loaded every session_
