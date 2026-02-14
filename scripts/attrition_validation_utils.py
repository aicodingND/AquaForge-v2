"""
Attrition Validation Utilities — shared helpers for all 3 validation experiments.

Used by:
  - validate_attrition_calibration.py (Experiment 2)
  - validate_attrition_holdout.py (Experiment 3)
  - validate_attrition_ab.py (Experiment 1)
"""

import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Reuse parsing infrastructure from the original rate computation script
from scripts.compute_dq_dns_rates import MDB_DIRS, process_mdb
from swim_ai_reflex.backend.core.attrition_model import STANDARD_EVENTS

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "data" / "attrition_validation"


def ensure_output_dir() -> Path:
    """Create output directory if it doesn't exist."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR


def load_all_mdb_stats() -> list[dict]:
    """Parse all MDB files and return per-meet stats dicts.

    Each dict has: {meet_name, meet_type, events: defaultdict({total, dq, dns, ...})}
    """
    mdb_paths = []
    for mdb_dir in MDB_DIRS:
        full_dir = PROJECT_ROOT / mdb_dir
        if full_dir.exists():
            for f in full_dir.iterdir():
                if f.suffix.lower() == ".mdb":
                    mdb_paths.append(str(f))

    if not mdb_paths:
        print("WARNING: No MDB files found. Check MDB_DIRS paths.")
        return []

    all_stats = []
    total = len(mdb_paths)
    for i, path in enumerate(sorted(mdb_paths)):
        if (i + 1) % 50 == 0 or i == 0:
            print(f"  Parsing MDB {i + 1}/{total}...")
        stats = process_mdb(path)
        if stats:
            all_stats.append(stats)

    print(f"  Parsed {len(all_stats)}/{total} MDB files successfully")
    return all_stats


def compute_per_meet_event_dns_rates(
    all_stats: list[dict],
) -> list[dict[str, Any]]:
    """For each meet, compute observed DNS rate per standard event.

    Returns list of:
      {
        "meet_name": str,
        "meet_type": str,
        "events": {event_name: {"total": int, "dns": int, "rate": float}}
      }
    """
    results = []
    for stats in all_stats:
        meet_result: dict[str, Any] = {
            "meet_name": stats["meet_name"],
            "meet_type": stats["meet_type"],
            "events": {},
        }
        for event_name, ev in stats["events"].items():
            if event_name not in STANDARD_EVENTS:
                continue
            total = ev["total"] - ev.get("exhibition", 0)
            dns = ev["dns"]
            if total > 0:
                meet_result["events"][event_name] = {
                    "total": total,
                    "dns": dns,
                    "rate": dns / total,
                }
        results.append(meet_result)
    return results


def build_rates_from_stats(stats_list: list[dict]) -> dict[str, float]:
    """Compute aggregate DNS rates per event from a subset of meets.

    Same logic as compute_dq_dns_rates.aggregate_rates() but returns just
    the dns_rate dict for AttritionRates construction.
    """
    event_totals: dict[str, dict[str, int]] = defaultdict(
        lambda: {"total": 0, "dns": 0}
    )
    for stats in stats_list:
        for event_name, ev in stats["events"].items():
            if event_name not in STANDARD_EVENTS:
                continue
            non_exh = ev["total"] - ev.get("exhibition", 0)
            event_totals[event_name]["total"] += non_exh
            event_totals[event_name]["dns"] += ev["dns"]

    dns_rates = {}
    for event_name, et in event_totals.items():
        if et["total"] >= 50:
            dns_rates[event_name] = et["dns"] / et["total"]
    return dns_rates


def compute_default_dns_from_stats(stats_list: list[dict]) -> float:
    """Compute global default DNS rate from a subset of meets."""
    total_dns = 0
    total_entries = 0
    for stats in stats_list:
        for ev in stats["events"].values():
            non_exh = ev["total"] - ev.get("exhibition", 0)
            total_dns += ev["dns"]
            total_entries += non_exh
    return total_dns / total_entries if total_entries > 0 else 0.20


def print_table(
    headers: list[str],
    rows: list[list[str]],
    col_widths: list[int] | None = None,
) -> None:
    """Simple tabular printer for console output."""
    if not rows:
        print("  (no data)")
        return
    if col_widths is None:
        col_widths = [
            max(
                len(str(h)),
                max((len(str(r[i])) for r in rows), default=4),
            )
            + 2
            for i, h in enumerate(headers)
        ]
    header_line = "".join(h.ljust(w) for h, w in zip(headers, col_widths))
    print(f"  {header_line}")
    print(f"  {'-' * sum(col_widths)}")
    for row in rows:
        print("  " + "".join(str(v).ljust(w) for v, w in zip(row, col_widths)))
