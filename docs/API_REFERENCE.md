# AquaForge API Reference

> **Base URL**: `http://localhost:8001/api`

## Overview

AquaForge provides a comprehensive REST API for swim meet optimization. The API is organized into versioned endpoints:

- **v1**: Core functionality (upload, optimize, export)
- **v2**: Advanced features (championship mode, dual meet mode)

---

## Authentication

Currently no authentication required for local development.

---

## Health Check Endpoints

### GET /v1/health
Basic health check.

### GET /v1/ready  
Kubernetes readiness probe.

### GET /v1/live
Kubernetes liveness probe.

---

## Data Management

### POST /v1/data/upload
Upload a psych sheet or roster file.

**Request**: `multipart/form-data`
| Field | Type | Description |
|-------|------|-------------|
| file | File | Excel/CSV file |
| team_type | string | "seton" or "opponent" |

**Response**:
```json
{
  "success": true,
  "team_name": "Seton School",
  "swimmer_count": 15,
  "entry_count": 42,
  "events": ["50 Free", "100 Back", ...]
}
```

### POST /v1/data/team
Set team data directly via JSON.

### GET /v1/data/events
List available events.

### GET /v1/data/templates/{template_type}
Get sample data template.

### DELETE /v1/data/clear
Clear all uploaded data.

---

## Optimization

### POST /v1/optimize
Run lineup optimization.

**Request**:
```json
{
  "mode": "dual",
  "strategy_id": "balanced_dual",
  "coach_locks": [
    {"swimmer": "John Smith", "events": ["50 Free"]}
  ]
}
```

**Response**:
```json
{
  "status": "success",
  "our_score": 187,
  "opponent_score": 128,
  "margin": 59,
  "events": [
    {
      "name": "50 Free",
      "our_entries": [...],
      "our_points": 9,
      "opponent_points": 4
    }
  ]
}
```

### POST /v1/optimize/preview
Preview optimization without saving.

### GET /v1/optimize/backends
List available optimizer backends (AquaOptimizer, Gurobi, etc.)

---

## Export

### POST /v1/export
Generate export file (PDF, CSV, Excel).

**Request**:
```json
{
  "format": "pdf",
  "include_analysis": true
}
```

### GET /v1/export/download/{filename}
Download generated export file.

### GET /v1/export/formats
List supported export formats.

---

## Analytics

### POST /v1/analytics/compare
Compare two teams head-to-head.

### POST /v1/analytics/swimmer/{swimmer_name}
Get detailed swimmer analysis.

### POST /v1/analytics/event/{event_name}
Get event-specific analysis.

### POST /v1/analytics/depth
Team depth chart analysis.

### GET /v1/analytics/scoring
Get scoring rules for current meet type.

---

## Dual Meet Mode (v2)

### POST /v2/dual-meet/optimize
Optimize for dual meet format.

### POST /v2/dual-meet/validate
Validate a proposed lineup.

### GET /v2/dual-meet/scoring-info
Get dual meet scoring rules.

---

## Championship Mode (v2)

### POST /v2/championship/project
Project team standings from psych sheet.

### POST /v2/championship/optimize
Optimize for championship meet format.

**Request**:
```json
{
  "target_team": "Seton Swimming",
  "meet_profile": "vcac_championship",
  "strategy_id": "maximize_margin"
}
```

### POST /v2/championship/upload-psych-sheet
Upload championship psych sheet.

### GET /v2/championship/meet-profiles
List available meet profiles (VCAC, VISAA, etc.)

### GET /v2/championship/scoring-info/{profile}
Get scoring details for a meet profile.

### GET /v2/championship/strategies
List available optimization strategies.

**Response**:
```json
{
  "strategies": [
    {
      "id": "maximize_margin",
      "name": "Maximize Margin",
      "description": "Maximize point margin over nearest competitor",
      "implemented": true
    },
    {
      "id": "risk_averse",
      "name": "Risk Averse",
      "description": "Conservative lineup for consistent results",
      "implemented": true
    }
  ]
}
```

---

## Error Handling

All errors follow this format:

```json
{
  "status": "error",
  "message": "Description of what went wrong",
  "errors": ["Specific error 1", "Specific error 2"]
}
```

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad Request (validation error) |
| 404 | Not Found |
| 422 | Unprocessable Entity |
| 500 | Internal Server Error |

---

## Rate Limits

No rate limits for local development. Production may implement limits.

---

*Generated: 2026-01-20*
