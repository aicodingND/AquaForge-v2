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
- **Max time**: 2 hours (auto-stop)
- **Commit frequency**: Every 3 successful changes
- **Stuck detection**: If same error 3x → escalate to PRISM or skip
- **Rollback checkpoint**: Git tag created each cycle for recovery
- **No destructive actions**: Won't delete files or force push

---

## 🔄 The Autopilot Loop

```
┌─────────────────────────────────────────────────────────────┐
│                    AUTOPILOT CYCLE                          │
├─────────────────────────────────────────────────────────────┤
│  1. INITIALIZE        → Create session log, checkpoint      │
│  2. HEALTH CHECK      → Backend + Frontend + Tests          │
│  3. IDENTIFY TASK     → Find highest priority issue         │
│  4. SKILL LOAD        → Auto-load via smart-loader          │
│  5. FIX/IMPROVE       → Apply fix using /ralph              │
│  6. VALIDATE          → Run tests, E2E check (every 5)      │
│  7. COMMIT (if pass)  → Auto-commit with message            │
│  8. LOG PROGRESS      → Update session log                  │
│  9. NEXT ITERATION    → Loop back to step 2                 │
└─────────────────────────────────────────────────────────────┘
```

---

## Phase 0: Initialize Session (NEW)

// turbo
```bash
cd /Users/mpage1/Desktop/AquaForge/AquaForge_v1.0.0-next_2026-01-10
SESSION_LOG=".agent/context/autopilot_$(date +%Y%m%d_%H%M).md"
echo "# Autopilot Session - $(date '+%Y-%m-%d %H:%M')" > $SESSION_LOG
echo "" >> $SESSION_LOG
echo "## Configuration" >> $SESSION_LOG
echo "- Max iterations: 20" >> $SESSION_LOG
echo "- Start time: $(date '+%H:%M')" >> $SESSION_LOG
echo "- Checkpoint tag: autopilot_start_$(date +%H%M)" >> $SESSION_LOG
echo "" >> $SESSION_LOG
echo "## Progress Log" >> $SESSION_LOG
echo "| # | Issue | Status | Time |" >> $SESSION_LOG
echo "|---|-------|--------|------|" >> $SESSION_LOG
git tag "autopilot_checkpoint_start" 2>/dev/null || true
echo "✅ Session initialized: $SESSION_LOG"
```

---

## Phase 1: System Health Check

### 1.1 Backend Health
// turbo
```bash
cd /Users/mpage1/Desktop/AquaForge/AquaForge_v1.0.0-next_2026-01-10
source .venv/bin/activate 2>/dev/null
python -c "from swim_ai_reflex.backend.api.main import api_app; print('✅ Backend OK')" 2>&1 || echo "❌ Backend Error"
```

### 1.2 Frontend Health (NEW)
// turbo
```bash
cd /Users/mpage1/Desktop/AquaForge/AquaForge_v1.0.0-next_2026-01-10/frontend
npm run lint 2>&1 | head -5 || echo "⚠️ Frontend lint issues"
echo "✅ Frontend check complete"
```

### 1.3 Quick Test Check
// turbo
```bash
cd /Users/mpage1/Desktop/AquaForge/AquaForge_v1.0.0-next_2026-01-10
source .venv/bin/activate 2>/dev/null
python -m pytest tests/ -x -q --tb=line 2>&1 | tail -5
```

---

## Phase 2: Identify Priority Task

Run in order, stop at first found issue:

