#!/usr/bin/env python3
"""
AquaOptimizer Championship Backtest Script.

Uses the custom AquaOptimizer (instead of Gurobi) to run backtests on championship
meets using CORRECT SCORING PROFILES per meet type.

Scoring Profiles (corrected 2026-01-21):
- vcac_championship: 12-place, Individual 16-13-12-11-10-9-7-5-4-3-2-1, Relay 2x
- visaa_championship: 16-place, Individual 20-17-16-15-14-13-12-11-9-7-6-5-4-3-2-1, Relay 2x
- visaa_dual: 7-place, Individual 8-6-5-4-3-2-1, Relay 10-5-3
"""

import sys
import time
from pathlib import Path
from typing import Any

import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Import shared functions from championship_backtest
from scripts.championship_backtest import (
    CHAMPIONSHIP_MEETS,
    load_mdb_championship_data,
    validate_historical_lineup,
)
from swim_ai_reflex.backend.core.strategies.aqua_optimizer import (
    ScoringProfile,
)
from swim_ai_reflex.backend.utils.mdb_connector import MDBConnector

# ============================================================================
# CONFIGURATION
# ============================================================================

MDB_PATH = Path("data/real_exports/SSTdata.mdb")
OUTPUT_DIR = Path("data/backtest")

# Profile mapping - maps meet profile strings to AquaOptimizer scoring profiles
PROFILE_MAPPING = {
    "vcac_championship": "vcac_championship",
    "visaa_championship": "vcac_championship",  # Same points structure
    "dual": "visaa_dual",
    "invitational": "vcac_championship",  # Most invitationals use championship scoring
}


def get_scoring_profile(profile_name: str) -> ScoringProfile:
    """Get the appropriate ScoringProfile for a meet type."""
    # Normalize
    profile_name = profile_name.lower()

    if "visaa" in profile_name and "championship" in profile_name:
        return ScoringProfile.visaa_championship()
    elif "vcac" in profile_name and "championship" in profile_name:
        return ScoringProfile.vcac_championship()
    elif "championship" in profile_name:
        # Default fallback for generic championship
        return ScoringProfile.vcac_championship()
    else:
        return ScoringProfile.visaa_dual()


def entries_to_dataframe(entries: list[dict], team_name: str = None) -> pd.DataFrame:
    """Convert psych sheet entries to DataFrame format for AquaOptimizer."""
    if not entries:
        return pd.DataFrame(
            columns=["swimmer", "event", "time", "team", "gender", "grade"]
        )

    df = pd.DataFrame(entries)

    # Filter by team if specified
    if team_name:
        df = df[df["team"] == team_name].copy()

    if df.empty:
        return pd.DataFrame(
            columns=["swimmer", "event", "time", "team", "gender", "grade"]
        )

    # Rename columns to match AquaOptimizer expectations
    df = df.rename(
        columns={
            "swimmer_name": "swimmer",
            "seed_time": "time",  # AquaOptimizer uses "time" column
        }
    )

    # Ensure required columns exist
    if "swimmer" not in df.columns:
        df["swimmer"] = df.get("name", "Unknown")
    if "time" not in df.columns and "seed_time" in df.columns:
        df["time"] = df["seed_time"]
    if "grade" not in df.columns:
        df["grade"] = 12
    if "is_relay" not in df.columns:
        df["is_relay"] = df["event"].str.contains("Relay", case=False, na=False)

    return df


