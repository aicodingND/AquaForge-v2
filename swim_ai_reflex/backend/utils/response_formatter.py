"""
Optimization Response Formatter

Handles the formatting of optimization results into the standard API response structure.
Centralizes logic for both Dual Meet and Championship response construction to keep routers clean.
"""

import logging
from typing import Any

import pandas as pd

from swim_ai_reflex.backend.api.models import OptimizationResponse, OptimizationResult

logger = logging.getLogger(__name__)


def format_dual_meet_response(
    result: dict[str, Any],
    seton_score: float,
    opponent_score: float,
    optimization_time_ms: float,
    method: str,
) -> OptimizationResponse:
    """
    Format a dual meet optimization result into the API response model.

    Args:
        result: Raw dictionary result from the optimization service
        seton_score: Total Seton score
        opponent_score: Total Opponent score
        optimization_time_ms: Execution time in milliseconds
        method: The optimization method used (e.g., 'heuristic', 'gurobi')

    Returns:
        OptimizationResponse object
    """

    warnings: list[str] = []

    if not result.get("success"):
        # Convert error to string for warnings list
        error = result.get("error", "Optimization did not complete successfully")
        if isinstance(error, dict):
            error = str(error.get("message", error))
        warnings.append(str(error))

    # Transform lineup data to response format
    results: list[OptimizationResult] = []

    # Extract data from the result dictionary
    data = result.get("data", {})
    lineup_data = data.get("best_lineup", [])
    opponent_lineup_data = data.get("opponent_lineup", [])
    details_data = data.get("details", [])

    if not opponent_lineup_data:
        logger.info("DEBUG: Opponent lineup data is EMPTY!")

    # Convert details to DataFrame for easier querying
    details_df = pd.DataFrame(details_data) if details_data else None

    # Build opponent lookup from Nash-derived lineup
    opponent_by_event = {}

    if opponent_lineup_data:
        opp_df = pd.DataFrame(opponent_lineup_data)
        if "event" in opp_df.columns:
            for event in opp_df["event"].unique():
                event_rows = opp_df[opp_df["event"] == event]
                opponent_by_event[event] = {
                    "swimmers": event_rows["swimmer"].tolist()
                    if "swimmer" in event_rows.columns
                    else [],
                    "times": [str(t) for t in event_rows["time"].tolist()]
                    if "time" in event_rows.columns
                    else [],
                }

    if lineup_data:
        lineup_df = pd.DataFrame(lineup_data)

        # Group by event
        if "event" in lineup_df.columns:
            # Process each event
            for event in lineup_df["event"].unique():
                event_rows = lineup_df[lineup_df["event"] == event]
                seton_rows = (
                    event_rows[event_rows["team"] == "seton"]
                    if "team" in event_rows.columns
                    else pd.DataFrame()
                )

                # Get opponent swimmers for this event
                opp_data = opponent_by_event.get(event, {"swimmers": [], "times": []})

                # Get detailed scoring data
                seton_points = []
                opponent_points = []

                if (
                    details_df is not None
                    and not details_df.empty
                    and "points" in details_df.columns
                ):
                    # Filter for this event
                    evt_details = details_df[details_df["event"] == event]

                    if evt_details.empty:
                        logger.warning(f"No scoring details found for event '{event}'.")
                        seton_points = [0.0] * len(seton_rows)
                        opponent_points = [0.0] * len(opp_data["swimmers"])
                    else:
                        # Normalize columns for matching
                        # We use a copy to avoid SettingWithCopyWarning
                        evt_details = evt_details.copy()
                        evt_details["swimmer_match"] = (
                            evt_details["swimmer"].astype(str).str.lower().str.strip()
                        )
                        evt_details["team_match"] = (
                            evt_details["team"].astype(str).str.lower().str.strip()
                        )

                        # Match Seton points
                        # Improved logic: Try to match by (swimmer + team) first
                        for swimmer in (
                            seton_rows["swimmer"].tolist()
                            if "swimmer" in seton_rows.columns
                            else []
                        ):
                            swimmer_norm = str(swimmer).lower().strip()

                            # Filter for swimmer name match
                            name_matches = evt_details[
                                evt_details["swimmer_match"] == swimmer_norm
                            ]

                            # Try binding to 'seton' team
                            team_matches = name_matches[
                                name_matches["team_match"].str.contains("seton")
                            ]

                            if not team_matches.empty:
                                seton_points.append(
                                    float(team_matches.iloc[0]["points"])
                                )
                            elif not name_matches.empty:
                                # Fallback: if only one person has this name, use it
                                if len(name_matches) == 1:
                                    seton_points.append(
                                        float(name_matches.iloc[0]["points"])
                                    )
                                else:
                                    # Ambiguous name match
                                    logger.warning(
                                        f"Ambiguous score match for Seton swimmer {swimmer} in {event}"
                                    )
                                    seton_points.append(0.0)
                            else:
                                logger.warning(
                                    f"No score match for Seton swimmer {swimmer} in {event}"
                                )
                                seton_points.append(0.0)

                        # Match Opponent points
                        for swimmer in opp_data["swimmers"]:
                            swimmer_norm = str(swimmer).lower().strip()

                            # Opponent logic: Match name AND (NOT seton)
                            name_matches = evt_details[
                                evt_details["swimmer_match"] == swimmer_norm
                            ]

                            # Filter out Seton
                            opp_matches = name_matches[
                                ~name_matches["team_match"].str.contains("seton")
                            ]

                            if not opp_matches.empty:
                                opponent_points.append(
                                    float(opp_matches.iloc[0]["points"])
                                )
                            elif not name_matches.empty:
                                # Fallback if name found but team distinct check failed (e.g. slight team name mismatch)
                                if len(name_matches) == 1:
                                    opponent_points.append(
                                        float(name_matches.iloc[0]["points"])
                                    )
                                else:
                                    opponent_points.append(0.0)
                            else:
                                opponent_points.append(0.0)
                else:
                    # No details dataframe available
                    seton_points = [0.0] * len(seton_rows)
                    opponent_points = [0.0] * len(opp_data["swimmers"])

                # Determine event number safely
                event_num = 0
                if "event_num" in event_rows.columns and len(event_rows) > 0:
                    try:
                        event_num = int(event_rows["event_num"].iloc[0])
                    except (ValueError, TypeError):
                        pass

                results.append(
                    OptimizationResult(
                        event=str(event),
                        event_number=event_num,
                        seton_swimmers=seton_rows["swimmer"].tolist()
                        if "swimmer" in seton_rows.columns
                        else [],
                        opponent_swimmers=opp_data["swimmers"],
                        seton_times=[str(t) for t in seton_rows["time"].tolist()]
                        if "time" in seton_rows.columns
                        else [],
                        opponent_times=opp_data["times"],
                        seton_points=seton_points,
                        opponent_points=opponent_points,
                        projected_score={
                            "seton": float(sum(seton_points)),
                            "opponent": float(sum(opponent_points)),
                        },
                    )
                )

    # Extract sensitivity and relay data from optimizer details
    sensitivity = None
    relay_assignments = None
    if data:
        # Sensitivity and relay_assignments may be in the top-level data dict or nested in details
        raw_details = data.get("details", [])
        if isinstance(raw_details, list):
            for d in raw_details:
                if isinstance(d, dict):
                    if "sensitivity" in d and sensitivity is None:
                        sensitivity = d["sensitivity"]
                    if "relay_assignments" in d and relay_assignments is None:
                        relay_assignments = d["relay_assignments"]

    # Build statistics dict with championship factor metadata
    stats: dict[str, Any] = {
        "method": method,
        "iterations": data.get("iterations", 0) if data else 0,
    }
    if isinstance(raw_details, list):
        for d in raw_details:
            if isinstance(d, dict):
                if d.get("championship_factors_applied"):
                    stats["championship_factors_applied"] = True
                    stats["championship_factors"] = d.get("championship_factors")

    return OptimizationResponse(
        success=result.get("success", False),
        seton_score=float(seton_score),
        opponent_score=float(opponent_score),
        score_margin=float(seton_score) - float(opponent_score),
        results=results,
        statistics=stats,
        warnings=warnings,
        optimization_time_ms=optimization_time_ms,
        sensitivity=sensitivity,
        relay_assignments=relay_assignments,
    )
