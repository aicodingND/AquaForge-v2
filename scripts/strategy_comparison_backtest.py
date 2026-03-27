#!/usr/bin/env python3
"""
Championship Strategy Comparison Backtest.

Compares Gurobi MILP vs AquaOptimizer (Beam Search + Nash) on championship meets
using IDENTICAL scoring profiles for fair comparison.

Strategies:
- Gurobi: MILP optimization via ChampionshipGurobiStrategy
- AquaOptimizer: Beam Search + Nash Equilibrium + Simulated Annealing

Scoring Profiles (corrected 2026-01-21):
- vcac_championship: 12-place, Individual 16-13-12-11-10-9-7-5-4-3-2-1, Relay 2x
- visaa_championship: 16-place, Individual 20-17-16-15-14-13-12-11-9-7-6-5-4-3-2-1, Relay 2x
"""

import sys
import time
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.championship_backtest import (
    CHAMPIONSHIP_MEETS,
    get_actual_team_standings,
    load_mdb_championship_data,
    validate_historical_lineup,
)
from swim_ai_reflex.backend.core.strategies.aqua_optimizer import (
    AquaOptimizer,
    FatigueModel,
    Lineup,
    ScoringEngine,
    ScoringProfile,
)
from swim_ai_reflex.backend.core.strategies.championship_strategy import (
    ChampionshipEntry,
    ChampionshipGurobiStrategy,
)
from swim_ai_reflex.backend.utils.mdb_connector import MDBConnector

# ============================================================================
# CONFIGURATION
# ============================================================================

MDB_PATH = Path("data/real_exports/SSTdata.mdb")
OUTPUT_DIR = Path("data/backtest")


@dataclass
class ComparisonResult:
    """Single meet comparison result."""

    meet_id: int
    meet_name: str
    profile: str

    # Actual results
    actual_seton_score: float
    actual_seton_rank: int
    actual_teams: int

    # Gurobi results
    gurobi_score: float
    gurobi_time_ms: float
    gurobi_vs_coach: float  # Advantage over coach (legal)

    # AquaOptimizer results
    aqua_score: float
    aqua_time_ms: float
    aqua_vs_coach: float  # Advantage over coach (legal)

    # Coach baseline
    coach_legal_score: float
    coach_fatigue_score: float  # Coach (Legal) + Fatigue Model
    coach_illegal_score: float  # Coach with Errors
    coach_violations: int

    # Comparison
    winner: str  # "gurobi", "aqua", or "tie"
    score_difference: float


def get_scoring_profile(profile_name: str) -> ScoringProfile:
    """Get the appropriate ScoringProfile for a meet type."""
    profile_name = profile_name.lower()

    if "visaa" in profile_name and "championship" in profile_name:
        return ScoringProfile.visaa_championship()
    elif "vcac" in profile_name or "championship" in profile_name:
        return ScoringProfile.vcac_championship()
    else:
        return ScoringProfile.visaa_dual()


def entries_to_dataframe(entries: list[dict], team_name: str = None) -> pd.DataFrame:
    """Convert psych sheet entries to DataFrame format."""
    if not entries:
        return pd.DataFrame(
            columns=["swimmer", "event", "time", "team", "gender", "grade"]
        )

    df = pd.DataFrame(entries)

    if team_name:
        df = df[df["team"].str.lower().str.contains(team_name.lower(), na=False)].copy()

    if df.empty:
        return pd.DataFrame(
            columns=["swimmer", "event", "time", "team", "gender", "grade"]
        )

    df = df.rename(columns={"swimmer_name": "swimmer", "seed_time": "time"})

    if "grade" not in df.columns:
        df["grade"] = 12
    if "is_relay" not in df.columns:
        df["is_relay"] = df["event"].str.contains("Relay", case=False, na=False)

    return df


