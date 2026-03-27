#!/usr/bin/env python3
"""
Data Merger: Combines HY3 championship data with SwimCloud scraped data
Creates a unified psych sheet for VCAC Championship projections
"""

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path


def load_scraped_data(scraped_dir: Path) -> list[dict]:
    """Load all scraped SwimCloud data."""
    all_times = []

    for json_file in scraped_dir.glob("*_swimcloud.json"):
        try:
            with open(json_file) as f:
                data = json.load(f)
                times = data.get("times", [])
                all_times.extend(times)
                print(f"▸ {json_file.name}: {len(times)} times")
        except Exception as e:
            print(f"! Error loading {json_file.name}: {e}")

    return all_times


def load_hy3_psych_sheet(psych_sheet_path: Path) -> dict:
    """Load existing HY3-based psych sheet."""
    with open(psych_sheet_path) as f:
        return json.load(f)


def normalize_event_name(event: str) -> str:
    """Normalize event names for matching."""
    # Standardize format: "Boys 50 Free" or "Girls 100 Back"
    event = event.strip()

    # Handle various formats
    replacements = {
        "Freestyle": "Free",
        "Backstroke": "Back",
        "Breaststroke": "Breast",
        "Butterfly": "Fly",
        "Individual Medley": "IM",
        "Men": "Boys",
        "Women": "Girls",
        "Male": "Boys",
        "Female": "Girls",
    }

    for old, new in replacements.items():
        event = event.replace(old, new)

    return event


def merge_data(hy3_data: dict, scraped_times: list[dict]) -> dict:
    """
    Merge HY3 and scraped data.
    Strategy: Keep the FASTER time for each swimmer/event combo.
    """
    # Build lookup: (swimmer_name_lower, event_normalized) -> best_entry
    best_times = {}

    # First, add all HY3 entries
    for entry in hy3_data.get("entries", []):
        swimmer = entry["swimmer_name"].lower().strip()
        event = normalize_event_name(entry["event"])
        key = (swimmer, event)

        seed_time = entry.get("seed_time", 0)
        if seed_time and seed_time > 0:
            if key not in best_times or seed_time < best_times[key]["seed_time"]:
                best_times[key] = {
                    "swimmer_name": entry["swimmer_name"],
                    "team": entry["team"],
                    "event": event,
                    "seed_time": seed_time,
                    "gender": entry.get("gender", ""),
                    "grade": entry.get("grade"),
                    "source": "hy3",
                }

    print(f"\n▸ HY3 entries: {len(best_times)}")

    # Now add scraped data, keeping faster times
    scraped_added = 0
    scraped_improved = 0

    for entry in scraped_times:
        swimmer = entry["swimmer_name"].lower().strip()
        event = normalize_event_name(entry["event"])
        key = (swimmer, event)

        seed_time = entry.get("seed_time", 0)
        if not seed_time or seed_time <= 0:
            continue

        if key not in best_times:
            # New entry from scraped data
            best_times[key] = {
                "swimmer_name": entry["swimmer_name"],
                "team": entry["team"],
                "event": event,
                "seed_time": seed_time,
                "gender": entry.get("gender", ""),
                "grade": None,
                "source": "swimcloud",
            }
            scraped_added += 1
        elif seed_time < best_times[key]["seed_time"]:
            # Faster time from scraped data
            best_times[key]["seed_time"]
            best_times[key]["seed_time"] = seed_time
            best_times[key]["source"] = "swimcloud"
            scraped_improved += 1

    print(f"▸ New from SwimCloud: {scraped_added}")
    print(f"▸ Improved times: {scraped_improved}")
    print(f"▸ Total entries: {len(best_times)}")

    # Build merged output
    merged_entries = sorted(
        best_times.values(), key=lambda x: (x["event"], x["seed_time"])
    )

    # Get all unique teams
    all_teams = sorted(set(e["team"] for e in merged_entries))

    return {
        "meet_name": "2026 VCAC Championship - Unified Projection",
        "meet_date": "2026-02-07",
        "meet_profile": "vcac_championship",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "data_sources": ["HY3 Championship Data", "SwimCloud Scraped Data"],
        "teams": all_teams,
        "total_entries": len(merged_entries),
        "entries": merged_entries,
    }


def generate_summary_stats(merged_data: dict) -> dict:
    """Generate summary statistics for the merged data."""
    entries = merged_data["entries"]

    # Count by team
    by_team = defaultdict(int)
    for e in entries:
        by_team[e["team"]] += 1

    # Count by event
    by_event = defaultdict(int)
    for e in entries:
        by_event[e["event"]] += 1

    # Count by source
    by_source = defaultdict(int)
    for e in entries:
        by_source[e.get("source", "unknown")] += 1

    return {
        "by_team": dict(sorted(by_team.items(), key=lambda x: -x[1])),
        "by_event": dict(sorted(by_event.items())),
        "by_source": dict(by_source),
    }


def main():
    print("→ Starting Data Merge")
    print("=" * 60)

    base_dir = Path(".")
    scraped_dir = base_dir / "data" / "scraped"
    championship_dir = base_dir / "data" / "championship_data"

    # Load data sources
    print("\nLoading data sources...")

    # Load HY3 psych sheet
    hy3_path = championship_dir / "vcac_2026_psych_sheet_projection.json"
    hy3_data = load_hy3_psych_sheet(hy3_path)
    print(f"▸ HY3 Psych Sheet: {len(hy3_data.get('entries', []))} entries")

    # Load scraped data
    print("\nLoading scraped SwimCloud data...")
    scraped_times = load_scraped_data(scraped_dir)
    print(f"▸ Total scraped: {len(scraped_times)} times")

    # Merge
    print("\nMerging data sources...")
    merged = merge_data(hy3_data, scraped_times)

    # Generate stats
    stats = generate_summary_stats(merged)

    # Save merged output
    output_path = championship_dir / "vcac_2026_unified_psych_sheet.json"
    with open(output_path, "w") as f:
        json.dump(merged, f, indent=2)

    print(f"\n✓ Saved merged data to: {output_path}")

    # Print summary
    print("\n" + "=" * 60)
    print("▸ MERGE SUMMARY")
    print("=" * 60)

    print("\n▸ Entries by Team:")
    for team, count in stats["by_team"].items():
        print(f"{team}: {count}")

    print("\n▸ Entries by Source:")
    for source, count in stats["by_source"].items():
        print(f"{source}: {count}")

    print("\nTop Events:")
    for event, count in list(stats["by_event"].items())[:10]:
        print(f"{event}: {count}")

    print("\n" + "=" * 60)
    print(f"Total: {merged['total_entries']} entries from {len(merged['teams'])} teams")
    print("=" * 60)


if __name__ == "__main__":
    main()
