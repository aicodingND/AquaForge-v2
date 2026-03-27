"""
Championship Pipeline

Pipeline for multi-team championship meets (VCAC, VISAA State, etc.).
Provides projection, entry optimization, and relay configuration.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from swim_ai_reflex.backend.pipelines.base import (
    MeetPipeline,
    MeetType,
    ValidationResult,
)
from swim_ai_reflex.backend.services.championship.projection import (
    PointProjectionService,
    StandingsProjection,
)
from swim_ai_reflex.backend.services.shared.normalization import (
    normalize_team_name,
)
from swim_ai_reflex.backend.services.shared.validation import MeetDataValidator

logger = logging.getLogger(__name__)


@dataclass
class ChampionshipInput:
    """Input data for championship pipeline."""

    entries: list[dict[str, Any]]  # All entries from psych sheet
    target_team: str = "Seton"
    meet_name: str = "Championship"
    meet_profile: str = "vcac_championship"

    # Entry optimization parameters
    divers: set[str] = field(default_factory=set)
    relay_1_swimmers: set[str] = field(default_factory=set)  # 200 Medley Relay
    relay_2_swimmers: set[str] = field(default_factory=set)  # 200 Free Relay
    relay_3_swimmers: set[str] = field(default_factory=set)  # 400 Free Relay

    def __post_init__(self):
        """Convert sets if needed."""
        if isinstance(self.divers, list):
            self.divers = set(self.divers)
        if isinstance(self.relay_1_swimmers, list):
            self.relay_1_swimmers = set(self.relay_1_swimmers)
        if isinstance(self.relay_2_swimmers, list):
            self.relay_2_swimmers = set(self.relay_2_swimmers)
        if isinstance(self.relay_3_swimmers, list):
            self.relay_3_swimmers = set(self.relay_3_swimmers)


@dataclass
class ChampionshipResult:
    """Result from championship pipeline."""

    projection: StandingsProjection
    entry_assignments: dict[str, list[str]] | None = None
    relay_configurations: dict[str, Any] | None = None
    exhibition_strategy: dict[str, Any] | None = None  # NEW: Exhibition deployment
    optimization_improvement: float = 0.0
    recommendations: list[str] = field(default_factory=list)


class ChampionshipPipeline(MeetPipeline[ChampionshipInput, ChampionshipResult]):
    """
    Pipeline for championship meet analysis and optimization.

    Supports multiple stages:
    1. Projection: Calculate expected standings from psych sheet
    2. Entry Optimization: Optimize swimmer-event assignments
    3. Relay Configuration: Optimize relay compositions
    4. Exhibition Strategy: Deploy exhibition swimmers for displacement
    """

    def __init__(self, meet_profile: str = "vcac_championship"):
        super().__init__(MeetType.CONFERENCE_CHAMPIONSHIP)
        self.validator = MeetDataValidator()
        self.projection_service = PointProjectionService(meet_profile)
        self.meet_profile = meet_profile

    def validate_input(self, data: ChampionshipInput) -> ValidationResult:
        """Validate championship input data."""
        result = ValidationResult(valid=True)

        if not data.entries:
            result.add_error("No entries provided")
            return result

        # Validate entries
        for i, entry in enumerate(data.entries[:100]):  # Check first 100
            entry_result = self.validator.validate_swimmer_entry(
                entry, require_team=True
            )
            if not entry_result.valid:
                for error in entry_result.errors:
                    result.add_error(f"Entry {i + 1}: {error}")
            result.warnings.extend(entry_result.warnings)

        if len(data.entries) > 100 and not result.valid:
            result.add_warning(
                f"Only first 100 of {len(data.entries)} entries validated"
            )

        # Validate target team exists
        teams = set(entry.get("team", "") for entry in data.entries)
        normalized_target = normalize_team_name(data.target_team)
        normalized_teams = {normalize_team_name(t) for t in teams}

        if normalized_target not in normalized_teams:
            result.add_warning(
                f"Target team '{data.target_team}' not found in entries. "
                f"Available teams: {', '.join(sorted(teams))}"
            )

        return result

    def run(
        self,
        data: ChampionshipInput,
        stage: str = "full",  # "projection", "entries", "relays", "exhibition", "full"
        **options,
    ) -> ChampionshipResult:
        """
        Run championship pipeline.

        Args:
            data: ChampionshipInput with all entries
            stage: Which stage(s) to run:
                - "projection": Only project standings
                - "entries": Project + optimize entries
                - "relays": Project + entries + relays
                - "exhibition": Full pipeline including exhibition strategy
                - "full": All stages (default)

        Returns:
            ChampionshipResult
        """
        _ = time.perf_counter()  # Track timing but don't store

        # Stage 1: Projection (always run)
        projection = self.projection_service.project_standings(
            entries=data.entries,
            target_team=data.target_team,
            meet_name=data.meet_name,
        )

        entry_assignments = None
        relay_configurations = None
        exhibition_strategy = None
        optimization_improvement = 0.0
        recommendations = []

        # Stage 2: Entry optimization
        if stage in ("entries", "relays", "exhibition", "full"):
            try:
                entry_assignments, improvement = self._optimize_entries(
                    entries=data.entries,
                    target_team=data.target_team,
                    divers=data.divers,
                    relay_1_swimmers=data.relay_1_swimmers,
                    relay_2_swimmers=data.relay_2_swimmers,
                    relay_3_swimmers=data.relay_3_swimmers,
                )
                optimization_improvement = improvement
            except Exception as e:
                self.logger.warning(f"Entry optimization failed: {e}")
                recommendations.append(f"Entry optimization unavailable: {e}")

        # Stage 3: Relay configuration
        if stage in ("relays", "exhibition", "full") and entry_assignments:
            try:
                relay_configurations = self._optimize_relays(
                    entries=data.entries,
                    target_team=data.target_team,
                    entry_assignments=entry_assignments,
                )
            except Exception as e:
                self.logger.warning(f"Relay optimization failed: {e}")
                recommendations.append(f"Relay optimization unavailable: {e}")

        # Stage 4: Exhibition strategy (NEW)
        if stage in ("exhibition", "full"):
            try:
                exhibition_strategy = self._optimize_exhibition(
                    entries=data.entries,
                    target_team=data.target_team,
                )
            except Exception as e:
                self.logger.warning(f"Exhibition strategy failed: {e}")
                recommendations.append(f"Exhibition strategy unavailable: {e}")

        # Generate recommendations
        recommendations.extend(
            self._generate_recommendations(
                projection=projection,
                entry_assignments=entry_assignments,
                target_team=data.target_team,
            )
        )

        return ChampionshipResult(
            projection=projection,
            entry_assignments=entry_assignments,
            relay_configurations=relay_configurations,
            exhibition_strategy=exhibition_strategy,
            optimization_improvement=optimization_improvement,
            recommendations=recommendations,
        )

    def format_response(self, result: ChampionshipResult) -> dict[str, Any]:
        """Format result for API response."""
        response = {
            "projection": result.projection.to_dict(),
            "standings": result.projection.to_dict()["standings"],
            "target_team_total": result.projection.target_team_total,
            "target_team_rank": result.projection.target_team_rank,
            "swing_events": [se.to_dict() for se in result.projection.swing_events],
            "recommendations": result.recommendations,
        }

        if result.entry_assignments:
            response["entry_assignments"] = result.entry_assignments
            response["optimization_improvement"] = result.optimization_improvement

        if result.relay_configurations:
            response["relay_configurations"] = result.relay_configurations

        return response

    def project_only(
        self,
        entries: list[dict[str, Any]],
        target_team: str = "Seton",
        meet_name: str = "Championship",
    ) -> StandingsProjection:
        """
        Run projection only (fast path).

        Useful when you just need standings without optimization.
        """
        return self.projection_service.project_standings(
            entries=entries,
            target_team=target_team,
            meet_name=meet_name,
        )

    def _optimize_entries(
        self,
        entries: list[dict[str, Any]],
        target_team: str,
        divers: set[str],
        relay_1_swimmers: set[str] | None = None,
        relay_2_swimmers: set[str] | None = None,
        relay_3_swimmers: set[str] | None = None,
    ) -> tuple[dict[str, list[str]], float]:
        """
        Optimize entry selections.

        Returns:
            Tuple of (assignments dict, improvement points)
        """
        # Try to use existing championship optimizer
        try:
            from swim_ai_reflex.backend.core.strategies.championship_strategy import (
                ChampionshipEntry,
                ChampionshipGurobiStrategy,
            )

            # Convert entries to ChampionshipEntry objects
            championship_entries = [
                ChampionshipEntry(
                    swimmer_name=e.get("swimmer", e.get("swimmer_name", "")),
                    team=e.get("team", ""),
                    event=e.get("event", ""),
                    seed_time=e.get("seed_time", e.get("time", float("inf"))),
                )
                for e in entries
            ]

            strategy = ChampionshipGurobiStrategy(self.meet_profile)
            result = strategy.optimize_entries(
                all_entries=championship_entries,
                target_team=target_team,
                divers=divers,
                relay_1_swimmers=relay_1_swimmers or set(),
                relay_2_swimmers=relay_2_swimmers or set(),
                relay_3_swimmers=relay_3_swimmers or set(),
            )

            return result.assignments, result.improvement

        except ImportError:
            self.logger.warning("Championship Gurobi strategy not available")
            return {}, 0.0
        except Exception as e:
            self.logger.warning(f"Entry optimization error: {e}")
            return {}, 0.0

    def _optimize_relays(
        self,
        entries: list[dict[str, Any]],
        target_team: str,
        entry_assignments: dict[str, list[str]],
    ) -> dict[str, Any]:
        """
        Optimize relay configurations.

        Returns:
            Dictionary with relay configurations
        """
        # Try to use existing relay optimizer
        try:
            # Import relay optimizer for future use - noqa: F401
            from swim_ai_reflex.backend.services.relay_optimizer_service import (  # noqa: F401
                relay_optimizer_service as _relay_optimizer,
            )

            # Filter to target team
            _team_entries = [  # Available for future use
                e
                for e in entries
                if normalize_team_name(e.get("team", ""))
                == normalize_team_name(target_team)
            ]

            # This would need adaptation to work with the new structure
            # For now, return a placeholder
            return {
                "200_medley_relay": {"status": "optimization_available"},
                "200_free_relay": {"status": "optimization_available"},
                "400_free_relay": {"status": "optimization_available"},
            }

        except ImportError:
            return {"status": "relay_optimizer_not_available"}
        except Exception as e:
            self.logger.warning(f"Relay optimization error: {e}")
            return {"status": "error", "message": str(e)}

    def _optimize_exhibition(
        self,
        entries: list[dict[str, Any]],
        target_team: str,
    ) -> dict[str, Any]:
        """
        Optimize exhibition swimmer deployment.

        Uses ExhibitionDeploymentAnalyzer to find strategic placement
        of non-scoring swimmers to displace opponents.

        Returns:
            Dictionary with exhibition strategy recommendations
        """
        try:
            import pandas as pd

            from swim_ai_reflex.backend.core.exhibition_strategy import (
                ExhibitionDeploymentAnalyzer,
            )

            # Convert entries to DataFrame format expected by analyzer
            target_entries = [
                e
                for e in entries
                if normalize_team_name(e.get("team", ""))
                == normalize_team_name(target_team)
            ]
            opponent_entries = [
                e
                for e in entries
                if normalize_team_name(e.get("team", ""))
                != normalize_team_name(target_team)
            ]

            if not target_entries:
                return {"status": "no_target_team_entries"}

            # Build DataFrames
            target_df = pd.DataFrame(
                [
                    {
                        "name": e.get("swimmer", e.get("swimmer_name", "")),
                        "event": e.get("event", ""),
                        "time": e.get("seed_time", e.get("time", float("inf"))),
                        "grade": e.get("grade", 12),
                    }
                    for e in target_entries
                ]
            )

            opponent_df = pd.DataFrame(
                [
                    {
                        "name": e.get("swimmer", e.get("swimmer_name", "")),
                        "team": e.get("team", ""),
                        "event": e.get("event", ""),
                        "time": e.get("seed_time", e.get("time", float("inf"))),
                    }
                    for e in opponent_entries
                ]
            )

            # Run exhibition analysis
            analyzer = ExhibitionDeploymentAnalyzer()
            result = analyzer.analyze_deployment(
                seton_roster=target_df,
                opponent_roster=opponent_df,
            )

            return {
                "status": "success",
                "recommended_assignments": result.recommended_assignments,
                "total_points_denied": result.total_points_denied,
                "opportunities": [
                    {
                        "swimmer": opp.swimmer,
                        "event": opp.event,
                        "opponent_displaced": opp.opponent_displaced,
                        "points_denied": opp.points_denied,
                        "explanation": opp.explanation,
                    }
                    for opp in result.opportunities[:5]  # Top 5
                ],
                "summary": result.summary,
            }

        except ImportError as e:
            self.logger.warning(f"Exhibition strategy dependencies not available: {e}")
            return {"status": "not_available", "reason": str(e)}
        except Exception as e:
            self.logger.warning(f"Exhibition strategy error: {e}")
            return {"status": "error", "message": str(e)}

    def _generate_recommendations(
        self,
        projection: StandingsProjection,
        entry_assignments: dict[str, list[str]] | None,
        target_team: str,
    ) -> list[str]:
        """Generate coaching recommendations."""
        recommendations = []

        # Standing analysis
        rank = projection.target_team_rank
        total = projection.target_team_total

        if rank == 1:
            recommendations.append(
                f"{target_team} projected 1st with {total:.0f} points"
            )
        else:
            # Find gap to leader
            leader = projection.standings[0]
            gap = leader[1] - total
            recommendations.append(
                f"{target_team} projected {rank}{'st' if rank == 1 else 'nd' if rank == 2 else 'rd' if rank == 3 else 'th'} "
                f"with {total:.0f} points ({gap:.0f} behind {leader[0]})"
            )

        # Top swing events
        if projection.swing_events:
            top_swing = projection.swing_events[0]
            recommendations.append(
                f"Top opportunity: {top_swing.swimmer} in {top_swing.event} "
                f"(+{top_swing.point_gain:.0f} points if improves {top_swing.time_gap:.2f}s)"
            )

        # Entry optimization summary
        if entry_assignments:
            swimmers_with_multiple = [
                s for s, events in entry_assignments.items() if len(events) >= 2
            ]
            recommendations.append(
                f"{len(swimmers_with_multiple)} swimmers assigned 2 individual events"
            )

        return recommendations[:5]


# Factory function
def create_championship_pipeline(
    meet_profile: str = "vcac_championship",
) -> ChampionshipPipeline:
    """Create a new championship pipeline instance."""
    return ChampionshipPipeline(meet_profile)
