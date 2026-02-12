# AquaForge.ai - Version Log

## Platform History

> **Canonical Platform:** macOS (as of 2026-01-10)
> **Original Development:** Windows — fully migrated, Windows scripts deprecated.

### Transfer Record: v1.0.0-next

**Date**: 2026-01-10
**Source**: Windows development environment
**Destination**: macOS (canonical)
**Status**: ✅ Complete — Mac is the single source of truth.

---

## Version Information

### v1.0.0-next (2026-01-10)

**Major Changes**:

- ✅ Migrated from Reflex to Next.js + FastAPI architecture
- ✅ Reorganized project structure (archived legacy UI)
- ✅ Created comprehensive documentation (HANDOFF.md)
- ✅ Organized data files into `__DATA__/` directory
- ✅ Consolidated Windows development into macOS as canonical platform

**Tech Stack**:

- Frontend: Next.js 16, React 19, TypeScript, Tailwind v4
- Backend: FastAPI, Python 3.11+
- Optimization: Nash Equilibrium + Heuristic algorithms

**Key Files**:

- `HANDOFF.md` - Project overview and setup
- `start_dev.sh` - Development startup script (macOS)
- `run_server.py` - Server runner

---

### v1.0.1-dev (2026-01-16)

**Relay & Diving Integration**:

- ✅ Created `constraint_validator.py` - Enforces back-to-back constraints including relay legs
- ✅ Back-to-back is now a **STANDARD RULE** (not optional fatigue toggle)
- ✅ Relay leg swimmers cannot swim immediately following event
- ✅ Created comprehensive tests (`test_constraint_validator.py` - 29 tests passing)
- ✅ Created `OPTIMIZATION_STRATEGIES_GUIDE.md` - Central reference for all algorithms
- ✅ VCAC 400 Free Relay penalty correctly implemented (counts as 1 individual)
- ✅ Diver constraint handling (diving = 1 individual event)
- ✅ Integrated constraint validator into `championship_strategy.py`
- ✅ Added `get_relay_swimmers_for_constraints()` and `get_blocked_swimmers_for_event()` utilities
- ✅ All existing tests passing (13 relay + 14 entry + 29 constraint = 56 tests)

**Key Constraint Rules**:

- 200 Medley Relay → blocks 200 Free
- 200 Free Relay → blocks 100 Back
- 500 Free → blocks 200 Free Relay
- 100 Breast → blocks 400 Free Relay

**Optimization Algorithms Documented**:

- Nash Equilibrium (dual meets)
- Gurobi MILP (championship meets)
- Hungarian Algorithm (medley relay assignment)
- Monte Carlo (uncertainty quantification)
- Stackelberg (unexploitable strategies)

### v1.0.1-dev-advanced (2026-01-16)

**Advanced Optimization & Championship Options**:

- ✅ **Advanced Settings UI**: New "Scoring & Strategy" panel in Optimizer.
- ✅ **Championship Scoring Support**:
  - VCAC (Top 12): Places 1-12 scoring.
  - VISAA State (Top 16): Finals + Consolation scoring.
- ✅ **Adaptive Logic**:
  - Automatically disables "Robust Mode" in Championship Mode.
  - Dynamic file upload requirements (Psych Sheet for Championship vs Team Files for Dual).
- ✅ **Backend Integration**:
  - Updated API models to support `scoring_type` and `robust_mode`.
  - Logic wired through to Optimization Service.
- ✅ **Bug Fixes**:
  - Fixed `export.csv` sorting and place assignment.
  - Resolved build error in OptimizePage (unterminated regexp/comment issue).

---

## Development Setup

See `MAC_QUICKSTART.md` for setup instructions or run:

```bash
chmod +x setup_mac.sh start_dev.sh
./setup_mac.sh
./start_dev.sh
```

## Deprecated Files

The following Windows-era files are deprecated and will be removed in a future cleanup:

- `start_dev.bat` — use `start_dev.sh`
- `launch.bat` — use `run_server.py` directly
- `docker-quickstart.bat` — use `docker-compose` directly
- `run_e2e_check.bat` — use `test_e2e_full.sh`
- `TRANSFER_TO_MAC.md` — migration complete, retained for reference only
