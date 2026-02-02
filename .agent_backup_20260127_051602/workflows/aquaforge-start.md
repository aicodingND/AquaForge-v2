---
description: Start an AquaForge development session by loading context and reviewing current focus
---

# AquaForge Session Startup Workflow 🚀

Use this workflow at the **start of each development session** to ensure Antigravity has optimal context loading.

---

## How to Invoke

Simply tell Antigravity:

- "Let's start an AquaForge session"
- "Load the AquaForge context"
- `/aquaforge-start`

---

## Tiered Context Loading System

| Tier | File                | When Loaded           | Size      |
| ---- | ------------------- | --------------------- | --------- |
| 0    | `CONTEXT_LOADER.md` | Auto (always known)   | ~2KB      |
| 1    | `KNOWLEDGE_BASE.md` | On `/aquaforge-start` | ~10KB     |
| 2    | `REFERENCE.md`      | On historical lookups | ~15KB     |
| 3    | `skills/*`          | On task-specific need | ~3KB each |

---

## Workflow Steps

### Step 1: Load Tier 1 - Domain Knowledge

// turbo
Read the core knowledge base for domain facts, rules, and decisions:

```
View file: .agent/KNOWLEDGE_BASE.md
```

### Step 2: Load Current Focus

// turbo
Read what we were working on and current sprint context:

```
View file: .agent/context/current_focus.md
```

### Step 3: Check Available Skills

// turbo
Review available specialized skills:

```
View file: .agent/skills/SKILLS_INDEX.md
```

### Step 4: Check for Recent Changes (Optional)

If relevant, review recent git commits:

```bash
git log --oneline -5
```

### Step 5: Confirm Context & Summarize

Antigravity should summarize:

- ✅ Current sprint goal
- ✅ Open tasks/blockers
- ✅ Key constraints to remember
- ✅ Available skills for current work
- ✅ Suggested next action

### Step 6: Begin Work

Ask the user what they'd like to focus on, or continue from where we left off.

---

## Skill Loading (On-Demand)

When specific task types are detected, load relevant skill:

| Task Type           | Load Skill                              |
| ------------------- | --------------------------------------- |
| Scoring bugs        | `skills/scoring-validator/SKILL.md`     |
| E2E test failures   | `skills/e2e-debugger/SKILL.md`          |
| Optimizer review    | `skills/optimization-reviewer/SKILL.md` |
| Data quality issues | `skills/data-validator/SKILL.md`        |
| Championship work   | `skills/championship-mode/SKILL.md`     |

---

## End of Session Checklist

Before ending a significant session, Antigravity should:

1. **Update current_focus.md** with:
   - What was accomplished
   - Any new decisions made
   - Next steps for future sessions

2. **Update KNOWLEDGE_BASE.md** if:
   - New domain facts were learned
   - New gotchas were discovered
   - Decisions were finalized

3. **Update REFERENCE.md** if:
   - Major bugs were fixed (add to changelog)
   - Architecture decisions were made

4. **Commit changes** (optional):

```bash
git add .agent/
git commit -m "docs: update AI context for session [DATE]"
```

---

## Quick Commands Reference

| You Say                    | Antigravity Does                          |
| -------------------------- | ----------------------------------------- |
| "Load AquaForge context"   | Runs `/aquaforge-start`                   |
| "What were we working on?" | Reads `current_focus.md`                  |
| "Add X to knowledge base"  | Updates `KNOWLEDGE_BASE.md`               |
| "Update the focus"         | Updates `current_focus.md`                |
| "Load scoring skill"       | Views `skills/scoring-validator/SKILL.md` |
| "/delegate [task]"         | Auto-routes to appropriate subagent       |
| "End session"              | Updates docs, suggests commit             |

---

## Example Session Start

**User**: "Let's work on AquaForge championship mode"

**Antigravity**:

1. _Tier 0 already loaded_ - Critical constraints known
2. _Reads KNOWLEDGE_BASE.md_ - Gets full domain rules
3. _Reads current_focus.md_ - Sees sprint context
4. _Identifies task type_ - Championship work detected
5. _Loads championship-mode skill_ - Specialized strategies available
6. _Summarizes_:
   > "Welcome back! Current sprint: VCAC Championship Prep (~20 days to deadline).
   >
   > **Status**: Tests at 90% pass rate. Data integration in progress.
   >
   > **Loaded**: Championship-mode skill for multi-team optimization.
   >
   > **Key constraint**: Remember 400 FR counts as individual slot (VCAC).
   >
   > Ready to continue with psych sheet merging or would you like to focus on something else?"

---

## Files This Workflow Uses

| File                              | Purpose                                |
| --------------------------------- | -------------------------------------- |
| `.agent/CONTEXT_LOADER.md`        | Tier 0 - Always known meta-context     |
| `.agent/KNOWLEDGE_BASE.md`        | Tier 1 - Core domain knowledge         |
| `.agent/REFERENCE.md`             | Tier 2 - Historical context, changelog |
| `.agent/context/current_focus.md` | Current sprint, session notes          |
| `.agent/skills/*`                 | Tier 3 - Specialized skills            |
| `docs/SCORING_RULES.yaml`         | Structured scoring tables (if exists)  |

---

// turbo-all
