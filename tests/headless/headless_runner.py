"""
Headless Test Runner for AquaForge

High-performance batch testing framework for:
- Multi-configuration strategy testing
- Team vs team simulations
- Backtesting with historical data
- Forward testing validation

Features:
- Parallel execution
- Parquet result storage for fast analysis
- Configuration matrix support
- Automatic data merge from all sources
"""

import asyncio
import itertools
import logging

# Project imports
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from swim_ai_reflex.backend.services.optimization_service import optimization_service
from swim_ai_reflex.backend.services.unified_data_service import get_data_service

logger = logging.getLogger(__name__)


# ============================================================================
# DATA CONTRACTS
# ============================================================================


@dataclass
class TestConfiguration:
    """Single test configuration."""

    name: str
    seton_team: str = "SST"
    opponent_team: str = "TCS"
    strategy: str = "gurobi"  # gurobi, heuristic, greedy
    gender: Optional[str] = None  # M, F, or None for both
    events: Optional[List[str]] = None  # Specific events or None for all
    enforce_fatigue: bool = False
    max_entries_per_event: int = 4
    max_events_per_swimmer: int = 2

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "seton_team": self.seton_team,
            "opponent_team": self.opponent_team,
            "strategy": self.strategy,
            "gender": self.gender,
            "enforce_fatigue": self.enforce_fatigue,
        }


@dataclass
class TestResult:
    """Result from a single test run."""

    config: TestConfiguration
    seton_score: float
    opponent_score: float
    margin: float
    winner: str
    execution_time_ms: float
    success: bool
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            **self.config.to_dict(),
            "seton_score": self.seton_score,
            "opponent_score": self.opponent_score,
            "margin": self.margin,
            "winner": self.winner,
            "execution_time_ms": self.execution_time_ms,
            "success": self.success,
            "error": self.error,
            "timestamp": self.timestamp,
        }


@dataclass
class BatchResult:
    """Results from a batch of tests."""

    results: List[TestResult]
    total_time_ms: float
    success_count: int
    failure_count: int

    def to_dataframe(self) -> pd.DataFrame:
        """Convert results to DataFrame for analysis."""
        return pd.DataFrame([r.to_dict() for r in self.results])

    def save_parquet(self, path: Path) -> None:
        """Save results to parquet for fast future loading."""
        df = self.to_dataframe()
        df.to_parquet(path, index=False)
        logger.info(f"Saved {len(self.results)} results to {path}")

    def print_summary(self) -> None:
        """Print human-readable summary."""
        print("\n" + "=" * 70)
        print("HEADLESS TEST BATCH SUMMARY")
        print("=" * 70)
        print(f"Total tests: {len(self.results)}")
        print(f"Passed: {self.success_count}")
        print(f"Failed: {self.failure_count}")
        print(f"Total time: {self.total_time_ms:.0f}ms")

        if self.results:
            df = self.to_dataframe()

            # Win/loss summary by Seton
            wins = len(df[df["winner"] == "Seton"])
            losses = len(df[df["winner"] != "Seton"])
            print(f"\nSeton Record: {wins}W - {losses}L")

            # Average margin
            avg_margin = df["margin"].mean()
            print(f"Average Margin: {avg_margin:.1f} points")

            # Strategy comparison
            if "strategy" in df.columns:
                print("\nBy Strategy:")
                for strat, grp in df.groupby("strategy"):
                    avg = grp["seton_score"].mean()
                    print(f"  {strat}: {avg:.1f} avg Seton score")

        print("=" * 70 + "\n")


# ============================================================================
# CONFIGURATION MATRIX BUILDER
# ============================================================================


