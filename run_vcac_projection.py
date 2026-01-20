#!/usr/bin/env python3
"""
VCAC Championship Point Projection

Projects meet results for all teams using the unified psych sheet.
Generates detailed analysis of where Seton can gain/lose points.

Usage:
    python3 run_vcac_projection.py
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, field, asdict
from collections import defaultdict
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


@dataclass
class EventProjection:
    """Projection for a single event."""

    event: str
    gender: str
    entries: List[Dict[str, Any]] = field(default_factory=list)
    team_points: Dict[str, float] = field(default_factory=dict)


@dataclass
class TeamSummary:
    """Summary of team performance."""

    team_code: str
    team_name: str
    total_points: float = 0.0
    event_breakdown: Dict[str, float] = field(default_factory=dict)
    top_scorers: List[Dict[str, Any]] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)


# VCAC Championship Scoring (Individual events)
# Places 1-12: 32-26-24-22-20-18-14-10-8-6-4-2
VCAC_INDIVIDUAL_POINTS = [32, 26, 24, 22, 20, 18, 14, 10, 8, 6, 4, 2]
VCAC_RELAY_POINTS = [16, 13, 12, 11, 10, 9, 7, 5, 4, 3, 2, 1]
MAX_SCORERS_PER_TEAM = 4  # Top 4 per team per event score


def load_psych_sheet(json_path: Path) -> Dict[str, Any]:
    """Load the unified psych sheet."""
    with open(json_path, "r") as f:
        return json.load(f)


def get_team_name(team_code: str) -> str:
    """Map team code to full name."""
    names = {
        "SST": "Seton Swimming",
        "ICS": "Immanuel Christian",
        "TCS": "Trinity Christian",
        "FCS": "Fredericksburg Christian",
        "DJO": "Bishop O'Connell",
        "OAK": "Oakcrest School",
        "BI": "Bishop Ireton",
        "PVI": "Paul VI",
    }
    return names.get(team_code, team_code)


def project_event(entries: List[Dict], event: str, gender: str) -> EventProjection:
    """Project results for a single event."""
    # Filter entries for this event and gender
    event_entries = [
        e for e in entries if e["event"] == event and e["gender"] == gender
    ]

    # Sort by seed time
    event_entries.sort(key=lambda x: x["seed_time"])

    # Assign places and points
    team_points: Dict[str, float] = defaultdict(float)
    team_scorer_count: Dict[str, int] = defaultdict(int)

    place = 0
    for entry in event_entries:
        team = entry["team_code"]

        # Only top 4 per team score
        if team_scorer_count[team] >= MAX_SCORERS_PER_TEAM:
            entry["place"] = None
            entry["points"] = 0
            continue

        # Assign place and points
        place += 1
        entry["place"] = place

        if place <= len(VCAC_INDIVIDUAL_POINTS):
            points = VCAC_INDIVIDUAL_POINTS[place - 1]
        else:
            points = 0

        entry["points"] = points
        team_points[team] += points
        team_scorer_count[team] += 1

    return EventProjection(
        event=event,
        gender=gender,
        entries=event_entries[:24],  # Top 24 for display
        team_points=dict(team_points),
    )


def run_projection(
    psych_sheet: Dict,
) -> Tuple[List[EventProjection], Dict[str, TeamSummary]]:
    """Run full meet projection."""
    entries = psych_sheet["entries"]

    # Get unique events and genders
    events_seen = set()
    for entry in entries:
        events_seen.add((entry["event"], entry["gender"]))

    # Standard VCAC events
    standard_events = [
        "200 Free",
        "200 IM",
        "50 Free",
        "100 Fly",
        "100 Free",
        "500 Free",
        "100 Back",
        "100 Breast",
    ]

    projections = []
    team_totals: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {"total": 0.0, "events": {}, "swimmer_points": defaultdict(float)}
    )

    # Project each event
    for event_name in standard_events:
        for gender in ["M", "F"]:
            projection = project_event(entries, event_name, gender)

            if projection.entries:
                projections.append(projection)

                # Accumulate team totals
                for team, points in projection.team_points.items():
                    team_totals[team]["total"] += points
                    team_totals[team]["events"][f"{gender} {event_name}"] = points

                # Track individual scorers
                for entry in projection.entries:
                    if entry.get("points", 0) > 0:
                        team = entry["team_code"]
                        swimmer = entry["swimmer_name"]
                        team_totals[team]["swimmer_points"][swimmer] += entry["points"]

    # Build team summaries
    team_summaries = {}
    for team_code, data in team_totals.items():
        # Get top scorers
        top_scorers = sorted(
            [{"name": k, "points": v} for k, v in data["swimmer_points"].items()],
            key=lambda x: -x["points"],
        )[:5]

        # Identify strengths (events where team scores well)
        strengths = [
            ev
            for ev, pts in data["events"].items()
            if pts >= 50  # At least 50 points = very strong
        ]

        # Identify weaknesses (events where team scores poorly)
        weaknesses = [
            ev
            for ev, pts in data["events"].items()
            if pts <= 10 and pts > 0  # Low but not zero
        ]

        team_summaries[team_code] = TeamSummary(
            team_code=team_code,
            team_name=get_team_name(team_code),
            total_points=data["total"],
            event_breakdown=data["events"],
            top_scorers=top_scorers,
            strengths=strengths,
            weaknesses=weaknesses,
        )

    return projections, team_summaries


def find_swing_events(
    projections: List[EventProjection], target_team: str = "SST"
) -> List[Dict]:
    """Find events where small improvements would significantly change standings."""
    swing_events = []

    for proj in projections:
        seton_entries = [
            e for e in proj.entries if e["team_code"] == target_team and e.get("place")
        ]

        if not seton_entries:
            continue

        best_seton = (
            min(seton_entries, key=lambda x: x["place"]) if seton_entries else None
        )
        if not best_seton:
            continue

        # Find competitor just ahead of Seton's best
        ahead = [
            e
            for e in proj.entries
            if e.get("place") and e["place"] < best_seton["place"]
        ]

        if ahead:
            nearest_ahead = max(ahead, key=lambda x: x["place"])
            time_gap = best_seton["seed_time"] - nearest_ahead["seed_time"]

            # If close (within 2 seconds for sprints, 5 for distance)
            threshold = 5.0 if proj.event in ["500 Free", "200 Free", "200 IM"] else 2.0

            if time_gap <= threshold:
                points_gain = (
                    VCAC_INDIVIDUAL_POINTS[nearest_ahead["place"] - 1]
                    - VCAC_INDIVIDUAL_POINTS[best_seton["place"] - 1]
                    if best_seton["place"] <= len(VCAC_INDIVIDUAL_POINTS)
                    else 0
                )

                swing_events.append(
                    {
                        "event": f"{proj.gender} {proj.event}",
                        "seton_swimmer": best_seton["swimmer_name"],
                        "seton_place": best_seton["place"],
                        "seton_time": best_seton["seed_time"],
                        "target_place": nearest_ahead["place"],
                        "target_swimmer": nearest_ahead["swimmer_name"],
                        "target_team": nearest_ahead["team_code"],
                        "target_time": nearest_ahead["seed_time"],
                        "time_gap": time_gap,
                        "potential_points_gain": points_gain,
                    }
                )

    # Sort by potential points gain
    swing_events.sort(key=lambda x: -x["potential_points_gain"])
    return swing_events


def main():
    """Run the VCAC projection."""
    print("=" * 70)
    print("🏊 VCAC Championship 2026 - Point Projection")
    print("=" * 70)

    project_root = Path(__file__).parent
    psych_path = project_root / "data" / "vcac" / "VCAC_2026_unified_psych_sheet.json"

    if not psych_path.exists():
        print(f"ERROR: Psych sheet not found at {psych_path}")
        print("Run build_vcac_psych_sheet.py first!")
        return

    # Load psych sheet
    print("\n[1] Loading unified psych sheet...")
    psych_sheet = load_psych_sheet(psych_path)
    print(
        f"  Loaded {psych_sheet['total_entries']} entries from {len(psych_sheet['teams'])} teams"
    )

    # Run projection
    print("\n[2] Projecting meet results...")
    projections, team_summaries = run_projection(psych_sheet)
    print(f"  Projected {len(projections)} event/gender combinations")

    # Display standings
    print("\n" + "=" * 70)
    print("📊 PROJECTED TEAM STANDINGS")
    print("=" * 70)

    standings = sorted(team_summaries.values(), key=lambda x: -x.total_points)

    for i, team in enumerate(standings, 1):
        print(f"\n  {i}. {team.team_name} ({team.team_code})")
        print(f"     Total Points: {team.total_points:.0f}")
        if team.top_scorers:
            top_3 = team.top_scorers[:3]
            print(
                f"     Top Scorers: {', '.join(f'{s['name']} ({s['points']:.0f})' for s in top_3)}"
            )

    # Find swing events for Seton
    print("\n" + "=" * 70)
    print("🎯 SWING EVENT ANALYSIS (Where Seton Can Gain Points)")
    print("=" * 70)

    swing_events = find_swing_events(projections, "SST")

    if swing_events:
        print(f"\n  Found {len(swing_events)} potential swing events:")
        for i, se in enumerate(swing_events[:10], 1):
            print(f"\n  {i}. {se['event']}")
            print(
                f"     {se['seton_swimmer']} ({se['seton_time']:.2f}s) → currently {se['seton_place']}th"
            )
            print(
                f"     Target: {se['target_swimmer']} ({se['target_team']}) at {se['target_time']:.2f}s"
            )
            print(
                f"     Gap: {se['time_gap']:.2f}s | Potential gain: +{se['potential_points_gain']} pts"
            )
    else:
        print("\n  No swing events identified.")

    # Save detailed results
    print("\n" + "=" * 70)
    print("[3] Saving detailed results...")

    output_dir = project_root / "data" / "vcac"

    # Save standings
    standings_data = {
        "meet": "VCAC Championship 2026",
        "generated_at": psych_sheet["generated_at"],
        "standings": [asdict(team) for team in standings],
        "swing_events": swing_events,
    }

    standings_path = output_dir / "VCAC_2026_standings_projection.json"
    with open(standings_path, "w") as f:
        json.dump(standings_data, f, indent=2)
    print(f"  Saved to: {standings_path}")

    # Summary for Seton
    seton_summary = team_summaries.get("SST")
    if seton_summary:
        seton_position = next(
            (i for i, t in enumerate(standings, 1) if t.team_code == "SST"), None
        )
        print("\n" + "=" * 70)
        print("🏅 SETON SUMMARY")
        print("=" * 70)
        print(f"\n  Projected Position: {seton_position}th place")
        print(f"  Projected Points: {seton_summary.total_points:.0f}")

        if standings and seton_position and seton_position > 1:
            team_ahead = standings[seton_position - 2]
            gap = team_ahead.total_points - seton_summary.total_points
            print(f"  Gap to {seton_position - 1}th: {gap:.0f} points")

        if seton_summary.top_scorers:
            print("\n  Top Scorers:")
            for scorer in seton_summary.top_scorers:
                print(f"    - {scorer['name']}: {scorer['points']:.0f} pts")

    print("\n" + "=" * 70)
    print("✅ VCAC Projection Complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
