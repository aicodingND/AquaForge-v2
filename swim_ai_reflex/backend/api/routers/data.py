"""
Data Router

Provides endpoints for team data management, file uploads, and data processing.
"""

import hashlib
import logging
import os
from pathlib import Path

from fastapi import APIRouter, File, Form, UploadFile

from swim_ai_reflex.backend.api.exceptions import (
    DataProcessingError,
    FileUploadError,
    ValidationError,
)
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
    team_name: str | None = Form(None),
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
            raise ValidationError(
                f"Invalid team_type: {team_type}",
                details={"allowed_values": ["seton", "opponent"]},
            )

        # Validate file extension
        filename = file.filename or "unknown"
        ext = Path(filename).suffix.lower()
        allowed_extensions = [".xlsx", ".xls", ".csv", ".json"]

        if ext not in allowed_extensions:
            raise FileUploadError(
                f"Unsupported file type: {ext}",
                details={"allowed_extensions": allowed_extensions},
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
            raise FileUploadError(
                result.get("error", "Failed to parse file"),
                details={"filename": file.filename},
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

    except (ValidationError, FileUploadError):
        raise
    except Exception as e:
        logger.error(f"File upload failed: {str(e)}", exc_info=True)
        raise FileUploadError(f"File processing failed: {str(e)}")


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
        raise ValidationError(str(e))


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
        raise ValidationError(
            f"Invalid template_type: {template_type}",
            details={"allowed_values": ["csv", "json"]},
        )


@router.delete("/data/clear")
async def clear_all_data():
    """
    Clear all uploaded data (for session reset).
    """
    # In a stateless API, this would clear any server-side cache
    # For now, just return success
    return {"success": True, "message": "Data cleared"}


# Pre-aggregated data source mappings
# Separated by type: championship (full psych sheets) vs dual/team (single team rosters)
DATA_SOURCES = {
    # Championship mode sources (all teams in one file)
    "vcac_2026": {
        "path": "data/vcac/VCAC_2026_unified_psych_sheet.json",
        "name": "VCAC Championship 2026",
        "description": "Full psych sheet with all 7 VCAC teams",
        "type": "championship",
        "teams": 7,
    },
    "vcac_2026_projection": {
        "path": "data/championship_data/vcac_2026_psych_sheet_projection.json",
        "name": "VCAC 2026 Projection",
        "description": "Projected championship results",
        "type": "championship",
        "teams": 7,
    },
    # Dual mode sources - Seton team data
    "seton_2026": {
        "path": "data/championship_data/seton_2026_season_data.json",
        "name": "Seton 2026 Season",
        "description": "Complete Seton roster with best times",
        "type": "dual",
        "for_team": "seton",
    },
    # Dual mode sources - Opponent teams (extracted from VCAC psych sheet)
    # Trinity Christian
    "tcs_boys_2026": {
        "path": "data/vcac/VCAC_2026_unified_psych_sheet.json",
        "name": "TCS - Boys",
        "description": "Trinity Christian Boys Roster",
        "type": "team",
        "for_team": "opponent",
        "filter_team": "TCS",
        "filter_gender": "M",
    },
    "tcs_girls_2026": {
        "path": "data/vcac/VCAC_2026_unified_psych_sheet.json",
        "name": "TCS - Girls",
        "description": "Trinity Christian Girls Roster",
        "type": "team",
        "for_team": "opponent",
        "filter_team": "TCS",
        "filter_gender": "F",
    },
    # Immanuel Christian
    "ics_boys_2026": {
        "path": "data/vcac/VCAC_2026_unified_psych_sheet.json",
        "name": "ICS - Boys",
        "description": "Immanuel Christian Boys Roster",
        "type": "team",
        "for_team": "opponent",
        "filter_team": "ICS",
        "filter_gender": "M",
    },
    "ics_girls_2026": {
        "path": "data/vcac/VCAC_2026_unified_psych_sheet.json",
        "name": "ICS - Girls",
        "description": "Immanuel Christian Girls Roster",
        "type": "team",
        "for_team": "opponent",
        "filter_team": "ICS",
        "filter_gender": "F",
    },
    # Fredericksburg Christian
    "fcs_boys_2026": {
        "path": "data/vcac/VCAC_2026_unified_psych_sheet.json",
        "name": "FCS - Boys",
        "description": "Fredericksburg Christian Boys Roster",
        "type": "team",
        "for_team": "opponent",
        "filter_team": "FCS",
        "filter_gender": "M",
    },
    "fcs_girls_2026": {
        "path": "data/vcac/VCAC_2026_unified_psych_sheet.json",
        "name": "FCS - Girls",
        "description": "Fredericksburg Christian Girls Roster",
        "type": "team",
        "for_team": "opponent",
        "filter_team": "FCS",
        "filter_gender": "F",
    },
    # Oakcrest (Girls only)
    "oak_girls_2026": {
        "path": "data/vcac/VCAC_2026_unified_psych_sheet.json",
        "name": "OAK - Girls",
        "description": "Oakcrest Girls Roster",
        "type": "team",
        "for_team": "opponent",
        "filter_team": "OAK",
        "filter_gender": "F",
    },
    # Don Juan of Austria
    "djo_boys_2026": {
        "path": "data/vcac/VCAC_2026_unified_psych_sheet.json",
        "name": "DJO - Boys",
        "description": "Don Juan of Austria Boys Roster",
        "type": "team",
        "for_team": "opponent",
        "filter_team": "DJO",
        "filter_gender": "M",
    },
    "djo_girls_2026": {
        "path": "data/vcac/VCAC_2026_unified_psych_sheet.json",
        "name": "DJO - Girls",
        "description": "Don Juan of Austria Girls Roster",
        "type": "team",
        "for_team": "opponent",
        "filter_team": "DJO",
        "filter_gender": "F",
    },
    # Bishop Ireton
    "bi_boys_2026": {
        "path": "data/vcac/VCAC_2026_unified_psych_sheet.json",
        "name": "BI - Boys",
        "description": "Bishop Ireton Boys Roster",
        "type": "team",
        "for_team": "opponent",
        "filter_team": "BI",
        "filter_gender": "M",
    },
    "bi_girls_2026": {
        "path": "data/vcac/VCAC_2026_unified_psych_sheet.json",
        "name": "BI - Girls",
        "description": "Bishop Ireton Girls Roster",
        "type": "team",
        "for_team": "opponent",
        "filter_team": "BI",
        "filter_gender": "F",
    },
}


@router.get("/data/sources")
async def list_data_sources(mode: str | None = None, team_type: str | None = None):
    """
    List available pre-aggregated data sources.

    Args:
        mode: Filter by 'championship' or 'dual'
        team_type: Filter by 'seton' or 'opponent' for dual mode
    """
    sources = []
    for source_id, info in DATA_SOURCES.items():
        # Filter by mode if specified
        if mode:
            if mode == "championship" and info["type"] != "championship":
                continue
            if mode == "dual" and info["type"] not in ("dual", "team"):
                continue

        # Filter by team_type if specified
        if team_type and info.get("for_team"):
            if team_type != info["for_team"]:
                continue

        source_path = Path(info["path"])
        exists = source_path.exists()

        sources.append(
            {
                "id": source_id,
                "name": info["name"],
                "description": info.get("description", ""),
                "type": info["type"],
                "teams": info.get("teams"),
                "for_team": info.get("for_team"),
                "available": exists,
            }
        )
    return {"sources": sources}


@router.get("/data/load-source")
async def load_data_source(source: str):
    """
    Load a pre-aggregated data source by ID.

    Args:
        source: Data source ID (e.g., 'vcac_2026', 'seton_2026')

    Returns:
        Processed data ready for the frontend
    """
    import json

    if source not in DATA_SOURCES:
        raise ValidationError(
            f"Unknown source: {source}",
            details={"available_sources": list(DATA_SOURCES.keys())},
        )

    source_info = DATA_SOURCES[source]
    source_path = Path(source_info["path"])

    if not source_path.exists():
        raise DataProcessingError(
            f"Data file not found: {source_info['path']}",
            details={"source": source, "path": str(source_path)},
        )

    try:
        with open(source_path, encoding="utf-8") as f:
            data = json.load(f)

        # Handle championship psych sheet format
        if "entries" in data:
            entries = data["entries"]
            teams = data.get("teams", [])

            # Normalize entries
            normalized = []
            swimmers = set()
            events = set()

            for entry in entries:
                swimmer = entry.get("swimmer_name") or entry.get("swimmer", "Unknown")
                event = entry.get("event", "Unknown")
                time = entry.get("seed_time") or entry.get("time", 0)
                team = entry.get("team_code") or entry.get("team", "Unknown")

                # Filter by team if specified in source config
                if source_info.get("filter_team"):
                    if team != source_info["filter_team"]:
                        continue

                # Filter by gender if specified in source config
                if source_info.get("filter_gender"):
                    entry_gender = entry.get("gender", "U")
                    if entry_gender != source_info["filter_gender"]:
                        continue

                normalized.append(
                    {
                        "swimmer": swimmer,
                        "event": event,
                        "time": str(time),
                        "team": team,
                        "team_name": entry.get("team_name", ""),
                        "grade": entry.get("grade"),
                        "gender": entry.get("gender"),
                    }
                )
                swimmers.add(swimmer)
                events.add(event)

            return {
                "success": True,
                "team_name": source_info.get("name")
                if source_info.get("filter_team")
                else (data.get("meet") or source_info["name"]),
                "data": normalized,
                "swimmer_count": len(swimmers),
                "entry_count": len(normalized),
                "events": list(events),
                "teams": [source_info["filter_team"]]
                if source_info.get("filter_team")
                else teams,
                "source_type": source_info["type"],
            }
        else:
            # Handle simple roster format
            entries = data if isinstance(data, list) else []
            swimmers = set(e.get("swimmer", "Unknown") for e in entries)
            events = set(e.get("event", "Unknown") for e in entries)

            return {
                "success": True,
                "team_name": source_info["name"],
                "data": entries,
                "swimmer_count": len(swimmers),
                "entry_count": len(entries),
                "events": list(events),
                "teams": [],
                "source_type": source_info["type"],
            }

    except json.JSONDecodeError as e:
        raise DataProcessingError(
            f"Invalid JSON in data file: {str(e)}",
            details={"source": source, "path": str(source_path)},
        )
    except (ValidationError, DataProcessingError):
        raise
    except Exception as e:
        logger.error(f"Failed to load source {source}: {str(e)}")
        raise DataProcessingError(
            f"Failed to load data source: {str(e)}", details={"source": source}
        )
