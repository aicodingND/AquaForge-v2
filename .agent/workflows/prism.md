---
description: PRISM - Perspective-based Recursive Iterative Self-improvement Method for complex problem solving
---

# PRISM Workflow 🔮

**P**erspective-based **R**ecursive **I**terative **S**elf-improvement **M**ethod

A meta-cognitive prompting framework that simulates an expert panel for superior problem-solving. Based on MIT research showing **110% accuracy improvement** through recursive self-reflection.

---

## What Is PRISM?

PRISM is a structured approach where I:
1. Generate an initial solution
2. Critique it from multiple expert perspectives  
3. Synthesize feedback and improve
4. Repeat until confidence threshold is met
5. Document learnings for future sessions

Think of it as having a room full of experts reviewing your code, rather than just one person.

---

## When To Use PRISM

Invoke PRISM for:
- 🏗️ **Architecture decisions** - "How should we structure this module?"
- 🐛 **Complex debugging** - "Why is this failing and how do we fix it properly?"
- ✨ **Feature design** - "What's the best way to implement X?"
- 🔄 **Refactoring** - "How do we improve this code without breaking things?"
- 📊 **Optimization** - "How do we make this faster/better/more reliable?"

---

## How To Invoke

Tell Antigravity:
- `/prism [problem or task]`
- "Use PRISM to design the new scoring system"
- "Think through this carefully with multiple perspectives"

---

## THE PRISM PROCESS

```
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 1: UNDERSTAND & GENERATE                                  │
│  ▸ State the problem clearly                                     │
│  ▸ Identify constraints and goals                                │
│  ▸ Generate initial solution                                     │
│  ▸ Document initial reasoning                                    │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 2: MULTI-PERSPECTIVE CRITIQUE  (The Expert Panel)        │
│                                                                  │
│  🔬 SCIENTIST: Is this logically sound? Assumptions?            │
│  🛡️ SECURITY: What could go wrong? Edge cases?                  │
│  🎨 UX EXPERT: Is this intuitive? User experience?              │
│  ⚡ PERFORMANCE: Is this efficient? Complexity?                 │
│  🧪 QA TESTER: How would I break this? Missing tests?           │
│  📚 DOCS EXPERT: Is this clear? What needs explanation?         │
│                                                                  │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 3: SYNTHESIS                                              │
│  ▸ Collect all critiques                                         │
│  ▸ Identify actionable improvements                              │
│  ▸ Prioritize by impact                                          │
│  ▸ Estimate confidence level (0-100%)                            │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 4: REFINE                                                 │
│  ▸ Apply high-priority improvements                              │
│  ▸ Document why each change was made                             │
│  ▸ Verify with tests/examples                                    │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 5: META-REFLECTION                                        │
│  ▸ What did I learn from this iteration?                         │
│  ▸ What patterns should I apply next time?                       │
│  ▸ Update knowledge base with learnings                          │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  RECURSION CHECK                                                 │
│  If confidence < 80% OR critical issues found → Return to PHASE 1│
│  Otherwise → COMPLETE ✅                                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## PHASE 1: UNDERSTAND & GENERATE

### Step 1.1: Problem Decomposition

Use `sequential-thinking` MCP to break down the problem:

```
Thought 1: "What is the user actually asking for?"
Thought 2: "What are the constraints?"
Thought 3: "What are the success criteria?"
Thought 4: "What approaches are possible?"
```

### Step 1.2: Initial Solution

Generate the first complete solution. Don't overthink - get something working.

### Step 1.3: Document Reasoning

Write down WHY you chose this approach. This becomes input for critique.

---

## PHASE 2: MULTI-PERSPECTIVE CRITIQUE

### The Expert Panel

For each perspective, ask yourself the specific questions:

#### 🔬 Scientist Perspective

```
- Is this logically sound?
- What assumptions am I making?
- Is there evidence this approach works?
- What could invalidate this solution?
```

#### 🛡️ Security Auditor Perspective

```
- What could go wrong?
- What are the edge cases?
- What happens with bad input?
- Are there race conditions or state issues?
```

#### 🎨 UX Designer Perspective

```
- Is this intuitive to use?
- What's the user's mental model?
- Are error messages helpful?
- Is the API/interface consistent?
```

#### ⚡ Performance Engineer Perspective

```
- What's the time complexity?
- What's the space complexity?
- Are there unnecessary operations?
- Will this scale?
```

#### 🧪 QA Tester Perspective

```
- How would I break this?
- What tests are missing?
- What are the boundary conditions?
- What's the test coverage?
```

#### 📚 Documentation Expert Perspective

```
- Is this self-documenting?
- What needs comments?
- Are the names descriptive?
- Would a new developer understand this?
```

### Recording Critiques

For each perspective, record:
- **Issue found** (or "None")
- **Severity**: Critical / High / Medium / Low / Info
- **Suggested fix** (if applicable)

---

## PHASE 3: SYNTHESIS

### Prioritization Matrix

| Severity | Action                     |
| -------- | -------------------------- |
| Critical | Must fix before proceeding |
| High     | Fix in this iteration      |
| Medium   | Consider fixing            |
| Low      | Document for later         |
| Info     | Note for learning          |

### Confidence Estimation

Ask: "On a scale of 0-100%, how confident am I that this solution is correct and complete?"

Consider:
- Coverage of all requirements
- Quality of tests
- Consistency of approach
- Robustness to edge cases

---

## PHASE 4: REFINE

### Apply Improvements

1. Address all Critical and High severity issues
2. Verify each fix with a test or example
3. Document the change and reasoning

### Verification

// turbo

```bash
# Run relevant tests
python -m pytest tests/ -v -k "relevant_test_pattern"

