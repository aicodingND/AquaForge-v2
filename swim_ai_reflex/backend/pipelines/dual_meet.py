"""
Dual Meet Pipeline

Pipeline for head-to-head 2-team dual meet optimization.
Uses Nash Equilibrium or Gurobi for lineup optimization.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List

import pandas as pd

from swim_ai_reflex.backend.pipelines.base import (
    MeetPipeline,
    MeetType,
    ValidationResult,
)
from swim_ai_reflex.backend.services.dual_meet.scoring import (
    DualMeetResult,
    DualMeetScoringService,
)
from swim_ai_reflex.backend.services.shared.validation import MeetDataValidator

logger = logging.getLogger(__name__)


@dataclass
class DualMeetInput:
    """Input data for dual meet pipeline."""

    our_roster: pd.DataFrame
    opponent_roster: pd.DataFrame
    our_team: str = "Seton"
    opponent_team: str = "Opponent"

    def __post_init__(self):
        """Validate and normalize input DataFrames."""
        # Ensure DataFrames have required columns
        required_cols = {"swimmer", "event", "time"}

        if not isinstance(self.our_roster, pd.DataFrame):
            raise ValueError("our_roster must be a DataFrame")
        if not isinstance(self.opponent_roster, pd.DataFrame):
            raise ValueError("opponent_roster must be a DataFrame")

        # Handle empty DataFrames gracefully
        if not self.our_roster.empty:
            our_cols = set(self.our_roster.columns.str.lower())
            for col in required_cols:
                if col not in our_cols:
                    logger.warning(f"Missing column '{col}' in our_roster")

        if not self.opponent_roster.empty:
            opp_cols = set(self.opponent_roster.columns.str.lower())
            for col in required_cols:
                if col not in opp_cols:
                    logger.warning(f"Missing column '{col}' in opponent_roster")


@dataclass
class DualMeetOptimizationResult:
    """Result of dual meet optimization."""

    meet_result: DualMeetResult
    optimized_lineup: pd.DataFrame
    baseline_score: float
    optimized_score: float
    improvement: float
    method_used: str
    recommendations: List[str] = field(default_factory=list)
    solve_time_ms: float = 0.0


class DualMeetPipeline(MeetPipeline[DualMeetInput, DualMeetOptimizationResult]):
    """
    Pipeline for dual meet optimization.

    Workflow:
    1. Validate input rosters
    2. Normalize event names and times
    3. Run optimization (Nash/Gurobi/Heuristic)
    4. Score the result
    5. Generate recommendations
    """

    def __init__(self):
        super().__init__(MeetType.DUAL_MEET)
        self.validator = MeetDataValidator()
        self.scoring_service = DualMeetScoringService()

    def validate_input(self, data: DualMeetInput) -> ValidationResult:
        """Validate dual meet input data."""
        result = ValidationResult(valid=True)

        # Validate our roster
        if data.our_roster.empty:
            result.add_error("Our roster is empty")
        else:
            our_entries = data.our_roster.to_dict("records")
            our_validation = self.validator.validate_full_roster(our_entries)
            if not our_validation.valid:
                for error in our_validation.errors:
                    result.add_error(f"Our roster: {error}")
            result.warnings.extend(our_validation.warnings)

        # Validate opponent roster
        if data.opponent_roster.empty:
            result.add_error("Opponent roster is empty")
        else:
            opp_entries = data.opponent_roster.to_dict("records")
            opp_validation = self.validator.validate_full_roster(opp_entries)
            if not opp_validation.valid:
                for error in opp_validation.errors:
                    result.add_error(f"Opponent roster: {error}")
            result.warnings.extend(opp_validation.warnings)

        return result

    def run(
        self,
        data: DualMeetInput,
        method: str = "gurobi",
        max_iters: int = 1000,
        enforce_fatigue: bool = False,
        **options,
    ) -> DualMeetOptimizationResult:
        """
        Run dual meet optimization.

        Args:
            data: DualMeetInput with both rosters
            method: Optimization method ("gurobi", "nash", "heuristic")
            max_iters: Maximum iterations for iterative methods
            enforce_fatigue: Whether to apply fatigue penalties

        Returns:
            DualMeetOptimizationResult
        """
        start_time = time.perf_counter()

        # Normalize input data
        our_roster = self._normalize_roster(data.our_roster.copy())
        opponent_roster = self._normalize_roster(data.opponent_roster.copy())

        # Calculate baseline score (before optimization)
        baseline_result = self.scoring_service.score_meet(
            our_roster=our_roster,
            opponent_roster=opponent_roster,
            our_team=data.our_team,
            opponent_team=data.opponent_team,
        )
        baseline_score = baseline_result.our_score

        # Run optimization
        try:
            optimized_lineup = self._run_optimizer(
                our_roster=our_roster,
                opponent_roster=opponent_roster,
                method=method,
                max_iters=max_iters,
                enforce_fatigue=enforce_fatigue,
            )
            method_used = method
        except Exception as e:
            self.logger.warning(
                f"Optimizer {method} failed: {e}, falling back to heuristic"
            )
            optimized_lineup = self._run_heuristic(our_roster, opponent_roster)
            method_used = "heuristic_fallback"

        # Score the optimized lineup
        optimized_result = self.scoring_service.score_lineup(
            combined_lineup=optimized_lineup,
            our_team=data.our_team,
        )
        optimized_score = optimized_result.our_score

        solve_time = (time.perf_counter() - start_time) * 1000

        # Generate recommendations
        recommendations = self._generate_recommendations(
            baseline_result=baseline_result,
            optimized_result=optimized_result,
        )

        return DualMeetOptimizationResult(
            meet_result=optimized_result,
            optimized_lineup=optimized_lineup,
            baseline_score=baseline_score,
            optimized_score=optimized_score,
            improvement=optimized_score - baseline_score,
            method_used=method_used,
            recommendations=recommendations,
            solve_time_ms=solve_time,
        )

    def format_response(self, result: DualMeetOptimizationResult) -> Dict[str, Any]:
        """Format result for API response."""
        meet_dict = result.meet_result.to_dict()

        return {
            "our_score": result.meet_result.our_score,
            "opponent_score": result.meet_result.opponent_score,
            "total_points": result.meet_result.total_points,
            "winner": result.meet_result.winner,
            "is_valid": result.meet_result.is_valid(),
            "baseline_score": result.baseline_score,
            "optimized_score": result.optimized_score,
            "improvement": result.improvement,
            "method_used": result.method_used,
            "event_breakdown": meet_dict["event_breakdown"],
            "recommendations": result.recommendations,
            "details": result.optimized_lineup.to_dict("records"),
        }

    def _normalize_roster(self, roster: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize a roster DataFrame using centralized entry schema.

        Handles all known column name variations:
        - swimmer/swimmer_name/name/athlete
        - team/team_code/school
        - time/seed_time/best_time
        - event/event_name
        """
        from swim_ai_reflex.backend.services.shared.entry_schema import (
            normalize_entry_dict,
        )

        # Standardize column names to lowercase
        roster = roster.copy()
        roster.columns = roster.columns.str.lower()

        # Convert to records and normalize each entry
        records = roster.to_dict("records")
        normalized_records = []

        for record in records:
            norm = normalize_entry_dict(record)
            normalized_records.append(
                {
                    "swimmer": norm["swimmer"],
                    "team": norm.get("team_name") or norm["team"],  # Use display name
                    "event": norm["event"],
                    "time": norm["time"],
                    "grade": norm.get("grade"),
                    "is_exhibition": norm.get("grade") is not None
                    and norm["grade"] < 9,
                }
            )

        return pd.DataFrame(normalized_records)

    def _run_optimizer(
        self,
        our_roster: pd.DataFrame,
        opponent_roster: pd.DataFrame,
        method: str,
        max_iters: int,
        enforce_fatigue: bool,
    ) -> pd.DataFrame:
        """Run the appropriate optimizer."""
        import asyncio

        # Import here to avoid circular dependencies
        from swim_ai_reflex.backend.services.optimization_service import (
            optimization_service,
        )

        # The optimization service is async, so we need to run it with asyncio
        async def run_async():
            return await optimization_service.predict_best_lineups(
                seton_roster=our_roster,
                opponent_roster=opponent_roster,
                method=method,
                max_iters=max_iters,
                enforce_fatigue=enforce_fatigue,
                use_cache=True,
            )

        # Run in event loop
        try:
            # Try to get existing event loop
            loop = asyncio.get_running_loop()
            # If we're already in an async context, use run_coroutine_threadsafe
            future = asyncio.run_coroutine_threadsafe(run_async(), loop)
            result = future.result(timeout=60)
        except RuntimeError:
            # No running loop, create one
            result = asyncio.run(run_async())

        if "details" in result and result["details"]:
            return pd.DataFrame(result["details"])
        elif "lineup" in result:
            return result["lineup"]
        else:
            # Fallback to combined rosters
            our_roster["team"] = "Seton"
            opponent_roster["team"] = "Opponent"
            return pd.concat([our_roster, opponent_roster], ignore_index=True)

    def _run_heuristic(
        self,
        our_roster: pd.DataFrame,
        opponent_roster: pd.DataFrame,
    ) -> pd.DataFrame:
        """Run simple heuristic optimization."""
        # Just combine rosters for now - actual heuristic would do lineup selection
        our_roster = our_roster.copy()
        opponent_roster = opponent_roster.copy()

        our_roster["team"] = "Seton"
        opponent_roster["team"] = "Opponent"

        return pd.concat([our_roster, opponent_roster], ignore_index=True)

    def _generate_recommendations(
        self,
        baseline_result: DualMeetResult,
        optimized_result: DualMeetResult,
    ) -> List[str]:
        """Generate coaching recommendations."""
        recommendations = []

        improvement = optimized_result.our_score - baseline_result.our_score

        if improvement > 0:
            recommendations.append(
                f"Optimization found +{improvement:.0f} points improvement"
            )
        elif improvement < 0:
            recommendations.append(
                f"Warning: Optimization shows {improvement:.0f} points (check constraints)"
            )
        else:
            recommendations.append("Lineup is already optimal")

        # Find swing events (close races)
        for event_result in optimized_result.event_results:
            # Check for close battles
            entries = event_result.entries
            if len(entries) >= 2:
                time_diff = abs(entries[0].time - entries[1].time)
                if time_diff < 0.5 and entries[0].time > 0:  # Within 0.5 seconds
                    recommendations.append(
                        f"Close race in {event_result.event}: "
                        f"{entries[0].swimmer} vs {entries[1].swimmer} "
                        f"({time_diff:.2f}s apart)"
                    )

        return recommendations[:5]  # Limit to top 5


# Factory function for easy instantiation
def create_dual_meet_pipeline() -> DualMeetPipeline:
    """Create a new dual meet pipeline instance."""
    return DualMeetPipeline()
