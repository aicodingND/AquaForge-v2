"""
Strategic Exhibition Deployment Module

Grade 7 and below swimmers cannot score points, but can strategically
displace opponents from scoring positions.

Key Strategies:
1. DISPLACEMENT: Place fast exhibition swimmers to push opponents down
2. EVENT SWARMING: Pack 8th graders into events where we're weak
3. PSYCHOLOGICAL: Show fast exhibition times to opponents

Usage:
    analyzer = ExhibitionDeploymentAnalyzer()
    recommendations = analyzer.analyze_deployment(
        seton_roster, opponent_roster, events
    )
"""

import logging
from dataclasses import dataclass

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class DisplacementOpportunity:
    """A potential exhibition deployment opportunity."""

    swimmer: str
    event: str
    swimmer_time: float
    swimmer_grade: int
    opponent_displaced: str
    opponent_time: float
    opponent_new_place: int
    points_denied: float
    explanation: str

    @property
    def priority_score(self) -> float:
        """Higher = better opportunity."""
        return self.points_denied * 1.5 + (8 - self.opponent_new_place)


@dataclass
class ExhibitionDeploymentResult:
    """Result of exhibition deployment analysis."""

    recommended_assignments: dict[str, list[str]]  # swimmer → events
    opportunities: list[DisplacementOpportunity]
    total_points_denied: float
    summary: str