# Type check changes
pyright changed_file.py
```

---

## PHASE 5: META-REFLECTION

### Learning Extraction

Answer these questions:

1. **What worked well?**
   - Which perspective found the most issues?
   - What approach was most effective?

2. **What should I do differently next time?**
   - Did I miss something obvious?
   - Was there a pattern I should recognize faster?

3. **What should be added to the knowledge base?**
   - New gotchas discovered?
   - New best practices?
   - Domain facts learned?

### Knowledge Base Update

If significant learnings, update `.agent/KNOWLEDGE_BASE.md`

---

## RECURSION CONDITION

**Return to PHASE 1 if:**
- Confidence < 80%
- Any Critical issues remain unfixed
- Major architectural changes were made

**Complete if:**
- Confidence ≥ 80%
- All Critical/High issues addressed
- Tests passing
- Solution is documented

---

## EXAMPLE PRISM SESSION

**Problem**: "Optimize the relay assignment algorithm"

### PHASE 1: Generate
```
Initial solution: Use Hungarian algorithm for optimal assignment
Reasoning: Classic optimization algorithm for assignment problems
```

### PHASE 2: Critique

| Perspective   | Issue                                                           | Severity |
| ------------- | --------------------------------------------------------------- | -------- |
| 🔬 Scientist   | Hungarian assumes costs are comparable - are relay split times? | High     |
| 🛡️ Security    | What if swimmer has no split time? Division by zero?            | Critical |
| ⚡ Performance | O(n³) - is this acceptable for expected team sizes?             | Medium   |
| 🧪 QA          | No test for edge case with fewer swimmers than positions        | High     |

### PHASE 3: Synthesis
- Confidence: 60% (Critical issue found)
- Priority: Fix division by zero, add edge case handling

### PHASE 4: Refine
- Added null check for split times
- Added default value fallback
- Created test for missing split times

### PHASE 5: Meta-Reflection
- **Learning**: Always check for null/missing data in optimization inputs
- **Knowledge Base Update**: Added to gotchas: "Relay split times may be null"

### RECURSION: Return to Phase 2
- Re-critique with fixes applied
- New confidence: 85%
- Complete ✅

---

## INTEGRATION WITH OTHER WORKFLOWS

| Workflow           | When PRISM Calls It                        |
| ------------------ | ------------------------------------------ |
| `/ralph`           | During Phase 4 for iterative testing       |
| `/e2e-fix`         | After Phase 4 for comprehensive validation |
| `/aquaforge-start` | Before Phase 1 to load context             |

---

## PRISM + SEQUENTIAL-THINKING

PRISM naturally integrates with the `sequential-thinking` MCP:

```python
# Each PRISM phase can be a thought
Thought 1: "PHASE 1 - Understanding the problem..."
Thought 2: "PHASE 2 - Scientist perspective..."
Thought 3: "PHASE 2 - Security perspective..."
Thought 4: "PHASE 3 - Synthesizing critiques..."
Thought 5: "PHASE 4 - Refining solution..."
Thought 6: "PHASE 5 - Meta-reflection..."
```

---

## TIPS FOR EFFECTIVE PRISM

1. **Don't skip perspectives** - Even if you think they're not relevant
2. **Be your own harshest critic** - Better to find issues now than later
3. **Document everything** - Your future self will thank you
4. **Trust the process** - Even if it feels slow, the quality improves
5. **Update the knowledge base** - Compound learnings over time

---

## QUICK REFERENCE: The 6 Perspectives

| Icon | Perspective | Key Question             |
| ---- | ----------- | ------------------------ |
| 🔬    | Scientist   | Is this logically sound? |
| 🛡️    | Security    | What could go wrong?     |
| 🎨    | UX Expert   | Is this intuitive?       |
| ⚡    | Performance | Is this efficient?       |
| 🧪    | QA Tester   | How would I break this?  |
| 📚    | Docs Expert | Is this clear?           |

---

_Workflow Version: 1.0_
_Created: 2026-01-16_
_Based on: MIT Recursive Meta-Cognition Research_
_Author: Antigravity AI_
