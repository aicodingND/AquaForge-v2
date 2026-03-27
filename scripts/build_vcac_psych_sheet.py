#!/usr/bin/env python3
"""
VCAC Psych Sheet Builder

Merges scraped SwimCloud data with coach-provided Seton data
to create a unified psych sheet for VCAC Championship projection.

Usage:
    python3 build_vcac_psych_sheet.py

Output:
    data/vcac/VCAC_2026_unified_psych_sheet.json
"""

import json
import re

# Add project root to path
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


@dataclass
class PsychEntry:
    """Single entry in the psych sheet."""

    swimmer_name: str
    team_code: str
    team_name: str
    event: str
    seed_time: float
    gender: str
    grade: str | None = None
    is_diver: bool = False
    is_varsity: bool = True
    source: str = "swimcloud"


def normalize_event_name(event: str) -> str:
    """Normalize event names to standard format."""
    event = event.strip()

    # Remove gender prefix if present
    event = re.sub(r"^(Boys?|Girls?)\s+", "", event, flags=re.IGNORECASE)

    # Standardize common variations
    event = re.sub(r"\bFree(?:style)?\b", "Free", event, flags=re.IGNORECASE)
    event = re.sub(r"\bBack(?:stroke)?\b", "Back", event, flags=re.IGNORECASE)
    event = re.sub(r"\bBreast(?:stroke)?\b", "Breast", event, flags=re.IGNORECASE)
    event = re.sub(r"\bFly\b", "Fly", event, flags=re.IGNORECASE)
    event = re.sub(r"\bButterfly\b", "Fly", event, flags=re.IGNORECASE)
    event = re.sub(r"\bIM\b", "IM", event, flags=re.IGNORECASE)
    event = re.sub(r"\bIndividual Medley\b", "IM", event, flags=re.IGNORECASE)

    return event.strip()


def parse_time_to_seconds(time_val) -> float:
    """Parse time value to seconds."""
    if isinstance(time_val, (int, float)):
        return float(time_val)

    if isinstance(time_val, str):
        # Handle MM:SS.ss format
        if ":" in time_val:
            parts = time_val.split(":")
            minutes = int(parts[0])
            seconds = float(parts[1])
            return minutes * 60 + seconds
        # Handle SS.ss format
        return float(time_val.replace(",", "."))

    return 0.0


def load_scraped_team(json_path: Path) -> list[PsychEntry]:
    """Load a scraped team JSON file into psych entries."""
    if not json_path.exists():
        print(f"! File not found: {json_path}")
        return []

    with open(json_path) as f:
        data = json.load(f)

    team_code = data.get("team_code", "UNK")
    team_name = data.get("team_name", "Unknown")

    entries = []
    for time_entry in data.get("times", []):
        event = normalize_event_name(time_entry.get("event", ""))
        seed_time = parse_time_to_seconds(time_entry.get("seed_time", 0))

        if seed_time <= 0:
            continue

        # Determine gender from event name
        gender = time_entry.get("gender", "U")
        if gender == "U":
            if "boys" in time_entry.get("event", "").lower():
                gender = "M"
            elif "girls" in time_entry.get("event", "").lower():
                gender = "F"

        entry = PsychEntry(
            swimmer_name=time_entry.get("swimmer_name", "Unknown"),
            team_code=team_code,
            team_name=team_name,
            event=event,
            seed_time=seed_time,
            gender=gender,
            source="swimcloud",
        )
        entries.append(entry)

    return entries


