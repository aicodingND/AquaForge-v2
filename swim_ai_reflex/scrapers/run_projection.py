#!/usr/bin/env python3
"""
Run VCAC Championship Point Projections

Uses the unified psych sheet to calculate expected team standings.
"""

import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from swim_ai_reflex.backend.models.championship import MeetPsychSheet, PsychSheetEntry
from swim_ai_reflex.backend.services.point_projection_service import (
    PointProjectionEngine,
)


def load_unified_psych_sheet(path: Path) -> MeetPsychSheet:
    """Load the unified psych sheet and convert to MeetPsychSheet format."""
    with open(path) as f:
        data = json.load(f)

    entries = []
    for entry in data.get("entries", []):
        entries.append(
            PsychSheetEntry(
                swimmer_name=entry["swimmer_name"],
                team=entry["team"],
                event=entry["event"],
                seed_time=entry["seed_time"],
                gender=entry.get("gender", ""),
                grade=entry.get("grade"),
            )
        )

    return MeetPsychSheet(
        meet_name=data.get("meet_name", "VCAC Championship"),
        meet_date=data.get("meet_date", "2026-02-07"),
        entries=entries,
        teams=data.get("teams", []),
    )


def main():
    print("=" * 70)
    print("VCAC 2026 CHAMPIONSHIP POINT PROJECTION")
    print("=" * 70)

    # Load unified psych sheet
    psych_path = Path("data/championship_data/vcac_2026_unified_psych_sheet.json")
    print(f"\nLoading: {psych_path}")

    psych = load_unified_psych_sheet(psych_path)
    print(f"Entries: {len(psych.entries)}")
    print(f"Teams: {len(psych.teams)}")
    print(f"Events: {len(psych.get_all_events())}")

    # Initialize projection engine
    engine = PointProjectionEngine(meet_profile="vcac_championship")

    # Run projection
    print("\nRunning Point Projection...")
    projection = engine.project_full_meet(psych, target_team="SST")

    # Display standings
    print("\n" + "=" * 70)
    print("▸ PROJECTED TEAM STANDINGS")
    print("=" * 70)
    print(f"{'Place':<8}{'Team':<25}{'Points':>12}")
    print("-" * 70)

    for i, (team, points) in enumerate(projection.standings[:15], 1):
        medal = "" if i == 1 else "" if i == 2 else "" if i == 3 else " "
        highlight = " " if team == "SST" else ""
        print(f"{medal} {i:<5}{team:<25}{points:>12.1f}{highlight}")

    # Seton summary
    print("\n" + "=" * 70)
    print("▸ SETON (SST) DETAILED ANALYSIS")
    print("=" * 70)

    seton_summary = engine.summarize_team(projection, "SST")
    print(f"\nProjected Standing: #{seton_summary['standing']}")
    print(f"▸ Total Points: {seton_summary['total_points']:.1f}")
    print(f"Scoring Entries: {seton_summary['total_scoring_entries']}")

    print("\nTop Scorers:")
    for scorer in seton_summary["top_scorers"][:8]:
        print(
            f"{scorer['swimmer']:<25} {scorer['event']:<20} #{scorer['place']} ({scorer['points']}pts)"
        )

    print("\n▸ Best Events:")
    for event in seton_summary["best_events"]:
        print(f"{event['event']:<30} {event['points']:.0f} pts")

    # Swing events (opportunities)
    if projection.swing_events:
        print("\n" + "=" * 70)
        print("→ SWING EVENTS (IMPROVEMENT OPPORTUNITIES)")
        print("=" * 70)

        for swing in projection.swing_events[:10]:
            priority_icon = "" if swing["priority"] == "high" else ""
            print(f"\n{priority_icon} {swing['event']}")
            print(
                f"{swing['swimmer']}: {swing['current_place']}→{swing['target_place']} = +{swing['point_gain']} pts"
            )

    # Head-to-head vs top competitor
    if len(projection.standings) >= 2:
        top_competitor = (
            projection.standings[0][0]
            if projection.standings[0][0] != "SST"
            else projection.standings[1][0]
        )

        print("\n" + "=" * 70)
        print(f"HEAD-TO-HEAD: SST vs {top_competitor}")
        print("=" * 70)

        h2h = engine.get_head_to_head(projection, "SST", top_competitor)
        print(f"\nSST: {h2h['team1_total']:.1f} pts")
        print(f"{top_competitor}: {h2h['team2_total']:.1f} pts")
        print(f"Differential: {h2h['overall_differential']:+.1f}")
        print(
            f"Events Won: SST {h2h['events_won'].get('SST', 0)} - {h2h['events_won'].get(top_competitor, 0)} {top_competitor}"
        )

    # Save detailed report
    report = {
        "generated_at": str(Path(".")),
        "standings": projection.standings,
        "team_totals": projection.team_totals,
        "seton_summary": seton_summary,
        "swing_events": projection.swing_events[:15],
    }

    report_path = Path("data/championship_data/vcac_2026_projection_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"\n\n ✓ Detailed report saved to: {report_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
