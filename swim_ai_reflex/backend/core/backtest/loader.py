"""Load actual meet results and optimizer predictions from JSON/CSV files."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

from swim_ai_reflex.backend.core.backtest.schemas import (
    ActualMeetResults,
    EventResult,
    EventResults,
    PredictionSnapshot,
)


def parse_time_to_seconds(time_val: str | float | int | None) -> float | None:
    """Convert a time value to seconds.

    Handles multiple formats for manual entry convenience:
    - Float/int: returned as-is (already seconds, e.g. 116.87)
    - "1:56.87" → 116.87
    - "25.03" → 25.03
    - None/empty/"DQ"/"NS" → None
    """
    if time_val is None:
        return None
    if isinstance(time_val, (int, float)):
        return float(time_val) if time_val > 0 else None

    time_str = str(time_val).strip()
    if not time_str or time_str.lower() in ("none", "nan", "dq", "ns", "dns", "scr"):
        return None

    # Match "M:SS.ss" format
    match = re.match(r"(\d+):(\d+\.?\d*)", time_str)
    if match:
        minutes = int(match.group(1))
        seconds = float(match.group(2))
        return minutes * 60 + seconds

    try:
        val = float(time_str)
        return val if val > 0 else None
    except ValueError:
        return None


def load_actual_results_json(path: Path) -> ActualMeetResults:
    """Load actual results from the canonical JSON schema.

    Schema expects:
    {
      "meet_id": "visaa_2026",
      "meet_profile": "visaa_state",
      "events": [
        {
          "event_name": "200 Free",
          "gender": "Boys",
          "results": [{"place": 1, "swimmer": "...", "team": "SST", "time": 116.87, ...}]
        }
      ]
    }
    """
    with open(path) as f:
        data = json.load(f)

    events = []
    for evt_data in data.get("events", []):
        results = []
        for r in evt_data.get("results", []):
            results.append(
                EventResult(
                    place=r["place"],
                    swimmer=r.get("swimmer", ""),
                    team=r["team"],
                    time=parse_time_to_seconds(r.get("time")),
                    points=r.get("points", 0.0),
                    seed_time=parse_time_to_seconds(r.get("seed_time")),
                    dq=r.get("dq", False),
                    exhibition=r.get("exhibition", False),
                )
            )
        events.append(
            EventResults(
                event_name=evt_data["event_name"],
                gender=evt_data["gender"],
                event_type=evt_data.get("event_type", "individual"),
                results=results,
            )
        )

    return ActualMeetResults(
        meet_id=data["meet_id"],
        meet_name=data.get("meet_name", ""),
        meet_date=data.get("meet_date", ""),
        meet_profile=data["meet_profile"],
        source=data.get("source", ""),
        transcribed_date=data.get("transcribed_date", ""),
        events=events,
        team_scores=data.get("team_scores", {}),
    )


def actual_results_to_scoring_df(
    results: ActualMeetResults,
    target_team: str = "SST",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Convert actual results to optimizer-compatible DataFrames.

    Returns (seton_df, opponent_df) with columns:
    swimmer, event, time, team, grade, place, points
    """
    seton_rows: list[dict] = []
    opponent_rows: list[dict] = []

    for evt in results.events:
        full_event = evt.full_event_name
        is_relay = "relay" in evt.event_name.lower()

        for r in evt.results:
            if r.dq or r.time is None:
                continue
            row = {
                "swimmer": r.swimmer,
                "event": full_event,
                "time": r.time,
                "team": r.team,
                "grade": 10,  # Default; enrich from roster if available
                "is_relay": is_relay,
                "place": r.place,
                "points": r.points,
            }
            if r.team.upper() == target_team.upper():
                seton_rows.append(row)
            else:
                opponent_rows.append(row)

    seton_df = pd.DataFrame(seton_rows) if seton_rows else pd.DataFrame()
    opponent_df = pd.DataFrame(opponent_rows) if opponent_rows else pd.DataFrame()

    return seton_df, opponent_df


def load_prediction_snapshot(path: Path) -> PredictionSnapshot:
    """Load a saved optimizer prediction from JSON."""
    with open(path) as f:
        data = json.load(f)
    return PredictionSnapshot(
        meet_id=data["meet_id"],
        optimizer=data["optimizer"],
        meet_profile=data["meet_profile"],
        timestamp=data.get("timestamp", ""),
        solve_time_ms=data.get("solve_time_ms", 0.0),
        quality_mode=data.get("quality_mode", ""),
        assignments=data.get("assignments", {}),
        predicted_scores=data.get("predicted_scores", {}),
        event_breakdown=data.get("event_breakdown", {}),
    )
