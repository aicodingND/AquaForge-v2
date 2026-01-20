---
name: Multi-Agent Orchestration
description: Patterns for orchestrating multiple AI agents for complex tasks
triggers:
  - parallel tasks
  - multi-agent
  - delegate multiple
  - orchestrate
---

# Multi-Agent Orchestration Skill 🎭

Patterns for coordinating multiple AI agents to tackle complex tasks efficiently.

---

## Why Multi-Agent?

Research shows multi-agent architectures are **50-60% more efficient** for complex tasks:
- Specialized agents do specific jobs better
- Parallel execution saves time
- Fresh context prevents confusion
- Separation of concerns

---

## Orchestration Patterns

### Pattern 1: Writer-Reviewer (Quality)

**Use When**: Code changes need validation

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Writer    │ ──▶ │  Reviewer   │ ──▶ │   Writer    │
│ Creates code│     │ Reviews for │     │ Fixes based │
│             │     │ bugs/issues │     │ on feedback │
└─────────────┘     └─────────────┘     └─────────────┘
```

**Implementation**:
1. Main agent writes code
2. Load `code-reviewer` skill with "fresh eyes" perspective
3. Apply fixes based on review

---

### Pattern 2: Parallel Explorers (Speed)

**Use When**: Searching across large codebase

```
         ┌─────────────┐
         │ Orchestrator│
         └──────┬──────┘
                │
    ┌───────────┼───────────┐
    ▼           ▼           ▼
┌───────┐   ┌───────┐   ┌───────┐
│Search │   │Search │   │Search │
│ api/  │   │ core/ │   │ tests/│
└───────┘   └───────┘   └───────┘
    │           │           │
    └───────────┼───────────┘
                ▼
         ┌─────────────┐
         │  Synthesize │
         └─────────────┘
```

**Implementation** (via `/delegate`):
```
// subagent: parallel
Search for "scoring" in:
- swim_ai_reflex/backend/api/
- swim_ai_reflex/backend/core/
- tests/
```

---

### Pattern 3: Pipeline (Sequential Tasks)

**Use When**: Tasks have dependencies

```
┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐
│ Analyze │ ▶ │  Plan   │ ▶ │ Execute │ ▶ │ Verify  │
└─────────┘   └─────────┘   └─────────┘   └─────────┘
```

**Implementation** (via PRISM workflow):
1. Understanding phase
2. Multi-perspective critique
3. Synthesis and planning
4. Execution
5. Meta-reflection

---

### Pattern 4: Specialist Routing (Expertise)

**Use When**: Different task types need different expertise

```
         ┌─────────────┐
         │   Router    │
         │ (classifies │
         │   request)  │
         └──────┬──────┘
                │
    ┌───────────┼───────────┬───────────┐
    ▼           ▼           ▼           ▼
┌───────┐   ┌───────┐   ┌───────┐   ┌───────┐
│Scoring│   │ E2E   │   │ API   │   │  Data │
│Expert │   │Debug  │   │Expert │   │Expert │
└───────┘   └───────┘   └───────┘   └───────┘
```

**Implementation** (via Smart Skill Loader):
- Detect task type from keywords
- Load appropriate skill
- Apply specialized reasoning

---

## AquaForge Multi-Agent Examples

### Example 1: Full Feature Implementation

```markdown
Task: Add Monte Carlo simulation to championship mode

// Phase 1: Research (Parallel)
// subagent: parallel
- Search existing optimization code
- Search for probability patterns
- Check test patterns

// Phase 2: Plan (Sequential via PRISM)
/prism Analyze how to add Monte Carlo to championship optimizer

// Phase 3: Implement (Writer)
[Create implementation]

// Phase 4: Review (Reviewer)
// skill: code-reviewer
Review the Monte Carlo implementation for:
- Statistical correctness
- Performance implications
- Edge cases

// Phase 5: Test (Specialist)
// skill: test-generator
Generate tests for Monte Carlo simulation

// Phase 6: Verify (Sequential)
/health
```

---

### Example 2: Bug Investigation

```markdown
Task: Championship shows 270-0 score

// Parallel investigation
// subagent: parallel
- Check scoring calculations
- Check team name handling
- Check API response formatting

// Specialist analysis
// skill: scoring-validator
Validate the scoring flow for championship mode

// Fix with review
[Apply fix]
// skill: code-reviewer
Review this fix for the X-0 scoring bug
```

---

### Example 3: Data Pipeline

```markdown
Task: Ingest new psych sheet data

// Step 1: Validate
// skill: data-validator
Validate the uploaded psych sheet

// Step 2: Transform (if issues)
[Apply normalizations]

// Step 3: Load
[Import to database/dataframe]

// Step 4: Verify
// skill: optimization-reviewer
Run optimization and verify output quality
```

---

## Integration with Existing Workflows

| Workflow              | Multi-Agent Pattern  |
| --------------------- | -------------------- |
| `/prism`              | Pipeline (5 phases)  |
| `/delegate`           | Specialist Routing   |
| `/ralph`              | Writer-Reviewer loop |
| `/e2e-fix`            | Pipeline + Parallel  |
| `code-reviewer` skill | Writer-Reviewer      |

---

## Frameworks Reference

For advanced orchestration beyond these patterns:

| Framework            | Best For              | Complexity |
| -------------------- | --------------------- | ---------- |
| **LangGraph**        | Stateful workflows    | High       |
| **CrewAI**           | Role-based agents     | Medium     |
| **AutoGen**          | Conversational agents | Medium     |
| **Claude Subagents** | Simple parallelism    | Low        |

---

## Best Practices

1. **Prefer simple patterns** - Don't over-engineer
2. **Use skills first** - Before spawning new agents
3. **Keep context focused** - Each agent has specific scope
4. **Synthesize results** - Combine outputs meaningfully
5. **Add human checkpoints** - For critical decisions

---

_Skill: multi-agent-orchestration | Version: 1.0 | Pattern: Enterprise_
