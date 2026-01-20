---
name: API Documentation
description: Generate and maintain API documentation from code
triggers:
  - document API
  - generate docs
  - update documentation
  - OpenAPI
---

# API Documentation Skill 📚

Use this skill to generate and maintain API documentation.

---

## Documentation Types

### 1. OpenAPI/Swagger (Auto-generated)

FastAPI automatically generates OpenAPI docs at:
- `/api/docs` - Swagger UI
- `/api/redoc` - ReDoc UI
- `/api/openapi.json` - Raw OpenAPI spec

### 2. Markdown Documentation

For human-readable docs in `/docs/` folder.

### 3. Code Docstrings

Inline documentation in Python source.

---

## Documentation Procedure

### Step 1: Ensure Proper Docstrings

Every endpoint should have:

```python
@router.post("/optimize", response_model=OptimizationResponse)
async def optimize_lineup(
    request: OptimizationRequest,
) -> OptimizationResponse:
    """
    Optimize swim meet lineup.
    
    This endpoint takes a roster of swimmers and returns the optimal
    lineup based on the specified meet type and constraints.
    
    Args:
        request: The optimization request containing roster and settings
        
    Returns:
        OptimizationResponse containing optimal lineup and projected score
        
    Raises:
        HTTPException(400): If roster is empty or invalid
        HTTPException(422): If validation fails
        
    Example:
        ```json
        {
            "roster": [...],
            "mode": "championship",
            "target_team": "SST"
        }
        ```
    """
```

### Step 2: Add Response Examples

Use Pydantic's `Field` with examples:

```python
class OptimizationResponse(BaseModel):
    """Response from optimization endpoint."""
    
    status: str = Field(
        ...,
        description="Status of the optimization",
        examples=["success", "partial", "failed"]
    )
    
    our_score: int = Field(
        ...,
        description="Projected score for our team",
        examples=[254]
    )
    
    events: list[EventResult] = Field(
        ...,
        description="Results per event"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "success",
                "our_score": 254,
                "events": [...]
            }
        }
    )
```

### Step 3: Generate Markdown Docs

Create `/docs/API_REFERENCE.md`:

```markdown
# AquaForge API Reference

## Base URL

- Development: `http://localhost:8001/api`
- Production: `https://[domain]/api`

## Authentication

Currently no authentication required.

## Endpoints

### POST /v1/optimize

Optimize swim meet lineup.

**Request Body**:
| Field       | Type   | Required | Description                |
| ----------- | ------ | -------- | -------------------------- |
| roster      | array  | Yes      | List of swimmers           |
| mode        | string | Yes      | "dual" or "championship"   |
| target_team | string | No       | Team code for championship |

**Response**:
| Field     | Type    | Description        |
| --------- | ------- | ------------------ |
| status    | string  | "success" or error |
| our_score | integer | Projected score    |
| events    | array   | Per-event results  |

**Example Request**:
```bash
curl -X POST http://localhost:8001/api/v1/optimize \
  -H "Content-Type: application/json" \
  -d '{"roster": [...], "mode": "dual"}'
```

**Example Response**:
```json
{
    "status": "success",
    "our_score": 187,
    "opponent_score": 128,
    "events": [...]
}
```
```

### Step 4: Keep in Sync

When API changes:
1. Update endpoint docstrings
2. Update Pydantic models with examples
3. Regenerate markdown if significant changes
4. Verify OpenAPI spec at `/api/openapi.json`

---

## AquaForge API Structure

### Current Endpoints

| Method | Path                              | Description               |
| ------ | --------------------------------- | ------------------------- |
| GET    | `/api/v1/health`                  | Health check              |
| POST   | `/api/v1/optimize`                | Run optimization          |
| POST   | `/api/v1/upload`                  | Upload psych sheet        |
| GET    | `/api/v1/roster`                  | Get current roster        |
| POST   | `/api/v2/dual-meet/optimize`      | Dual meet optimization    |
| POST   | `/api/v2/championship/optimize`   | Championship optimization |
| GET    | `/api/v2/championship/strategies` | List strategies           |

### Response Conventions

All responses follow this structure:

```python
class BaseResponse(BaseModel):
    status: Literal["success", "error"]
    message: str | None = None
    data: Any = None
    errors: list[str] | None = None
```

---

## Thunder Client Collection

API tests are in `.thunder/`:

```
.thunder/
├── aquaforge-api.http
├── collections/
│   ├── optimization.json
│   └── championship.json
```

---

## Quick Doc Generation

```python
# Generate OpenAPI JSON
import json
from swim_ai_reflex.backend.api.main import api_app

with open("docs/openapi.json", "w") as f:
    json.dump(api_app.openapi(), f, indent=2)
```

---

_Skill: api-docs | Version: 1.0_
