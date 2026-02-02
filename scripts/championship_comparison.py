#!/usr/bin/env python3
"""
Championship Strategy Backtest - Gurobi vs AquaOptimizer
=========================================================
Runs comprehensive backtests on all championship meets using:
- Gurobi MILP (ChampionshipGurobiStrategy)
- AquaOptimizer with Nash+Beam+SimAnnealing (best combo)

Uses CORRECT scoring profiles:
- VCAC: 12-place (16-13-12-11-10-9-7-5-4-3-2-1), relay 2×
- VISAA: 16-place (20-17-16...), relay 2×
"""

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

# Championship meets to backtest
CHAMPIONSHIP_MEETS = [
    # (meet_id, name, profile)
    (1, "VCAC Championship 2020", "vcac_championship"),
    (2, "VCAC Championship 2019", "vcac_championship"),
    (3, "VCAC Championship 2018", "vcac_championship"),
    (8, "VISAA State 2020", "visaa_championship"),
    (9, "VISAA State 2019", "visaa_championship"),
    (13, "VCAC Championship 2022", "vcac_championship"),
    (14, "VCAC Championship 2023", "vcac_championship"),
    (15, "VCAC Championship 2024", "vcac_championship"),
    (16, "VISAA State 2022", "visaa_championship"),
    (17, "VISAA State 2023", "visaa_championship"),
    (18, "VISAA State 2024", "visaa_championship"),
]


@dataclass
class BacktestResult:
    """Result from a single backtest."""

    meet_id: int
    meet_name: str
    profile: str

    # Scores
    gurobi_score: float = 0.0
    aqua_score: float = 0.0
    coach_score: float = 0.0
    actual_score: float = 0.0

    # Times
    gurobi_time_ms: float = 0.0
    aqua_time_ms: float = 0.0

    # Analysis
    gurobi_vs_coach: float = 0.0
    aqua_vs_coach: float = 0.0
    winner: str = ""
    entries: int = 0
    teams: int = 0
    error: str = ""


def get_scoring_profile(profile: str) -> ScoringProfile:
    """Get the correct ScoringProfile for the meet type."""
    if profile == "vcac_championship":
        return ScoringProfile.vcac_championship()
    elif profile == "visaa_championship":
        return ScoringProfile.visaa_championship()
    else:
        return ScoringProfile.visaa_dual()


def load_meet_data(meet_id: int) -> tuple[pd.DataFrame, str | None]:
    """Load entries from MDB for a meet."""
    mdb_paths = [
        Path(__file__).parent.parent / "data" / "real_exports" / "SSTdata.mdb",
        Path(
            "/Users/mpage1/Desktop/AquaForge/AquaForge_v1.0.0-next_2026-01-10/data/real_exports/SSTdata.mdb"
        ),
        Path("/Users/mpage1/Documents/Swim MDB/Seton SwimMeet.mdb"),
        Path("/Volumes/Storage/Swim MDB/Seton SwimMeet.mdb"),
    ]

    mdb_path = None
    for path in mdb_paths:
        if path.exists():
            mdb_path = path
            break

    if mdb_path is None:
        return pd.DataFrame(), "MDB not found"

    try:
        from swim_ai_reflex.backend.utils.mdb_connector import MDBConnector

        connector = MDBConnector(str(mdb_path))

        # Read required tables
        entries = connector.read_table("ENTRIES")
        results = connector.read_table("RESULTS")
        swimmers = connector.read_table("SWIMMERS")

        # Filter to this meet
        if "MEET_ID" not in entries.columns:
            return pd.DataFrame(), "MEET_ID column missing"

        meet_entries = entries[entries["MEET_ID"] == meet_id].copy()

        # Join with swimmers for names
        if "SWIMMER_ID" in meet_entries.columns and "SWIMMER_ID" in swimmers.columns:
            meet_entries = meet_entries.merge(
                swimmers[["SWIMMER_ID", "LAST_NAME", "FIRST_NAME", "TEAM_CODE"]],
                on="SWIMMER_ID",
                how="left",
            )

        # Get actual results if available
        if "MEET_ID" in results.columns:
            meet_results = results[results["MEET_ID"] == meet_id]
            if len(meet_results) > 0 and "POINTS" in meet_results.columns:
                # Sum total points for Seton - handle both string and numeric TEAM_CODE
                seton_mask = (
                    meet_results["TEAM_CODE"]
                    .astype(str)
                    .str.upper()
                    .isin(["SST", "SETON"])
                )
                seton_results = meet_results[seton_mask]
                actual_points = (
                    seton_results["POINTS"].sum() if len(seton_results) > 0 else 0
                )
                meet_entries["ACTUAL_POINTS"] = actual_points

        return meet_entries, None
    except Exception as e:
        return pd.DataFrame(), str(e)


