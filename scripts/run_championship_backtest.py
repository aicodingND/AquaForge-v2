#!/usr/bin/env python3
"""
Championship Strategy Backtest - JSON Data
===========================================
Runs backtests on existing JSON championship data using:
- Gurobi MILP (ChampionshipGurobiStrategy)
- AquaOptimizer with Nash+Beam+SimAnnealing

Uses correct scoring profiles:
- VCAC: 12-place (16-13-12-11-10-9-7-5-4-3-2-1), relay 2×
- VISAA: 16-place (20-17-16...), relay 2×
"""

import json
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

# Setup paths
sys.path.insert(0, str(Path(__file__).parent.parent))

from swim_ai_reflex.backend.core.strategies.aqua_optimizer import (
    AquaOptimizer,
    ScoringProfile,
)
from swim_ai_reflex.backend.core.strategies.championship_strategy import (
    ChampionshipEntry,
    ChampionshipGurobiStrategy,
)

# Championship data files
DATA_DIR = Path(__file__).parent.parent / "data"
CHAMPIONSHIP_FILES = [
    # (path, profile, target_team)
    (
        DATA_DIR / "championship_data" / "vcac_2026_unified_psych_sheet.json",
        "vcac_championship",
        "SST",
    ),
    (
        DATA_DIR / "championship_data" / "vcac_2026_psych_sheet_projection.json",
        "vcac_championship",
        "SST",
    ),
    (
        DATA_DIR / "championship_data" / "2026_nova_catholic_case_study.json",
        "vcac_championship",
        "SST",
    ),
    (
        DATA_DIR / "vcac" / "VCAC_2026_unified_psych_sheet.json",
        "vcac_championship",
        "SST",
    ),
]


@dataclass
class BacktestResult:
    """Result from a single backtest."""

    meet_name: str
    profile: str

    # Scores
    gurobi_score: float = 0.0
    aqua_score: float = 0.0
    actual_score: float = 0.0  # Coach's actual score from meet results

    # Times
    gurobi_time_ms: float = 0.0
    aqua_time_ms: float = 0.0

    # Analysis
    winner: str = ""
    entries: int = 0
    teams: int = 0
    seton_entries: int = 0
    error: str = ""


def get_scoring_profile(profile: str) -> ScoringProfile:
    """Get the correct ScoringProfile for the meet type."""
    if profile == "vcac_championship":
        return ScoringProfile.vcac_championship()
    elif profile == "visaa_championship":
        return ScoringProfile.visaa_championship()
    else:
        return ScoringProfile.visaa_dual()


def load_json_data(json_path: Path) -> tuple[list[ChampionshipEntry], dict, str]:
    """Load entries from JSON file. Handles both formats:
    1. Flat 'entries' list (vcac_unified)
    2. Nested 'events' dict with entries per event (nova_catholic)
    """
    if not json_path.exists():
        return [], {}, f"File not found: {json_path}"

    try:
        with open(json_path) as f:
            data = json.load(f)

        entries = []

        # Format 1: Flat entries list
        if "entries" in data:
            for e in data.get("entries", []):
                seed = e.get("seed_time", 0) or e.get("final_time", 0)
                entries.append(
                    ChampionshipEntry(
                        swimmer_name=e.get("swimmer_name", "Unknown"),
                        team=e.get("team", "UNK"),
                        event=e.get("event", "Unknown"),
                        seed_time=float(seed) if seed else 0.0,
                        gender=e.get("gender", ""),
                    )
                )

        # Format 2: Nested events dict
        elif "events" in data:
            for event_name, event_data in data["events"].items():
                for e in event_data.get("entries", []):
                    # Use final_time as seed if seed_time is 0
                    seed = e.get("seed_time", 0)
                    if not seed or seed == 0:
                        seed = e.get("final_time", 0)

                    # Add gender prefix if event doesn't have it
                    full_event = event_name
                    gender = e.get("gender", "")
                    if gender == "M" and not event_name.startswith("Boys"):
                        full_event = f"Boys {event_name}"
                    elif gender == "F" and not event_name.startswith("Girls"):
                        full_event = f"Girls {event_name}"

                    entries.append(
                        ChampionshipEntry(
                            swimmer_name=e.get("swimmer_name", "Unknown"),
                            team=e.get("team", "UNK"),
                            event=full_event,
                            seed_time=float(seed) if seed else 0.0,
                            gender=gender,
                        )
                    )

        return entries, data, None
    except Exception as e:
        return [], {}, str(e)


