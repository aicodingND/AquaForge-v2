# Multi-stage build for AquaForge Reflex App
# Cache bust: 2025-12-30-v7-debug-sed
FROM python:3.11-slim AS builder

WORKDIR /app

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    git \
    pkg-config \
    libcairo2-dev \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js (required for Reflex frontend)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs

# Copy requirements first (better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set Gurobi WLS credentials from environment if available
ARG WLSACCESSID
ARG WLSSECRET
ARG LICENSEID
ENV WLSACCESSID=${WLSACCESSID}
ENV WLSSECRET=${WLSSECRET}
ENV LICENSEID=${LICENSEID}

# Initialize Reflex and BUILD FRONTEND at build time
# Use placeholder URL that we'll replace at runtime
RUN reflex init && \
    reflex export --frontend-only --no-zip

# Production stage
FROM python:3.11-slim

# Install runtime dependencies including Caddy
RUN apt-get update && apt-get install -y \
    libpq5 \
    libcairo2 \
    curl \
    unzip \
    procps \
    debian-keyring \
    debian-archive-keyring \
    apt-transport-https \
    && curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg \
    && curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list \
    && apt-get update \
    && apt-get install -y caddy \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 swimai && \
    mkdir -p /app/uploads /app/assets /app/.web && \
    chown -R swimai:swimai /app

WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code AND pre-built frontend
COPY --from=builder --chown=swimai:swimai /app /app

# Explicitly copy assets to guarantee existence
COPY --chown=swimai:swimai assets /app/assets

# Copy Caddyfile
COPY Caddyfile /etc/caddy/Caddyfile

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV REFLEX_ENV=prod
ENV PORT=3000

# Gurobi WLS environment (set at runtime via Railway/Render env vars)
ENV WLSACCESSID=""
ENV WLSSECRET=""
ENV LICENSEID=""

# Expose port (Railway typically uses 8080)
EXPOSE 8080

# Create startup script - now just patches URLs and starts services
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
echo "========================================"\n\
echo "Starting AquaForge..."\n\
echo "PORT: ${PORT:-8080}"\n\
echo "========================================"\n\
\n\
# Debug: List JS files\n\
echo "DEBUG: Listing JS files in build directory..."\n\
find /app/.web/build/client -name "*.js" 2>/dev/null | head -20\n\
\n\
# Patch API URL in frontend JavaScript if Railway domain is set\n\
if [ -n "$RAILWAY_PUBLIC_DOMAIN" ]; then\n\
    echo "Railway domain detected: $RAILWAY_PUBLIC_DOMAIN"\n\
    \n\
    # Debug: Show content before patching\n\
    echo "DEBUG: Checking for RAILWAY_DOMAIN_PLACEHOLDER before patch..."\n\
    grep -l "RAILWAY_DOMAIN_PLACEHOLDER" /app/.web/build/client/*.js /app/.web/build/client/assets/*.js 2>/dev/null || echo "No placeholder found in root JS files"\n\
    \n\
    echo "Patching frontend API URLs..."\n\
    # Replace placeholder with actual Railway domain\n\
    find /app/.web/build/client -name "*.js" -exec sed -i "s|RAILWAY_DOMAIN_PLACEHOLDER|$RAILWAY_PUBLIC_DOMAIN|g" {} \\;\n\
    \n\
    # Debug: Verify patching worked\n\
    echo "DEBUG: Checking for Railway domain after patch..."\n\
    grep -l "$RAILWAY_PUBLIC_DOMAIN" /app/.web/build/client/*.js /app/.web/build/client/assets/*.js 2>/dev/null | head -5 || echo "WARNING: Domain not found after patch"\n\
    \n\
    echo "URL patching complete"\n\
else\n\
    echo "WARNING: RAILWAY_PUBLIC_DOMAIN not set!"\n\
fi\n\
\n\
# Start Caddy\n\
echo "Starting Caddy on port ${PORT:-8080}..."\n\
caddy start --config /etc/caddy/Caddyfile 2>&1 &\n\
sleep 1\n\
\n\
# Verify Caddy is running\n\
if pgrep -x caddy > /dev/null; then\n\
    echo "Caddy started successfully"\n\
else\n\
    echo "ERROR: Caddy failed to start"\n\
    exit 1\n\
fi\n\
\n\
# Start Reflex Backend\n\
echo "Starting Reflex Backend on port 8000..."\n\
exec reflex run --env prod --backend-only --loglevel info\n\
' > /app/start.sh && chmod +x /app/start.sh

# Copy Caddyfile with read permissions for all users
RUN chmod 644 /etc/caddy/Caddyfile

# Switch to non-root user
USER swimai

# Start the application
CMD ["/bin/bash", "/app/start.sh"]