def entries_to_championship_entries(entries: list[dict]) -> list[ChampionshipEntry]:
    """Convert dict entries to ChampionshipEntry objects for Gurobi."""
    champ_entries = []
    for e in entries:
        if e.get("seed_time", 0) <= 0:
            continue
        champ_entries.append(
            ChampionshipEntry(
                swimmer_name=e.get("swimmer_name", "Unknown"),
                team=e.get("team", "Unknown"),
                event=e.get("event", ""),
                seed_time=float(e.get("seed_time", 0)),
                gender=e.get("gender", ""),
                grade=str(e.get("grade", "12")),
            )
        )
    return champ_entries


def run_comparison(
    meet_id: int, meet_name: str, profile: str
) -> ComparisonResult | None:
    """Run single meet comparison between Gurobi and AquaOptimizer."""
    print(f"\n{'=' * 70}")
    print(f"COMPARING: {meet_name}")
    print(f"Profile: {profile}")
    print("=" * 70)

    try:
        # Load MDB data
        connector = MDBConnector(str(MDB_PATH))
        entries, team_map, meet_meta = load_mdb_championship_data(connector, meet_id)

        if not entries:
            print("! No entries found")
            return None

        # Get actual standings
        actual_standings = get_actual_team_standings(connector, meet_id, team_map)

        # Find Seton
        teams = set(e["team"] for e in entries)
        seton_team = next((t for t in teams if "seton" in t.lower()), None)

        if not seton_team:
            print("! Seton not in meet")
            return None

        # Calculate actual Seton rank
        sorted_actual = sorted(actual_standings.items(), key=lambda x: -x[1])
        actual_seton_rank = next(
            (
                i
                for i, (t, _) in enumerate(sorted_actual, 1)
                if seton_team.lower() in t.lower()
            ),
            0,
        )
        actual_seton_score = actual_standings.get(seton_team, 0)

        # Coach baseline (Legal and Illegal)
        coach_analysis = validate_historical_lineup(entries, seton_team, profile)
        coach_legal_score = coach_analysis.get("legal_score", 0)
        coach_illegal_score = coach_analysis.get("illegal_score", 0)
        coach_violations = len(coach_analysis.get("violations", []))
        coach_legal_entries = coach_analysis.get("legal_entries", [])

        # Calculate Coach Fatigue Score (to compare apples-to-apples with Aqua)
        coach_fatigue_score = 0.0
        if coach_legal_entries:
            try:
                # 1. Build Lineup from Legal Entries
                coach_assignments = {}
                for e in coach_legal_entries:
                    if seton_team.lower() in e["team"].lower():
                        s = e["swimmer_name"]
                        ev = e["event"]
                        if s not in coach_assignments:
                            coach_assignments[s] = set()
                        coach_assignments[s].add(ev)

                coach_lineup = Lineup(assignments=coach_assignments)

                # 2. Setup Engine
                scoring_profile = get_scoring_profile(profile)
                fatigue_engine = ScoringEngine(
                    scoring_profile, FatigueModel(enabled=True)
                )

                # 3. Prepare DataFrames
                # We need a roster DF that covers all Coach assignments
                coach_roster_df = entries_to_dataframe(coach_legal_entries, seton_team)

                # And opponents
                opp_entries = [
                    e for e in entries if seton_team.lower() not in e["team"].lower()
                ]
                opponent_df_for_coach = entries_to_dataframe(opp_entries)

                # 4. Score
                all_events = sorted(
                    list(
                        set(coach_roster_df["event"].unique())
                        | set(opponent_df_for_coach["event"].unique())
                    )
                )
                c_score, _, _ = fatigue_engine.score_lineup(
                    coach_lineup, coach_roster_df, opponent_df_for_coach, all_events
                )
                coach_fatigue_score = c_score
            except Exception as e:
                print(f"! Failed to calculate fatigue score: {e}")
                coach_fatigue_score = coach_legal_score  # Fallback

        print(f"▸ Entries: {len(entries)}, Teams: {len(teams)}")
        print(f"✗ Coach Score (w/ Errors): {coach_illegal_score:.1f}")
        print(
            f"▸ Coach Score (Legal): {coach_legal_score:.1f} ({coach_violations} violations)"
        )
        print(f"Coach Score (Fatigue): {coach_fatigue_score:.1f} (Apples-to-Apples)")
        print(f"Actual Score: {actual_seton_score:.1f} (Rank #{actual_seton_rank})")

        # --------------- GUROBI OPTIMIZATION ---------------
        print("\n→ Running Gurobi MILP...")
        gurobi_score = 0.0
        gurobi_time_ms = 0.0

        try:
            gurobi_strategy = ChampionshipGurobiStrategy(meet_profile=profile)
            champ_entries = entries_to_championship_entries(entries)

            start = time.time()
            gurobi_result = gurobi_strategy.optimize_entries(
                all_entries=champ_entries,
                target_team=seton_team,
                time_limit=60,
            )
            gurobi_time_ms = (time.time() - start) * 1000

            gurobi_score = gurobi_result.total_points if gurobi_result else 0.0
            print(f"Gurobi Score: {gurobi_score:.1f} ({gurobi_time_ms:.0f}ms)")
        except Exception as e:
            print(f"✗ Gurobi failed: {e}")

        # --------------- AQUAOPTIMIZER ---------------
        print("\n▸ Running AquaOptimizer (Nash+Beam)...")
        aqua_score = 0.0
        aqua_time_ms = 0.0

        try:
            scoring_profile = get_scoring_profile(profile)

            optimizer = AquaOptimizer(
                profile=scoring_profile,
                fatigue=FatigueModel(enabled=True),
                quality_mode="fast",  # Faster execution for backtests
                nash_iterations=2,  # Reduced iterations
                use_parallel=True,
            )

            seton_df = entries_to_dataframe(entries, seton_team)
            opponent_df = entries_to_dataframe(
                [e for e in entries if e["team"] != seton_team]
            )

            start = time.time()
            lineup_df, scored_df, totals, details = optimizer.optimize(
                seton_df, opponent_df, None, None
            )
            aqua_time_ms = (time.time() - start) * 1000

            aqua_score = totals.get("seton", 0) if totals else 0.0
            print(f"AquaOptimizer Score: {aqua_score:.1f} ({aqua_time_ms:.0f}ms)")
        except Exception as e:
            print(f"✗ AquaOptimizer failed: {e}")
            import traceback

            traceback.print_exc()

        # --------------- COMPARISON ---------------
        gurobi_vs_coach = gurobi_score - coach_legal_score
        aqua_vs_coach = aqua_score - coach_legal_score
        score_diff = gurobi_score - aqua_score

        if abs(score_diff) < 0.5:
            winner = "tie"
        elif gurobi_score > aqua_score:
            winner = "gurobi"
        else:
            winner = "aqua"

        print(f"\nWINNER: {winner.upper()}")
        print(
            f"Gurobi vs Coach: {'+' if gurobi_vs_coach >= 0 else ''}{gurobi_vs_coach:.1f}"
        )
        print(f"Aqua vs Coach: {'+' if aqua_vs_coach >= 0 else ''}{aqua_vs_coach:.1f}")
        print(f"Difference: {score_diff:.1f}")

        return ComparisonResult(
            meet_id=meet_id,
            meet_name=meet_name,
            profile=profile,
            actual_seton_score=actual_seton_score,
            actual_seton_rank=actual_seton_rank,
            actual_teams=len(teams),
            gurobi_score=gurobi_score,
            gurobi_time_ms=gurobi_time_ms,
            gurobi_vs_coach=gurobi_vs_coach,
            aqua_score=aqua_score,
            aqua_time_ms=aqua_time_ms,
            aqua_vs_coach=aqua_vs_coach,
            coach_legal_score=coach_legal_score,
            coach_fatigue_score=coach_fatigue_score,
            coach_illegal_score=coach_illegal_score,
            coach_violations=coach_violations,
            winner=winner,
            score_difference=score_diff,
        )

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback

        traceback.print_exc()
        return None


