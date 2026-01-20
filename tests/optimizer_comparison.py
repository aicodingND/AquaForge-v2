"""
Optimizer Comparison Harness

Run Gurobi and AquaOptimizer side-by-side to compare results.

Usage:
    python tests/optimizer_comparison.py --scenarios 10
"""

import asyncio
import logging
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from swim_ai_reflex.backend.core.rules import VISAADualRules
from swim_ai_reflex.backend.services.unified_data_service import get_data_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ComparisonResult:
    """Result from comparing two optimizers."""

    scenario: str
    gurobi_seton: float
    gurobi_opponent: float
    gurobi_time_ms: float
    aqua_seton: float
    aqua_opponent: float
    aqua_time_ms: float

    @property
    def gurobi_margin(self) -> float:
        return self.gurobi_seton - self.gurobi_opponent

    @property
    def aqua_margin(self) -> float:
        return self.aqua_seton - self.aqua_opponent

    @property
    def winner(self) -> str:
        if self.aqua_margin > self.gurobi_margin:
            return "AquaOptimizer"
        elif self.gurobi_margin > self.aqua_margin:
            return "Gurobi"
        return "Tie"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario": self.scenario,
            "gurobi_seton": self.gurobi_seton,
            "gurobi_opponent": self.gurobi_opponent,
            "gurobi_margin": self.gurobi_margin,
            "gurobi_time_ms": self.gurobi_time_ms,
            "aqua_seton": self.aqua_seton,
            "aqua_opponent": self.aqua_opponent,
            "aqua_margin": self.aqua_margin,
            "aqua_time_ms": self.aqua_time_ms,
            "winner": self.winner,
        }