### 2.1 Check for Failing Tests
// turbo
```bash
cd /Users/mpage1/Desktop/AquaForge/AquaForge_v1.0.0-next_2026-01-10
source .venv/bin/activate 2>/dev/null
python -m pytest tests/ --lf -q --tb=line 2>&1 | tail -10
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

| Priority | Issue Type          | Skill to Load       | Action             |
| -------- | ------------------- | ------------------- | ------------------ |
| 🔴 P0     | Import/Syntax error | -                   | Fix immediately    |
| 🔴 P1     | Failing test        | `test-generator`    | Use /ralph         |
| 🟠 P2     | Lint error          | -                   | `ruff check --fix` |
| 🟠 P3     | Type error          | `code-reviewer`     | Add type hints     |
| 🟡 P4     | Code smell          | `code-reviewer`     | Refactor           |
| 🟢 P5     | Missing tests       | `test-generator`    | Add tests          |
| 🟢 P6     | Docs outdated       | `api-docs`          | Update docs        |
| 🔵 P7     | E2E issue           | `e2e-debugger`      | Browser debugging  |
| 🟣 P8     | Championship issue  | `championship-mode` | Scoring validation |

---

## Phase 4: Execute Fix (Ralph Loop)

### 4.1 Auto-Load Skill (via Smart Loader) (ENHANCED)
Before fixing, automatically detect and load relevant skill:

```markdown
SKILL AUTO-DETECTION:
1. Parse issue text against smart-loader detection matrix
2. Patterns detected:
   - "test" / "pytest" / "failure" → load test-generator
   - "scoring" / "points" / "X-0" → load scoring-validator
   - "E2E" / "browser" / "playwright" → load e2e-debugger
   - "championship" / "VCAC" → load championship-mode
   - "optimize" / "constraint" → load optimization-reviewer
3. Read SKILL.md for loaded skill
4. Apply skill-specific patterns
```

### 4.2 Create Rollback Checkpoint (NEW)
// turbo
```bash
cd /Users/mpage1/Desktop/AquaForge/AquaForge_v1.0.0-next_2026-01-10
git stash push -m "autopilot_checkpoint_$(date +%H%M%S)" --include-untracked 2>/dev/null || true
```

### 4.3 Apply Ralph Pattern
```
RALPH ITERATION:
1. Read error/issue
2. Analyze root cause
3. Locate relevant code
4. Propose fix
5. Hypothesis: "This fix will resolve X because Y"
6. Apply fix
7. Test: Run affected tests (incremental)
8. If pass → commit, next issue
9. If fail → try alternative approach (max 2 attempts)
10. If stuck after 2 → ESCALATE TO PRISM (see 4.4)
```

### 4.4 PRISM Escalation (NEW)
If stuck on same issue after 2 attempts:
```markdown
PRISM ESCALATION:
1. "Invoking /prism for multi-perspective analysis..."
2. Apply 6-perspective critique:
   - 🔬 Scientist: Is the diagnosis correct?
   - 🛡️ Security: What edge cases missed?
   - 🎨 UX: Is this the right fix?
   - ⚡ Performance: Any efficiency issues?
   - 🧪 QA: What tests needed?
   - 📚 Docs: What needs documenting?
3. Synthesize and apply refined fix
4. If still stuck after PRISM → skip with detailed log
```

---

## Phase 5: Validate Fix

### 5.1 Incremental Testing (ENHANCED)
// turbo
```bash
cd /Users/mpage1/Desktop/AquaForge/AquaForge_v1.0.0-next_2026-01-10
source .venv/bin/activate
# Run only last-failed tests for speed
python -m pytest tests/ --lf -q --tb=short 2>&1 | tail -5
```

### 5.2 Full Test (every 3 iterations)
// turbo
```bash
cd /Users/mpage1/Desktop/AquaForge/AquaForge_v1.0.0-next_2026-01-10
source .venv/bin/activate
python -m pytest tests/ -x -q --tb=no 2>&1 | tail -3
```

### 5.3 E2E Browser Check (every 5 iterations) (NEW)
```markdown
E2E SANITY CHECK:
Use browser_subagent with task:
"Navigate to localhost:3000. Verify page loads without errors.
Check for console errors. Return: OK or list of issues found."

