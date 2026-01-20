# AquaForge.ai - Version Log

## Transfer Record: v1.0.0-next

**Date**: 2026-01-10 20:12:31  
**Source**: `C:\Users\Michael\Desktop\AquaForgeFinal`  
**Destination**: `E:\AquaForge_v1.0.0-next_2026-01-10`  
**Transfer Method**: Robocopy (Windows)

---

## Transfer Statistics

- **Files Copied**: 281
- **Data Size**: 4.41 MB
- **Directories**: 39
- **Excluded**: node_modules, .venv, .next, **pycache**, .git, cache directories
- **Status**: ✅ Complete

---

## Version Information

### v1.0.0-next (2026-01-10)

**Major Changes**:

- ✅ Migrated from Reflex to Next.js + FastAPI architecture
- ✅ Reorganized project structure (archived legacy UI)
- ✅ Created comprehensive documentation (HANDOFF.md)
- ✅ Organized data files into `__DATA__/` directory
- ✅ Prepared for Mac/iOS development

**Tech Stack**:

- Frontend: Next.js 16, React 19, TypeScript, Tailwind v4
- Backend: FastAPI, Python 3.11+
- Optimization: Nash Equilibrium + Heuristic algorithms

**Key Files**:

- `HANDOFF.md` - Project overview and setup
- `TRANSFER_TO_MAC.md` - Mac-specific setup instructions
- `start_dev.bat` - Windows startup script (convert to .sh for Mac)
- `run_server.py` - Cross-platform server runner

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

## Next Steps on Mac

1. **Install Prerequisites**:

   - Python 3.11+ via Homebrew
   - Node.js 18+ via Homebrew
   - Xcode (for iOS development)

2. **Setup Backend**:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Setup Frontend**:

   ```bash
   cd frontend
   npm install
   ```

4. **Run Application**:

   - Backend: `python run_server.py --mode api --port 8001 --reload`
   - Frontend: `cd frontend && npm run dev`

5. **iOS Mobile Development**:
   - Install Expo CLI
   - Create mobile app in `mobile/` directory
   - Test with iOS Simulator

---

## File Integrity

All source code, documentation, and configuration files have been successfully transferred.

**Excluded (as expected)**:

- Build artifacts (`.next/`, `__pycache__/`)
- Dependencies (`node_modules/`, `.venv/`)
- Git history (`.git/` - excluded for size, use git clone on Mac if needed)
- Cache files (`.cache/`, `.web/`)

---

## Contact & Support

For questions about this transfer or setup on Mac, refer to:

- `HANDOFF.md` - Comprehensive project documentation
- `TRANSFER_TO_MAC.md` - Mac setup guide
- `__ARCHIVE_REFLEX_APP__/README.md` - Legacy code reference

---

**Transfer Complete** ✅  
**Ready for Mac Development** 🍎
