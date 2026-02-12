# Quick Start Guide for Mac

## First Time Setup

1. **Make scripts executable**:

   ```bash
   chmod +x setup_mac.sh start_dev.sh
   ```

2. **Run automated setup**:

   ```bash
   ./setup_mac.sh
   ```

   This will:
   - ✅ Install Homebrew (if needed)
   - ✅ Install Python 3.11
   - ✅ Install Node.js
   - ✅ Create Python virtual environment
   - ✅ Install all Python dependencies
   - ✅ Install all Node.js dependencies
   - ✅ Optionally install Expo CLI for mobile dev

3. **Start the application**:

   ```bash
   ./start_dev.sh
   ```

## Manual Setup (Alternative)

If you prefer manual control:

```bash
# 1. Install Homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. Install dependencies
brew install python@3.11 node

# 3. Setup Python
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 4. Setup Node.js
cd frontend && npm install && cd ..

# 5. Run servers
python run_server.py --mode api --port 8001 --reload &
cd frontend && npm run dev
```

## Access Points

- **Frontend**: <http://localhost:3000>
- **Backend API**: <http://localhost:8001>
- **API Docs**: <http://localhost:8001/api/docs>

## Troubleshooting

### Permission Denied

```bash
chmod +x setup_mac.sh start_dev.sh
```

### Python Version Issues

```bash
brew install python@3.11
python3.11 -m venv .venv
```

### Port Already in Use

```bash
# Kill process on port 8001
lsof -ti:8001 | xargs kill -9

# Kill process on port 3000
lsof -ti:3000 | xargs kill -9
```

For version history, see `VERSION_LOG.md`