def load_seton_excel_data(upload_dir: Path) -> list[PsychEntry]:
    """Load Seton data from coach Excel files."""
    # Look for Seton-specific Excel files
    seton_files = list(upload_dir.glob("Seton*.xlsx")) + list(
        upload_dir.glob("seton*.xlsx")
    )

    entries = []

    for excel_path in seton_files:
        print(f"Loading Seton file: {excel_path.name}")
        try:
            import pandas as pd

            df = pd.read_excel(excel_path)

            # Normalize column names
            df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

            # Map columns to expected format
            swimmer_col = next(
                (c for c in df.columns if "name" in c or "swimmer" in c), None
            )
            event_col = next((c for c in df.columns if "event" in c), None)
            time_col = next((c for c in df.columns if "time" in c), None)
            gender_col = next(
                (c for c in df.columns if "gender" in c or "sex" in c), None
            )

            if not all([swimmer_col, event_col, time_col]):
                print(f"! Missing required columns in {excel_path.name}")
                continue

            for _, row in df.iterrows():
                swimmer = str(row.get(swimmer_col, "")).strip()
                event = normalize_event_name(str(row.get(event_col, "")))
                time_val = row.get(time_col, 0)

                if not swimmer or not event:
                    continue

                seed_time = parse_time_to_seconds(time_val)
                if seed_time <= 0:
                    continue

                gender = "U"
                if gender_col:
                    gender = (
                        str(row.get(gender_col, "U")).upper()[0]
                        if row.get(gender_col)
                        else "U"
                    )

                entry = PsychEntry(
                    swimmer_name=swimmer,
                    team_code="SST",
                    team_name="Seton Swimming",
                    event=event,
                    seed_time=seed_time,
                    gender=gender,
                    source="coach_excel",
                )
                entries.append(entry)
        except Exception as e:
            print(f"! Error loading {excel_path.name}: {e}")

    return entries


def build_vcac_psych_sheet():
    """Build the unified VCAC psych sheet."""
    print("=" * 60)
    print("▸ VCAC Championship Psych Sheet Builder")
    print("=" * 60)

    project_root = Path(__file__).parent
    scraped_dir = project_root / "data" / "scraped"
    upload_dir = project_root / "uploads"
    output_dir = project_root / "data" / "vcac"

    output_dir.mkdir(parents=True, exist_ok=True)

    all_entries: list[PsychEntry] = []

    # Load scraped competitor data
    print("\n[1] Loading scraped competitor data...")

    team_files = {
        "ICS": "ICS_swimcloud.json",
        "TCS": "TCS_swimcloud.json",
        "FCS": "FCS_swimcloud.json",
        "DJO": "DJO_swimcloud.json",
        "OAK": "OAK_swimcloud.json",
        "BI": "BI_swimcloud.json",
        "PVI": "PVI_swimcloud.json",
    }

    for code, filename in team_files.items():
        json_path = scraped_dir / filename
        entries = load_scraped_team(json_path)
        print(f"{code}: {len(entries)} entries loaded")
        all_entries.extend(entries)

    # Load Seton data from coach Excel files
    print("\n[2] Loading Seton coach data...")
    seton_entries = load_seton_excel_data(upload_dir)
    print(f"SST: {len(seton_entries)} entries loaded")
    all_entries.extend(seton_entries)

    # Deduplicate (keep best time per swimmer-event)
    print("\n[3] Deduplicating entries...")
    deduped: dict[str, PsychEntry] = {}
    for entry in all_entries:
        key = f"{entry.team_code}:{entry.swimmer_name}:{entry.event}:{entry.gender}"
        if key not in deduped or entry.seed_time < deduped[key].seed_time:
            deduped[key] = entry

    final_entries = list(deduped.values())
    print(f"Before: {len(all_entries)}, After: {len(final_entries)}")

    # Summary by team
    print("\n[4] Summary by team:")
    team_counts = {}
    for entry in final_entries:
        team_counts[entry.team_code] = team_counts.get(entry.team_code, 0) + 1

    for code, count in sorted(team_counts.items(), key=lambda x: -x[1]):
        print(f"{code}: {count} entries")

    # Save unified psych sheet
    print("\n[5] Saving unified psych sheet...")
    output_path = output_dir / "VCAC_2026_unified_psych_sheet.json"

    output_data = {
        "meet": "VCAC Championship 2026",
        "date": "2026-02-07",
        "generated_at": datetime.now().isoformat(),
        "total_entries": len(final_entries),
        "teams": list(team_counts.keys()),
        "entries": [asdict(e) for e in final_entries],
    }

    with open(output_path, "w") as f:
        json.dump(output_data, f, indent=2)

    print(f"✓ Saved to: {output_path}")
    print(f"Total entries: {len(final_entries)}")
    print(f"Teams: {', '.join(team_counts.keys())}")

    print("\n" + "=" * 60)
    print("✓ VCAC Psych Sheet Build Complete!")
    print("=" * 60)

    return output_path


if __name__ == "__main__":
    build_vcac_psych_sheet()
