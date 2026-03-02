# AquaForge — Next.js (static) + FastAPI + Caddy
# Single-service deployment for Railway

# ── Stage 1: Build Next.js frontend ──────────────────────────────────────────
FROM node:20-slim AS frontend-builder

WORKDIR /frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --prefer-offline

COPY frontend/ .

# Relative URL so the browser calls the same origin; Caddy proxies /api/* to FastAPI
ENV NEXT_PUBLIC_API_URL=/api/v1
ENV NODE_OPTIONS="--max-old-space-size=4096"

RUN npm run build
# Produces /frontend/out/ (static export)

# ── Stage 2: Production runtime ──────────────────────────────────────────────
FROM python:3.11-slim

# System deps + Caddy
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libcairo2 \
    curl \
    procps \
    debian-keyring \
    debian-archive-keyring \
    apt-transport-https \
    && curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
       | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg \
    && curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
       | tee /etc/apt/sources.list.d/caddy-stable.list \
    && apt-get update && apt-get install -y caddy \
    && rm -rf /var/lib/apt/lists/*

# Non-root user
RUN useradd -m -u 1000 swimai \
    && mkdir -p /app/uploads /app/frontend-build \
    && chown -R swimai:swimai /app

WORKDIR /app

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Application code
COPY --chown=swimai:swimai swim_ai_reflex/ ./swim_ai_reflex/
COPY --chown=swimai:swimai run_server.py .
COPY --chown=swimai:swimai assets/ ./assets/

# Pre-built frontend from Stage 1
COPY --from=frontend-builder --chown=swimai:swimai /frontend/out/ ./frontend-build/

# Caddy config + start script
COPY Caddyfile /etc/caddy/Caddyfile
RUN chmod 644 /etc/caddy/Caddyfile
COPY --chown=swimai:swimai start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Environment
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production
ENV CORS_ALLOW_ALL=false

# Gurobi WLS (optional — set via Railway env vars)
ENV WLSACCESSID=""
ENV WLSSECRET=""
ENV LICENSEID=""

EXPOSE 8080

USER swimai

CMD ["/bin/bash", "/app/start.sh"]
