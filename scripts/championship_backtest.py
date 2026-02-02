#!/usr/bin/env python3
"""
Championship Mode Backtest Script.

Uses the existing ChampionshipPipeline to run backtests on championship meets
and compare predicted standings against actual recorded results.
"""

import os
import sys
import time
from typing import Any

import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import datetime

from swim_ai_reflex.backend.pipelines.championship import (
    ChampionshipInput,
    create_championship_pipeline,
)
from swim_ai_reflex.backend.services.championship.projection import (
    PointProjectionService,
)
from swim_ai_reflex.backend.services.championship.reporting import PremiumReporter
from swim_ai_reflex.backend.services.constraint_validator import (
    normalize_event_name,
    validate_lineup,
)
from swim_ai_reflex.backend.utils.mdb_connector import MDBConnector

# Use local MDB file (was external drive)
DB_PATH = "data/real_exports/SSTdata.mdb"
SETON_TEAM_ID = 1

# Import validation tools

# Stroke mapping from Hy-Tek codes
STROKE_MAP = {
    1: "Free",
    2: "Back",
    3: "Breast",
    4: "Fly",
    5: "IM",
}

# Comprehensive list of championship meets (2024-2026)
CHAMPIONSHIP_MEETS = [
    # =====================
    # 2024 SEASON (10 meets)
    # =====================
    (464, "National Catholic H.S. Championship 2024", "visaa_championship"),
    (465, "2024 VISAA Swimming & Diving Championship", "visaa_championship"),
    (470, "Seton Winter Invitational", "vcac_championship"),
    (471, "2024 NoVa Catholic Invitational Championship", "vcac_championship"),
    (476, "18th Annual VISAA Division II Invitational", "visaa_championship"),
    (478, "VCAC Regular Season Championship", "vcac_championship"),
    (479, "2024 VCAC Championship Meet", "vcac_championship"),
    (482, "17th Annual VISAA Junior Varsity Invitational", "visaa_championship"),
    (485, "Seton Icebreaker Invitational", "vcac_championship"),
    # =====================
    # 2025 SEASON (11 meets)
    # =====================
    (488, "VCAC Invitational", "vcac_championship"),
    (489, "Seton Winter Invitational", "vcac_championship"),
    (493, "2025 NoVa Catholic Invitational Championship", "vcac_championship"),
    (494, "VISAA Junior Varsity Invitational", "visaa_championship"),
    (495, "2025 Annual VISAA Division II Invitational", "visaa_championship"),
    (496, "2025 VCAC Championship Meet", "vcac_championship"),
    (497, "National Catholic H.S. Championship 2025", "visaa_championship"),
    (498, "2025 VISAA Swimming & Diving Championship", "visaa_championship"),
    (500, "NoVA Catholic High School Times", "vcac_championship"),
    (506, "Seton Icebreaker Invitational", "vcac_championship"),
    (509, "Seton December Invitational", "vcac_championship"),
    (510, "Seton Homecoming Invitational", "vcac_championship"),
    # =====================
    # 2026 SEASON (2 meets so far)
    # =====================
    (512, "VCAC Regular Season Championship", "vcac_championship"),
    (513, "2026 NoVa Catholic Invitational Championship", "vcac_championship"),
]