def entries_to_dataframe(entries: list[ChampionshipEntry]) -> pd.DataFrame:
    """Convert entries to DataFrame for AquaOptimizer."""
    return pd.DataFrame(
        [
            {
                "swimmer": e.swimmer_name,
                "event": e.event,
                "time": e.seed_time,
                "team": e.team,
            }
            for e in entries
        ]
    )


def get_actual_score(metadata: dict, target_team: str) -> float:
    """Extract actual team score from JSON metadata if available."""
    # Check for team_standings array (Nova Catholic format)
    if "team_standings" in metadata:
        for standing in metadata["team_standings"]:
            if standing.get("team", "").upper() == target_team.upper():
                return float(standing.get("total_points", 0))

    # Check for actual_results or results section
    if "actual_results" in metadata:
        actual = metadata["actual_results"]
        if isinstance(actual, dict):
            return float(actual.get(target_team, actual.get(target_team.upper(), 0)))

    return 0.0


def run_gurobi_backtest(
    entries: list[ChampionshipEntry], profile: str, target_team: str = "SST"
) -> tuple[float, float, dict]:
    """Run Gurobi optimization and return (score, time_ms, details)."""
    try:
        strategy = ChampionshipGurobiStrategy(meet_profile=profile)

        start = time.time()
        result = strategy.optimize_entries(
            entries,
            target_team=target_team,
            time_limit=60,  # 60 second limit
        )
        elapsed = (time.time() - start) * 1000

        return (
            result.total_points,
            elapsed,
            {
                "baseline": result.baseline_points,
                "improvement": result.improvement,
                "status": result.status,
                "assignments": result.assignments,
            },
        )

    except Exception as e:
        print(f"! Gurobi error: {e}")
        return 0.0, 0.0, {"error": str(e)}


def run_aqua_backtest(
    entries: list[ChampionshipEntry], profile: str, target_team: str = "SST"
) -> tuple[float, float, dict]:
    """Run AquaOptimizer with best settings and return (score, time_ms, details)."""
    try:
        from swim_ai_reflex.backend.core.rules import get_meet_profile

        scoring_profile = get_scoring_profile(profile)
        rules = get_meet_profile(profile)

        # Best configuration: thorough mode + Nash
        optimizer = AquaOptimizer(
            profile=scoring_profile,
            quality_mode="thorough",
            nash_iterations=5,
        )

        # Convert to DataFrames
        df = entries_to_dataframe(entries)
        seton_df = df[df["team"].str.upper() == target_team.upper()].copy()
        opponent_df = df[df["team"].str.upper() != target_team.upper()].copy()

        if len(seton_df) == 0:
            return 0.0, 0.0, {"error": "No entries for target team"}

        # Create scoring function from rules
        def scoring_fn(place: int, is_relay: bool = False) -> int:
            points = rules.relay_points if is_relay else rules.individual_points
            if 0 <= place - 1 < len(points):
                return points[place - 1]
            return 0

        start = time.time()
        result = optimizer.optimize(
            seton_roster=seton_df,
            opponent_roster=opponent_df,
            scoring_fn=scoring_fn,
            rules=rules,
        )
        elapsed = (time.time() - start) * 1000

        # Result is tuple: (lineup_df, scored_df, totals_dict, details_list)
        if isinstance(result, tuple) and len(result) >= 3:
            totals = result[2]
            seton_score = totals.get("seton_pts", totals.get("seton", 0))
            opponent_score = totals.get("opponent_pts", totals.get("opponent", 0))
            return (
                float(seton_score),
                elapsed,
                {
                    "seton_score": seton_score,
                    "opponent_score": opponent_score,
                    "quality_mode": "thorough",
                },
            )
        elif isinstance(result, dict):
            score = result.get("total_score", result.get("seton_score", 0))
            return float(score), elapsed, result

        return 0.0, elapsed, {"error": "Unexpected result format"}

    except Exception as e:
        print(f"! AquaOptimizer error: {e}")
        import traceback

        traceback.print_exc()
        return 0.0, 0.0, {"error": str(e)}


