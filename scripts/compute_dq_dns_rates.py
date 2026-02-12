"""
DQ/DNS Rate Aggregation — Compute attrition probabilities from historical HyTek MDBs.

Parses all available MDB databases and calculates:
1. Global DQ and DNS rates
2. Per-event DQ and DNS rates
3. Meet-type breakdowns (championship vs dual vs invitational)
4. Relay-specific DQ rates

Output: data/dq_dns_rates.json for use by the AttritionRates module.
"""

import json
import os
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from swim_ai_reflex.backend.etl.hytek_mdb_parser import MeetData, parse_mdb

# Directories containing HyTek MDB files
MDB_DIRS = [
    "data/organized/hytek_databases",
]

# Heuristic: classify meet type from meet name
CHAMPIONSHIP_KEYWORDS = [
    "championship",
    "champ",
    "state",
    "vcac",
    "visaa",
    "dac",
    "invitational",
    "invite",
]


def classify_meet_type(meet_name: str) -> str:
    """Classify meet as championship/invitational or dual based on name."""
    lower = meet_name.lower()
    for kw in CHAMPIONSHIP_KEYWORDS:
        if kw in lower:
            return "championship"
    if "dual" in lower or "time trial" in lower or "timetrial" in lower:
        return "dual"
    return "other"


def normalize_event_name(raw: str) -> str:
    """Normalize event names to standard form (e.g. '200 Free', '100 Back')."""
    raw = raw.strip()
    # Remove gender/age prefixes like "Girls ", "Boys ", "11-12 "
    for prefix in ["Girls ", "Boys ", "Mixed "]:
        if raw.startswith(prefix):
            raw = raw[len(prefix) :]
    # Remove age group prefixes
    import re

    raw = re.sub(r"^\d+-\d+\s+", "", raw)
    raw = re.sub(r"^Open\s+", "", raw)

    # Map stroke abbreviations
    stroke_map = {
        "Freestyle": "Free",
        "Backstroke": "Back",
        "Breaststroke": "Breast",
        "Butterfly": "Fly",
        "Individual Medley": "IM",
        "Medley Relay": "Medley Relay",
        "Freestyle Relay": "Free Relay",
        "FR": "Free",
        "BK": "Back",
        "BR": "Breast",
        "FL": "Fly",
    }
    for long, short in stroke_map.items():
        raw = raw.replace(long, short)

    return raw.strip()


def process_mdb(mdb_path: str) -> dict:
    """Parse one MDB and extract DQ/DNS statistics."""
    try:
        data: MeetData = parse_mdb(mdb_path)
    except Exception:
        return {}

    if data.is_empty:
        return {}

    meet_name = data.meet_info.name if data.meet_info else os.path.basename(mdb_path)
    meet_type = classify_meet_type(meet_name or os.path.basename(mdb_path))

    event_map = {e.event_ptr: e for e in data.events}

    stats: dict = {
        "meet_name": meet_name,
        "meet_type": meet_type,
        "events": defaultdict(
            lambda: {
                "total": 0,
                "dq": 0,
                "dns": 0,
                "completed": 0,
                "exhibition": 0,
                "is_relay": False,
            }
        ),
    }

    # Process individual entries
    for entry in data.entries:
        evt = event_map.get(entry.event_ptr)
        if not evt:
            continue

        event_name = normalize_event_name(evt.event_name)
        if not event_name:
            continue

        ev_stats = stats["events"][event_name]
        ev_stats["is_relay"] = evt.is_relay
        ev_stats["total"] += 1

        if entry.is_exhibition:
            ev_stats["exhibition"] += 1
        elif entry.is_dq:
            ev_stats["dq"] += 1
        elif entry.is_dns:
            ev_stats["dns"] += 1
        elif entry.finals_time is not None and entry.finals_time > 0:
            ev_stats["completed"] += 1
        else:
            # No finals time, no seed time, not DQ — could be unswum entry
            ev_stats["dns"] += 1

    # Process relay entries
    for relay in data.relays:
        evt = event_map.get(relay.event_ptr)
        if not evt:
            continue

        event_name = normalize_event_name(evt.event_name)
        if not event_name:
            continue

        ev_stats = stats["events"][event_name]
        ev_stats["is_relay"] = True
        ev_stats["total"] += 1

        if relay.is_dq:
            ev_stats["dq"] += 1
        elif relay.finals_time is not None and relay.finals_time > 0:
            ev_stats["completed"] += 1
        else:
            ev_stats["dns"] += 1

    return stats


