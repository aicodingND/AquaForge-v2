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

## Recurring Error Patterns (check these FIRST on every task)

| # | Pattern | Frequency | Files Most Affected | Quick Check |
|---|---------|-----------|---------------------|-------------|
| 1 | **Docs wrong, code correct** — documentation diverges from implementation | 3/5 errors | `docs/`, `.agent/KNOWLEDGE_BASE.md`, YAML configs | Always trust the code, verify docs against it |
| 2 | **Incomplete edits** — partial changes that leave broken references | 2/5 errors | Any file touched by AI or bulk refactor | After every edit: grep for old names, run `tsc --noEmit` |
| 3 | **React callback instability** — inline functions in hook dep arrays | 1/5 errors | `hooks/`, any custom hook with callback options | Any `useEffect`/`useCallback` with a callback dep → use ref pattern |
| 4 | **Config value mismatches** — YAML/JSON configs disagree with code constants | 2/5 errors | `SCORING_RULES.yaml`, meet JSON files, `rules.py` | Diff config values against code constants before trusting either |

**On every session start:** Scan modified files for patterns #1 and #2 before doing new work.

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

## [2026-02-02] UI State Persistence Glitch — Restore Session Popup Infinite Loop

**Files:** `frontend/src/components/AutoSaveIndicator.tsx`, `frontend/src/hooks/usePersistence.tsx`

**Issue:** "Restore Session" popup reoccurred on every render, couldn't be dismissed, and did nothing when clicked.

**Root Causes (2):**

1. **Broken JSX in AutoSaveIndicator.tsx:78** — The component's `return` statement, modal wrapper (`<div className="fixed inset-0 z-50..."`), heading, description, and `handleForceSave` function were replaced with a literal `// ...` comment. This made the component syntactically invalid — the popup couldn't render, and the "Save Now" button crashed on the undefined `handleForceSave`.

2. **Unstable callback refs in usePersistence.tsx** — `onLoad`, `onSave`, `onError` were inline functions included in `useEffect`/`useCallback` dependency arrays. Every re-render created new function references → React saw deps "changed" → load effect re-fired → `setShowRestorePrompt(true)` called again → re-render → infinite cycle. The same instability caused the auto-save `useEffect` (which depended on `saveData`, which depended on `onSave`) to re-fire every render, resetting the 2s debounce timer endlessly.

**Fix:**
1. Restored complete JSX: `handleForceSave` function + `return (<>` + `{showRestorePrompt && (` conditional + modal overlay + glass card + heading + description.
2. Added stable `useRef` wrappers for all three callbacks (`onLoadRef`, `onSaveRef`, `onErrorRef`). Refs are updated synchronously during render (`ref.current = callback`) but never change identity, so effects only fire when `key` changes — not on every render.

**Cost of Bug:**
- Users could never restore a previous session → lost work every page reload
- Save indicator pulsed continuously (isSaving toggled every 2s) → visual noise
- Potential localStorage thrashing from constant re-saves

**Prevention:**
- Never include inline callbacks in `useEffect`/`useCallback` dependency arrays — use the callback ref pattern instead (see PATTERNS.md → "Callback Ref")
- When editing JSX, always verify the return statement and conditional wrappers remain intact
- Run `tsc --noEmit` or check IDE diagnostics after edits — the broken file would have shown immediate syntax errors

**Recurring pattern match:** #2 (incomplete edit — `// ...` replaced code) + #3 (React callback instability)

**What worked in diagnosis:** Reading the component file revealed the `// ...` immediately. Tracing the `useEffect` dep chain (`onLoad` → re-render → new `onLoad` → effect re-fires) identified the infinite loop. Both fixes took <5 min once root causes were clear — the lesson is **read the file first, trace the render cycle second**.

## 2026-02-15 Error: Gurobi uses DUAL scoring tables for championship meets

**Files:** `swim_ai_reflex/backend/core/strategies/gurobi_strategy.py` (line 147), `data/meets/2026-02-12_visaa_state.json`, `scripts/generate_visaa_championship_pdf.py`
**Issue:** Three scoring table problems compounded:
1. Gurobi hardcoded DUAL meet scoring `[8,6,5,4,3,2,1]` instead of championship `[20,17,16,...,1]` — results in 2.5× lower totals than AquaOptimizer
2. VISAA meet JSON labeled tables "championship"/"consolation" instead of "relay"/"individual" — same swapped-labels bug as VCAC (2026-02-02)
3. PDF generator used relay table `[40,34,...]` for individual scoring — 2× inflation
**Root Cause:** Gurobi never received a championship scoring mode. Built for dual meets, never parameterized for different meet types. Meet JSON repeated the VCAC labeling mistake.
**Fix:**
1. Added `scoring_profile` kwarg to Gurobi so it can receive `ScoringProfile.visaa_championship()` — logs a warning when using default dual tables
2. Renamed JSON keys to `"relay"` / `"individual"` (clear, unambiguous)
3. Fixed PDF to use `INDIVIDUAL_POINTS=[20,17,...]` and `RELAY_POINTS=[40,34,...]` with `get_points(place, is_relay=bool)`
4. Added opponent completeness validation to BOTH optimizers — warns when events have no opponents
**Prevention:** (a) Never hardcode scoring tables — always accept them as parameters, (b) Name scoring table keys by what they ARE (relay/individual) not where they're used (championship/consolation), (c) Always validate opponent roster completeness before running optimization
**Recurring pattern match:** #4 (config value mismatches)