def run_aqua_backtest(meet_id: int, meet_name: str, profile: str) -> dict[str, Any]:
    """Run AquaOptimizer backtest for a single meet with CORRECT scoring profile."""
    print(f"\n{'=' * 60}")
    print(f"AQUAOPTIMIZER BACKTEST: {meet_name}")
    print(f"Profile: {profile}")
    print(f"{'=' * 60}")

    result = {
        "meet_id": meet_id,
        "meet_name": meet_name,
        "profile": profile,
        "aqua_projected_score": 0.0,
        "aqua_opponent_score": 0.0,
        "coach_analysis": {},
        "entry_assignments": {},
        "execution_time_ms": 0,
        "entries": [],
        "meet_meta": {},
    }

    try:
        # Load MDB data
        connector = MDBConnector(str(MDB_PATH))
        entries, team_map, meet_meta = load_mdb_championship_data(connector, meet_id)
        result["meet_meta"] = meet_meta

        if not entries:
            print(f"  ⚠️ No entries found for meet {meet_id}")
            return result

        print(f"  📊 Loaded {len(entries)} entries from MDB")

        # Get unique teams
        teams = set(e["team"] for e in entries)
        print(f"  🏊 Teams: {len(teams)}")

        # Find Seton team
        seton_team = None
        for t in teams:
            if "seton" in t.lower():
                seton_team = t
                break

        if not seton_team:
            print("  ⚠️ Seton team not found in meet")
            return result

        # Convert entries to DataFrames
        seton_df = entries_to_dataframe(entries, seton_team)

        # Create opponent roster (all other teams combined)
        opponent_entries = [e for e in entries if e["team"] != seton_team]
        opponent_df = entries_to_dataframe(opponent_entries)

        if seton_df.empty:
            print("  ⚠️ No Seton entries in meet")
            return result

        print(f"  🔵 Seton swimmers: {seton_df['swimmer'].nunique()}")
        print(
            f"  🔴 Opponent swimmers: {opponent_df['swimmer'].nunique() if not opponent_df.empty else 0}"
        )

        # Get CORRECT scoring profile based on meet type
        scoring_profile = get_scoring_profile(profile)
        print(
            f"  📏 Scoring: {scoring_profile.name} - Points: {scoring_profile.individual_points[:5]}..."
        )

        # Create AquaOptimizer with MAXIMUM POWER - thorough mode + extra Nash equilibrium
        # thorough: beam_width=75, nash_iterations=6, num_seeds=15, annealing=5000
        from swim_ai_reflex.backend.core.strategies.aqua_optimizer import (
            AquaOptimizer,
            FatigueModel,
        )

        optimizer = AquaOptimizer(
            profile=scoring_profile,
            fatigue=FatigueModel(enabled=True),
            quality_mode="thorough",  # Maximum quality mode
            nash_iterations=10,  # Extra Nash equilibrium iterations for game theory optimization
            use_parallel=True,
        )
        print("  ⚔️ Mode: THOROUGH (Nash x10, 15 seeds, parallel)")

        start_time = time.time()
        lineup_df, scored_df, totals, details = optimizer.optimize(
            seton_df, opponent_df, None, None
        )
        execution_time = (time.time() - start_time) * 1000

        result["execution_time_ms"] = round(execution_time)
        result["aqua_projected_score"] = round(totals.get("seton", 0), 1)
        result["aqua_opponent_score"] = round(totals.get("opponent", 0), 1)

        # Extract assignments from lineup
        if lineup_df is not None and not lineup_df.empty:
            assignments = {}
            for _, row in lineup_df.iterrows():
                swimmer = row.get("swimmer", "")
                event = row.get("event", "")
                if swimmer and event:
                    if swimmer not in assignments:
                        assignments[swimmer] = []
                    assignments[swimmer].append(event)
            result["entry_assignments"] = assignments

        print("\n  ✅ AquaOptimizer Result:")
        print(f"     Seton Score: {totals.get('seton', 0):.1f}")
        print(f"     Opponent Score: {totals.get('opponent', 0):.1f}")
        print(f"     Execution Time: {execution_time:.0f}ms")

        # Validate coach lineup (same as championship_backtest)
        seton_entries = [e for e in entries if e["team"] == seton_team]
        result["entries"] = seton_entries
        coach_analysis = validate_historical_lineup(seton_entries, seton_team, profile)
        result["coach_analysis"] = coach_analysis

        print("\n  📋 Coach Analysis:")
        print(f"     Legal Score: {coach_analysis.get('legal_score', 0):.1f}")
        print(f"     Violations: {len(coach_analysis.get('violations', []))}")

        # Calculate advantage over coach
        advantage = result["aqua_projected_score"] - coach_analysis.get(
            "legal_score", 0
        )
        print(
            f"\n  🎯 AquaOptimizer Advantage: {'+' if advantage >= 0 else ''}{advantage:.1f} pts"
        )

    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback

        traceback.print_exc()

    return result


def main():
    """Run AquaOptimizer backtests on all championship meets."""
    print("\n" + "=" * 70)
    print("AQUAOPTIMIZER CHAMPIONSHIP BACKTEST")
    print("Custom AI Model vs Coach Decisions (2024-2026)")
    print("Using CORRECT SCORING PROFILES per meet type")
    print("=" * 70)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    results = []
    total_aqua_score = 0
    total_coach_score = 0
    total_violations = 0
    aqua_wins = 0

    for meet_id, meet_name, profile in CHAMPIONSHIP_MEETS:
        result = run_aqua_backtest(meet_id, meet_name, profile)
        results.append(result)

        # Aggregate stats
        aqua_score = result.get("aqua_projected_score", 0)
        coach_score = result.get("coach_analysis", {}).get("legal_score", 0)
        violations = len(result.get("coach_analysis", {}).get("violations", []))

        total_aqua_score += aqua_score
        total_coach_score += coach_score
        total_violations += violations

        if aqua_score > coach_score:
            aqua_wins += 1

    # Save results to CSV
    output_csv = OUTPUT_DIR / "aqua_optimizer_backtest_results.csv"
    df = pd.DataFrame(
        [
            {
                "meet_id": r["meet_id"],
                "meet_name": r["meet_name"],
                "profile": r["profile"],
                "aqua_projected_score": r["aqua_projected_score"],
                "aqua_opponent_score": r.get("aqua_opponent_score", 0),
                "coach_legal_score": r.get("coach_analysis", {}).get("legal_score", 0),
                "coach_illegal_score": r.get("coach_analysis", {}).get(
                    "illegal_score", 0
                ),
                "violations": len(r.get("coach_analysis", {}).get("violations", [])),
                "execution_time_ms": r.get("execution_time_ms", 0),
                "coach_analysis": str(r.get("coach_analysis", {})),
                "entry_assignments": str(r.get("entry_assignments", {})),
                "entries": str(r.get("entries", [])),
                "meet_meta": str(r.get("meet_meta", {})),
            }
            for r in results
        ]
    )
    df.to_csv(output_csv, index=False)

    # Summary
    print("\n" + "=" * 70)
    print("AQUAOPTIMIZER BACKTEST SUMMARY")
    print("=" * 70)
    print(f"\n📊 Meets Analyzed: {len(results)}")
    print(f"🤖 Total AquaOptimizer Score: {total_aqua_score:,.0f}")
    print(f"👨‍🏫 Total Coach Legal Score: {total_coach_score:,.0f}")
    print(f"🎯 AquaOptimizer Advantage: +{total_aqua_score - total_coach_score:,.0f}")
    print(
        f"🏆 AquaOptimizer Win Rate: {100 * aqua_wins / max(len(results), 1):.0f}% ({aqua_wins}/{len(results)})"
    )
    print(f"⚠️ Total Violations: {total_violations}")
    print(f"\n💾 Results saved to: {output_csv}")

    return results


if __name__ == "__main__":
    main()
