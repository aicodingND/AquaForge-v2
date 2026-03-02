"""
Attrition Model — Empirical DQ/DNS/Scratch Probability Estimates

Derived from 77,345 entries across 162 meets (513 HyTek MDB databases).
Source: scripts/compute_dq_dns_rates.py → data/dq_dns_rates.json

Key finding: DQ is negligible (0.01%), but DNS/scratch is ~20% of all
seeded entries. This significantly affects championship projections where
psych sheet entries may not actually swim.

Validated finding (22-meet A/B test): Event-level attrition rates are
nearly uniform (~19-26%) and have ZERO impact on deterministic optimizer
lineup decisions. Attrition is therefore only used in:
  - Monte Carlo simulation (stochastic swimmer dropout per trial)
  - Championship projections (expected-value discounting)
It is NOT used in optimizer objective functions (Gurobi, Aqua, HiGHS, etc.)
because uniform scaling cannot change which assignment maximizes total points.

Usage:
    from swim_ai_reflex.backend.core.attrition_model import (
        AttritionRates,
        get_completion_probability,
        ATTRITION_RATES,
    )

    # Probability that a seeded swimmer actually competes
    prob = get_completion_probability("100 Fly")  # 0.744

    # Discount factor for expected value scoring
    factor = ATTRITION_RATES.completion_factor("200 IM")  # 0.762
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# Standard championship events — excludes JV-only events (25yd, 50 Back, etc.)
STANDARD_EVENTS = {
    "50 Free",
    "100 Free",
    "200 Free",
    "500 Free",
    "100 Back",
    "100 Breast",
    "100 Fly",
    "200 IM",
    "Diving",
    "200 Medley Relay",
    "200 Free Relay",
    "400 Free Relay",
}

# Empirical DNS rates from 162 meets, 77,345 entries
# These represent P(swimmer is seeded but doesn't swim)
DNS_RATES: dict[str, float] = {
    "50 Free": 0.2166,
    "100 Free": 0.2081,
    "200 Free": 0.2201,
    "500 Free": 0.1979,
    "100 Back": 0.2002,
    "100 Breast": 0.1910,
    "100 Fly": 0.2561,
    "200 IM": 0.2377,
    "Diving": 0.0647,
    "200 Medley Relay": 0.1850,
    "200 Free Relay": 0.1852,
    "400 Free Relay": 0.2472,
}

# DQ rates are negligible (< 0.1%) but included for completeness
DQ_RATES: dict[str, float] = {
    "200 Free": 0.00066,
    "500 Free": 0.00061,
    "100 Fly": 0.00027,
    "100 Back": 0.00015,
    "100 Free": 0.00010,
    "200 Free Relay": 0.00016,
}

DEFAULT_DNS_RATE = 0.2009  # Global average
DEFAULT_DQ_RATE = 0.00012  # Global average (effectively zero)


@dataclass
class AttritionRates:
    """Container for per-event attrition (DNS/DQ) probabilities."""

    enabled: bool = True
    dns_rates: dict[str, float] = field(default_factory=lambda: dict(DNS_RATES))
    dq_rates: dict[str, float] = field(default_factory=lambda: dict(DQ_RATES))
    default_dns: float = DEFAULT_DNS_RATE
    default_dq: float = DEFAULT_DQ_RATE

    # Per-swimmer overrides for targeted attrition modeling
    # Format: {"swimmer_name": {"100 Fly": 0.08, "50 Free": 0.02}}
    swimmer_overrides: dict[str, dict[str, float]] = field(default_factory=dict)
    # Sample sizes for hierarchical blending: {"swimmer_name": {"100 Fly": 12}}
    swimmer_sample_sizes: dict[str, dict[str, int]] = field(default_factory=dict)

    def dns_rate(self, event_name: str) -> float:
        """P(seeded swimmer doesn't swim this event)."""
        if not self.enabled:
            return 0.0
        return self.dns_rates.get(event_name, self.default_dns)

    def dq_rate(self, event_name: str) -> float:
        """P(swimmer is disqualified). Negligible in practice."""
        if not self.enabled:
            return 0.0
        return self.dq_rates.get(event_name, self.default_dq)

    def attrition_rate(self, event_name: str) -> float:
        """P(swimmer doesn't score) = P(DNS) + P(DQ)."""
        return self.dns_rate(event_name) + self.dq_rate(event_name)

    def completion_factor(self, event_name: str) -> float:
        """Expected value discount: 1 - P(attrition).

        Multiply projected points by this factor to account for the
        probability that the swimmer scratches or DQs.
        """
        return 1.0 - self.attrition_rate(event_name)

    def swimmer_attrition_rate(
        self, swimmer: str, event_name: str, min_n: int = 5
    ) -> float:
        """Blended swimmer+event attrition rate using hierarchical shrinkage.

        When we have per-swimmer historical data, blend it with the event-level
        prior. The weight increases with sample size: at min_n entries, the
        swimmer-specific rate fully replaces the prior.

        Falls back to event-level rate when no swimmer data exists.
        """
        event_rate = self.attrition_rate(event_name)

        swimmer_rates = self.swimmer_overrides.get(swimmer, {})
        if event_name not in swimmer_rates:
            return event_rate

        swimmer_rate = swimmer_rates[event_name]
        swimmer_n = self.swimmer_sample_sizes.get(swimmer, {}).get(event_name, 0)

        # Shrinkage weight: full weight at min_n entries, zero at 0
        weight = min(swimmer_n / min_n, 1.0) if min_n > 0 else 1.0
        return weight * swimmer_rate + (1 - weight) * event_rate

    @classmethod
    def from_json(cls, path: str | Path) -> "AttritionRates":
        """Load rates from the computed JSON file."""
        path = Path(path)
        if not path.exists():
            logger.warning(f"Attrition rates file not found: {path}, using defaults")
            return cls()

        with open(path) as f:
            data = json.load(f)

        dns_rates = {}
        dq_rates = {}

        for event_name, info in data.get("by_event", {}).items():
            if event_name not in STANDARD_EVENTS:
                continue
            if info.get("n", 0) < 50:
                continue
            dns_rates[event_name] = info.get("dns_rate", DEFAULT_DNS_RATE)
            dq_rate = info.get("dq_rate", 0.0)
            if dq_rate > 0:
                dq_rates[event_name] = dq_rate

        return cls(
            dns_rates=dns_rates,
            dq_rates=dq_rates,
            default_dns=data.get("global_dns_rate", DEFAULT_DNS_RATE),
            default_dq=data.get("global_dq_rate", DEFAULT_DQ_RATE),
        )

    @classmethod
    def disabled(cls) -> "AttritionRates":
        """Create a no-op instance (attrition not modeled)."""
        return cls(enabled=False)


# Singleton — loaded once, used everywhere
ATTRITION_RATES = AttritionRates()


def get_completion_probability(
    event_name: str, rates: AttritionRates | None = None
) -> float:
    """P(seeded swimmer actually competes and scores) for an event.

    Args:
        event_name: Event name (e.g., "100 Fly")
        rates: Optional custom rates instance (uses singleton if None)

    Returns:
        Probability between 0 and 1 (typically 0.74-0.94 for standard events)
    """
    r = rates or ATTRITION_RATES
    return r.completion_factor(event_name)


def should_swimmer_compete(
    event_name: str,
    rng_value: float,
    rates: AttritionRates | None = None,
) -> bool:
    """Stochastic decision: does this swimmer compete in this simulation trial?

    Used by Monte Carlo simulation to randomly drop swimmers based on
    historical attrition rates.

    Args:
        event_name: Event name
        rng_value: Random float in [0, 1) from numpy.random
        rates: Optional custom rates instance

    Returns:
        True if swimmer competes, False if scratched/DQ
    """
    r = rates or ATTRITION_RATES
    if not r.enabled:
        return True
    return rng_value >= r.attrition_rate(event_name)