def load_mdb_championship_data(
    connector: MDBConnector, meet_id: int
) -> tuple[list[dict], dict[int, str], dict[str, Any]]:
    """Load championship meet data from MDB as psych sheet entries."""
    # Load tables
    result_df = connector.read_table("RESULT")
    athlete_df = connector.read_table("ATHLETE")
    team_df = connector.read_table("TEAM")
    meet_df = connector.read_table("MEET")

    # Get meet info
    meet_row = meet_df[meet_df["MEET"] == meet_id]
    meet_row["MNAME"].values[0] if not meet_row.empty else f"Meet {meet_id}"

    meet_meta = {
        "start_date": str(meet_row["Start"].values[0])
        if not meet_row.empty and "Start" in meet_row
        else "Unknown",
        "end_date": str(meet_row["End"].values[0])
        if not meet_row.empty and "End" in meet_row
        else "Unknown",
        "location": str(meet_row["Location"].values[0])
        if not meet_row.empty and "Location" in meet_row
        else "Unknown",
        "course": str(meet_row["Course"].values[0])
        if not meet_row.empty and "Course" in meet_row
        else "Y",
        "remarks": str(meet_row["Remarks"].values[0])
        if not meet_row.empty and "Remarks" in meet_row
        else "",
    }

    # Build team ID -> name map
    team_map = dict(zip(team_df["TEAM"], team_df["TNAME"]))

    # Filter results for this meet
    meet_results = result_df[result_df["MEET"] == meet_id].copy()

    if meet_results.empty:
        return [], team_map

    # Merge with athlete info
    athlete_df_slim = athlete_df[["ATHLETE", "FIRST", "LAST", "SEX", "TEAM1"]]
    merged = pd.merge(meet_results, athlete_df_slim, on="ATHLETE", how="left")

    # Filter individual and relay events
    if "I_R" in merged.columns:
        merged = merged[merged["I_R"].isin(["I", "R"])]

    # Process entries
    entries = []
    for _, row in merged.iterrows():
        # Check time validity first
        time = pd.to_numeric(row.get("SCORE"), errors="coerce")
        if pd.isna(time) or time <= 0:
            continue

        # Convert centiseconds if needed
        if time > 1000:
            time = time / 100.0

        # Common attributes
        gender = "M" if row.get("SEX") == "M" else "F"
        team_id = row.get("TEAM")
        team_name = team_map.get(team_id, f"Team_{team_id}")
        distance = int(row.get("DISTANCE", 0))

        # Determine event name based on type
        if row.get("I_R") == "R":
            # Relay Event
            stroke_code = row.get("STROKE")

            # Infer event name
            if distance == 200 and stroke_code == 1:
                event_name = f"{gender}s 200 Free Relay"
            elif distance == 400 and stroke_code == 1:
                event_name = f"{gender}s 400 Free Relay"
            elif distance == 200 and stroke_code == 2:
                # Map code 2 to Medley if standard? Or fallback.
                # Let's assume standard order if STROKE is Back (2).
                # Actually, usually Medley Relay uses a specific stroke code.
                # Safest is to check pattern.
                event_name = f"{gender}s 200 Medley Relay"
            # Simple fallback for Medley (often code 5=IM)
            elif distance == 200 and stroke_code == 5:
                event_name = f"{gender}s 200 Medley Relay"
            else:
                s_name = STROKE_MAP.get(stroke_code, "Free")
                event_name = f"{gender}s {distance} {s_name} Relay"
        else:
            # Individual Event
            stroke = STROKE_MAP.get(row.get("STROKE"), None)
            if stroke is None:
                continue
            event_name = f"{gender}s {distance} {stroke}"

        entries.append(
            {
                "swimmer_name": f"{row.get('FIRST', '')} {row.get('LAST', '')}".strip(),
                "team": team_name,
                "event": event_name,
                "seed_time": time,
                "gender": gender,
            }
        )

    return entries, team_map, meet_meta


def get_actual_team_standings(
    connector: MDBConnector, meet_id: int, team_map: dict[int, str]
) -> dict[str, float]:
    """Extract actual team standings from MDB POINTS column."""
    result_df = connector.read_table("RESULT")
    meet_results = result_df[result_df["MEET"] == meet_id]

    standings = {}
    for team_id, points in meet_results.groupby("TEAM")["POINTS"].sum().items():
        team_name = team_map.get(team_id, f"Team_{team_id}")
        # MDB points are scaled by 10 (e.g., 6780 -> 678 pts)
        standings[team_name] = float(points) / 10.0

    return standings


