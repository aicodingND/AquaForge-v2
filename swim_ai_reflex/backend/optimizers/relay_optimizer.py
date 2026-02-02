"""
Relay Leg Optimizer

Optimizes relay composition and leg order for maximum performance.

Key considerations:
- Anchor (leg 4): Fastest with best flat start, handles pressure
- Lead-off (leg 1): Best reaction time, sets pace
- Middle legs (2, 3): Best exchange swimmers

Designed for FastAPI migration with clean interfaces.
"""

import math
from itertools import permutations

from pydantic import BaseModel, Field


class RelaySwimmer(BaseModel):
    """A swimmer available for relay assignment."""

    name: str
    split_time: float  # Their best split time for this stroke
    reaction_time: float = Field(default=0.70, description="Reaction time for lead-off")
    exchange_skill: float = Field(
        default=1.0, ge=0, le=2, description="Exchange efficiency (1.0 = average)"
    )
    pressure_factor: float = Field(
        default=1.0, ge=0, le=2, description="Performance under pressure"
    )


class RelayComposition(BaseModel):
    """Optimized relay composition."""

    event: str
    legs: list[str]  # Swimmer names in order [lead-off, 2nd, 3rd, anchor]
    expected_time: float
    confidence: str
    rationale: list[str]


class RelayOptimizer:
    """
    Optimize relay composition and leg order.

    Uses combinatorial optimization to find the best arrangement
    of swimmers to relay legs, considering each swimmer's strengths.
    """

    # Leg adjustment factors
    LEADOFF_REACTION_WEIGHT = 0.3  # How much reaction time matters for lead-off
    ANCHOR_PRESSURE_WEIGHT = 0.5  # How much pressure handling matters for anchor
    EXCHANGE_WEIGHT = 0.2  # How much exchange skill matters for middle legs

    def optimize_relay(
        self,
        relay_event: str,
        available_swimmers: list[RelaySwimmer],
        required_count: int = 4,
    ) -> RelayComposition:
        """
        Optimize relay leg assignments.

        Args:
            relay_event: Event name (e.g., "200 Medley Relay")
            available_swimmers: Swimmers available for this relay
            required_count: Number of swimmers needed (usually 4)

        Returns:
            RelayComposition with optimized leg order
        """
        if len(available_swimmers) < required_count:
            # Not enough swimmers - just use what we have
            return RelayComposition(
                event=relay_event,
                legs=[s.name for s in available_swimmers[:required_count]],
                expected_time=sum(
                    s.split_time for s in available_swimmers[:required_count]
                ),
                confidence="Low - insufficient swimmers",
                rationale=["Using all available swimmers"],
            )

        # Try all permutations of top swimmers (limit to avoid explosion)
        # First, select top N swimmers by raw split time
        top_n = min(6, len(available_swimmers))  # Max 6 to keep permutations manageable
        sorted_swimmers = sorted(available_swimmers, key=lambda s: s.split_time)[:top_n]

        best_time = float("inf")
        best_arrangement = None
        best_rationale = []

        # Try all permutations of exactly 4 swimmers from top_n
        for perm in permutations(sorted_swimmers, required_count):
            time, rationale = self._evaluate_arrangement(list(perm), relay_event)
            if time < best_time:
                best_time = time
                best_arrangement = list(perm)
                best_rationale = rationale

        if best_arrangement is None:
            # Fallback
            best_arrangement = sorted_swimmers[:required_count]
            best_time = sum(s.split_time for s in best_arrangement)
            best_rationale = ["Fallback: sorted by split time"]

        return RelayComposition(
            event=relay_event,
            legs=[s.name for s in best_arrangement],
            expected_time=round(best_time, 2),
            confidence=self._assess_confidence(best_arrangement),
            rationale=best_rationale,
        )

    def _evaluate_arrangement(
        self, swimmers: list[RelaySwimmer], event: str
    ) -> tuple[float, list[str]]:
        """
        Evaluate a specific relay arrangement.

        Returns adjusted time and rationale.
        """
        if len(swimmers) != 4:
            return float("inf"), ["Invalid arrangement"]

        total_time = 0.0
        rationale = []

        # Leg 1: Lead-off - reaction time matters most
        lead_off = swimmers[0]
        leg1_time = (
            lead_off.split_time
            + (lead_off.reaction_time - 0.70) * self.LEADOFF_REACTION_WEIGHT
        )
        total_time += leg1_time
        rationale.append(
            f"Lead-off: {lead_off.name} (reaction: {lead_off.reaction_time:.2f}s)"
        )

        # Legs 2 & 3: Middle - exchange skill matters
        for i, swimmer in enumerate(swimmers[1:3], 2):
            leg_time = swimmer.split_time
            # Better exchange skill reduces time
            exchange_bonus = (
                swimmer.exchange_skill - 1.0
            ) * -0.1  # Good exchange = negative adjustment
            leg_time += exchange_bonus
            total_time += leg_time
            rationale.append(
                f"Leg {i}: {swimmer.name} (exchange: {swimmer.exchange_skill:.1f})"
            )

        # Leg 4: Anchor - pressure handling matters
        anchor = swimmers[3]
        anchor_time = anchor.split_time
        # Better pressure handling = faster under race conditions
        pressure_bonus = (anchor.pressure_factor - 1.0) * -0.15
        anchor_time += pressure_bonus
        total_time += anchor_time
        rationale.append(
            f"Anchor: {anchor.name} (pressure factor: {anchor.pressure_factor:.1f})"
        )

        return total_time, rationale

    def _assess_confidence(self, swimmers: list[RelaySwimmer]) -> str:
        """Assess confidence level of the relay."""
        # Check variance in abilities
        times = [s.split_time for s in swimmers]
        if not times:
            return "Unknown"

        avg_time = sum(times) / len(times)
        variance = sum((t - avg_time) ** 2 for t in times) / len(times)
        std_dev = math.sqrt(variance)

        # Lower variance = more balanced = higher confidence
        if std_dev < 1.0:
            return "High - balanced team"
        elif std_dev < 2.0:
            return "Medium - some variation"
        else:
            return "Low - high variation"

    def optimize_medley_relay(
        self,
        backstroke: list[RelaySwimmer],
        breaststroke: list[RelaySwimmer],
        butterfly: list[RelaySwimmer],
        freestyle: list[RelaySwimmer],
    ) -> RelayComposition:
        """
        Optimize medley relay with stroke-specific swimmers.

        Order: Back → Breast → Fly → Free
        """
        # Pick best swimmer from each stroke
        best_back = min(backstroke, key=lambda s: s.split_time) if backstroke else None
        best_breast = (
            min(breaststroke, key=lambda s: s.split_time) if breaststroke else None
        )
        best_fly = min(butterfly, key=lambda s: s.split_time) if butterfly else None
        best_free = min(freestyle, key=lambda s: s.split_time) if freestyle else None

        if not all([best_back, best_breast, best_fly, best_free]):
            return RelayComposition(
                event="200 Medley Relay",
                legs=[],
                expected_time=0.0,
                confidence="Failed - missing stroke specialists",
                rationale=["Cannot form complete medley relay"],
            )

        swimmers = [best_back, best_breast, best_fly, best_free]

        # For medley, order is fixed by rules
        return RelayComposition(
            event="200 Medley Relay",
            legs=[s.name for s in swimmers],
            expected_time=sum(s.split_time for s in swimmers),
            confidence="Standard medley order",
            rationale=[
                f"Backstroke: {best_back.name}",
                f"Breaststroke: {best_breast.name}",
                f"Butterfly: {best_fly.name}",
                f"Freestyle: {best_free.name}",
            ],
        )


# Singleton instance for service pattern
relay_optimizer = RelayOptimizer()
