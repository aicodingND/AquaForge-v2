"""
Data Router

Provides endpoints for team data management, file uploads, and data processing.
"""

import hashlib
import logging
import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from swim_ai_reflex.backend.api.models import (
    ErrorResponse,
    TeamDataRequest,
    TeamDataResponse,
    TeamType,
)

router = APIRouter()
logger = logging.getLogger(__name__)

# Upload directory
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post(
    "/data/upload",
    response_model=TeamDataResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def upload_team_file(
    file: UploadFile = File(...),
    team_type: str = Form(...),
    team_name: Optional[str] = Form(None),
):
    """
    Upload and process a team roster file.

    Supports Excel (.xlsx, .xls), CSV, and JSON files.

    Args:
        file: The roster file to upload
        team_type: Either 'seton' or 'opponent'
        team_name: Optional team name override

    Returns:
        Processing results with swimmer and entry counts
    """
    try:
        # Validate team type
        try:
            tt = TeamType(team_type.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid team_type: {team_type}. Must be 'seton' or 'opponent'",
            )

        # Validate file extension
        filename = file.filename or "unknown"
        ext = Path(filename).suffix.lower()
        allowed_extensions = [".xlsx", ".xls", ".csv", ".json"]

        if ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {ext}. Allowed: {allowed_extensions}",
            )

        # Read file content
        content = await file.read()
        file_hash = hashlib.sha256(content).hexdigest()[:16]

        # Save file temporarily
        temp_path = UPLOAD_DIR / f"{file_hash}_{filename}"
        with open(temp_path, "wb") as f:
            f.write(content)

        logger.info(f"Saved uploaded file: {temp_path}")

        # Process the file
        from swim_ai_reflex.backend.api.deps import get_data_service

        data_service = get_data_service()

        result = await data_service.load_roster_from_path(str(temp_path))

        if not result.get("success"):
            raise HTTPException(
                status_code=400, detail=result.get("error", "Failed to parse file")
            )

        entries = result.get("data", [])

        # Convert DataFrame to list of dicts if needed
        if hasattr(entries, "to_dict"):
            entries_list = entries.to_dict("records")
        else:
            entries_list = entries if isinstance(entries, list) else []

        # Extract unique swimmers and events
        swimmers = set()
        event_set = set()
        for entry in entries_list:
            swimmers.add(entry.get("swimmer", "Unknown"))
            event_set.add(entry.get("event", "Unknown"))

        # Clean up temp file
        try:
            os.remove(temp_path)
        except Exception:
            pass

        # Extract team metadata from championship files
        metadata = result.get("metadata", {})
        teams = metadata.get("teams", [])

        # For championship files, use meet name as team_name if not provided
        resolved_team_name = (
            team_name
            or metadata.get("meet_name")
            or result.get("team_name", tt.value.capitalize())
        )

        return TeamDataResponse(
            success=True,
            team_name=resolved_team_name,
            team_type=tt,
            swimmer_count=len(swimmers),
            entry_count=len(entries_list),
            events=list(event_set),
            data=entries_list,
            warnings=result.get("warnings", []),
            file_hash=file_hash,
            message=result.get("message"),
            teams=teams if teams else None,  # Include teams for championship files
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File upload failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"File processing failed: {str(e)}")


@router.post("/data/team", response_model=TeamDataResponse)
async def submit_team_data(request: TeamDataRequest):
    """
    Submit team data directly as JSON.

    Alternative to file upload for programmatic access.
    """
    try:
        entries = [dict(entry) for entry in request.entries]

        # Extract unique swimmers and events
        swimmers = set()
        events = set()
        for entry in entries:
            swimmers.add(entry.get("swimmer", "Unknown"))
            events.add(entry.get("event", "Unknown"))

        return TeamDataResponse(
            success=True,
            team_name=request.team_name,
            team_type=request.team_type,
            swimmer_count=len(swimmers),
            entry_count=len(entries),
            events=list(events),
            warnings=[],
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/data/events")
async def list_standard_events():
    """
    Get the list of standard swim meet events.
    """
    events = [
        {"number": 1, "name": "200 Medley Relay", "type": "relay"},
        {"number": 2, "name": "200 Freestyle", "type": "individual"},
        {"number": 3, "name": "200 IM", "type": "individual"},
        {"number": 4, "name": "50 Freestyle", "type": "individual"},
        {"number": 5, "name": "100 Butterfly", "type": "individual"},
        {"number": 6, "name": "100 Freestyle", "type": "individual"},
        {"number": 7, "name": "500 Freestyle", "type": "individual"},
        {"number": 8, "name": "200 Freestyle Relay", "type": "relay"},
        {"number": 9, "name": "100 Backstroke", "type": "individual"},
        {"number": 10, "name": "100 Breaststroke", "type": "individual"},
        {"number": 11, "name": "400 Freestyle Relay", "type": "relay"},
    ]
    return {"events": events, "total": len(events)}


@router.get("/data/templates/{template_type}")
async def get_data_template(template_type: str):
    """
    Get a data template for file uploads.

    Args:
        template_type: Either 'csv' or 'json'
    """
    if template_type == "csv":
        return {
            "content_type": "text/csv",
            "headers": ["swimmer", "event", "time", "seed_time", "age", "grade"],
            "example": "John Smith,50 Freestyle,23.45,23.50,16,Junior",
        }
    elif template_type == "json":
        return {
            "content_type": "application/json",
            "schema": {
                "team_name": "string",
                "entries": [
                    {
                        "swimmer": "string",
                        "event": "string",
                        "time": "string (MM:SS.ss or SS.ss)",
                        "seed_time": "string (optional)",
                        "age": "integer (optional)",
                        "grade": "string (optional)",
                    }
                ],
            },
        }
    else:
        raise HTTPException(
            status_code=400, detail="Template type must be 'csv' or 'json'"
        )


@router.delete("/data/clear")
async def clear_all_data():
    """
    Clear all uploaded data (for session reset).
    """
    # In a stateless API, this would clear any server-side cache
    # For now, just return success
    return {"success": True, "message": "Data cleared"}
