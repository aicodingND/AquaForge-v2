# AquaForge.ai - Transfer Package

> **DEPRECATED** (2026-02-11): This document is retained for historical reference only.
> The Windows-to-Mac migration is complete. macOS is the canonical platform.
> For current setup instructions, see `MAC_QUICKSTART.md`.

**Transfer Date**: 2026-01-10
**Source**: Windows Development Environment
**Destination**: Mac Development Environment (now canonical)
**Version**: v1.0.0-next (Post-Reflex Migration)

---

## 📦 Package Contents

This is a complete snapshot of the AquaForge.ai project after the Next.js migration and reorganization.

### What's Included

- ✅ **Next.js Frontend** (`frontend/`)
- ✅ **FastAPI Backend** (`swim_ai_reflex/backend/`)
- ✅ **Tests** (`tests/`, `swim_ai_reflex/tests/`)
- ✅ **Documentation** (`docs/`, `HANDOFF.md`)
- ✅ **Archived Reflex UI** (`__ARCHIVE_REFLEX_APP__/`)
- ✅ **Sample Data** (`__DATA__/`)
- ✅ **Configuration Files** (`.env.example`, `requirements.txt`, etc.)

### What's NOT Included

- ❌ `node_modules/` (reinstall with `npm install`)
- ❌ `.venv/` (recreate with `python -m venv .venv`)
- ❌ `.next/` build cache
- ❌ `__pycache__/` Python cache
- ❌ `.web/` Reflex cache (legacy)

---

## 🚀 Setup on Mac

### 1. Prerequisites

```bash
# Install Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python 3.11+
brew install python@3.11

# Install Node.js 18+
brew install node
```

### 2. Backend Setup

```bash
cd AquaForgeFinal

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Frontend Setup

```bash
cd frontend
npm install
cd ..
```

### 4. Run the Application

```bash
# Option 1: Use the startup script (may need adjustment for Mac)
./start_dev.bat  # Convert to .sh if needed

# Option 2: Manual start
# Terminal 1 - Backend
source .venv/bin/activate
python run_server.py --mode api --port 8001 --reload

# Terminal 2 - Frontend
cd frontend
npm run dev
```

---

## 🔧 Mac-Specific Adjustments Needed

### Convert Batch Scripts to Shell Scripts

The `.bat` files are Windows-specific. You'll need to create `.sh` equivalents:

**`start_dev.sh`** (example):

```bash
#!/bin/bash

echo "Starting AquaForge Development Servers..."

# Start backend
source .venv/bin/activate
python run_server.py --mode api --port 8001 --reload &
BACKEND_PID=$!

# Wait for backend
sleep 3

# Start frontend
cd frontend
npm run dev &
FRONTEND_PID=$!

echo "Backend PID: $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"
echo "Press Ctrl+C to stop both servers"

# Wait for user interrupt
wait
```

### Environment Variables

Check `.env` file and adjust paths if needed (Windows paths → Unix paths).

---

## 📱 Mobile Development (iOS)

Once on Mac, you can proceed with the iOS mobile app development:

1. Install Xcode from App Store
2. Install Expo CLI: `npm install -g expo-cli`
3. Create mobile app in `mobile/` directory
4. Use iOS Simulator for testing

---

## 🔄 Version History

- **v1.0.0-next** (2026-01-10): Post-Reflex migration, Next.js + FastAPI stack
- **v0.9.0** (2026-01-08): Reflex-based application (archived)

---

## 📞 Notes

- All Python backend code is platform-independent
- Frontend (Next.js) is platform-independent
- Only startup scripts need conversion (.bat → .sh)
- Database/data files are compatible across platforms

---

**Ready for Mac Development!** 🍎
