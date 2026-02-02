---
name: Smart Skill Loader
description: Automatically detect task type and load relevant skills based on user request
triggers:
  - (auto-detected from user message)
---

# Smart Skill Loader 🧠

This skill provides automatic detection and loading of specialized skills based on user requests.

---

## How It Works

1. **Analyze user request** for keywords and patterns
2. **Match against detection matrix** below
3. **Pre-load relevant skill(s)** before responding
4. **Chain skills** for complex tasks

---

## Detection Matrix

### Scoring Issues → `scoring-validator`

**Trigger Patterns**:
- "scoring", "points", "place", "placing"
- "wrong score", "score bug", "X-0", "270-0"
- "VISAA scoring", "VCAC scoring", "championship scoring"
- "dual meet points", "individual points", "relay points"
- "exhibition", "no points", "didn't score"
- Numeric patterns: "16-13-12", "8-6-5-4-3-2-1"
- "first place", "second place", "DQ"

**Load**: `.agent/skills/scoring-validator/SKILL.md`

---

### Test Generation → `test-generator`

**Trigger Patterns**:
- "write tests", "generate tests", "add tests", "create tests"
- "TDD", "test-driven", "test first"
- "coverage", "test coverage", "untested"
- "pytest", "unit test", "test case", "test file"
- "failing test", "test for this", "needs tests"
- "edge cases", "boundary", "corner case"
- "mock", "fixture", "parametrize"

**Load**: `.agent/skills/test-generator/SKILL.md`

---

### Code Review → `code-reviewer`

**Trigger Patterns**:
- "review", "code review", "review this"
- "check this code", "look at this", "anything wrong"
- "bugs", "issues", "problems with"
- "quality check", "sanity check"
- "security review", "performance review"
- "before merging", "PR review", "ready to merge"
- "refactor", "clean up", "improve"

**Load**: `.agent/skills/code-reviewer/SKILL.md`

---

### E2E/Browser Testing → `e2e-debugger`

**Trigger Patterns**:
- "E2E", "end-to-end", "e2e test"
- "Playwright", "puppeteer", "selenium"
- "browser test", "UI test", "integration test"
- "locator", "selector", "CSS selector", "XPath"
- "click fails", "element not found", "timeout"
- "page load", "navigation", "headless"
- "screenshot", "visual test", "recording"
- "DOM", "page object"

**Load**: `.agent/skills/e2e-debugger/SKILL.md`

---

### Championship Mode → `championship-mode`

**Trigger Patterns**:
- "championship", "championships"
- "VCAC", "VISAA States", "states meet"
- "multi-team", "12 teams", "16 teams", "8 teams"
- "point projection", "projected score"
- "win probability", "chance of winning"
- "seeding", "seed time", "psych sheet ranking"
- "relay trade-off", "strategic", "game theory"
- "Monte Carlo", "simulation", "probability"
- "February 7", "Feb 12-14"

**Load**: `.agent/skills/championship-mode/SKILL.md`

---

### API Development → `api-docs`

**Trigger Patterns**:
- "API", "endpoint", "route", "router"
- "FastAPI", "swagger", "OpenAPI", "redoc"
- "request", "response", "HTTP"
- "Pydantic", "schema", "model", "validation"
- "422", "400", "500", "status code"
- "document API", "API docs", "API reference"
- "POST", "GET", "PUT", "DELETE"
- "JSON", "payload", "body"

**Load**: `.agent/skills/api-docs/SKILL.md`

---

### Data Validation → `data-validator`

**Trigger Patterns**:
- "psych sheet", "roster", "entries", "lineup"
- "swimmer data", "swimmer times", "seed time"
- "SwimCloud", "scraped", "scraping"
- "data quality", "missing data", "null", "NaN"
- "format", "parse", "CSV", "Excel", "XLSX"
- "normalization", "normalize", "duplicates"
- "time format", "MM:SS.ss", "invalid time"
- "team name", "swimmer name", "event name"

**Load**: `.agent/skills/data-validator/SKILL.md`

---

### Optimization Review → `optimization-reviewer`

**Trigger Patterns**:
- "optimizer", "optimization", "optimize"
- "lineup", "assignments", "entries"
- "Gurobi", "MILP", "solver"
- "constraint", "feasibility", "infeasible"
- "Nash", "equilibrium", "game theory"
- "objective function", "maximize", "minimize"
- "solution", "optimal", "suboptimal"
- "dual meet", "meet result"

**Load**: `.agent/skills/optimization-reviewer/SKILL.md`

---

### Memory/History → `project-memory`

**Trigger Patterns**:
- "remember", "recall", "what did we"
- "decision", "decided", "we chose"
- "last time", "previously", "before"
- "history", "past session", "earlier"
- "save this", "note this", "log this"
- "knowledge base", "update docs"
- "where is", "where did", "what file"

**Load**: `.agent/skills/project-memory/SKILL.md`

---

## Multi-Skill Chains

For complex tasks, load multiple skills:

| Request Type                     | Primary Skill         | Secondary Skill       |
| -------------------------------- | --------------------- | --------------------- |
| "Debug championship scoring"     | championship-mode     | scoring-validator     |
| "Review optimizer output"        | optimization-reviewer | code-reviewer         |
| "Generate tests for API"         | test-generator        | api-docs              |
| "Validate scraped psych sheet"   | data-validator        | championship-mode     |
| "E2E test for scoring page"      | e2e-debugger          | scoring-validator     |
| "Fix test failures in optimizer" | test-generator        | optimization-reviewer |
| "Document the scoring API"       | api-docs              | scoring-validator     |

---

## Anti-Patterns (Don't Auto-Load)

These are too vague - ask for clarification:

- "fix this" (what specifically?)
- "help" (with what?)
- "it's broken" (what is?)
- "doesn't work" (what behavior expected?)

**Instead, ask**: "Could you specify what aspect you'd like help with? (scoring, testing, optimization, etc.)"

---

## Usage Example

```
User: "The championship scoring shows 270-0 which seems wrong"

Smart Loader Detects:
- "championship" → championship-mode
- "scoring" → scoring-validator
- "270-0" → scoring bug pattern

Action: Load scoring-validator (primary), then apply championship context

Response: "Loading scoring-validator skill for championship mode...
Based on the X-0 pattern, this looks like the team name normalization bug.
[proceeds with diagnosis from skill]"
```

---

_Skill: smart-skill-loader | Version: 1.0 | Core system skill_
