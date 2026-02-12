"""
Championship Adjustment Factors — Empirical Seed-to-Finals Corrections

Derived from 25,830 swim entries across 52 championship meets.
Source: scripts/analyze_seed_accuracy.py → data/championship_factors.json

Usage:
    from swim_ai_reflex.backend.core.championship_factors import (
        adjust_time,
        get_event_confidence,
        CHAMPIONSHIP_FACTORS,
    )

    adjusted = adjust_time(seed_time=25.5, event="50 Free")
    tier = get_event_confidence("200 IM")  # "high"
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# Default factor when no per-event data is available (1% speed-up)
DEFAULT_FACTOR = 0.9899

# Per-event factors from empirical analysis (25,830 entries, 52 meets)
# Factor < 1.0 = swimmers go faster than seed; > 1.0 = slower than seed
# Only includes standard championship events with N >= 20
EVENT_FACTORS: dict[str, float] = {
    "100 Back": 0.988,
    "100 Breast": 0.9871,
    "100 Fly": 0.9949,
    "100 Free": 0.9883,
    "200 Free": 0.9859,
    "200 IM": 0.9953,
    "50 Free": 0.9917,
    "500 Free": 0.9971,
}

# Confidence tiers based on flip rate and top-3 stability
# high:   flip < 72%, top-3 stability > 75% — optimizer can trust these
# medium: flip < 82%, top-3 stability > 60% — generally reliable
# low:    flip >= 82% or top-3 stability <= 60% — flag for coach review
EVENT_CONFIDENCE: dict[str, str] = {
    "100 Back": "medium",
    "100 Breast": "medium",
    "100 Fly": "high",
    "100 Free": "medium",
    "200 Free": "high",
    "200 IM": "high",
    "50 Free": "low",
    "500 Free": "high",
}


@dataclass
class ChampionshipFactors:
    """Container for championship adjustment configuration."""

    enabled: bool = True
    default_factor: float = DEFAULT_FACTOR
    event_factors: dict[str, float] = field(default_factory=lambda: dict(EVENT_FACTORS))
    confidence_tiers: dict[str, str] = field(
        default_factory=lambda: dict(EVENT_CONFIDENCE)
    )

    def get_factor(self, event_name: str) -> float:
        """Get championship adjustment factor for an event.

        Returns per-event factor if available, otherwise default.
        Factor < 1.0 means swimmers go faster (multiply seed_time by factor).
        """
        if not self.enabled:
            return 1.0
        return self.event_factors.get(event_name, self.default_factor)

    def get_confidence(self, event_name: str) -> str:
        """Get prediction confidence tier for an event."""
        return self.confidence_tiers.get(event_name, "medium")

    @classmethod
    def from_json(cls, path: str | Path) -> "ChampionshipFactors":
        """Load factors from exported JSON file."""
        path = Path(path)
        if not path.exists():
            logger.warning(
                f"Championship factors file not found: {path}, using defaults"
            )
            return cls()

        with open(path) as f:
            data = json.load(f)

        # Only include standard championship events (filter out JV-only events)
        standard_events = {
            "50 Free",
            "100 Free",
            "200 Free",
            "500 Free",
            "100 Back",
            "100 Breast",
            "100 Fly",
            "200 IM",
        }

        event_factors = {
            k: v
            for k, v in data.get("event_factors", {}).items()
            if k in standard_events
        }
        confidence_tiers = {
            k: v
            for k, v in data.get("confidence_tiers", {}).items()
            if k in standard_events
        }

        return cls(
            default_factor=data.get("default_factor", DEFAULT_FACTOR),
            event_factors=event_factors,
            confidence_tiers=confidence_tiers,
        )

    @classmethod
    def disabled(cls) -> "ChampionshipFactors":
        """Create a no-op instance (for dual meets)."""
        return cls(enabled=False)


# Singleton — loaded once, used everywhere
CHAMPIONSHIP_FACTORS = ChampionshipFactors()


def adjust_time(
    seed_time: float, event_name: str, factors: ChampionshipFactors | None = None
) -> float:
    """Apply championship adjustment to a seed time.

    Args:
        seed_time: Original seed time in seconds
        event_name: Event name (e.g., "200 Free")
        factors: Optional custom factors instance (uses singleton if None)

    Returns:
        Adjusted time (lower = faster for championship projection)
    """
    if seed_time <= 0 or seed_time >= 599.0:
        return seed_time
    f = factors or CHAMPIONSHIP_FACTORS
    return seed_time * f.get_factor(event_name)


def adjust_times_df(
    df,
    time_col: str = "time",
    event_col: str = "event",
    factors: ChampionshipFactors | None = None,
):
    """Apply championship adjustment to a DataFrame of times in-place.

    Adds an 'adjusted_time' column and overwrites the time column.
    Original times are preserved in 'seed_time_raw'.

    Args:
        df: DataFrame with time and event columns
        time_col: Name of the time column
        event_col: Name of the event column
        factors: Optional custom factors instance

    Returns:
        DataFrame with adjusted times
    """
    import pandas as pd

    if time_col not in df.columns or event_col not in df.columns:
        return df

    f = factors or CHAMPIONSHIP_FACTORS
    if not f.enabled:
        return df

    # Preserve original
    df["seed_time_raw"] = df[time_col].copy()

    # Apply per-event factor
    df[time_col] = df.apply(
        lambda row: adjust_time(
            row[time_col] if pd.notna(row[time_col]) else 0.0,
            row[event_col],
            f,
        ),
        axis=1,
    )

    return df


def get_event_confidence(
    event_name: str, factors: ChampionshipFactors | None = None
) -> str:
    """Get confidence tier for an event's seed-based predictions."""
    f = factors or CHAMPIONSHIP_FACTORS
    return f.get_confidence(event_name)


def get_low_confidence_events(factors: ChampionshipFactors | None = None) -> list[str]:
    """Get list of events that should be flagged for coach review."""
    f = factors or CHAMPIONSHIP_FACTORS
    return [event for event, tier in f.confidence_tiers.items() if tier == "low"]
