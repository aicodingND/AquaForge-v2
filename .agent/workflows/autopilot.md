---
description: Autonomous development loop - continuous optimization, debugging, refactoring while you're away
---

# 🤖 Autopilot Mode - Autonomous Development Loop

Run this workflow to let Antigravity continuously improve the codebase while you're away.

---

## How to Invoke

```
/autopilot
```

Or: "Run autopilot mode", "Autonomous development", "Work while I nap"

---

## ⚠️ Safety Guardrails

Before starting, these limits are enforced:
- **Max iterations**: 20 cycles (prevents infinite loops)
- **Max time**: 8 hours (auto-stop)
- **Commit frequency**: Every 3 successful changes
- **Stuck detection**: If same error 3x, skip and move on
- **No destructive ac8ions**: Won't delete files or force push

---

## 🔄 The Autopilot Loop

```
┌─────────────────────────────────────────────────────────────┐
│                    AUTOPILOT CYCLE                          │
├─────────────────────────────────────────────────────────────┤
│  1. HEALTH CHECK          → Assess system state             │
│  2. IDENTIFY TASK         → Find highest priority issue; research, optimize and improve
   │
│  3. SKILL LOAD            → Auto-load relevant skill        │
│  4. FIX/IMPROVE           → Apply fix using /ralph          │
│  5. VALIDATE              → Run tests, verify fix           │
│  6. COMMIT (if success)   → Auto-commit with message        │
│  7. NEXT ITERATION        → Loop back to step 1             │
└─────────────────────────────────────────────────────────────┘
```

---

## Phase 1: System Health Check

// turbo
```bash
cd /Users/mpage1/Desktop/AquaForge/AquaForge_v1.0.0-next_2026-01-10
echo "=== AUTOPILOT HEALTH CHECK ===" && date
python -c "from swim_ai_reflex.backend.api.main import api_app; print('✅ Backend OK')" 2>&1 || echo "❌ Backend Error"
```

---

## Phase 2: Identify Priority Task

Run in order, stop at first found issue:

### 2.1 Check for Failing Tests
// turbo
```bash
cd /Users/mpage1/Desktop/AquaForge/AquaForge_v1.0.0-next_2026-01-10
source .venv/bin/activate 2>/dev/null
python -m pytest tests/ -x -q --tb=line 2>&1 | tail -10
```

### 2.2 Check for Lint Errors
// turbo
```bash
cd /Users/mpage1/Desktop/AquaForge/AquaForge_v1.0.0-next_2026-01-10
ruff check . --statistics 2>&1 | head -10
```

### 2.3 Check for Type Errors
// turbo
```bash
cd /Users/mpage1/Desktop/AquaForge/AquaForge_v1.0.0-next_2026-01-10
pyright swim_ai_reflex/ --stats 2>&1 | tail -5 || echo "pyright not configured"
```

---

## Phase 3: Task Prioritization Matrix

| Priority | Issue Type          | Skill to Load    | Action             |
| -------- | ------------------- | ---------------- | ------------------ |
| 🔴 P0     | Import/Syntax error | -                | Fix immediately    |
| 🔴 P1     | Failing test        | `test-generator` | Use /ralph         |
| 🟠 P2     | Lint error          | -                | `ruff check --fix` |
| 🟠 P3     | Type error          | `code-reviewer`  | Add type hints     |
| 🟡 P4     | Code smell          | `code-reviewer`  | Refactor           |
| 🟢 P5     | Missing tests       | `test-generator` | Add tests          |
| 🟢 P6     | Docs outdated       | `api-docs`       | Update docs        |

---

## Phase 4: Execute Fix (Ralph Loop)

For each issue found:

### 4.1 Load Appropriate Skill
Based on issue type, auto-load skill:
- Test failure → `test-generator` + `e2e-debugger`
- Scoring bug → `scoring-validator`
- Optimizer issue → `optimization-reviewer`
- Data issue → `data-validator`