def entries_to_championship_format(entries: pd.DataFrame) -> list[ChampionshipEntry]:
    """Convert DataFrame to ChampionshipEntry list."""
    result = []

    for _, row in entries.iterrows():
        # Get swimmer name
        if "LAST_NAME" in row and pd.notna(row.get("LAST_NAME")):
            name = f"{row.get('FIRST_NAME', '')} {row['LAST_NAME']}".strip()
        else:
            name = str(row.get("SWIMMER_ID", "Unknown"))

        # Get team
        team = str(row.get("TEAM_CODE", "UNK")).upper()

        # Get event
        event = str(row.get("EVENT_NAME", row.get("EVENT", "Unknown")))

        # Get seed time
        seed = 0.0
        for col in ["SEED_TIME", "TIME", "ENTRY_TIME"]:
            if col in row and pd.notna(row[col]):
                try:
                    seed = float(row[col])
                    break
                except (ValueError, TypeError):
                    pass

        if seed > 0:
            result.append(
                ChampionshipEntry(
                    swimmer_name=name,
                    team=team,
                    event=event,
                    seed_time=seed,
                )
            )

    return result


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


def run_gurobi_backtest(
    entries: list[ChampionshipEntry], profile: str, target_team: str = "SST"
) -> tuple[float, float]:
    """Run Gurobi optimization and return (score, time_ms)."""
    try:
        strategy = ChampionshipGurobiStrategy(meet_profile=profile)

        start = time.time()
        result = strategy.optimize_entries(
            entries,
            target_team=target_team,
            time_limit=30,  # 30 second limit
        )
        elapsed = (time.time() - start) * 1000

        return result.total_points, elapsed

    except Exception as e:
        print(f"  ⚠️ Gurobi error: {e}")
        return 0.0, 0.0


def run_aqua_backtest(
    entries: list[ChampionshipEntry], profile: str, target_team: str = "SST"
) -> tuple[float, float]:
    """Run AquaOptimizer with best settings and return (score, time_ms)."""
    try:
        scoring_profile = get_scoring_profile(profile)

        # Best configuration: thorough mode + Nash
        optimizer = AquaOptimizer(
            profile=scoring_profile,
            quality_mode="thorough",  # Beam search + simulated annealing
            nash_iterations=5,  # Nash equilibrium iterations
        )

        # Convert to DataFrames
        df = entries_to_dataframe(entries)
        seton_df = df[df["team"].str.upper().isin(["SST", "SETON"])]
        opponent_df = df[~df["team"].str.upper().isin(["SST", "SETON"])]

        if len(seton_df) == 0:
            return 0.0, 0.0

        start = time.time()
        result = optimizer.optimize(
            seton_roster=seton_df,
            opponent_roster=opponent_df,
        )
        elapsed = (time.time() - start) * 1000

        # Extract total score
        score = result.get("total_score", 0) if isinstance(result, dict) else 0

        return float(score), elapsed

    except Exception as e:
        print(f"  ⚠️ AquaOptimizer error: {e}")
        return 0.0, 0.0


def run_single_backtest(meet_id: int, meet_name: str, profile: str) -> BacktestResult:
    """Run backtest for a single meet."""
    result = BacktestResult(
        meet_id=meet_id,
        meet_name=meet_name,
        profile=profile,
    )

    print(f"\n{'=' * 60}")
    print(f"BACKTEST: {meet_name}")
    print(f"Profile: {profile}")
    print(f"{'=' * 60}")

    # Load data
    entries_df, error = load_meet_data(meet_id)
    if error:
        result.error = error
        print(f"  ❌ Error: {error}")
        return result

    if len(entries_df) == 0:
        result.error = "No entries found"
        print("  ❌ No entries found")
        return result

    # Convert to championship format
    entries = entries_to_championship_format(entries_df)
    result.entries = len(entries)
    result.teams = len(set(e.team for e in entries))

    print(f"  📊 Entries: {result.entries}, Teams: {result.teams}")

    # Get actual score if available
    if "ACTUAL_POINTS" in entries_df.columns:
        result.actual_score = (
            entries_df["ACTUAL_POINTS"].iloc[0] if len(entries_df) > 0 else 0
        )
        print(f"  📈 Actual Seton Score: {result.actual_score}")

    # Run Gurobi
    print("  🔧 Running Gurobi MILP...")
    result.gurobi_score, result.gurobi_time_ms = run_gurobi_backtest(entries, profile)
    print(f"     Score: {result.gurobi_score:.0f}, Time: {result.gurobi_time_ms:.0f}ms")

    # Run AquaOptimizer
    print("  🌊 Running AquaOptimizer (Nash+Beam)...")
    result.aqua_score, result.aqua_time_ms = run_aqua_backtest(entries, profile)
    print(f"     Score: {result.aqua_score:.0f}, Time: {result.aqua_time_ms:.0f}ms")

    # Determine winner
    if result.gurobi_score > result.aqua_score:
        result.winner = "Gurobi"
    elif result.aqua_score > result.gurobi_score:
        result.winner = "AquaOptimizer"
    else:
        result.winner = "Tie"

    print(
        f"  🏆 Winner: {result.winner} ({abs(result.gurobi_score - result.aqua_score):.0f} pts diff)"
    )

    return result