def validate_historical_lineup(
    entries: list[dict], team_name: str, profile: str = "vcac_championship"
) -> dict[str, Any]:
    """
    Validate historical lineup and calculate legal score.
    Returns: {
        "violations": List[str],
        "legal_score": float,
        "illegal_score": float # Projected including invalid entries
    }
    """
    # Filter for target team
    team_entries = [
        e for e in entries if team_name.lower() in e.get("team", "").lower()
    ]

    # 1. Build assignments dict for validator
    assignments = {}
    relay_assignments = {
        "200 Medley Relay": set(),
        "200 Free Relay": set(),
        "400 Free Relay": set(),
    }
    divers = set()

    # Helper to clean event names
    for entry in team_entries:
        swimmer = entry["swimmer_name"]
        event = normalize_event_name(entry["event"])

        if "diving" in event.lower():
            divers.add(swimmer)
            continue

        if "relay" in event.lower():
            # Add to relay set
            if "medley" in event.lower():
                relay_assignments["200 Medley Relay"].add(swimmer)
            elif "400" in event.lower() and "free" in event.lower():
                relay_assignments["400 Free Relay"].add(swimmer)
            else:
                relay_assignments["200 Free Relay"].add(swimmer)
        else:
            # Individual event
            if swimmer not in assignments:
                assignments[swimmer] = []
            assignments[swimmer].append(event)

    # 2. Validate
    simple_relay_assignments = {k: list(v) for k, v in relay_assignments.items() if v}

    result = validate_lineup(
        seton_assignments=assignments,
        divers=divers,
        relay_assignments=simple_relay_assignments,
        meet_profile=profile,
    )

    violations = []
    # 3. Calculate Scores using Projection Service
    # We need to project TWICE:
    # A. Full Lineup (Illegal)
    # B. Filtered Lineup (Legal) - Removing violating events

    # Strategy for removing violating events:
    # - If Back-to-Back: Remove the second event (chronologically)
    # - If Max Events: Remove events after the limit is reached (chronologically)

    # Flatten all swimmer events with simplified names for filtering
    # Structure: {swimmer: {event_name: entry}}
    swimmer_entries_map = {}
    for entry in team_entries:
        s = entry["swimmer_name"]
        e = normalize_event_name(entry["event"])
        if s not in swimmer_entries_map:
            swimmer_entries_map[s] = {}
        swimmer_entries_map[s][e] = entry

    # Events to EXCLUDE from legal calculation
    excluded_entries = []  # List of (swimmer, event) tuples

    if not result.is_valid:
        for v in result.violations:
            violations.append(f"{v.swimmer}: {v.message}")

            # Simple heuristic for now: drop ALL events involved in violation
            # Ideally we would be smarter, but "events_involved" gives us the specific culprits
            for event in v.events_involved:
                # If back-to-back, we should only drop the SECOND one?
                # v.events_involved usually has [event1, event2]
                # Let's try to be smart about B2B
                if v.violation_type == "back_to_back":
                    # Drop the second one in standard order
                    # Need import for get_event_index? Or just use list order
                    # Just drop the one with higher index if possible, or both if unsure
                    # Let's drop both to be safe/conservative about "Legal" score -
                    # if it was illegal, you effectively get DQ'd or have to scratch?
                    # Actually, usually you scratch one.
                    # Let's just drop the involved events.
                    excluded_entries.append((v.swimmer, normalize_event_name(event)))
                elif v.violation_type == "max_events":
                    # Drop individual events first? Or just drop all involved?
                    # Dropping all involved is harsh but fair baseline for "Strict" legality
                    excluded_entries.append((v.swimmer, normalize_event_name(event)))
                else:
                    excluded_entries.append((v.swimmer, normalize_event_name(event)))

    # Deduplicate excluded entries
    excluded_set = set(excluded_entries)

    # Create legal entries list
    legal_entries = []
    for entry in entries:  # Use ALL entries to score against opponents
        if team_name.lower() not in entry.get("team", "").lower():
            legal_entries.append(entry)
            continue

        # Check if this specific entry is invalid
        swimmer = entry["swimmer_name"]
        event = normalize_event_name(entry["event"])
        if (swimmer, event) in excluded_set:
            continue
        legal_entries.append(entry)

    # Project
    proj_service = PointProjectionService(profile)

    # A. Illegal Score (Projected)
    full_proj = proj_service.project_standings(entries, team_name)
    illegal_score = full_proj.target_team_total

    # B. Legal Score
    legal_proj = proj_service.project_standings(legal_entries, team_name)
    legal_score = legal_proj.target_team_total

    return {
        "violations": violations,
        "legal_score": legal_score,
        "illegal_score": illegal_score,
        "legal_entries": legal_entries,
    }


