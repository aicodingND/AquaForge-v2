---
name: Code Reviewer
description: Multi-perspective code review using writer/reviewer pattern
triggers:
  - review this code
  - code review
  - check for bugs
  - quality check
---

# Code Reviewer Skill 👁️

Use this skill for thorough code reviews using the multi-Claude pattern.

---

## Review Pattern: Writer → Reviewer

This skill implements the **writer/reviewer pattern** where:
1. One perspective wrote the code
2. A fresh perspective reviews it critically

This catches issues that the "writer" mindset would miss.

---

## Review Procedure

### Step 1: Context Gathering

Before reviewing, gather:
- What the code is supposed to do
- Related tests (if any)
- Dependencies affected

### Step 2: Fresh Eyes Review

Adopt the mindset of a **skeptical senior engineer** who didn't write this code.

Ask these questions:

#### Logic & Correctness
- Does this code do what it claims?
- Are there off-by-one errors?
- Are edge cases handled?
- Are return types correct?

#### Error Handling
- What happens when things fail?
- Are errors caught and handled appropriately?
- Are error messages helpful?

#### Security
- Is user input validated?
- Are there injection vulnerabilities?
- Is sensitive data protected?

#### Performance
- Are there N+1 query issues?
- Unnecessary loops or computations?
- Could this cause memory issues?

#### Maintainability
- Is the code readable?
- Are names descriptive?
- Are there magic numbers that should be constants?
- Would a new developer understand this?

#### Tests
- Is there test coverage?
- Do tests cover edge cases?
- Are tests actually testing the right thing?

### Step 3: Document Findings

Use this format:

```markdown
## Code Review: [File/Function]

### Summary
[1-2 sentence overview]

### Critical Issues 🔴
- [Issue]: [Why it's critical] → [Suggested fix]

### Major Issues 🟠
- [Issue]: [Why it matters] → [Suggested fix]

### Minor Issues 🟡
- [Issue] → [Suggested fix]

### Suggestions 💡
- [Improvement idea]

### Positive Notes ✅
- [What was done well]
```

---

## AquaForge-Specific Review Points

When reviewing AquaForge code, always check:

### Scoring Code
- [ ] Correct scoring table for meet type (dual vs championship)
- [ ] Team names normalized before scoring
- [ ] Exhibition swimmers excluded from point totals
- [ ] Place lookups use correct indexing (1-based)

### Optimization Code
- [ ] Max 2 individual events per swimmer enforced
- [ ] Relay 3 penalty applied at VCAC
- [ ] Diving counts as individual slot
- [ ] Fatigue modeling applied correctly

### API Endpoints
- [ ] Input validation using Pydantic
- [ ] Error responses are informative
- [ ] Response model matches documentation

### Frontend
- [ ] Type safety (no `any` types)
- [ ] Error states handled in UI
- [ ] Loading states shown

---

## Multi-Claude Review (Advanced)

For critical code, use two passes:

### Pass 1: Writer Perspective
"If I wrote this, what would I defend?"
- Identify the intent
- Note deliberate tradeoffs

### Pass 2: Reviewer Perspective
"If I'm reviewing this fresh, what concerns me?"
- Challenge assumptions
- Find hidden bugs

### Synthesis
Compare both perspectives and provide balanced review.

---

## Integration with GitHub Actions

This skill integrates with `.github/workflows/claude-review.yml`:
- Automatically reviews PRs when opened
- Responds to `@claude review` comments
- Uses this skill's methodology

---

## Example Review

```markdown
## Code Review: optimize_entries()

### Summary
Function optimizes swimmer entries for championship meets. Generally solid but has one critical edge case.

### Critical Issues 🔴
- **Division by zero**: Line 45 divides by `num_events` without checking if it's 0.
  → Add guard: `if num_events == 0: return []`

### Major Issues 🟠
- **Team code mismatch**: Function uses `team.name` but should use `team.code` ("SST").
  → Use `target_team="SST"` per KNOWLEDGE_BASE.md

### Minor Issues 🟡
- Magic number `0.95` on line 78 should be `FATIGUE_FACTOR` constant
- Missing type hint on return value

### Suggestions 💡
- Consider adding a docstring explaining the constraint system
- Could cache the scoring table lookup

### Positive Notes ✅
- Good use of guard clauses for early returns
- Clean separation of constraint building from solving
```

---

_Skill: code-reviewer | Version: 1.0 | Pattern: Multi-Claude Review_
