"""
Analytics Router

Provides endpoints for swim meet analytics and insights.
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
import logging


router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/analytics/compare")
async def compare_teams(
    seton_data: List[Dict[str, Any]],
    opponent_data: List[Dict[str, Any]]
):
    """
    Compare two teams across all events.
    
    Returns head-to-head analysis and event-by-event breakdown.
    """
    try:
        # Build comparison directly without relying on non-existent method
        seton_events = {}
        opponent_events = {}
        
        for entry in seton_data:
            event = entry.get("event", "Unknown")
            if event not in seton_events:
                seton_events[event] = []
            seton_events[event].append(entry)
        
        for entry in opponent_data:
            event = entry.get("event", "Unknown")
            if event not in opponent_events:
                opponent_events[event] = []
            opponent_events[event].append(entry)
        
        # Compare events
        event_analysis = []
        all_events = set(seton_events.keys()) | set(opponent_events.keys())
        
        for event in sorted(all_events):
            seton_entries = seton_events.get(event, [])
            opponent_entries = opponent_events.get(event, [])
            
            event_analysis.append({
                "event": event,
                "seton_count": len(seton_entries),
                "opponent_count": len(opponent_entries),
                "advantage": "seton" if len(seton_entries) > len(opponent_entries) else (
                    "opponent" if len(opponent_entries) > len(seton_entries) else "even"
                )
            })
        
        # Generate recommendations
        recommendations = []
        seton_strong_events = [e["event"] for e in event_analysis if e["advantage"] == "seton"]
        opponent_strong_events = [e["event"] for e in event_analysis if e["advantage"] == "opponent"]
        
        if seton_strong_events:
            recommendations.append(f"Seton has depth advantage in: {', '.join(seton_strong_events[:3])}")
        if opponent_strong_events:
            recommendations.append(f"Focus training on: {', '.join(opponent_strong_events[:3])}")
        
        return {
            "success": True,
            "comparison": {
                "seton_total_entries": len(seton_data),
                "opponent_total_entries": len(opponent_data),
                "seton_swimmers": len(set(e.get("swimmer") for e in seton_data)),
                "opponent_swimmers": len(set(e.get("swimmer") for e in opponent_data)),
            },
            "event_analysis": event_analysis,
            "recommendations": recommendations
        }
        
    except Exception as e:
        logger.error(f"Team comparison failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )


@router.post("/analytics/swimmer/{swimmer_name}")
async def analyze_swimmer(
    swimmer_name: str,
    team_data: List[Dict[str, Any]]
):
    """
    Get detailed analytics for a specific swimmer.
    """
    try:
        # Filter entries for this swimmer
        swimmer_entries = [
            entry for entry in team_data
            if entry.get("swimmer", "").lower() == swimmer_name.lower()
        ]
        
        if not swimmer_entries:
            raise HTTPException(
                status_code=404,
                detail=f"Swimmer '{swimmer_name}' not found"
            )
        
        events = []
        for entry in swimmer_entries:
            events.append({
                "event": entry.get("event"),
                "time": entry.get("time"),
                "seed_time": entry.get("seed_time"),
            })
        
        return {
            "swimmer": swimmer_name,
            "event_count": len(events),
            "events": events,
            "versatility_score": min(len(events) / 4.0, 1.0) * 100  # Simple metric
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analytics/event/{event_name}")
async def analyze_event(
    event_name: str,
    seton_data: List[Dict[str, Any]],
    opponent_data: List[Dict[str, Any]]
):
    """
    Get detailed analytics for a specific event.
    """
    try:
        # Normalize event name for matching
        event_lower = event_name.lower()
        
        seton_swimmers = []
        opponent_swimmers = []
        
        for entry in seton_data:
            if entry.get("event", "").lower() == event_lower:
                seton_swimmers.append({
                    "swimmer": entry.get("swimmer"),
                    "time": entry.get("time"),
                })
        
        for entry in opponent_data:
            if entry.get("event", "").lower() == event_lower:
                opponent_swimmers.append({
                    "swimmer": entry.get("swimmer"),
                    "time": entry.get("time"),
                })
        
        # Sort by time (simple string sort works for same-format times)
        seton_swimmers.sort(key=lambda x: x.get("time", "99:99.99"))
        opponent_swimmers.sort(key=lambda x: x.get("time", "99:99.99"))
        
        return {
            "event": event_name,
            "seton": {
                "swimmer_count": len(seton_swimmers),
                "swimmers": seton_swimmers[:5]  # Top 5
            },
            "opponent": {
                "swimmer_count": len(opponent_swimmers),
                "swimmers": opponent_swimmers[:5]  # Top 5
            },
            "depth_advantage": "seton" if len(seton_swimmers) > len(opponent_swimmers) else "opponent"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analytics/depth")
async def analyze_depth(team_data: List[Dict[str, Any]]):
    """
    Analyze team depth across all events.
    """
    try:
        event_counts = {}
        swimmer_events = {}
        
        for entry in team_data:
            event = entry.get("event", "Unknown")
            swimmer = entry.get("swimmer", "Unknown")
            
            event_counts[event] = event_counts.get(event, 0) + 1
            
            if swimmer not in swimmer_events:
                swimmer_events[swimmer] = []
            swimmer_events[swimmer].append(event)
        
        # Calculate metrics
        avg_depth = sum(event_counts.values()) / max(len(event_counts), 1)
        versatile_swimmers = [
            name for name, events in swimmer_events.items()
            if len(events) >= 3
        ]
        
        return {
            "event_depth": event_counts,
            "average_depth": round(avg_depth, 2),
            "total_swimmers": len(swimmer_events),
            "versatile_swimmers": versatile_swimmers,
            "versatile_count": len(versatile_swimmers)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/scoring")
async def get_scoring_rules():
    """
    Get the scoring rules used for meet calculations.
    """
    return {
        "individual_events": {
            "1st": 6,
            "2nd": 4,
            "3rd": 3,
            "4th": 2,
            "5th": 1,
            "6th": 0
        },
        "relay_events": {
            "1st": 8,
            "2nd": 4,
            "3rd": 0
        },
        "notes": [
            "Individual events allow up to 3 swimmers per team",
            "Relay events allow 1 team (4 swimmers) per relay",
            "Swimmers are limited to 4 individual events maximum",
            "Fatigue modeling reduces performance for consecutive events"
        ]
    }