def run_championship_backtest(
    meet_id: int, meet_name: str, profile: str
) -> dict[str, Any]:
    """Run championship backtest for a single meet."""
    result = {
        "meet_id": meet_id,
        "meet_name": meet_name,
        "profile": profile,
        "predicted_standings": {},
        "actual_standings": {},
        "seton_predicted_rank": 0,
        "seton_actual_rank": 0,
        "rank_accuracy": 0.0,
        "optimization_enabled": False,
        "ai_improvement": 0.0,
        "ai_projected_score": 0.0,
        "coach_analysis": None,  # New field
        "entry_assignments": None,  # Store pipeline entry assignments
        "error": None,
    }

    try:
        connector = MDBConnector(DB_PATH)

        # Load data
        # Load data
        entries, team_map, meet_meta = load_mdb_championship_data(connector, meet_id)

        if not entries:
            result["error"] = "No entries found"
            return result

        # Store entries for later use in report generation
        result["entries"] = entries
        result["meet_meta"] = meet_meta

        # Get actual standings
        actual_standings = get_actual_team_standings(connector, meet_id, team_map)
        result["actual_standings"] = actual_standings

        # --- VALIDATE COACH BASELINE ---
        coach_stats = validate_historical_lineup(entries, "Seton", profile)
        result["coach_analysis"] = coach_stats

        # Run championship pipeline
        pipeline = create_championship_pipeline(meet_profile=profile)

        input_data = ChampionshipInput(
            entries=entries,
            target_team="Seton Swimming",
            meet_name=meet_name,
            meet_profile=profile,
        )

        # Run full pipeline to get optimization
        pipeline_result = pipeline.run(input_data, stage="entries")

        # Check if optimization happened
        if pipeline_result.entry_assignments:
            result["optimization_enabled"] = True
            result["ai_improvement"] = pipeline_result.optimization_improvement

            # Find Seton's projected score
            seton_base_score = 0
            for team, points, rank in pipeline_result.projection.standings:
                if "seton" in team.lower():
                    seton_base_score = points
                    break

            result["ai_projected_score"] = seton_base_score + result.get(
                "ai_improvement", 0
            )

            # Store entry assignments for report generation
            result["entry_assignments"] = pipeline_result.entry_assignments

        # Extract predicted standings
        # standings is List[Tuple[str, float, int]] = (team, points, rank)
        if pipeline_result.projection:
            for team, points, rank in pipeline_result.projection.standings:
                result["predicted_standings"][team] = points

        # Calculate rank accuracy
        # Sort teams by points (descending) to get ranks
        pred_sorted = sorted(result["predicted_standings"].items(), key=lambda x: -x[1])
        actual_sorted = sorted(result["actual_standings"].items(), key=lambda x: -x[1])

        # Find Seton's rank
        for i, (team, _) in enumerate(pred_sorted, 1):
            if "seton" in team.lower():
                result["seton_predicted_rank"] = i
                break

        for i, (team, _) in enumerate(actual_sorted, 1):
            if "seton" in team.lower():
                result["seton_actual_rank"] = i
                break

        # Calculate rank accuracy
        if result["seton_actual_rank"] > 0:
            rank_diff = abs(
                result["seton_predicted_rank"] - result["seton_actual_rank"]
            )
            max_teams = len(actual_sorted)
            result["rank_accuracy"] = max(0, 100 * (1 - rank_diff / max_teams))

    except Exception as e:
        result["error"] = str(e)
        import traceback

        traceback.print_exc()

    return result


