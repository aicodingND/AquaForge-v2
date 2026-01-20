---
description: Intelligent auto-commit with conventional commit messages
---

# Auto-Commit Workflow 📝

Generate intelligent commit messages and manage atomic commits.

---

## How to Invoke

- `/commit`
- "Commit these changes"
- "Auto-commit"

---

## Workflow Steps

### Step 1: Check Git Status

// turbo
```bash
git status --short
```

### Step 2: Analyze Changes

// turbo
```bash
git diff --stat HEAD
```

### Step 3: Generate Commit Message

Based on the changes, generate a conventional commit:

**Format**: `type(scope): description`

| Type       | When to Use                 |
| ---------- | --------------------------- |
| `feat`     | New feature                 |
| `fix`      | Bug fix                     |
| `docs`     | Documentation only          |
| `style`    | Formatting, no code change  |
| `refactor` | Code change, no feature/fix |
| `test`     | Adding/updating tests       |
| `chore`    | Build process, dependencies |

**Scope Examples**:
- `scoring` - Scoring calculations
- `optimizer` - Optimization engine
- `api` - Backend API
- `ui` - Frontend changes
- `e2e` - End-to-end tests
- `agent` - AI agent configuration

### Step 4: Stage and Commit

```bash
git add -A
git commit -m "type(scope): description"
```

---

## Smart Grouping

If changes span multiple areas, suggest splitting:

```
Detected changes in:
- 3 files in /api/ (backend)
- 2 files in /frontend/ (UI)
- 1 file in /tests/ (tests)

Suggest splitting into:
1. feat(api): add new endpoint
2. feat(ui): update form component
3. test(api): add endpoint tests

Proceed with combined commit or split? [combined/split]
```

---

## Examples

### Single Feature
```bash
git commit -m "feat(scoring): add VCAC relay scoring table"
```

### Bug Fix
```bash
git commit -m "fix(optimizer): use team code SST not full name Seton"
```

### Documentation
```bash
git commit -m "docs(agent): update KNOWLEDGE_BASE with scoring rules"
```

### Multi-file Refactor
```bash
git commit -m "refactor(api): extract data contracts to separate module"
```

---

## Pre-Commit Validation

Before committing, optionally run:

```bash
ruff check . --fix
ruff format .
python -m pytest tests/ -x -q
```

---

// turbo-all
