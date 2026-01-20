#!/bin/bash

# AquaForge.ai - Development Server Launcher (Mac)
# Starts both backend and frontend servers

set -e

echo "=========================================="
echo "  AquaForge Development Server"
echo "=========================================="
echo ""

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found. Run ./setup_mac.sh first."
    exit 1
fi

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Stopping servers..."
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

echo "🚀 Starting FastAPI backend on port 8001..."
source .venv/bin/activate
python run_server.py --mode api --port 8001 --reload &
BACKEND_PID=$!

# Wait for backend to start
sleep 3

echo "🌐 Starting Next.js frontend on port 3000..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "=========================================="
echo "  Both servers running:"
echo "    Backend API: http://localhost:8001"
echo "    Frontend:    http://localhost:3000"
echo "    API Docs:    http://localhost:8001/api/docs"
echo "=========================================="
echo ""
echo "Press Ctrl+C to stop both servers"
echo ""

# Wait for user interrupt
wait
