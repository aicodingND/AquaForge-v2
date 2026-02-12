"""
Seed Accuracy Analysis — Do seed times predict championship placements?

Parses championship HyTek databases and measures:
1. Seed-to-finals time drop distribution (how much faster do swimmers go?)
2. Placement flip rate (how often do seeds predict wrong order?)
3. Event-specific variance (which events are most/least predictable?)
4. Grade-based patterns (do younger swimmers improve more?)

This directly validates whether the optimizer's seed-based assignments are reliable.
"""

import json
import os
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from swim_ai_reflex.backend.etl.hytek_mdb_parser import MeetData, parse_mdb


@dataclass
class SeedVsFinals:
    """One swimmer's seed vs finals comparison."""

    meet_name: str
    event_name: str
    swimmer_name: str
    gender: str
    grade: int | None
    seed_time: float
    finals_time: float
    seed_place: int  # Place based on seed ordering
    finals_place: int  # Actual finishing place
    is_relay: bool

    @property
    def drop(self) -> float:
        """Time drop in seconds (positive = faster than seed)."""
        return self.seed_time - self.finals_time

    @property
    def drop_pct(self) -> float:
        """Drop as percentage of seed time."""
        if self.seed_time <= 0:
            return 0.0
        return (self.drop / self.seed_time) * 100

    @property
    def placement_flipped(self) -> bool:
        """Did the finals placement differ from seed placement?"""
        return self.seed_place != self.finals_place


def extract_seed_vs_finals(mdb_path: str) -> list[SeedVsFinals]:
    """Parse one MDB and extract all seed-vs-finals comparisons."""
    try:
        data: MeetData = parse_mdb(mdb_path)
    except Exception as e:
        print(f"  SKIP: {os.path.basename(mdb_path)} — {e}")
        return []

    if data.is_empty:
        return []

    meet_name = data.meet_info.name if data.meet_info else os.path.basename(mdb_path)

    # Build lookup maps
    athlete_map = {a.ath_no: a for a in data.athletes}
    event_map = {e.event_ptr: e for e in data.events}
    _team_map = {t.team_no: t for t in data.teams}  # noqa: F841

    # Group entries by event for placement comparison
    entries_by_event: dict[int, list] = defaultdict(list)
    for entry in data.entries:
        if entry.seed_time and entry.finals_time:
            if entry.seed_time > 0 and entry.finals_time > 0:
                if not entry.is_dq and not entry.is_exhibition:
                    entries_by_event[entry.event_ptr].append(entry)

    results = []

    for event_ptr, entries in entries_by_event.items():
        event = event_map.get(event_ptr)
        if not event or event.is_relay or event.is_diving:
            continue  # Skip relays and diving (different scoring)

        if len(entries) < 2:
            continue  # Need at least 2 swimmers to compare placements

        # Sort by seed time to get seed placements
        seed_sorted = sorted(entries, key=lambda e: e.seed_time)
        # Sort by finals time to get actual placements
        finals_sorted = sorted(entries, key=lambda e: e.finals_time)

        # Build placement maps
        seed_rank = {e.ath_no: i + 1 for i, e in enumerate(seed_sorted)}
        finals_rank = {e.ath_no: i + 1 for i, e in enumerate(finals_sorted)}

        for entry in entries:
            athlete = athlete_map.get(entry.ath_no)
            if not athlete:
                continue

            name = f"{athlete.first_name} {athlete.last_name}".strip()
            gender = athlete.gender or event.gender or "?"

            results.append(
                SeedVsFinals(
                    meet_name=meet_name or "Unknown",
                    event_name=event.event_name,
                    swimmer_name=name,
                    gender=gender,
                    grade=athlete.school_year,
                    seed_time=entry.seed_time,
                    finals_time=entry.finals_time,
                    seed_place=seed_rank[entry.ath_no],
                    finals_place=finals_rank[entry.ath_no],
                    is_relay=False,
                )
            )

    return results