class ConfigurationMatrix:
    """Build test configurations from parameter combinations."""

    def __init__(self):
        self.seton_teams: List[str] = ["SST"]
        self.opponent_teams: List[str] = []
        self.strategies: List[str] = ["gurobi"]
        self.genders: List[Optional[str]] = [None]
        self.enforce_fatigue_options: List[bool] = [False]

    def with_seton_teams(self, teams: List[str]) -> "ConfigurationMatrix":
        self.seton_teams = teams
        return self

    def with_opponents(self, teams: List[str]) -> "ConfigurationMatrix":
        self.opponent_teams = teams
        return self

    def with_strategies(self, strategies: List[str]) -> "ConfigurationMatrix":
        self.strategies = strategies
        return self

    def with_genders(self, genders: List[Optional[str]]) -> "ConfigurationMatrix":
        self.genders = genders
        return self

    def with_fatigue_options(self, options: List[bool]) -> "ConfigurationMatrix":
        self.enforce_fatigue_options = options
        return self

    def build(self) -> List[TestConfiguration]:
        """Generate all configuration combinations."""
        configs = []

        # Use all available teams as opponents if not specified
        if not self.opponent_teams:
            data_service = get_data_service()
            self.opponent_teams = [
                t for t in data_service.get_all_teams() if t not in self.seton_teams
            ]

        for seton, opponent, strategy, gender, fatigue in itertools.product(
            self.seton_teams,
            self.opponent_teams,
            self.strategies,
            self.genders,
            self.enforce_fatigue_options,
        ):
            name = f"{seton}_vs_{opponent}_{strategy}"
            if gender:
                name += f"_{gender}"
            if fatigue:
                name += "_fatigue"

            configs.append(
                TestConfiguration(
                    name=name,
                    seton_team=seton,
                    opponent_team=opponent,
                    strategy=strategy,
                    gender=gender,
                    enforce_fatigue=fatigue,
                )
            )

        return configs


# ============================================================================
# HEADLESS TEST RUNNER
# ============================================================================


class HeadlessTestRunner:
    """
    High-performance headless test runner.

    Runs optimization tests without UI, storing results in parquet.
    Supports parallel execution and batch processing.
    """

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or Path("tests/headless/results")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.data_service = get_data_service()

    async def run_single(self, config: TestConfiguration) -> TestResult:
        """Run a single test configuration."""
        start = time.perf_counter()

        try:
            # Get data from unified service
            seton_data = self.data_service.get_team_data(config.seton_team)
            opponent_data = self.data_service.get_team_data(config.opponent_team)

            if not seton_data or not seton_data.times:
                return TestResult(
                    config=config,
                    seton_score=0,
                    opponent_score=0,
                    margin=0,
                    winner="N/A",
                    execution_time_ms=(time.perf_counter() - start) * 1000,
                    success=False,
                    error=f"No data for {config.seton_team}",
                )

            if not opponent_data or not opponent_data.times:
                return TestResult(
                    config=config,
                    seton_score=0,
                    opponent_score=0,
                    margin=0,
                    winner="N/A",
                    execution_time_ms=(time.perf_counter() - start) * 1000,
                    success=False,
                    error=f"No data for {config.opponent_team}",
                )

            # Convert to DataFrames
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
                    for t in opponent_data.times
                ]
            )

            # Filter by gender if specified
            if config.gender:
                seton_df = seton_df[seton_df["gender"] == config.gender]
                opponent_df = opponent_df[opponent_df["gender"] == config.gender]

            # Run optimization
            result = await optimization_service.predict_best_lineups(
                seton_roster=seton_df,
                opponent_roster=opponent_df,
                method=config.strategy,
                max_iters=1000,
                enforce_fatigue=config.enforce_fatigue,
                use_cache=False,
            )

            elapsed = (time.perf_counter() - start) * 1000

            if not result.get("success"):
                return TestResult(
                    config=config,
                    seton_score=0,
                    opponent_score=0,
                    margin=0,
                    winner="Error",
                    execution_time_ms=elapsed,
                    success=False,
                    error=result.get("message", "Unknown error"),
                )

            data = result["data"]
            seton_score = data["seton_score"]
            opponent_score = data["opponent_score"]
            margin = abs(seton_score - opponent_score)
            winner = "Seton" if seton_score > opponent_score else config.opponent_team

            return TestResult(
                config=config,
                seton_score=seton_score,
                opponent_score=opponent_score,
                margin=margin,
                winner=winner,
                execution_time_ms=elapsed,
                success=True,
                details=data.get("details"),
            )

        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            logger.error(f"Test failed for {config.name}: {e}")
            return TestResult(
                config=config,
                seton_score=0,
                opponent_score=0,
                margin=0,
                winner="Error",
                execution_time_ms=elapsed,
                success=False,
                error=str(e),
            )

    async def run_batch(
        self,
        configs: List[TestConfiguration],
        parallel: bool = True,
        max_concurrent: int = 4,
    ) -> BatchResult:
        """Run a batch of test configurations."""
        start = time.perf_counter()
        results: List[TestResult] = []

        if parallel:
            # Run in parallel with concurrency limit
            semaphore = asyncio.Semaphore(max_concurrent)

            async def run_with_semaphore(cfg: TestConfiguration) -> TestResult:
                async with semaphore:
                    return await self.run_single(cfg)

            results = await asyncio.gather(*[run_with_semaphore(c) for c in configs])
        else:
            # Run sequentially
            for cfg in configs:
                result = await self.run_single(cfg)
                results.append(result)
                print(
                    f"  ✓ {cfg.name}: {result.seton_score:.0f}-{result.opponent_score:.0f}"
                )

        elapsed = (time.perf_counter() - start) * 1000
        success_count = sum(1 for r in results if r.success)

        return BatchResult(
            results=list(results),
            total_time_ms=elapsed,
            success_count=success_count,
            failure_count=len(results) - success_count,
        )

    async def run_matrix(self, matrix: ConfigurationMatrix) -> BatchResult:
        """Run all configurations in a matrix."""
        configs = matrix.build()
        print(f"\n🧪 Running {len(configs)} test configurations...")
        result = await self.run_batch(configs)

        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result.save_parquet(self.output_dir / f"batch_{timestamp}.parquet")
        result.print_summary()

        return result


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================


