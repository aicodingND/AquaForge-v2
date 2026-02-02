# Mistakes Log 🐛

Track errors and their fixes to avoid repeating them.

---

## Format

```markdown
## [Date] Error: {summary}

**File:** `{filename}`
**Issue:** {description}
**Root Cause:** {why it happened}
**Fix:** {solution}
**Prevention:** {pattern to avoid in future}
```

---

## Logged Mistakes

<!-- Append new entries below this line -->

## 2026-02-01 Error: Optimization router used wrong parameter name

**File:** `optimization_router.py`
**Issue:** Logic checked `self.prefer_aqua` but parameter was renamed to `prefer_gurobi`
**Root Cause:** Incomplete refactor when changing Aqua to primary optimizer
**Fix:** Updated condition to `self.prefer_gurobi`
**Prevention:** When renaming parameters, grep for all usages before committing

## 2026-02-02 Error: VCAC scoring tables swapped in documentation

**Files:** `docs/VCAC_CHAMPIONSHIP_FEB7_2026.md`, `data/meets/2026-02-07_vcac_championship.json`, `docs/PRISM_CHAMPIONSHIP_SCORING_ANALYSIS.md`, `.agent/KNOWLEDGE_BASE.md`
**Issue:** Individual and relay point tables were swapped. Docs claimed individual=[32,26,24...] and relay=[16,13,12...] ("individual worth MORE than relay"). Code correctly had individual=[16,13,12...] and relay=[32,26,24...] (relay = 2x individual).
**Root Cause:** Original VCAC doc was written with tables mislabeled. The error then propagated to KNOWLEDGE_BASE, PRISM analysis, and JSON data file. Nobody cross-checked against NCAA/NFHS standard scoring rules.
**Fix:** Corrected all 4 files. Relay = 2x individual is the universal standard for championship swimming (NCAA Rule 7, NFHS, USA Swimming).
**Prevention:** Always verify scoring rules against authoritative external sources (NCAA, NFHS, governing body) before documenting. Don't trust a single source doc — cross-reference with the code AND external rules.

## 2026-02-02 Error: Grade exhibition rules said 7-8 instead of 6-7

**File:** `docs/SCORING_RULES.yaml`, `.agent/KNOWLEDGE_BASE.md`
**Issue:** `exhibition_grades: [7, 8]` and `scoring_grades: [9, 10, 11, 12]` — this incorrectly excludes 8th graders from scoring.
**Root Cause:** Original author may have confused "grades 7 and below" with "grades 7-8". The code correctly uses `min_scoring_grade = 8` (grade >= 8 scores).
**Fix:** Changed to `exhibition_grades: [6, 7]` and `scoring_grades: [8, 9, 10, 11, 12]`.
**Prevention:** When documenting grade rules, always cross-check against the code's `min_scoring_grade` value.