class ExhibitionDeploymentAnalyzer:
    """
    Analyzes optimal exhibition swimmer placement for maximum opponent disruption.

    CONSTRAINT: Grade ≤7 NEVER scores points.
    STRATEGY: Place fast exhibition swimmers where they can displace opponents.
    """

    def __init__(self, min_scoring_grade: int = 8):
        """
        Args:
            min_scoring_grade: Minimum grade for scoring eligibility (default: 8)
        """
        self.min_scoring_grade = min_scoring_grade
        # Standard dual meet points
        self.points_table = [8, 6, 5, 4, 3, 2, 1]

    def get_exhibition_swimmers(self, roster_df: pd.DataFrame) -> pd.DataFrame:
        """Filter roster to exhibition-only swimmers (grade < 8)."""
        if "grade" not in roster_df.columns:
            return pd.DataFrame()

        # Convert grade to int, handling various formats
        def parse_grade(g):
            if pd.isna(g):
                return 12  # Assume varsity if unknown
            try:
                return int(g)
            except (ValueError, TypeError):
                return 12

        roster_df = roster_df.copy()
        roster_df["_grade_int"] = roster_df["grade"].apply(parse_grade)

        exhibition = roster_df[roster_df["_grade_int"] < self.min_scoring_grade]
        return exhibition.drop(columns=["_grade_int"])

    def analyze_deployment(
        self,
        seton_roster: pd.DataFrame,
        opponent_roster: pd.DataFrame,
        max_events_per_swimmer: int = 2,
    ) -> ExhibitionDeploymentResult:
        """
        Analyze optimal exhibition swimmer deployment.

        Args:
            seton_roster: Full Seton roster (all grades)
            opponent_roster: Opponent roster
            max_events_per_swimmer: Max individual events per swimmer

        Returns:
            ExhibitionDeploymentResult with recommendations
        """
        exhibition_swimmers = self.get_exhibition_swimmers(seton_roster)

        if exhibition_swimmers.empty:
            return ExhibitionDeploymentResult(
                recommended_assignments={},
                opportunities=[],
                total_points_denied=0.0,
                summary="No exhibition swimmers available",
            )

        opportunities = []
        events = seton_roster["event"].unique()

        for event in events:
            if "Relay" in event:
                continue  # Skip relay events

            event_opps = self._find_opportunities_for_event(
                event, exhibition_swimmers, opponent_roster
            )
            opportunities.extend(event_opps)

        # Sort by priority (points denied)
        opportunities.sort(key=lambda x: x.priority_score, reverse=True)

        # Assign swimmers respecting max events constraint
        assignments, selected = self._assign_swimmers(
            opportunities, max_events_per_swimmer
        )

        total_denied = sum(o.points_denied for o in selected)

        summary_parts = []
        if selected:
            summary_parts.append(f"Recommended {len(selected)} exhibition placements")
            summary_parts.append(
                f"Estimated {total_denied:.0f} points denied to opponent"
            )
            for opp in selected[:3]:  # Top 3
                summary_parts.append(
                    f"  • {opp.swimmer} in {opp.event}: deny {opp.points_denied:.0f} pts"
                )
        else:
            summary_parts.append("No beneficial exhibition placements found")

        return ExhibitionDeploymentResult(
            recommended_assignments=assignments,
            opportunities=selected,
            total_points_denied=total_denied,
            summary="\n".join(summary_parts),
        )

    def _find_opportunities_for_event(
        self,
        event: str,
        exhibition_swimmers: pd.DataFrame,
        opponent_roster: pd.DataFrame,
    ) -> list[DisplacementOpportunity]:
        """Find displacement opportunities for a single event."""
        opportunities = []

        # Get exhibition swimmers for this event
        ex_event = exhibition_swimmers[exhibition_swimmers["event"] == event]
        if ex_event.empty:
            return []

        # Get opponent times for this event (sorted)
        opp_event = opponent_roster[opponent_roster["event"] == event].copy()
        if opp_event.empty:
            return []

        opp_event = opp_event.sort_values("time")
        opp_times = opp_event["time"].tolist()
        opp_swimmers = opp_event["swimmer"].tolist()

        for _, ex_row in ex_event.iterrows():
            ex_time = ex_row.get("time", 999)
            ex_swimmer = ex_row.get("swimmer", "Unknown")
            ex_grade = int(ex_row.get("grade", 7))

            # Find which opponent(s) this exhibition swimmer would displace
            for i, (opp_time, opp_swimmer) in enumerate(zip(opp_times, opp_swimmers)):
                if ex_time < opp_time:
                    # Exhibition swimmer beats this opponent
                    # Calculate points denied (opponent moves down one place)
                    current_place = i + 1  # 1-indexed
                    new_place = i + 2  # Pushed down one

                    if current_place <= len(self.points_table):
                        original_pts = self.points_table[current_place - 1]
                        new_pts = (
                            self.points_table[new_place - 1]
                            if new_place <= len(self.points_table)
                            else 0
                        )
                        points_denied = original_pts - new_pts

                        if points_denied > 0:
                            opp = DisplacementOpportunity(
                                swimmer=ex_swimmer,
                                event=event,
                                swimmer_time=ex_time,
                                swimmer_grade=ex_grade,
                                opponent_displaced=opp_swimmer,
                                opponent_time=opp_time,
                                opponent_new_place=new_place,
                                points_denied=points_denied,
                                explanation=(
                                    f"{ex_swimmer} ({ex_time:.2f}s) beats "
                                    f"{opp_swimmer} ({opp_time:.2f}s), "
                                    f"denies {points_denied:.0f} pts"
                                ),
                            )
                            opportunities.append(opp)
                    break  # Only count first displacement

        return opportunities

    def _assign_swimmers(
        self,
        opportunities: list[DisplacementOpportunity],
        max_events: int,
    ) -> tuple[dict[str, list[str]], list[DisplacementOpportunity]]:
        """
        Assign swimmers to maximize total points denied.

        Respects:
        - Max events per swimmer
        - No back-to-back events (if EVENT_ORDER available)
        """
        assignments: dict[str, list[str]] = {}
        selected: list[DisplacementOpportunity] = []
        swimmer_event_count: dict[str, int] = {}

        for opp in opportunities:
            swimmer = opp.swimmer
            event = opp.event

            # Check max events
            if swimmer_event_count.get(swimmer, 0) >= max_events:
                continue

            # Assign
            if swimmer not in assignments:
                assignments[swimmer] = []
            assignments[swimmer].append(event)
            swimmer_event_count[swimmer] = swimmer_event_count.get(swimmer, 0) + 1
            selected.append(opp)

        return assignments, selected


# Convenience function
def analyze_exhibition_strategy(
    seton_roster: pd.DataFrame,
    opponent_roster: pd.DataFrame,
) -> ExhibitionDeploymentResult:
    """
    Analyze optimal exhibition swimmer deployment.

    Args:
        seton_roster: Full Seton roster
        opponent_roster: Opponent roster

    Returns:
        ExhibitionDeploymentResult with recommendations
    """
    analyzer = ExhibitionDeploymentAnalyzer()
    return analyzer.analyze_deployment(seton_roster, opponent_roster)


__all__ = [
    "ExhibitionDeploymentAnalyzer",
    "ExhibitionDeploymentResult",
    "DisplacementOpportunity",
    "analyze_exhibition_strategy",
]