def aggregate_rates(all_stats: list[dict]) -> dict:
    """Aggregate per-MDB stats into overall rates."""
    # Accumulate by event
    event_totals: dict[str, dict] = defaultdict(
        lambda: {"total": 0, "dq": 0, "dns": 0, "completed": 0, "is_relay": False}
    )
    # Accumulate by meet type
    meet_type_totals: dict[str, dict] = defaultdict(
        lambda: {"total": 0, "dq": 0, "dns": 0, "completed": 0}
    )
    global_total = {"total": 0, "dq": 0, "dns": 0, "completed": 0}
    meets_parsed = 0

    for stats in all_stats:
        if not stats:
            continue
        meets_parsed += 1
        mt = stats["meet_type"]

        for event_name, ev in stats["events"].items():
            # Skip events with no entries
            if ev["total"] == 0:
                continue

            # Accumulate event-level
            et = event_totals[event_name]
            et["total"] += ev["total"]
            et["dq"] += ev["dq"]
            et["dns"] += ev["dns"]
            et["completed"] += ev["completed"]
            et["is_relay"] = et["is_relay"] or ev["is_relay"]

            # Accumulate meet-type level (exclude exhibition from totals)
            non_exh = ev["total"] - ev.get("exhibition", 0)
            meet_type_totals[mt]["total"] += non_exh
            meet_type_totals[mt]["dq"] += ev["dq"]
            meet_type_totals[mt]["dns"] += ev["dns"]
            meet_type_totals[mt]["completed"] += ev["completed"]

            # Global
            global_total["total"] += non_exh
            global_total["dq"] += ev["dq"]
            global_total["dns"] += ev["dns"]
            global_total["completed"] += ev["completed"]

    def safe_rate(count: int, total: int) -> float:
        return round(count / total, 5) if total > 0 else 0.0

    # Build per-event rates (minimum 20 entries)
    by_event = {}
    for event_name, et in sorted(event_totals.items()):
        if et["total"] < 20:
            continue
        by_event[event_name] = {
            "dq_rate": safe_rate(et["dq"], et["total"]),
            "dns_rate": safe_rate(et["dns"], et["total"]),
            "completion_rate": safe_rate(et["completed"], et["total"]),
            "n": et["total"],
            "dq_count": et["dq"],
            "dns_count": et["dns"],
            "is_relay": et["is_relay"],
        }

    # Build per-meet-type rates
    by_meet_type = {}
    for mt, mtt in sorted(meet_type_totals.items()):
        if mtt["total"] < 50:
            continue
        by_meet_type[mt] = {
            "dq_rate": safe_rate(mtt["dq"], mtt["total"]),
            "dns_rate": safe_rate(mtt["dns"], mtt["total"]),
            "n": mtt["total"],
        }

    return {
        "global_dq_rate": safe_rate(global_total["dq"], global_total["total"]),
        "global_dns_rate": safe_rate(global_total["dns"], global_total["total"]),
        "global_completion_rate": safe_rate(
            global_total["completed"], global_total["total"]
        ),
        "global_n": global_total["total"],
        "meets_parsed": meets_parsed,
        "by_event": by_event,
        "by_meet_type": by_meet_type,
    }


def main():
    project_root = Path(__file__).resolve().parent.parent

    # Collect all MDB paths
    mdb_paths = []
    for mdb_dir in MDB_DIRS:
        full_dir = project_root / mdb_dir
        if full_dir.exists():
            for f in full_dir.iterdir():
                if f.suffix.lower() == ".mdb":
                    mdb_paths.append(str(f))

    print(f"Found {len(mdb_paths)} MDB files to process")
    if not mdb_paths:
        print("No MDB files found. Check MDB_DIRS paths.")
        return

    # Process all MDBs
    all_stats = []
    success = 0
    for i, path in enumerate(sorted(mdb_paths)):
        if (i + 1) % 50 == 0 or i == 0:
            print(f"  Processing {i + 1}/{len(mdb_paths)}...")
        stats = process_mdb(path)
        if stats:
            all_stats.append(stats)
            success += 1

    print(f"\nSuccessfully parsed {success}/{len(mdb_paths)} MDBs")

    # Aggregate rates
    rates = aggregate_rates(all_stats)

    # Print summary
    print(f"\n{'=' * 60}")
    print("DQ/DNS RATE SUMMARY")
    print(f"{'=' * 60}")
    print(f"Total entries:       {rates['global_n']:,}")
    print(f"Meets parsed:        {rates['meets_parsed']}")
    print(f"Global DQ rate:      {rates['global_dq_rate'] * 100:.2f}%")
    print(f"Global DNS rate:     {rates['global_dns_rate'] * 100:.2f}%")
    print(f"Global completion:   {rates['global_completion_rate'] * 100:.1f}%")

    print(f"\n{'Event':<30} {'N':>6} {'DQ%':>7} {'DNS%':>7} {'Relay':>6}")
    print("-" * 58)
    for event, info in sorted(
        rates["by_event"].items(), key=lambda x: -x[1]["dq_rate"]
    ):
        if info["n"] >= 50:
            print(
                f"{event:<30} {info['n']:>6} "
                f"{info['dq_rate'] * 100:>6.2f}% "
                f"{info['dns_rate'] * 100:>6.2f}% "
                f"{'Yes' if info['is_relay'] else 'No':>6}"
            )

    print(f"\n{'Meet Type':<20} {'N':>8} {'DQ%':>7} {'DNS%':>7}")
    print("-" * 44)
    for mt, info in sorted(rates["by_meet_type"].items()):
        print(
            f"{mt:<20} {info['n']:>8} "
            f"{info['dq_rate'] * 100:>6.2f}% "
            f"{info['dns_rate'] * 100:>6.2f}%"
        )

    # Write output
    output_path = project_root / "data" / "dq_dns_rates.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(rates, f, indent=2)
    print(f"\nWrote rates to {output_path}")


if __name__ == "__main__":
    main()