def main():
    """Run full comparison backtest."""
    print("\n" + "=" * 70)
    print("CHAMPIONSHIP STRATEGY COMPARISON")
    print("Gurobi MILP vs AquaOptimizer (Nash+Beam)")
    print("Comparing against: Coach (Legal) and Coach (Errors)")
    print("Corrected Scoring: VCAC 12-place, VISAA 16-place")
    print("=" * 70)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    results: list[ComparisonResult] = []

    # Slice to first 2 meets which are known to run quickly for demo
    # The others (Icebreaker) have 500+ entries and time out in backtest
    recent_meets = CHAMPIONSHIP_MEETS[:2]
    print(f"Running first {len(recent_meets)} meets for backtest...")

    for meet_id, meet_name, profile in recent_meets:
        result = run_comparison(meet_id, meet_name, profile)
        if result:
            results.append(result)

    if not results:
        print("\n! No results to compare")
        return

    # --------------- SUMMARY ---------------
    print("\n" + "=" * 70)
    print("COMPARISON SUMMARY")
    print("=" * 70)

    gurobi_wins = sum(1 for r in results if r.winner == "gurobi")
    aqua_wins = sum(1 for r in results if r.winner == "aqua")
    ties = sum(1 for r in results if r.winner == "tie")

    total_gurobi = sum(r.gurobi_score for r in results)
    total_aqua = sum(r.aqua_score for r in results)
    total_coach_legal = sum(r.coach_legal_score for r in results)
    total_coach_fatigue = sum(r.coach_fatigue_score for r in results)
    total_coach_illegal = sum(r.coach_illegal_score for r in results)

    avg_gurobi_time = sum(r.gurobi_time_ms for r in results) / len(results)
    avg_aqua_time = sum(r.aqua_time_ms for r in results) / len(results)

    print(f"\n▸ Meets Compared: {len(results)}")
    print("\nHead-to-Head Record:")
    print(f"Gurobi Wins: {gurobi_wins}")
    print(f"Aqua Wins: {aqua_wins}")
    print(f"Ties: {ties}")

    print("\n▸ Total Scores Across All Meets:")
    print(f"Coach (Errors): {total_coach_illegal:,.0f}")
    print(f"Coach (Legal): {total_coach_legal:,.0f}")
    print(f"Coach (Fatigue): {total_coach_fatigue:,.0f} (Rule Enforced)")
    print(f"Gurobi: {total_gurobi:,.0f}")
    print(f"AquaOptimizer: {total_aqua:,.0f}")

    print("\nAverage Execution Time:")
    print(f"Gurobi: {avg_gurobi_time:,.0f}ms")
    print(f"AquaOptimizer: {avg_aqua_time:,.0f}ms")

    print("\n→ Advantage Over Coach (Legal):")
    g_adv = total_gurobi - total_coach_legal
    a_adv = total_aqua - total_coach_legal
    print(f"Gurobi: {'+' if g_adv >= 0 else ''}{g_adv:,.0f}")
    print(f"AquaOptimizer: {'+' if a_adv >= 0 else ''}{a_adv:,.0f}")

    # Save CSV
    df = pd.DataFrame(results)
    csv_path = OUTPUT_DIR / "strategy_comparison_results.csv"
    df.to_csv(csv_path, index=False)
    print(f"\nResults saved to: {csv_path}")

    # Detailed table
    print("\n" + "=" * 90)
    print("DETAILED RESULTS")
    print("=" * 90)
    print(
        f"{'Meet':<30} {'Err':>6} {'Legal':>6} {'Fatig':>6} {'Act':>6} {'Rk':>3} {'Gurobi':>8} {'Aqua':>8} {'Viol':>2} {'Winner':>8}"
    )
    print("-" * 96)
    for r in results:
        print(
            f"{r.meet_name[:28]:<30} {r.coach_illegal_score:>6.0f} {r.coach_legal_score:>6.0f} {r.coach_fatigue_score:>6.0f} {r.actual_seton_score:>6.0f} {r.actual_seton_rank:>3} {r.gurobi_score:>8.0f} {r.aqua_score:>8.0f} {r.coach_violations:>2} {r.winner:>8}"
        )


if __name__ == "__main__":
    main()