If E2E issues found → add to priority queue as P7
```

### 5.4 Championship Validation (every 10 iterations) (NEW)
// turbo
```bash
cd /Users/mpage1/Desktop/AquaForge/AquaForge_v1.0.0-next_2026-01-10
source .venv/bin/activate
python -m pytest tests/test_championship_scoring_verification.py -v --tb=short 2>&1 | tail -10
```

---

## Phase 6: Auto-Commit

If validation passes:
// turbo
```bash
git add -A
git commit -m "fix(autopilot): [auto-generated description]"
```

Commit message format based on change type:
- `fix(tests): resolve failing test in test_X`
- `style(lint): auto-fix lint errors via ruff`
- `refactor(types): add type annotations to module X`
- `docs(api): update API documentation`
- `fix(e2e): resolve browser test issue`
- `fix(scoring): correct championship scoring logic`

---

## Phase 7: Update Session Log (ENHANCED)

// turbo
```bash
SESSION_LOG=$(ls -t .agent/context/autopilot_*.md 2>/dev/null | head -1)
if [ -n "$SESSION_LOG" ]; then
  echo "| $ITERATION | $ISSUE_TYPE | $STATUS | $DURATION |" >> $SESSION_LOG
fi
```

**Metrics tracked per session:**
- Fixes completed
- Fixes skipped (with reasons)
- PRISM escalations
- E2E checks performed
- Commits made
- Total duration

---

## 🛑 Stop Conditions

Autopilot stops when ANY of these occur:

1. **All green**: No more issues found
2. **Max iterations**: Reached 20 cycles
3. **Max time**: 2 hours elapsed
4. **Critical failure**: System becomes unresponsive
5. **User interrupt**: Manual stop requested

---

## Phase 8: Completion Notification (NEW)

When autopilot ends, write summary and notify:

// turbo
```bash
SESSION_LOG=$(ls -t .agent/context/autopilot_*.md 2>/dev/null | head -1)
if [ -n "$SESSION_LOG" ]; then
  echo "" >> $SESSION_LOG
  echo "## Summary" >> $SESSION_LOG
  echo "- Ended: $(date '+%H:%M')" >> $SESSION_LOG
  echo "- Duration: $DURATION minutes" >> $SESSION_LOG
  echo "- Fixes: $FIXES_MADE" >> $SESSION_LOG
  echo "- Skipped: $SKIPPED" >> $SESSION_LOG
  echo "- Commits: $COMMITS" >> $SESSION_LOG
  echo "- PRISM escalations: $PRISM_COUNT" >> $SESSION_LOG
fi

# macOS notification (optional)
osascript -e 'display notification "Session complete! Check .agent/context/" with title "🤖 Autopilot"' 2>/dev/null || true
echo "=== AUTOPILOT COMPLETE ==="
```

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
   - Creates session log in .agent/context/
   - Creates rollback checkpoint
   - Fix failing tests (incremental)
   - Auto-fix lint issues
   - Add missing type hints
   - Refactor code smells
   - E2E check every 5 iterations
   - Championship validation every 10
   - PRISM escalation for stuck issues
   - Auto-commit every 3 fixes
   - macOS notification on completion

4. When you return:
   - Check session log: cat .agent/context/autopilot_*.md | tail -30
   - Review commits: git log --oneline -20
   - Verify test status: pytest tests/ -v
   - Rollback if needed: git tag -l "autopilot_*"
```

---

## Integration with Other Workflows

| Phase        | Workflow/Skill Used             |
| ------------ | ------------------------------- |
| Initialize   | Session logging                 |
| Health       | `/health-check` + frontend lint |
| Test Fix     | `/ralph` + `test-generator`     |
| E2E Fix      | `/e2e-fix` + `e2e-debugger`     |
| Stuck Issue  | `/prism` (auto-escalation)      |
| Skills       | `smart-loader` (auto-detect)    |
| Championship | `championship-mode`             |
| Code Review  | `code-reviewer`                 |
| Commit       | `/auto-commit`                  |

---

// turbo-all
_Workflow: autopilot | Version: 2.0 | Enhanced with PRISM recommendations_
_Updated: 2026-01-20 | See implementation_plan.md for rationale_