async def run_quick_test() -> BatchResult:
    """Run a quick test with default settings."""
    runner = HeadlessTestRunner()

    matrix = (
        ConfigurationMatrix().with_opponents(["TCS", "ICS"]).with_strategies(["gurobi"])
    )

    return await runner.run_matrix(matrix)


async def run_full_matrix() -> BatchResult:
    """Run full test matrix across all teams and strategies."""
    runner = HeadlessTestRunner()

    matrix = (
        ConfigurationMatrix()
        .with_opponents(["TCS", "ICS", "OAK", "DJO", "FCS", "BI", "PVI"])
        .with_strategies(["gurobi"])
        .with_genders([None, "F", "M"])
    )

    return await runner.run_matrix(matrix)


# ============================================================================
# CLI INTERFACE
# ============================================================================


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AquaForge Headless Test Runner")
    parser.add_argument("--quick", action="store_true", help="Run quick test")
    parser.add_argument("--full", action="store_true", help="Run full matrix")
    parser.add_argument("--opponent", type=str, help="Single opponent team code")
    args = parser.parse_args()

    if args.quick:
        asyncio.run(run_quick_test())
    elif args.full:
        asyncio.run(run_full_matrix())
    elif args.opponent:

        async def single():
            runner = HeadlessTestRunner()
            cfg = TestConfiguration(
                name=f"SST_vs_{args.opponent}",
                opponent_team=args.opponent,
            )
            result = await runner.run_single(cfg)
            print(f"\n{'✅' if result.success else '❌'} {result.config.name}")
            print(f"   Seton: {result.seton_score:.0f}")
            print(f"   Opponent: {result.opponent_score:.0f}")
            print(f"   Winner: {result.winner}")

        asyncio.run(single())
    else:
        print("Usage: python headless_runner.py [--quick | --full | --opponent CODE]")
