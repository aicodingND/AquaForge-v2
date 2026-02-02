---
name: Self-Learning Memory
description: Mem0-powered self-improving memory - learns from mistakes, updates agent rules
triggers:
  - learn from this
  - remember mistake
  - update agent rules
  - self improve
skills:
  - project-memory
---

# Self-Learning Memory Skill 🧠✨

Extends project-memory with Mem0-powered self-improvement capabilities.

---

## Quick Start (Mem0 Integration)

```bash
# Install Mem0
pip install mem0ai

# Set API key (get from https://app.mem0.ai)
export MEM0_API_KEY="your-key"
```

```python
from mem0 import MemoryClient

# Initialize
client = MemoryClient(api_key=os.environ["MEM0_API_KEY"])

# Store a learning
client.add([
    {"role": "assistant", "content": "Learned: Exhibition swimmers (grade ≤7) can displace opponents but never score"}
], user_id="aquaforge-agent")

# Retrieve relevant context
results = client.search("exhibition swimmer rules", filters={"user_id": "aquaforge-agent"})
```

---

## Memory Files (File-Based Fallback)

If Mem0 API unavailable, use local `.md` files:

| File                         | Purpose                      |
| ---------------------------- | ---------------------------- |
| `.agent/memory/MISTAKES.md`  | Errors + fixes (auto-append) |
| `.agent/memory/PATTERNS.md`  | Successful patterns to reuse |
| `.agent/memory/LEARNINGS.md` | Key learnings per session    |

---

## Self-Improvement Protocol

### On Error

```markdown
## [Date] Error: {summary}

**File:** `{filename}`
**Issue:** {what went wrong}
**Root Cause:** {why}
**Fix:** {solution}
**Prevention:** {pattern to avoid}
**Agent Update:** {which .md to update}
```

### On Success

```markdown
## [Date] Pattern: {name}

**Context:** {what worked}
**Reuse When:** {conditions}
**Code Example:**
```python
# snippet
```
```

### Session End

1. Review significant learnings
2. Append to MISTAKES.md or PATTERNS.md
3. Update relevant agent `.md` if rule change needed
4. Sync to Mem0 if connected

---

## Agent-Specific Updates

When a learning applies to a specific agent type:

| Agent        | File to Update                  | Example                    |
| ------------ | ------------------------------- | -------------------------- |
| Optimizer    | `.agent/agents/optimizer.md`    | Scoring rule clarification |
| Frontend     | `.agent/agents/frontend.md`     | UI pattern that worked     |
| Debugger     | `.agent/agents/debugger.md`     | Debug strategy that helped |
| Orchestrator | `.agent/agents/orchestrator.md` | Delegation pattern         |

**Format:**
```markdown
### Learning: {title} (added {date})

{description of what to do/avoid}
```

---

## Skills Pack System

### Loading External Skills

Skills are modular `.md` instruction files that enhance agent capabilities.

**Structure:**
```
.agent/skills/
├── {skill-name}/
│   ├── SKILL.md          # Main instructions (required)
│   ├── examples/         # Reference implementations
│   └── scripts/          # Helper scripts
```

**To add a new skill:**
1. Create folder in `.agent/skills/{skill-name}/`
2. Add `SKILL.md` with YAML frontmatter:
   ```yaml
   ---
   name: Skill Name
   description: What it does
   triggers:
     - when to activate
   ---
   ```
3. Register in `SKILLS_INDEX.md`

### Skill Quality Check

Before adopting a skill pack, verify:
- [ ] Clearer than full buildout?
- [ ] Tested in similar context?
- [ ] Non-breaking (additive only)?
- [ ] Documented triggers?

---

## Integration Points

- `/aquaforge-start` → Load recent learnings
- Session end → Prompt to save learnings
- Error encountered → Auto-append to MISTAKES.md
- Pattern recognized → Prompt to save to PATTERNS.md

---

_Skill: self-learning-memory | Version: 1.0 | Extends: project-memory_