### 4.2 Apply Ralph Pattern
```
RALPH ITERATION:
1. Read error/issue
2. Analyze root cause
3. Locate relevant code
4. Propose fix
5. Hypothesis: "This fix will resolve X because Y"
6. Apply fix
7. Test: Run affected tests
8. If pass → commit, next issue
9. If fail → try alternative approach (max 3 attempts)
10. If stuck → skip, log, move to next issue
```

### 4.3 Stuck Detection
```python
stuck_counter = {}

def check_stuck(error_signature):
    stuck_counter[error_signature] = stuck_counter.get(error_signature, 0) + 1
    if stuck_counter[error_signature] >= 3:
        log_skip(f"Skipping: {error_signature} - tried 3 times")
        return True  # Skip this issue
    return False
```

---

## Phase 5: Validate Fix

// turbo
```bash
cd /Users/mpage1/Desktop/AquaForge/AquaForge_v1.0.0-next_2026-01-10
source .venv/bin/activate
python -m pytest tests/ -x -q --tb=no 2>&1 | tail -3
```

---

## Phase 6: Auto-Commit

If validation passes:
```bash
git add -A
git commit -m "fix(autopilot): [auto-generated description]"
```

Commit message format based on change type:
- `fix(tests): resolve failing test in test_X`
- `style(lint): auto-fix lint errors via ruff`
- `refactor(types): add type annotations to module X`
- `docs(api): update API documentation`

---

## Phase 7: Progress Log

After each cycle, update progress:

```markdown
## Autopilot Session Log

Started: [timestamp]
Iteration: [N]

| #   | Issue                | Status            | Time |
| --- | -------------------- | ----------------- | ---- |
| 1   | test_scoring failure | ✅ Fixed           | 2m   |
| 2   | lint: unused import  | ✅ Fixed           | 30s  |
| 3   | E2E timeout          | ⏭️ Skipped (stuck) | 5m   |
| 4   | ...                  | ...               | ...  |

Commits made: [N]
Tests fixed: [N]
Issues skipped: [N]
```

---

## 🛑 Stop Conditions

Autopilot stops when ANY of these occur:

1. **All green**: No more issues found
2. **Max iterations**: Reached 20 cycles
3. **Max time**: 2 hours elapsed
4. **Critical failure**: System becomes unresponsive
5. **User interrupt**: Manual stop requested

---

## 🎯 Recommended Autopilot Sequence

For a nap-length autonomous run:

```
1. Start servers (manual):
   - Terminal 1: python run_server.py --mode api
   - Terminal 2: cd frontend && npm run dev

2. Run autopilot:
   /autopilot

3. Expected behavior:
   - Fix failing tests (5 E2E errors)
   - Auto-fix lint issues
   - Add missing type hints
   - Refactor code smells
   - Auto-commit every 3 fixes
   - Log all actions

4. When you return:
   - Check session log
   - Review commits: git log --oneline -20
   - Verify test status: pytest tests/ -v
```

---

## 📝 Session Template

When starting autopilot, create session log:

```markdown
# Autopilot Session - [DATE]

## Configuration
- Max iterations: 20
- Max time: 2 hours
- Start time: [TIME]
- Focus: [tests/lint/all]

## Progress Log
[Auto-updated during session]

## Summary
- Started: [TIME]
- Ended: [TIME]
- Duration: [X minutes]
- Iterations: [N]
- Fixes: [N]
- Skipped: [N]
- Commits: [N]
```

---

## Integration with Other Workflows

| Phase       | Workflow/Skill Used           |
| ----------- | ----------------------------- |
| Health      | `/health-check`               |
| Test Fix    | `/ralph` + `test-generator`   |
| E2E Fix     | `/e2e-fix` + `e2e-debugger`   |
| Code Review | `code-reviewer`               |
| Analysis    | `/prism` (for complex issues) |
| Commit      | `/auto-commit`                |

---

// turbo-all
_Workflow: autopilot | Version: 1.0 | Autonomous Development Loop_