---
description: Auto-delegate tasks to appropriate subagents for parallel execution
---

# Task Delegation Workflow

Use this workflow to automatically delegate tasks to specialized subagents for parallel, efficient execution.

---

## How to Invoke

- `/delegate [task description]`
- "Delegate this to the right subagent"
- "Run this in parallel"

---

## Delegation Categories

### 1. Browser Subagent Tasks

**Triggers:**
- UI testing / E2E tests
- Visual validation
- Web scraping
- Screenshot capture
- User flow simulation

**Delegation Pattern:**
```
// subagent: browser
Task: [Specific browser task]
Return: [Expected output - screenshot, test result, scraped data]
Stop When: [Clear termination condition]
```

**Example:**
```
// subagent: browser
Task: Navigate to localhost:3000, click "Load Sample", wait for roster to display,
      click "Optimize", capture screenshot of results, verify score > 0
Return: Screenshot and confirmation that optimization completed with score
Stop When: Results displayed OR error encountered
```

### 2. Sequential Thinking Tasks

**Triggers:**
- Complex problem decomposition
- Multi-step analysis
- Architecture decisions
- Debugging complex issues

**Delegation Pattern:**
Use `mcp_sequential-thinking_sequentialthinking` for structured reasoning.

**Example:**
```python
# Break down optimization failure
mcp_sequential-thinking_sequentialthinking(
    thought="Analyzing why VCAC optimization returned 0 points...",
    nextThoughtNeeded=True,
    thoughtNumber=1,
    totalThoughts=5
)
```

### 3. Parallel File Operations

**Triggers:**
- Multiple independent file edits
- Bulk search across codebase
- Independent test runs

**Pattern:**
Make multiple tool calls without `waitForPreviousTools: true` to run in parallel.

---

## Task Analysis

Before delegating, analyze the task:

```
1. Is this a browser/UI task? → Browser subagent
2. Does this need visual validation? → Browser subagent
3. Is this complex reasoning? → Sequential thinking
4. Are there multiple independent subtasks? → Parallel execution
5. Is this domain-specific? → Load skill first, then execute
```

---

## Integration with Skills

Load relevant skill before delegating:

```markdown
### Step 1: Load E2E Skill
// skill: e2e-debugger
View .agent/skills/e2e-debugger/SKILL.md

### Step 2: Delegate Browser Test
// subagent: browser
Task: Run E2E optimization test following e2e-debugger patterns
```

---

## Subagent Best Practices

### Browser Subagent

1. **Be specific about actions**
   - ❌ "Test the app"
   - ✅ "Navigate to localhost:3000, click button with text 'Submit', verify success message appears"

2. **Define clear return conditions**
   - ❌ "Let me know what happens"
   - ✅ "Return: Screenshot of results page, team score value, any console errors"

3. **Set explicit stop conditions**
   - ❌ "Keep testing"
   - ✅ "Stop when: Results displayed, OR error dialog appears, OR 30 seconds timeout"

### Sequential Thinking

1. **Start with clear problem statement**
2. **Estimate total thoughts needed**
3. **Be willing to revise and add thoughts**
4. **Document conclusions**

### Parallel Operations

1. **Ensure tasks are truly independent**
2. **Don't read files you're about to edit**
3. **Consolidate related edits into single tool call**

---

## Token Optimization

Delegation saves tokens by:
1. **Specialization** - Subagents have focused context
2. **Parallelization** - Multiple tasks run simultaneously
3. **Skill loading** - Only load relevant skills

---

## Workflow Integration

This workflow integrates with:
- `/e2e-fix` - Delegates browser testing
- `/prism` - Uses sequential thinking for critique
- `/ralph` - Parallelizes test-fix iterations

---

## Examples

### Example 1: E2E Test with Browser Subagent

```markdown
User: "Test the optimization flow end-to-end"

Agent:
1. Load e2e-debugger skill
2. Delegate to browser subagent:

   // subagent: browser
   Task:
   1. Navigate to localhost:3000
   2. Wait for page load
   3. Click "Load Sample Data"
   4. Wait for roster to appear (data-testid="roster-loaded")
   5. Click "Optimize" button
   6. Wait for results (data-testid="results-table")
   7. Capture score from data-testid="team-score"

   Return: Screenshot of results, score value, any errors
   Stop When: Score displayed OR error encountered
```

### Example 2: Multi-file Refactor

```markdown
User: "Update team name normalization across all files"

Agent: Run parallel grep + edit operations
- Search 1: grep_search "opponent" in optimization.py
- Search 2: grep_search "seton" in scoring.py
- Search 3: grep_search "team" in data_contracts.py
[All run in parallel, then sequential edits]
```

### Example 3: Complex Debug with Sequential Thinking

```markdown
User: "Why is championship scoring wrong?"

Agent: Use sequential thinking
- Thought 1: "What is the expected scoring behavior?"
- Thought 2: "What is the actual behavior?"
- Thought 3: "What could cause discrepancy?"
- Thought 4: "Test hypothesis: team name normalization"
- Thought 5: "Verify fix resolves issue"
```

---

// turbo-all

_Workflow: delegate | Version: 1.0_