class OptimizerComparison:
    """Compare Gurobi and AquaOptimizer side-by-side."""

    def __init__(self):
        self.data_service = get_data_service()
        self.rules = VISAADualRules()
        self.results: List[ComparisonResult] = []

    async def run_gurobi(
        self, seton_df: pd.DataFrame, opponent_df: pd.DataFrame
    ) -> Tuple[float, float, float]:
        """Run Gurobi optimizer and return (seton_score, opponent_score, time_ms)."""
        try:
            from swim_ai_reflex.backend.core.strategies.gurobi_strategy import (
                GurobiStrategy,
            )

            start = time.perf_counter()
            strategy = GurobiStrategy()

            _, _, totals, _ = strategy.optimize(seton_df, opponent_df, None, self.rules)

            elapsed = (time.perf_counter() - start) * 1000
            return totals.get("seton", 0), totals.get("opponent", 0), elapsed

        except Exception as e:
            logger.warning(f"Gurobi failed: {e}")
            return 0, 0, 0

    async def run_aqua(
        self, seton_df: pd.DataFrame, opponent_df: pd.DataFrame
    ) -> Tuple[float, float, float]:
        """Run AquaOptimizer and return (seton_score, opponent_score, time_ms)."""
        try:
            from swim_ai_reflex.backend.core.strategies.aqua_optimizer import (
                create_aqua_optimizer,
            )

            start = time.perf_counter()
            optimizer = create_aqua_optimizer()

            _, _, totals, _ = optimizer.optimize(
                seton_df, opponent_df, None, self.rules
            )

            elapsed = (time.perf_counter() - start) * 1000
            return totals.get("seton", 0), totals.get("opponent", 0), elapsed

        except Exception as e:
            logger.error(f"AquaOptimizer failed: {e}")
            import traceback

            traceback.print_exc()
            return 0, 0, 0

    async def compare_scenario(
        self,
        scenario_name: str,
        seton_df: pd.DataFrame,
        opponent_df: pd.DataFrame,
    ) -> ComparisonResult:
        """Compare both optimizers on a single scenario."""
        logger.info(f"Comparing: {scenario_name}")

        # Run both optimizers
        gurobi_result = await self.run_gurobi(seton_df.copy(), opponent_df.copy())
        aqua_result = await self.run_aqua(seton_df.copy(), opponent_df.copy())

        result = ComparisonResult(
            scenario=scenario_name,
            gurobi_seton=gurobi_result[0],
            gurobi_opponent=gurobi_result[1],
            gurobi_time_ms=gurobi_result[2],
            aqua_seton=aqua_result[0],
            aqua_opponent=aqua_result[1],
            aqua_time_ms=aqua_result[2],
        )

        self.results.append(result)
        return result

    async def run_all_teams(self) -> List[ComparisonResult]:
        """Run comparison across all team matchups."""
        teams = self.data_service.get_all_teams()
        seton_team = "SST"

        if seton_team not in teams:
            seton_team = teams[0] if teams else None

        if not seton_team:
            logger.error("No teams available")
            return []

        seton_data = self.data_service.get_team_data(seton_team)
        if not seton_data or not seton_data.times:
            logger.error(f"No data for {seton_team}")
            return []

        # Convert to DataFrame
        seton_df = pd.DataFrame(
            [
                {
                    "swimmer": t.swimmer,
                    "event": t.event,
                    "time": t.time,
                    "team": t.team,
                    "grade": t.grade or 12,
                    "gender": t.gender or "F",
                    "is_relay": False,
                }
                for t in seton_data.times
            ]
        )

        # Run against each opponent
        opponents = [t for t in teams if t != seton_team]

        for opponent_team in opponents[:7]:  # Limit to 7 opponents
            opp_data = self.data_service.get_team_data(opponent_team)
            if not opp_data or not opp_data.times:
                continue

            opponent_df = pd.DataFrame(
                [
                    {
                        "swimmer": t.swimmer,
                        "event": t.event,
                        "time": t.time,
                        "team": t.team,
                        "grade": t.grade or 12,
                        "gender": t.gender or "F",
                        "is_relay": False,
                    }
                    for t in opp_data.times
                ]
            )

            await self.compare_scenario(
                f"{seton_team} vs {opponent_team}",
                seton_df,
                opponent_df,
            )

        return self.results

    def print_summary(self) -> None:
        """Print comparison summary."""
        if not self.results:
            print("No results to summarize")
            return

        print("\n" + "=" * 80)
        print("OPTIMIZER COMPARISON SUMMARY")
        print("=" * 80)

        # Results table
        print(f"\n{'Scenario':<25} {'Gurobi':^15} {'Aqua':^15} {'Winner':^15}")
        print("-" * 80)

        for r in self.results:
            gurobi_str = f"{r.gurobi_margin:+.0f}" if r.gurobi_seton > 0 else "N/A"
            aqua_str = f"{r.aqua_margin:+.0f}"
            print(f"{r.scenario:<25} {gurobi_str:^15} {aqua_str:^15} {r.winner:^15}")

        # Summary stats
        aqua_wins = sum(1 for r in self.results if r.winner == "AquaOptimizer")
        gurobi_wins = sum(1 for r in self.results if r.winner == "Gurobi")
        ties = sum(1 for r in self.results if r.winner == "Tie")

        print("\n" + "-" * 80)
        print(f"AquaOptimizer Wins: {aqua_wins}")
        print(f"Gurobi Wins: {gurobi_wins}")
        print(f"Ties: {ties}")

        # Timing comparison
        aqua_times = [r.aqua_time_ms for r in self.results if r.aqua_time_ms > 0]
        gurobi_times = [r.gurobi_time_ms for r in self.results if r.gurobi_time_ms > 0]

        if aqua_times and gurobi_times:
            print("\nAverage Time:")
            print(f"  Gurobi: {sum(gurobi_times) / len(gurobi_times):.0f}ms")
            print(f"  Aqua:   {sum(aqua_times) / len(aqua_times):.0f}ms")

        print("=" * 80 + "\n")

    def save_results(self, path: Path) -> None:
        """Save results to parquet."""
        df = pd.DataFrame([r.to_dict() for r in self.results])
        df.to_parquet(path, index=False)
        logger.info(f"Saved {len(self.results)} results to {path}")


async def main():
    """Run optimizer comparison."""
    import argparse

    parser = argparse.ArgumentParser(description="Compare Gurobi vs AquaOptimizer")
    parser.add_argument("--output", type=str, default="comparison_results.parquet")
    args = parser.parse_args()

    comparison = OptimizerComparison()
    await comparison.run_all_teams()
    comparison.print_summary()

    output_path = Path("tests/headless/results") / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    comparison.save_results(output_path)


if __name__ == "__main__":
    asyncio.run(main())
