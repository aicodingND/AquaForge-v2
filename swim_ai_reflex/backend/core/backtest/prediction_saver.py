"""Save optimizer outputs as prediction snapshots for future backtesting."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


def save_aqua_prediction(
    meet_id: str,
    meet_profile: str,
    best_lineup_df: pd.DataFrame,
    totals: dict[str, float],
    details: list[dict[str, Any]],
    output_dir: Path,
    quality_mode: str = "balanced",
    solve_time_ms: float = 0.0,
) -> Path:
    """Save AquaOptimizer output as a prediction snapshot JSON.

    Extracts assignments from best_lineup_df and saves to the canonical
    prediction format for later comparison against actual results.
    """
    # Build assignments dict: swimmer -> [events]
    assignments: dict[str, list[str]] = {}
    if best_lineup_df is not None and not best_lineup_df.empty:
        for _, row in best_lineup_df.iterrows():
            swimmer = str(row.get("swimmer", ""))
            event = str(row.get("event", ""))
            if swimmer and event:
                assignments.setdefault(swimmer, []).append(event)

    # Build event breakdown from details if available
    event_breakdown: dict[str, Any] = {}
    if details:
        for detail in details:
            if isinstance(detail, dict) and "event_breakdown" in detail:
                event_breakdown = detail["event_breakdown"]
                break

    snapshot = {
        "meet_id": meet_id,
        "optimizer": "aqua",
        "meet_profile": meet_profile,
        "timestamp": datetime.now().isoformat(),
        "solve_time_ms": solve_time_ms,
        "quality_mode": quality_mode,
        "assignments": assignments,
        "predicted_scores": {
            "seton": totals.get("seton", totals.get("seton_points", 0.0)),
            "opponent": totals.get("opponent", totals.get("opponent_points", 0.0)),
        },
        "event_breakdown": event_breakdown,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "optimizer_prediction_aqua.json"
    with open(output_path, "w") as f:
        json.dump(snapshot, f, indent=2, default=str)

    return output_path


def save_gurobi_prediction(
    meet_id: str,
    meet_profile: str,
    assignments: dict[str, list[str]],
    total_points: float,
    output_dir: Path,
    event_breakdown: dict[str, Any] | None = None,
    solve_time_ms: float = 0.0,
) -> Path:
    """Save Gurobi championship strategy output as a prediction snapshot JSON."""
    snapshot = {
        "meet_id": meet_id,
        "optimizer": "gurobi",
        "meet_profile": meet_profile,
        "timestamp": datetime.now().isoformat(),
        "solve_time_ms": solve_time_ms,
        "quality_mode": "",
        "assignments": assignments,
        "predicted_scores": {"seton": total_points},
        "event_breakdown": event_breakdown or {},
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "optimizer_prediction_gurobi.json"
    with open(output_path, "w") as f:
        json.dump(snapshot, f, indent=2, default=str)

    return output_path