def run_single_backtest(
    json_path: Path, profile: str, target_team: str
) -> BacktestResult:
    """Run backtest for a single meet."""
    print(f"\n{'=' * 70}")
    print(f"BACKTEST: {json_path.name}")
    print(f"Profile: {profile}, Target: {target_team}")
    print(f"{'=' * 70}")

    # Load data
    entries, metadata, error = load_json_data(json_path)

    result = BacktestResult(
        meet_name=metadata.get("meet_name", json_path.stem),
        profile=profile,
    )

    if error:
        result.error = error
        print(f"✗ Error: {error}")
        return result

    if len(entries) == 0:
        result.error = "No entries found"
        print("✗ No entries found")
        return result

    result.entries = len(entries)
    result.teams = len(set(e.team for e in entries))
    result.seton_entries = len(
        [e for e in entries if e.team.upper() == target_team.upper()]
    )

    # Get coach's actual score if available
    result.actual_score = get_actual_score(metadata, target_team)

    print(f"▸ Total Entries: {result.entries}")
    print(f"▸ Teams: {result.teams}")
    print(f"→ {target_team} Entries: {result.seton_entries}")
    if result.actual_score > 0:
        print(f"▸ Coach Actual Score: {result.actual_score:.0f} pts")

    # Run Gurobi
    print("\n→ Running Gurobi MILP...")
    result.gurobi_score, result.gurobi_time_ms, gurobi_details = run_gurobi_backtest(
        entries, profile, target_team
    )
    print(f"✓ Score: {result.gurobi_score:.1f} pts")
    print(f"Time: {result.gurobi_time_ms:.0f}ms")
    if "baseline" in gurobi_details:
        print(f"Improvement: +{gurobi_details.get('improvement', 0):.1f} over baseline")

    # Run AquaOptimizer
    print("\n→ Running AquaOptimizer (Nash+Beam+SA)...")
    result.aqua_score, result.aqua_time_ms, aqua_details = run_aqua_backtest(
        entries, profile, target_team
    )
    print(f"✓ Score: {result.aqua_score:.1f} pts")
    print(f"Time: {result.aqua_time_ms:.0f}ms")

    # Determine winner
    diff = result.gurobi_score - result.aqua_score
    if result.gurobi_score > result.aqua_score:
        result.winner = "Gurobi"
    elif result.aqua_score > result.gurobi_score:
        result.winner = "AquaOptimizer"
    else:
        result.winner = "Tie"

    print(f"\nWINNER: {result.winner}")
    print(
        f"Gurobi: {result.gurobi_score:.1f} | Aqua: {result.aqua_score:.1f} | Diff: {abs(diff):.1f}"
    )

    # Compare to coach's actual
    if result.actual_score > 0:
        gurobi_vs_coach = result.gurobi_score - result.actual_score
        aqua_vs_coach = result.aqua_score - result.actual_score
        print(f"vs Coach: Gurobi {gurobi_vs_coach:+.0f} | Aqua {aqua_vs_coach:+.0f}")

    return result


