"""
Championship Response Formatter

Formats championship optimization results for API responses.
Separates championship logic from dual meet logic.
"""

import logging
from typing import Any, Dict, List

from swim_ai_reflex.backend.api.models import OptimizationResponse, OptimizationResult
from swim_ai_reflex.backend.core.strategies.championship_strategy import (
    ChampionshipEntry,
    ChampionshipOptimizationResult,
)

logger = logging.getLogger(__name__)


def _generate_championship_analytics(
    entries: List[ChampionshipEntry],
    champ_result: ChampionshipOptimizationResult,
    standings_projection: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """
    Generate advanced analytics for championship results.

    Runs Monte Carlo simulation, fatigue analysis, and Nash equilibrium
    to provide comprehensive strategic insights.

    Returns:
        Dictionary with monte_carlo, fatigue_warnings, nash_insights, relay_tradeoffs
    """
    analytics = {}
    target_team = "SST"  # Default to Seton

    # Convert entries to dict format for analysis functions
    entries_dicts = [
        {
            "swimmer": e.swimmer_name,
            "team": e.team,
            "event": e.event,
            "time": e.seed_time,
        }
        for e in entries
    ]

    # Identify target team from entries
    teams = list(set(e.team for e in entries))
    if "SST" in teams:
        target_team = "SST"
    elif "Seton" in teams:
        target_team = "Seton"
    elif teams:
        target_team = teams[0]

    # 1. Monte Carlo Simulation
    try:
        from swim_ai_reflex.backend.services.championship.monte_carlo import (
            run_monte_carlo,
        )

        mc_result = run_monte_carlo(
            entries_dicts,
            target_team=target_team,
            num_simulations=5000,  # Faster for API response
        )
        analytics["monte_carlo"] = {
            "win_probability": mc_result.get("win_probability", 0),
            "expected_score": mc_result.get("expected_score", 0),
            "confidence_interval": mc_result.get("confidence_interval", [0, 0]),
            "risk_level": mc_result.get("risk_level", "unknown"),
            "simulations": mc_result.get("simulations", 0),
        }
        logger.info(
            f"Monte Carlo: {mc_result.get('win_probability', 0)}% win probability"
        )
    except Exception as e:
        logger.warning(f"Monte Carlo analysis failed: {e}")
        analytics["monte_carlo"] = None

    # 2. Fatigue Warnings
    try:
        from swim_ai_reflex.backend.services.championship.fatigue_model import (
            FatigueModel,
        )

        model = FatigueModel()
        fatigue_warnings = []

        # Group assignments by swimmer
        swimmer_events = {}
        for event, swimmers in champ_result.assignments.items():
            for swimmer in swimmers:
                if swimmer not in swimmer_events:
                    swimmer_events[swimmer] = []
                swimmer_events[swimmer].append(event)

        # Check each swimmer for fatigue risk
        for swimmer, events in swimmer_events.items():
            if len(events) >= 2:  # Only check multi-event swimmers
                report = model.get_fatigue_report(swimmer, events)
                if report.get("risk_assessment") in ["medium", "high"]:
                    fatigue_warnings.append(
                        {
                            "swimmer": swimmer,
                            "events": events,
                            "total_fatigue": report.get("total_fatigue_cost", 0),
                            "risk": report.get("risk_assessment", "unknown"),
                        }
                    )

        analytics["fatigue_warnings"] = fatigue_warnings if fatigue_warnings else None
        if fatigue_warnings:
            logger.info(f"Fatigue warnings: {len(fatigue_warnings)} swimmers at risk")
    except Exception as e:
        logger.warning(f"Fatigue analysis failed: {e}")
        analytics["fatigue_warnings"] = None

    # 3. Nash Equilibrium Insights
    try:
        from swim_ai_reflex.backend.services.championship.nash_equilibrium import (
            run_nash_equilibrium,
        )

        nash_result = run_nash_equilibrium(
            entries_dicts,
            target_team=target_team,
        )
        analytics["nash_insights"] = {
            "equilibrium_found": nash_result.get("equilibrium_found", False),
            "target_rank": nash_result.get("target_team_rank", 0),
            "target_points": nash_result.get("target_team_points", 0),
            "stability_score": nash_result.get("stability_score", 0),
            "insights": nash_result.get("insights", [])[:5],  # Top 5 insights
        }
        logger.info(
            f"Nash: Rank {nash_result.get('target_team_rank')}, Equilibrium={nash_result.get('equilibrium_found')}"
        )
    except Exception as e:
        logger.warning(f"Nash equilibrium analysis failed: {e}")
        analytics["nash_insights"] = None

    # 4. Relay Trade-offs (placeholder for now)
    # TODO: Wire up relay analysis when 400FR trade-off is needed
    analytics["relay_tradeoffs"] = None

    return analytics if any(v is not None for v in analytics.values()) else None


def format_championship_response(
    champ_result: ChampionshipOptimizationResult,
    entries: List[ChampionshipEntry],
    optimization_time_ms: float,
    standings_projection: Dict[str, Any] = None,
) -> OptimizationResponse:
    """
    Format championship optimization result into API response.

    Args:
        champ_result: Result from ChampionshipGurobiStrategy
        entries: Original entries list for time lookup
        optimization_time_ms: Time taken for optimization
        standings_projection: Optional full meet standings projection

    Returns:
        OptimizationResponse formatted for championship mode
    """
    # Build entry lookup for times
    entry_lookup = {}
    for entry in entries:
        key = (entry.swimmer_name, entry.event)
        entry_lookup[key] = entry

    # Build results list (event-by-event breakdown for target team)
    results: List[OptimizationResult] = []

    # Group assignments by event
    event_num = 1
    for event, swimmers in sorted(champ_result.assignments.items()):
        # Get times for each swimmer
        swimmer_times = []
        for swimmer in swimmers:
            key = (swimmer, event)
            if key in entry_lookup:
                swimmer_times.append(str(entry_lookup[key].seed_time))
            else:
                swimmer_times.append("NT")

        # Get event points
        event_points = champ_result.event_breakdown.get(event, 0)

        # For championship, points are per swimmer (not per place)
        # Distribute points evenly among swimmers (or use actual breakdown if available)
        points_per_swimmer = event_points / len(swimmers) if swimmers else 0
        seton_points = [points_per_swimmer] * len(swimmers)

        results.append(
            OptimizationResult(
                event=event,
                event_number=event_num,
                seton_swimmers=swimmers,
                opponent_swimmers=[],  # No opponent in championship mode
                seton_times=swimmer_times,
                opponent_times=[],
                seton_points=seton_points,
                opponent_points=[],
                projected_score={
                    "seton": float(champ_result.total_points),
                    "opponent": 0.0,  # No opponent
                },
            )
        )
        event_num += 1

    # Build warnings list
    warnings: List[str] = []
    if champ_result.status != "optimal":
        warnings.append(f"Optimization status: {champ_result.status}")

    # Add recommendations as warnings (so they show in UI)
    for rec in champ_result.recommendations:
        warnings.append(f"💡 {rec}")

    # Extract championship-specific data from standings projection
    championship_standings = None
    event_breakdowns = None
    swing_events = None

    if standings_projection:
        # Full team standings: [{rank, team, points}, ...]
        championship_standings = standings_projection.get("standings", [])

        # Event breakdowns by team
        event_breakdowns = standings_projection.get("event_projections", {})

        # Swing events (top opportunities)
        swing_events = standings_projection.get("swing_events", [])

        logger.info(
            f"Championship standings: {len(championship_standings)} teams projected"
        )

    # Generate advanced analytics
    analytics = _generate_championship_analytics(
        entries, champ_result, standings_projection
    )

    return OptimizationResponse(
        success=champ_result.status == "optimal",
        seton_score=float(champ_result.total_points),
        opponent_score=0.0,  # Championship mode has no opponent
        score_margin=float(champ_result.total_points),
        results=results,
        statistics={
            "method": "championship_gurobi",
            "iterations": 0,
            "baseline_points": float(champ_result.baseline_points),
            "improvement": float(champ_result.improvement),
            "solve_time_ms": float(champ_result.solve_time_ms),
        },
        warnings=warnings,
        optimization_time_ms=optimization_time_ms,
        # Championship-specific fields
        championship_standings=championship_standings,
        event_breakdowns=event_breakdowns,
        swing_events=swing_events,
        # Advanced analytics
        analytics=analytics,
    )


def build_championship_entries(
    seton_data: List[Dict[str, Any]],
    convert_time_fn,
) -> List[ChampionshipEntry]:
    """
    Convert request data to ChampionshipEntry format.

    Args:
        seton_data: List of swimmer-event dictionaries
        convert_time_fn: Function to convert time strings to seconds

    Returns:
        List of ChampionshipEntry objects
    """
    entries = []
    for row in seton_data:
        entries.append(
            ChampionshipEntry(
                swimmer_name=str(row.get("swimmer", "")),
                team=str(row.get("team", "Seton")),
                event=str(row.get("event", "")),
                seed_time=convert_time_fn(row.get("time", 9999)),
                gender=str(row.get("gender", "")),
                grade=str(row.get("grade", "")) if row.get("grade") else None,
            )
        )
    return entries