def main():
    """Run championship backtests on all target meets."""
    if not os.path.exists(DB_PATH):
        print(f"MDB not found at {DB_PATH}")
        return

    print("=" * 80)
    print("CHAMPIONSHIP MODE BACKTEST")
    print("=" * 80)

    results = []

    for meet_id, meet_name, profile in CHAMPIONSHIP_MEETS:
        print(f"\n{'=' * 60}")
        print(f"Meet {meet_id}: {meet_name}")
        print(f"Profile: {profile}")
        print("-" * 60)

        start = time.time()
        result = run_championship_backtest(meet_id, meet_name, profile)
        elapsed = time.time() - start

        if result["error"]:
            print(f"ERROR: {result['error']}")
        else:
            print(f"Teams Found: {len(result['predicted_standings'])}")
            print("\nPredicted Standings:")
            for i, (team, pts) in enumerate(
                sorted(result["predicted_standings"].items(), key=lambda x: -x[1])[:5],
                1,
            ):
                seton_marker = " ⭐" if "seton" in team.lower() else ""
                print(f"  {i}. {team}: {pts:.0f} pts{seton_marker}")

            print("\nActual Standings:")
            for i, (team, pts) in enumerate(
                sorted(result["actual_standings"].items(), key=lambda x: -x[1])[:5], 1
            ):
                seton_marker = " ⭐" if "seton" in team.lower() else ""
                print(f"  {i}. {team}: {pts:.0f} pts{seton_marker}")

            print(
                f"\nSeton Rank: Predicted #{result['seton_predicted_rank']} vs Actual #{result['seton_actual_rank']}"
            )
            print(f"Rank Accuracy: {result['rank_accuracy']:.1f}%")

        # Coach Analysis Output
        coach_analysis = result.get("coach_analysis")
        if coach_analysis:
            print("\nCoach Baseline Analysis:")
            illegal = coach_analysis.get("illegal_score", 0)
            legal = coach_analysis.get("legal_score", 0)
            diff = illegal - legal

            print(f"  Raw Score (Actual Entries): {illegal:.0f} pts")
            print(f"  Legal Score (Valid Entries): {legal:.0f} pts")

            if diff > 0:
                print(f"  ⚠️  Coach score inflated by {diff:.0f} pts due to violations")

            violations = coach_analysis.get("violations", [])
            if violations:
                print(f"  Constraint Violations ({len(violations)}):")
                for i, v in enumerate(violations[:5], 1):  # Show top 5
                    print(f"    {i}. {v}")
                if len(violations) > 5:
                    print(f"    ... and {len(violations) - 5} more")
        else:
            print("\nCoach Analysis: Not available")

        if result.get("optimization_enabled"):
            print("\nAI Optimization Results:")
            print(f"  AI Improvement:    +{result['ai_improvement']:.0f} pts")
            # Compare AI against LEGAL coach score if available, else raw
            baseline = coach_analysis.get("legal_score", 0) if coach_analysis else 0

            ai_score = result["ai_projected_score"]
            print(f"  AI Projected Score: {ai_score:.0f} pts")

            if abs(baseline) > 0:
                delta = ai_score - baseline
                print(
                    f"  AI Advantage vs LEGAL Baseline: {'+' if delta >= 0 else ''}{delta:.0f} pts"
                )

            actual_scaled = result["actual_standings"].get("Seton Swimming", 0)
            if ai_score > actual_scaled:
                print(
                    f"  ✅ AI beats Historical Actuals by {ai_score - actual_scaled:.0f} pts"
                )
            else:
                print(
                    f"  ❌ AI loses to Historical Actuals by {actual_scaled - ai_score:.0f} pts"
                )

            # Generate Premium Report
            try:
                # Prepare top teams list
                pred_map = result["predicted_standings"]
                act_map = result["actual_standings"]
                all_teams = set(pred_map.keys()) | set(act_map.keys())

                # Sort by projected points for rank
                sorted_teams = sorted(all_teams, key=lambda t: -pred_map.get(t, 0))[
                    :5
                ]  # Top 5

                top_teams = []
                for t in sorted_teams:
                    is_seton = "seton" in t.lower()

                    # Points Logic
                    # Opponents: AI Proj == Coach Proj == Predicted Standing
                    # Seton: AI Proj = ai_score, Coach Proj = legal_score

                    p_score = pred_map.get(t, 0)

                    if is_seton:
                        ai_points = ai_score
                        coach_points = baseline
                    else:
                        ai_points = p_score
                        coach_points = p_score

                    top_teams.append(
                        {
                            "name": t,
                            "ai_points": ai_points,
                            "coach_points": coach_points,
                            "actual_points": act_map.get(t, 0),
                        }
                    )

                    # Fix for "Seton" vs "Seton Swimming" mismatch in console/dashboard
                    # If we found Seton under "Seton", but actuals under "Seton Swimming", merge them
                    if is_seton and act_map.get(t, 0) == 0:
                        # try looking for "Seton Swimming"
                        alt_name = "Seton Swimming"
                        if alt_name in act_map:
                            top_teams[-1]["actual_points"] = act_map[alt_name]

                # Unpack metadata
                meet_meta = result.get("meet_meta", {})

                context = {
                    "meet_name": meet_name,
                    "profile": profile,
                    "location": meet_meta.get("location", "Unknown"),
                    "meet_date": f"{meet_meta.get('start_date')} - {meet_meta.get('end_date')}",
                    "course": meet_meta.get("course", "Y"),
                    "remarks": meet_meta.get("remarks", ""),
                    "report_date": datetime.now().strftime("%Y-%m-%d"),
                    "ai_score": ai_score,
                    "ai_delta": ai_score - baseline,
                    "legal_coach_score": baseline,
                    "illegal_coach_score": coach_analysis.get("illegal_score", 0),
                    "actual_seton_score": result["actual_standings"].get(
                        "Seton Swimming", 0
                    ),
                    "rank_accuracy": result.get("rank_accuracy", 0),
                    "illegal_points_removed": coach_analysis.get("illegal_score", 0)
                    - baseline,
                    "violations": coach_analysis.get("violations", []),
                    "top_teams": top_teams,
                    "roster": [],
                    "ai_lineup": [],
                    "coach_lineup": [],
                    "anomalies": [],
                    "reasoning": [],
                }

                # Add illegal_points to each team in top_teams
                for team in top_teams:
                    if "seton" in team["name"].lower():
                        team["illegal_points"] = coach_analysis.get("illegal_score", 0)
                    else:
                        team["illegal_points"] = team["ai_points"]  # Same for opponents

                # Build AI Lineup
                entry_assignments = result.get("entry_assignments")
                if entry_assignments:
                    for swimmer, events in sorted(entry_assignments.items()):
                        # Skip "nan nan" entries - these are relay placeholders
                        if swimmer.lower() == "nan nan" or not swimmer.strip():
                            context["anomalies"].append(
                                "⚠️ Relay placeholder 'nan nan' detected - relay swimmer names missing from database"
                            )
                            continue
                        context["ai_lineup"].append(
                            {
                                "name": swimmer,
                                "events": events,
                                "is_new": False,  # Will be updated if not in coach lineup
                            }
                        )
                    context["roster"] = [
                        {"name": s, "events": [{"name": e} for e in evts]}
                        for s, evts in sorted(entry_assignments.items())
                        if s.lower() != "nan nan" and s.strip()
                    ]

                # Build Coach Lineup from historical entries (with violations marked)
                # Get Seton entries from original data
                violation_swimmers = set()
                for v in coach_analysis.get("violations", []):
                    parts = v.split(":")
                    if parts:
                        violation_swimmers.add(parts[0].strip())

                # Build coach lineup from entries
                coach_swimmers = {}
                historical_entries = result.get("entries", [])
                for entry in historical_entries:
                    if "seton" in entry.get("team", "").lower():
                        name = entry.get("swimmer_name", "")
                        event = entry.get("event", "")
                        if name not in coach_swimmers:
                            coach_swimmers[name] = []
                        if event and event not in coach_swimmers[name]:
                            coach_swimmers[name].append(event)

                for swimmer, events in sorted(coach_swimmers.items()):
                    context["coach_lineup"].append(
                        {
                            "name": swimmer,
                            "events": events,
                            "has_violation": swimmer in violation_swimmers,
                        }
                    )

                # Generate reasoning for AI advantage
                if ai_score > baseline:
                    context["reasoning"].append(
                        f"AI avoids {len(coach_analysis.get('violations', []))} constraint violations that cost coach {coach_analysis.get('illegal_score', 0) - baseline:.0f} pts"
                    )
                    context["reasoning"].append(
                        "AI optimally assigns swimmers to their best events given constraints"
                    )

                    # Check for back-to-back violations
                    b2b_count = sum(
                        1
                        for v in coach_analysis.get("violations", [])
                        if "back-to-back" in v.lower()
                    )
                    if b2b_count > 0:
                        context["reasoning"].append(
                            f"Coach had {b2b_count} back-to-back violations (swimmers in consecutive events)"
                        )

                    # Check for max events violations
                    max_ev_count = sum(
                        1
                        for v in coach_analysis.get("violations", [])
                        if "max" in v.lower()
                        or "effective individual events" in v.lower()
                    )
                    if max_ev_count > 0:
                        context["reasoning"].append(
                            f"Coach had {max_ev_count} max-events violations (swimmers in too many events)"
                        )

                # Detect anomalies
                if result["actual_standings"].get("Seton Swimming", 0) == 0:
                    context["anomalies"].append(
                        "📊 Actual meet results may be incomplete (Seton shows 0 points)"
                    )

                if any("nan" in s.lower() for s in coach_swimmers.keys()):
                    context["anomalies"].append(
                        "⚠️ Some swimmer names are missing ('nan nan') - likely relay-only swimmers without individual entries"
                    )

                reporter = PremiumReporter()
                reporter.generate_dashboard(context)
                if context["roster"]:
                    reporter.generate_roster(context)

            except Exception as e:
                print(f"⚠️ Failed to generate report: {e}")
                import traceback

                traceback.print_exc()

        print(f"Time: {elapsed:.1f}s")
        results.append(result)

    # Summary
    valid_results = [r for r in results if not r["error"]]
    if valid_results:
        avg_accuracy = sum(r["rank_accuracy"] for r in valid_results) / len(
            valid_results
        )
        rank_matches = sum(
            1
            for r in valid_results
            if r["seton_predicted_rank"] == r["seton_actual_rank"]
        )

        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Meets Tested: {len(valid_results)}/{len(results)}")
        print(f"Exact Rank Matches: {rank_matches}/{len(valid_results)}")
        print(f"Average Rank Accuracy: {avg_accuracy:.1f}%")

    # Save results
    df = pd.DataFrame(results)
    output_path = "data/backtest/championship_backtest_results.csv"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"\nResults saved to {output_path}")


if __name__ == "__main__":
    main()