def analyze_results(all_results: list[SeedVsFinals]) -> None:
    """Print comprehensive analysis of seed accuracy."""
    if not all_results:
        print("No data to analyze.")
        return

    n = len(all_results)
    print(f"\n{'=' * 70}")
    print(
        f"SEED ACCURACY ANALYSIS — {n:,} swim entries across {len(set(r.meet_name for r in all_results))} meets"
    )
    print(f"{'=' * 70}")

    # --- 1. Time Drop Distribution ---
    drops = [r.drop for r in all_results]
    drop_pcts = [r.drop_pct for r in all_results]

    avg_drop = sum(drops) / n
    avg_drop_pct = sum(drop_pcts) / n
    median_drop = sorted(drops)[n // 2]
    median_drop_pct = sorted(drop_pcts)[n // 2]

    faster_count = sum(1 for d in drops if d > 0)
    slower_count = sum(1 for d in drops if d < 0)
    same_count = sum(1 for d in drops if d == 0)

    print("\n--- TIME DROP (seed - finals) ---")
    print(f"  Avg drop:    {avg_drop:+.2f}s ({avg_drop_pct:+.2f}%)")
    print(f"  Median drop: {median_drop:+.2f}s ({median_drop_pct:+.2f}%)")
    print(f"  Swam faster: {faster_count:,} ({faster_count / n * 100:.1f}%)")
    print(f"  Swam slower: {slower_count:,} ({slower_count / n * 100:.1f}%)")
    print(f"  Same time:   {same_count:,} ({same_count / n * 100:.1f}%)")

    # Percentiles
    sorted_pcts = sorted(drop_pcts)
    p10 = sorted_pcts[int(n * 0.10)]
    p25 = sorted_pcts[int(n * 0.25)]
    p75 = sorted_pcts[int(n * 0.75)]
    p90 = sorted_pcts[int(n * 0.90)]
    print("\n  Drop % distribution:")
    print(f"    10th pctile: {p10:+.2f}%  (worst 10% went this much slower)")
    print(f"    25th pctile: {p25:+.2f}%")
    print(f"    Median:      {median_drop_pct:+.2f}%")
    print(f"    75th pctile: {p75:+.2f}%")
    print(f"    90th pctile: {p90:+.2f}%  (best 10% dropped this much)")

    # --- 2. Placement Flip Rate ---
    flips = sum(1 for r in all_results if r.placement_flipped)
    flip_rate = flips / n * 100

    # How many places did they flip by?
    flip_magnitudes = [
        abs(r.finals_place - r.seed_place) for r in all_results if r.placement_flipped
    ]
    avg_flip = sum(flip_magnitudes) / len(flip_magnitudes) if flip_magnitudes else 0

    # Top-3 stability (do seeds predict podium correctly?)
    top3_seed = [r for r in all_results if r.seed_place <= 3]
    top3_stayed = sum(1 for r in top3_seed if r.finals_place <= 3)
    top3_rate = top3_stayed / len(top3_seed) * 100 if top3_seed else 0

    # Scoring-place stability (do seeds predict top-12 correctly?)
    top12_seed = [r for r in all_results if r.seed_place <= 12]
    top12_stayed = sum(1 for r in top12_seed if r.finals_place <= 12)
    top12_rate = top12_stayed / len(top12_seed) * 100 if top12_seed else 0

    print("\n--- PLACEMENT FLIP RATE ---")
    print(f"  Any flip:        {flips:,} / {n:,} ({flip_rate:.1f}%)")
    print(f"  Avg flip size:   {avg_flip:.1f} places")
    print(
        f"  Top-3 stability: {top3_stayed}/{len(top3_seed)} seeds stayed top-3 ({top3_rate:.1f}%)"
    )
    print(
        f"  Top-12 stability: {top12_stayed}/{len(top12_seed)} seeds stayed top-12 ({top12_rate:.1f}%)"
    )

    # --- 3. Event-Specific Variance ---
    events: dict[str, list[SeedVsFinals]] = defaultdict(list)
    for r in all_results:
        events[r.event_name].append(r)

    print("\n--- EVENT-SPECIFIC ACCURACY ---")
    print(
        f"  {'Event':<20} {'N':>5} {'Avg Drop%':>10} {'Flip%':>8} {'Top3 Stable':>12}"
    )
    print(f"  {'-' * 55}")

    for event_name in sorted(events.keys()):
        ev_results = events[event_name]
        ev_n = len(ev_results)
        if ev_n < 5:
            continue
        ev_drop_pct = sum(r.drop_pct for r in ev_results) / ev_n
        ev_flips = sum(1 for r in ev_results if r.placement_flipped) / ev_n * 100
        ev_top3 = [r for r in ev_results if r.seed_place <= 3]
        ev_top3_stable = (
            sum(1 for r in ev_top3 if r.finals_place <= 3) / len(ev_top3) * 100
            if ev_top3
            else 0
        )
        print(
            f"  {event_name:<20} {ev_n:>5} {ev_drop_pct:>+9.2f}% {ev_flips:>7.1f}% {ev_top3_stable:>10.1f}%"
        )

    # --- 4. Grade-Based Patterns ---
    grades: dict[int, list[SeedVsFinals]] = defaultdict(list)
    for r in all_results:
        if r.grade and 7 <= r.grade <= 12:
            grades[r.grade].append(r)

    if grades:
        print("\n--- GRADE-BASED DROP ---")
        print(f"  {'Grade':>6} {'N':>5} {'Avg Drop%':>10} {'Flip%':>8}")
        print(f"  {'-' * 35}")
        for grade in sorted(grades.keys()):
            g_results = grades[grade]
            g_n = len(g_results)
            g_drop_pct = sum(r.drop_pct for r in g_results) / g_n
            g_flips = sum(1 for r in g_results if r.placement_flipped) / g_n * 100
            print(f"  {grade:>6} {g_n:>5} {g_drop_pct:>+9.2f}% {g_flips:>7.1f}%")

    # --- 5. Optimizer Implication ---
    print("\n--- OPTIMIZER IMPLICATIONS ---")
    if flip_rate < 30:
        print(
            f"  FINDING: Placement flip rate is {flip_rate:.1f}% — SEED RANKINGS ARE RELIABLE."
        )
        print(
            "  The optimizer's event-swimmer assignments based on seed times will hold"
        )
        print(
            f"  in ~{100 - flip_rate:.0f}% of cases. Focus on search quality, not seed accuracy."
        )
    elif flip_rate < 50:
        print(
            f"  FINDING: Placement flip rate is {flip_rate:.1f}% — MODERATE SEED RELIABILITY."
        )
        print(
            "  Seed-based assignments are right more often than wrong, but close races"
        )
        print("  flip frequently. Consider sensitivity analysis for close placements.")
    else:
        print(
            f"  FINDING: Placement flip rate is {flip_rate:.1f}% — SEEDS ARE UNRELIABLE."
        )
        print(
            "  The optimizer needs better seed inputs. Priority: recent-meet weighting,"
        )
        print("  championship taper factors, or ML-based time prediction.")

    if top3_rate > 70:
        print(
            f"  TOP-3 STABILITY: {top3_rate:.0f}% — top seeds reliably win. Optimizer should"
        )
        print("  focus on mid-pack placements (4th-8th) where flips matter most.")

    avg_drop_sec = abs(avg_drop)
    print(
        f"\n  CHAMPIONSHIP ADJUSTMENT: Swimmers are on average {avg_drop_sec:.2f}s ({abs(avg_drop_pct):.2f}%)"
    )
    if avg_drop > 0:
        print("  faster at championships than their seed times suggest.")
        print(
            f"  Recommendation: Apply a {abs(avg_drop_pct):.1f}% speed-up factor to seed times"
        )
        print("  when projecting championship performance.")
    else:
        print("  slower at championships than their seed times suggest.")
        print("  Seeds may already include best times — no taper adjustment needed.")


def export_championship_factors(
    all_results: list[SeedVsFinals], output_path: Path
) -> dict:
    """Export per-event championship adjustment factors as JSON.

    Returns dict with:
    - default_factor: uniform baseline (1 - avg_drop_pct/100)
    - event_factors: {event_name: factor} for events with N >= 20
    - confidence_tiers: {event_name: "high"|"medium"|"low"}
    - stats: raw statistics for each event
    """
    if not all_results:
        return {}

    # Overall factor
    n = len(all_results)
    avg_drop_pct = sum(r.drop_pct for r in all_results) / n
    default_factor = 1.0 - (avg_drop_pct / 100.0)

    # Per-event analysis
    events: dict[str, list[SeedVsFinals]] = defaultdict(list)
    for r in all_results:
        events[r.event_name].append(r)

    event_factors = {}
    confidence_tiers = {}
    stats = {}

    # Minimum sample size for per-event factors
    MIN_SAMPLES = 20

    for event_name, ev_results in sorted(events.items()):
        ev_n = len(ev_results)
        if ev_n < MIN_SAMPLES:
            continue

        ev_drop_pct = sum(r.drop_pct for r in ev_results) / ev_n
        ev_flip_rate = sum(1 for r in ev_results if r.placement_flipped) / ev_n * 100

        ev_top3 = [r for r in ev_results if r.seed_place <= 3]
        ev_top3_stable = (
            sum(1 for r in ev_top3 if r.finals_place <= 3) / len(ev_top3) * 100
            if ev_top3
            else 0
        )

        ev_top12 = [r for r in ev_results if r.seed_place <= 12]
        ev_top12_stable = (
            sum(1 for r in ev_top12 if r.finals_place <= 12) / len(ev_top12) * 100
            if ev_top12
            else 0
        )

        # Championship factor for this event
        factor = 1.0 - (ev_drop_pct / 100.0)
        event_factors[event_name] = round(factor, 4)

        # Confidence tier based on flip rate and top-3 stability
        if ev_flip_rate < 72 and ev_top3_stable > 75:
            tier = "high"
        elif ev_flip_rate < 82 and ev_top3_stable > 60:
            tier = "medium"
        else:
            tier = "low"

        confidence_tiers[event_name] = tier

        stats[event_name] = {
            "n": ev_n,
            "avg_drop_pct": round(ev_drop_pct, 3),
            "flip_rate_pct": round(ev_flip_rate, 1),
            "top3_stability_pct": round(ev_top3_stable, 1),
            "top12_stability_pct": round(ev_top12_stable, 1),
            "factor": round(factor, 4),
            "confidence": tier,
        }

    result = {
        "source": "scripts/analyze_seed_accuracy.py",
        "total_entries": n,
        "total_meets": len(set(r.meet_name for r in all_results)),
        "default_factor": round(default_factor, 4),
        "event_factors": event_factors,
        "confidence_tiers": confidence_tiers,
        "event_stats": stats,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)

    print(f"\nExported championship factors to {output_path}")
    return result


def main():
    db_dir = (
        Path(__file__).resolve().parent.parent
        / "data"
        / "organized"
        / "hytek_databases"
    )

    if not db_dir.exists():
        print(f"Database directory not found: {db_dir}")
        sys.exit(1)

    # Find championship-related MDB files
    mdb_files = sorted(db_dir.glob("*.mdb"))
    championship_keywords = ["champ", "state", "vcac", "invite", "invitational"]

    championship_mdbs = [
        f
        for f in mdb_files
        if any(kw in f.name.lower() for kw in championship_keywords)
    ]

    print(
        f"Found {len(championship_mdbs)} championship databases out of {len(mdb_files)} total"
    )
    print("Parsing...\n")

    all_results: list[SeedVsFinals] = []

    for i, mdb_path in enumerate(championship_mdbs):
        name = mdb_path.name
        print(f"  [{i + 1}/{len(championship_mdbs)}] {name[:60]}...")
        results = extract_seed_vs_finals(str(mdb_path))
        if results:
            print(f"    -> {len(results)} seed-vs-finals pairs")
            all_results.extend(results)
        else:
            print("    -> no valid pairs")

    analyze_results(all_results)

    # Export per-event championship factors
    factors_path = (
        Path(__file__).resolve().parent.parent / "data" / "championship_factors.json"
    )
    export_championship_factors(all_results, factors_path)

    # Also output per-meet summary
    meets = defaultdict(list)
    for r in all_results:
        meets[r.meet_name].append(r)

    print("\n--- PER-MEET SUMMARY ---")
    print(f"  {'Meet':<45} {'N':>5} {'Drop%':>8} {'Flip%':>8}")
    print(f"  {'-' * 70}")
    for meet_name in sorted(meets.keys()):
        m = meets[meet_name]
        m_n = len(m)
        m_drop = sum(r.drop_pct for r in m) / m_n
        m_flip = sum(1 for r in m if r.placement_flipped) / m_n * 100
        print(f"  {meet_name[:45]:<45} {m_n:>5} {m_drop:>+7.2f}% {m_flip:>7.1f}%")


if __name__ == "__main__":
    main()
