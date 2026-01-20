# 📚 AquaForge Reference (Tier 2)

**Historical Context & Changelog**

This file contains historical decisions, changelogs, and reference material that doesn't need to be loaded every session. Load on-demand when historical context is needed.

---

## 📝 Changelog

| Date       | Update                                                      | Author |
| ---------- | ----------------------------------------------------------- | ------ |
| 2026-01-19 | **Token optimization** - Tiered context loading system      | AI     |
| 2026-01-19 | Created skills system with 5 modular skills                 | AI     |
| 2026-01-19 | Created /delegate workflow for subagent delegation          | AI     |
| 2026-01-19 | Researched AI coding tools - 12 key opportunities found     | AI     |
| 2026-01-19 | Created AI_CODING_TOOLS_RESEARCH_2026.md                    | AI     |
| 2026-01-18 | **Fixed championship target_team bug** - "SST" not "Seton"  | AI     |
| 2026-01-18 | PRISM analysis: Debugged E2E championship optimization      | AI     |
| 2026-01-17 | **Pipeline Architecture Implemented** - Phase 1 complete    | AI     |
| 2026-01-17 | Created DualMeetPipeline + ChampionshipPipeline             | AI     |
| 2026-01-17 | Created shared services (validation, normalization)         | AI     |
| 2026-01-17 | New API routers: /api/v2/dual-meet, /api/v2/championship    | AI     |
| 2026-01-17 | 29 new pipeline tests (189 total passing)                   | AI     |
| 2026-01-17 | PRISM analysis: Meet type architecture redesign             | AI     |
| 2026-01-17 | Created MEET_TYPE_ARCHITECTURE.md with pipeline pattern     | AI     |
| 2026-01-17 | Created PRISM workflow for meta-cognitive problem-solving   | AI     |
| 2026-01-17 | Created data_contracts.py for centralized validation        | AI     |
| 2026-01-17 | Integrated data contracts into optimization router          | AI     |
| 2026-01-17 | Added 35 dataflow validation tests (161 total passing)      | AI     |
| 2026-01-16 | Refactored back-to-back constraint to use proper validation | AI     |
| 2026-01-16 | Coach-facing strategy reports (MD + HTML)                   | AI     |
| 2026-01-16 | VCAC point projection complete (Seton #1 at 1202 pts)       | AI     |
| 2026-01-16 | Integration tests fixed: 125 passed, 1 failed               | AI     |
| 2026-01-16 | Diving score projection added to PointProjectionEngine      | AI     |
| 2026-01-16 | Unified VCAC psych sheet created (997 entries, 7 teams)     | AI     |
| 2026-01-16 | Fixed legacy test files (pandas boolean filtering)          | AI     |
| 2026-01-16 | Test suite at 94% pass rate (125/133)                       | AI     |
| 2026-01-16 | SwimCloud scraping complete for all VCAC teams              | AI     |
| 2026-01-15 | Created knowledge base, added VISAA championship info       | AI     |
| 2026-01-10 | Next.js migration completed                                 |        |
| 2025-12-30 | Meet alignment service integrated                           | AI     |

---

## 🏗️ Architecture Decisions Record

### ADR-001: Meet Type Pipeline Pattern

**Decision:** Dual meet and championship workflows use separate pipeline classes with a shared data layer.

**Context:**
- Dual meets and championship meets have fundamentally different structures
- Mixing them in `optimization_service.py` caused the 270-0 scoring bug
- They have different inputs (2 rosters vs psych sheet), outputs, and algorithms

**Key Insight:**

| Aspect       | Dual Meet                      | Championship Meet   |
| ------------ | ------------------------------ | ------------------- |
| Input        | 2 team rosters                 | Unified psych sheet |
| Teams        | 2 (head-to-head)               | 6-8+ (multi-team)   |
| Algorithm    | Nash Equilibrium / Game Theory | Entry Selection ILP |
| API          | Single endpoint                | Multi-step wizard   |
| Optimization | Beat ONE opponent              | Maximize vs field   |

**Implementation:**
- `pipelines/dual_meet.py` - DualMeetPipeline class
- `pipelines/championship.py` - ChampionshipPipeline class  
- `services/shared/` - Validation, normalization, caching

**Reference:** [MEET_TYPE_ARCHITECTURE.md](../docs/MEET_TYPE_ARCHITECTURE.md)

---

### ADR-002: Token-Optimized Context System (2026-01-19)

**Decision:** Implement tiered context loading for AI sessions.

**Context:**
- Previous system loaded 25KB+ at session start
- Not all context is needed for every task
- Specialized tasks need deep knowledge, routine tasks need minimal context

**Implementation:**
```
Tier 0: CONTEXT_LOADER.md      (~2KB, always loaded)
Tier 1: KNOWLEDGE_BASE.md      (~10KB, on-demand)
Tier 2: REFERENCE.md           (~15KB, historical lookups)
Tier 3: skills/*               (dynamic, task-specific)
```

**Benefits:**
- ~60% reduction in baseline token usage
- Specialized skills for complex tasks
- Scalable as knowledge grows

---

## 🐛 Historical Bug Fixes

### Bug: Team Name Scoring (270-0 Scores)
**Date:** 2026-01-16  
**Symptoms:** Dual meets showing "270 - 0" scores  
**Cause:** `full_meet_scoring()` only recognized teams named 'seton' or 'opponent'. Real team names caused 0 scores.  
**Fix:** Force-set team names: `nash_opponent_lineup["team"] = "opponent"` and `best_lineup["team"] = "seton"` before scoring.  
**Note:** Use assignment, NOT `.fillna()` - fillna only sets null values.

### Bug: Championship target_team (254-0 Display)
**Date:** 2026-01-18  
**Symptoms:** Championship showing "254 - 0" like dual meet format  
**Cause:** `ChampionshipGurobiStrategy` filters by team CODE ("SST"), router passed full name ("Seton")  
**Fix:** Use `target_team="SST"` in router, not `target_team="Seton"`

### Bug: Championship UI Format
**Date:** 2026-01-18  
**Symptoms:** Championship results showing "X vs 0" format  
**Cause:** Frontend used dual meet template for championship  
**Fix:** Check `meetMode === 'championship'` and render "Projected Score: X" instead

---

## 📊 Test Suite History

| Date       | Tests | Passed | Failed | Coverage |
| ---------- | ----- | ------ | ------ | -------- |
| 2026-01-19 | 130   | 117    | 2      | 90%      |
| 2026-01-17 | 189   | 189    | 0      | 100%     |
| 2026-01-16 | 133   | 125    | 1      | 94%      |
| 2026-01-15 | 120   | 110    | 10     | 92%      |

---

## 🔗 External References

- **Seton Swimming**: https://setonswimming.org
- **VISAA**: https://visaa.org
- **SwimCloud**: https://www.swimcloud.com
- **NFHS Rules**: https://www.nfhs.org/activities-sports/swimming-diving/

---

_This is Tier 2 reference material. Load when historical context is needed._  
_For active development knowledge, see KNOWLEDGE_BASE.md_
