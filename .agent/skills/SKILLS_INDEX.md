# 🧰 AquaForge Skills Index

Skills are modular, battle-tested behaviors that load dynamically to enhance specialized reasoning without bloating the main context.

---

## 📦 Available Skills (12 Total)

### Domain Skills

| Skill                     | Path                            | Use Case                                 |
| ------------------------- | ------------------------------- | ---------------------------------------- |
| **scoring-validator**     | `skills/scoring-validator/`     | Validate VISAA/VCAC scoring calculations |
| **optimization-reviewer** | `skills/optimization-reviewer/` | Review optimizer output quality          |
| **data-validator**        | `skills/data-validator/`        | Validate psych sheet data integrity      |
| **championship-mode**     | `skills/championship-mode/`     | Multi-team championship optimization     |

### Development Skills

| Skill                  | Path                         | Use Case                                      |
| ---------------------- | ---------------------------- | --------------------------------------------- |
| **e2e-debugger**       | `skills/e2e-debugger/`       | Debug E2E test failures (Playwright, browser) |
| **test-generator**     | `skills/test-generator/`     | Generate tests using TDD principles           |
| **code-reviewer**      | `skills/code-reviewer/`      | Multi-perspective code review                 |
| **api-docs**           | `skills/api-docs/`           | Generate and maintain API documentation       |
| **browser-automation** | `skills/browser-automation/` | Stagehand/AI-powered web scraping             |

### Thinking Skills

| Skill               | Path                      | Use Case                                                         |
| -------------------- | ------------------------- | ---------------------------------------------------------------- |
| **discovery-flow**   | `skills/discovery-flow/`  | Structured creative exploration — find patterns across domains, name them, see where they break. For when the goal is the INSIGHT, not a deliverable. |

### Meta Skills

| Skill              | Path                     | Use Case                                      |
| ------------------ | ------------------------ | --------------------------------------------- |
| **project-memory** | `skills/project-memory/` | Persistent knowledge across sessions          |
| **smart-loader**   | `skills/smart-loader/`   | Auto-detect task type and load skills         |
| **multi-agent**    | `skills/multi-agent/`    | Orchestrate multiple agents for complex tasks |

---

## 🔄 Workflows

| Workflow          | Command            | Purpose                    |
| ----------------- | ------------------ | -------------------------- |
| **Start Session** | `/aquaforge-start` | Load context, review focus |
| **Health Check**  | `/health-check`    | Validate system state      |
| **Delegate**      | `/delegate`        | Route to subagents         |
| **Auto-Commit**   | `/auto-commit`     | Generate commit messages   |
| **Lint Fix**      | `/lint-fix`        | Fix all linting issues     |
| **PRISM**         | `/prism`           | Multi-perspective analysis |
| **Ralph**         | `/ralph`           | Iterative test-fix loop    |
| **E2E Fix**       | `/e2e-fix`         | Debug E2E failures         |

---

## 🚀 How to Use Skills

### Manual Loading

```markdown
"Load the scoring-validator skill"
→ AI reads skills/scoring-validator/SKILL.md
```

### Auto-Loading (via smart-loader)

Skills load automatically based on keywords:
- "scoring bug" → scoring-validator
- "write tests" → test-generator
- "code review" → code-reviewer
- "championship" → championship-mode

### Multi-Skill Loading

For complex tasks, chain skills:
```markdown
"Debug championship scoring E2E test"
→ e2e-debugger + championship-mode + scoring-validator
```

---

## 📊 Skill Categories

```
                    ┌─────────────────────┐
                    │    Meta Skills      │
                    │ (smart-loader,      │
                    │  project-memory,    │
                    │  multi-agent)       │
                    └──────────┬──────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
        ▼                      ▼                      ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│ Domain Skills │    │  Dev Skills   │    │   Workflows   │
│               │    │               │    │               │
│ scoring       │    │ test-gen      │    │ /health       │
│ optimizer     │    │ code-review   │    │ /commit       │
│ data          │    │ api-docs      │    │ /lint-fix     │
│ championship  │    │ e2e-debug     │    │ /delegate     │
│               │    │ browser-auto  │    │ /prism        │
└───────────────┘    └───────────────┘    └───────────────┘
```

---

## 🔧 Creating New Skills

Follow the SKILL.md template:

```markdown
---
name: Skill Name
description: One-line description
triggers:
  - keyword 1
  - keyword 2
---

# Skill Name

[Full documentation]
```

Place in `.agent/skills/[skill-name]/SKILL.md`

---

_Skills System v2.0 | AquaForge | 12 Skills + 8 Workflows_