def generate_summary_report(results: list[BacktestResult]) -> str:
    """Generate markdown summary report."""
    lines = [
        "# Championship Backtest Results",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Summary",
        "",
    ]

    # Count wins
    gurobi_wins = sum(1 for r in results if r.winner == "Gurobi")
    aqua_wins = sum(1 for r in results if r.winner == "AquaOptimizer")
    ties = sum(1 for r in results if r.winner == "Tie")
    errors = sum(1 for r in results if r.error)

    lines.extend(
        [
            "| Metric | Value |",
            "|--------|-------|",
            f"| Total Meets | {len(results)} |",
            f"| Gurobi Wins | **{gurobi_wins}** |",
            f"| AquaOptimizer Wins | **{aqua_wins}** |",
            f"| Ties | {ties} |",
            f"| Errors | {errors} |",
            "",
            "## Detailed Results",
            "",
            "| Meet | Profile | Gurobi | Aqua | Diff | Winner | Time (G/A) |",
            "|------|---------|--------|------|------|--------|------------|",
        ]
    )

    for r in results:
        if r.error:
            lines.append(
                f"| {r.meet_name} | {r.profile} | ❌ | ❌ | - | Error: {r.error} | - |"
            )
        else:
            diff = r.gurobi_score - r.aqua_score
            diff_str = f"+{diff:.0f}" if diff > 0 else f"{diff:.0f}"
            lines.append(
                f"| {r.meet_name} | {r.profile} | "
                f"{r.gurobi_score:.0f} | {r.aqua_score:.0f} | "
                f"{diff_str} | **{r.winner}** | "
                f"{r.gurobi_time_ms:.0f}ms / {r.aqua_time_ms:.0f}ms |"
            )

    # Speed comparison
    total_gurobi_time = sum(r.gurobi_time_ms for r in results if not r.error)
    total_aqua_time = sum(r.aqua_time_ms for r in results if not r.error)

    lines.extend(
        [
            "",
            "## Performance",
            "",
            f"- **Gurobi Total Time:** {total_gurobi_time / 1000:.1f}s",
            f"- **AquaOptimizer Total Time:** {total_aqua_time / 1000:.1f}s",
            f"- **Speed Ratio:** {total_gurobi_time / total_aqua_time:.1f}x"
            if total_aqua_time > 0
            else "",
            "",
            "## Scoring Profiles Used",
            "",
            "- **VCAC 12-place:** 16-13-12-11-10-9-7-5-4-3-2-1 (relay 2×)",
            "- **VISAA 16-place:** 20-17-16-15-14-13-12-11-9-7-6-5-4-3-2-1 (relay 2×)",
        ]
    )

    return "\n".join(lines)


def main():
    """Run all championship backtests."""
    print("=" * 70)
    print("CHAMPIONSHIP BACKTEST: Gurobi vs AquaOptimizer")
    print("Correct Scoring Profiles Applied")
    print("=" * 70)

    results: list[BacktestResult] = []

    for meet_id, meet_name, profile in CHAMPIONSHIP_MEETS:
        try:
            result = run_single_backtest(meet_id, meet_name, profile)
            results.append(result)
        except Exception as e:
            print(f"\n❌ Fatal error for {meet_name}: {e}")
            results.append(
                BacktestResult(
                    meet_id=meet_id,
                    meet_name=meet_name,
                    profile=profile,
                    error=str(e),
                )
            )

    # Generate report
    print("\n" + "=" * 70)
    print("GENERATING REPORT...")
    print("=" * 70)

    report = generate_summary_report(results)

    # Save to file
    output_dir = Path(__file__).parent.parent / "data" / "backtest"
    output_dir.mkdir(parents=True, exist_ok=True)

    report_path = output_dir / "championship_comparison_report.md"
    report_path.write_text(report)
    print(f"📝 Report saved: {report_path}")

    # Save CSV
    csv_path = output_dir / "championship_comparison_results.csv"
    pd.DataFrame(
        [
            {
                "meet_id": r.meet_id,
                "meet_name": r.meet_name,
                "profile": r.profile,
                "gurobi_score": r.gurobi_score,
                "aqua_score": r.aqua_score,
                "gurobi_time_ms": r.gurobi_time_ms,
                "aqua_time_ms": r.aqua_time_ms,
                "winner": r.winner,
                "entries": r.entries,
                "teams": r.teams,
                "error": r.error,
            }
            for r in results
        ]
    ).to_csv(csv_path, index=False)
    print(f"📊 CSV saved: {csv_path}")

    # Print summary
    print("\n" + report)

    return results


if __name__ == "__main__":
    main()
