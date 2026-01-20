# Railway Deployment Guide for AquaForge

## Architecture Overview

```
[User Browser] 
    ↓ HTTPS
[Railway Edge] 
    ↓ PORT 8080
[Caddy Reverse Proxy]
    ├── /health, /ping → Instant response (health checks)
    ├── /_event/* → WebSocket to Reflex Backend (localhost:8000)
    ├── /assets/* → Static files from .web/build/client/assets/
    └── /* → SPA from .web/build/client/index.html
    
[Reflex Backend (localhost:8000)]
    └── Python API + WebSocket state sync
```

## Critical Configuration Files

| File | Purpose |
|------|---------|
| `Caddyfile` | Reverse proxy configuration |
| `Dockerfile` | Multi-stage build + runtime URL patching |
| `rxconfig.py` | Reflex config with RAILWAY_DOMAIN_PLACEHOLDER |
| `railway.toml` | Health check path configuration |

## Common Issues & Solutions

### 1. "Buttons don't work" / WebSocket errors

**Cause:** Frontend has wrong API URL baked in  
**Solution:** The `RAILWAY_DOMAIN_PLACEHOLDER` in rxconfig.py gets sed-replaced at startup

### 2. "404 for assets"

**Cause:** Conflicting `/assets/*` handler in Caddyfile  
**Solution:** Only use specific file handlers, not wildcards that conflict with frontend

### 3. "Health check timeout"

**Cause:** Slow startup blocking health endpoint  
**Solution:** Caddy starts first, responds to /health immediately

### 4. "UI mangled"

**Cause:** CSS/JS not loading (see #2) or WebSocket failing (see #1)

## Deployment Checklist

- [ ] `.web` folder is in `.dockerignore` (forces fresh frontend build)
- [ ] `rxconfig.py` uses `RAILWAY_DOMAIN_PLACEHOLDER` as fallback
- [ ] `Dockerfile` sed-replaces placeholder at startup
- [ ] `Caddyfile` has NO `/assets/*` handler
- [ ] `railway.toml` has `healthcheckPath = "/health"`

## Environment Variables (Railway Dashboard)

| Variable | Value | Required |
|----------|-------|----------|
| `RAILWAY_PUBLIC_DOMAIN` | Auto-set by Railway | ✅ |
| `PORT` | Auto-set by Railway | ✅ |
| `WLSACCESSID` | Gurobi license | For optimization |
| `WLSSECRET` | Gurobi license | For optimization |
| `LICENSEID` | Gurobi license | For optimization |

## Making Changes

1. Test locally with `reflex run`
2. Commit and push to GitHub
3. Railway auto-deploys from GitHub
4. Check deployment logs for DEBUG output
5. Verify at <https://swim-ai-reflex-production.up.railway.app>