def generate_report(results: list[BacktestResult]) -> str:
    """Generate markdown summary report."""
    lines = [
        "# Championship Backtest Results - Gurobi vs AquaOptimizer",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Summary",
        "",
    ]

    # Count wins
    gurobi_wins = sum(1 for r in results if r.winner == "Gurobi")
    aqua_wins = sum(1 for r in results if r.winner == "AquaOptimizer")
    ties = sum(1 for r in results if r.winner == "Tie")
    sum(1 for r in results if r.error)

    # Calculate totals
    total_gurobi = sum(r.gurobi_score for r in results if not r.error)
    total_aqua = sum(r.aqua_score for r in results if not r.error)

    lines.extend(
        [
            "| Metric | Value |",
            "|--------|-------|",
            f"| Total Meets | {len(results)} |",
            f"| Gurobi Wins | **{gurobi_wins}** |",
            f"| AquaOptimizer Wins | **{aqua_wins}** |",
            f"| Ties | {ties} |",
            f"| Total Gurobi Score | **{total_gurobi:.1f}** |",
            f"| Total AquaOptimizer Score | **{total_aqua:.1f}** |",
            "",
            "## Detailed Results",
            "",
            "| Meet | Entries | Gurobi Score | Aqua Score | Diff | Winner | Speed (G/A) |",
            "|------|---------|--------------|------------|------|--------|-------------|",
        ]
    )

    for r in results:
        if r.error:
            lines.append(f"| {r.meet_name} | - | | | - | Error | - |")
        else:
            diff = r.gurobi_score - r.aqua_score
            diff_str = f"+{diff:.1f}" if diff > 0 else f"{diff:.1f}"
            r.gurobi_time_ms / r.aqua_time_ms if r.aqua_time_ms > 0 else 0
            lines.append(
                f"| {r.meet_name} | {r.entries} | "
                f"**{r.gurobi_score:.1f}** | **{r.aqua_score:.1f}** | "
                f"{diff_str} | **{r.winner}** | {r.gurobi_time_ms / 1000:.1f}s / {r.aqua_time_ms / 1000:.1f}s |"
            )

    lines.extend(
        [
            "",
            "## Scoring Profiles",
            "",
            "### VCAC Championship (12-place)",
            "```",
            "Individual: 16-13-12-11-10-9-7-5-4-3-2-1",
            "Relay: 32-26-24-22-20-18-14-10-8-6-4-2 (2× individual)",
            "```",
            "",
            "### VISAA Championship (16-place)",
            "```",
            "Individual: 20-17-16-15-14-13-12-11-9-7-6-5-4-3-2-1",
            "Relay: 40-34-32-30-28-26-24-22-18-14-12-10-8-6-4-2 (2× individual)",
            "```",
        ]
    )

    return "\n".join(lines)


def main():
    """Run championship backtests on JSON data."""
    print("=" * 70)
    print("CHAMPIONSHIP BACKTEST: Gurobi vs AquaOptimizer")
    print("Using existing championship JSON data")
    print("=" * 70)

    results: list[BacktestResult] = []

    for json_path, profile, target_team in CHAMPIONSHIP_FILES:
        try:
            result = run_single_backtest(json_path, profile, target_team)
            results.append(result)
        except Exception as e:
            print(f"\n✗ Fatal error: {e}")
            import traceback

            traceback.print_exc()
            results.append(
                BacktestResult(
                    meet_name=json_path.stem,
                    profile=profile,
                    error=str(e),
                )
            )

    # Generate and save report
    print("\n" + "=" * 70)
    print("GENERATING REPORT...")
    print("=" * 70)

    report = generate_report(results)

    output_dir = DATA_DIR / "backtest"
    output_dir.mkdir(parents=True, exist_ok=True)

    report_path = output_dir / "gurobi_vs_aqua_report.md"
    report_path.write_text(report)
    print(f"\nReport saved: {report_path}")

    # Print summary
    print("\n" + report)

    return results


if __name__ == "__main__":
    main()
