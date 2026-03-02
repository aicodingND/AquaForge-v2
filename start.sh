#!/bin/bash
set -e

echo "========================================"
echo "Starting AquaForge"
echo "PORT: ${PORT:-8080}"
echo "========================================"

# Start Caddy (background)
echo "Starting Caddy on port ${PORT:-8080}..."
caddy start --config /etc/caddy/Caddyfile 2>&1 &
sleep 1

if pgrep -x caddy > /dev/null; then
    echo "Caddy started"
else
    echo "ERROR: Caddy failed to start"
    exit 1
fi

# Start FastAPI (foreground — Railway tracks this PID)
echo "Starting FastAPI on port 8001..."
exec python -m uvicorn swim_ai_reflex.backend.api.main:api_app \
    --host 0.0.0.0 \
    --port 8001 \
    --log-level info
