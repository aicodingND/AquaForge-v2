"""
HY3 File Parser — Adapter for hytek-parser library.

Converts HyTek Meet Manager .hy3 files into the standard AquaForge
DataFrame format (swimmer, event, time, team, grade, gender, is_relay).

HY3 is HyTek's proprietary fixed-width format used by virtually every
high school and club swim team in the US. Supporting it removes the #1
onboarding barrier for coaches.

Record types handled via hytek-parser:
  A1 — File description
  B1 — Meet info
  C1 — Team ID
  D1 — Swimmer entry (name, gender, age, DOB, team code)
  E1 — Individual event entry (distance, stroke, seed time)
  E2 — Event result (finals/prelim time, heat, lane, place)
  F1 — Relay entry
  G1 — Split records

Usage:
    from swim_ai_reflex.backend.core.hy3_parser import parse_hy3_file
    df = parse_hy3_file("/path/to/meet.hy3")
"""

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

# Stroke enum value → canonical AquaForge event name fragment
_STROKE_MAP = {
    "FREESTYLE": "Free",
    "BACKSTROKE": "Back",
    "BREASTSTROKE": "Breast",
    "BUTTERFLY": "Fly",
    "MEDLEY": "IM",
}

# Gender enum → prefix
_GENDER_PREFIX = {
    "MALE": "Boys",
    "FEMALE": "Girls",
}


def _format_event_name(
    distance: int, stroke_name: str, is_relay: bool, gender_name: str
) -> str:
    """Build canonical event name like 'Girls 200 Free' or 'Boys 200 Medley Relay'."""
    stroke_label = _STROKE_MAP.get(stroke_name, stroke_name.title())

    if is_relay:
        if stroke_label == "IM":
            stroke_label = "Medley"
        name = f"{distance} {stroke_label} Relay"
    elif stroke_label == "IM":
        name = f"{distance} IM"
    else:
        name = f"{distance} {stroke_label}"

    prefix = _GENDER_PREFIX.get(gender_name, "")
    return f"{prefix} {name}" if prefix else name


def _best_time(entry) -> float | None:
    """Extract the best (fastest) available time from an EventEntry.

    Priority: finals > prelim > seed (skip non-numeric codes like NT, NS, DQ).
    """
    for attr in ("finals_time", "prelim_time", "seed_time"):
        val = getattr(entry, attr, None)
        if val is not None and isinstance(val, (int, float)):
            return float(val)
    return None


def _age_to_grade(age: int | None) -> int | None:
    """Estimate high school grade from age (rough heuristic).

    Age 14 → 9th, 15 → 10th, 16 → 11th, 17+ → 12th.
    Returns None if age is unknown or out of range.
    """
    if age is None or age < 12:
        return None
    if age <= 14:
        return max(8, age - 5)
    if age >= 18:
        return 12
    return age - 5


def parse_hy3_file(filepath: str | Path) -> pd.DataFrame:
    """Parse a HyTek .hy3 file and return a normalized DataFrame.

    Args:
        filepath: Path to the .hy3 file.

    Returns:
        DataFrame with columns: swimmer, event, time, team, grade, gender, is_relay

    Raises:
        ValueError: If the file is not a valid HY3 file.
        FileNotFoundError: If the file does not exist.
    """
    try:
        from hytek_parser import parse_hy3
    except ImportError as e:
        raise ImportError(
            "hytek-parser is required for .hy3 file support. "
            "Install it with: pip install hytek-parser"
        ) from e

    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"HY3 file not found: {filepath}")

    parsed = parse_hy3(str(filepath), validate_checksums=False)
    meet = parsed.meet

    rows: list[dict] = []

    for event_num, event in meet.events.items():
        stroke_name = event.stroke.name if event.stroke else "UNKNOWN"
        gender_name = event.gender.name if event.gender else "UNKNOWN"
        is_relay = event.relay

        event_name = _format_event_name(
            event.distance,
            stroke_name,
            is_relay,
            gender_name,
        )

        for entry in event.entries:
            time_val = _best_time(entry)
            if time_val is None or time_val <= 0:
                continue

            if is_relay:
                # For relays, use team name as the swimmer identifier
                team_code = entry.swimmers[0].team_code if entry.swimmers else ""
                team_obj = meet.teams.get(team_code)
                team_name = team_obj.short_name if team_obj else team_code

                rows.append(
                    {
                        "swimmer": f"{team_name} Relay",
                        "event": event_name,
                        "time": time_val,
                        "team": team_name,
                        "grade": None,
                        "gender": "F" if gender_name == "FEMALE" else "M",
                        "is_relay": True,
                    }
                )
            else:
                for swimmer in entry.swimmers:
                    name = f"{swimmer.first_name} {swimmer.last_name}".strip()
                    team_code = swimmer.team_code
                    team_obj = meet.teams.get(team_code)
                    team_name = team_obj.short_name if team_obj else team_code
                    grade = _age_to_grade(swimmer.age if swimmer.age else None)
                    gender = (
                        "F"
                        if swimmer.gender and swimmer.gender.name == "FEMALE"
                        else "M"
                    )

                    rows.append(
                        {
                            "swimmer": name,
                            "event": event_name,
                            "time": time_val,
                            "team": team_name,
                            "grade": grade,
                            "gender": gender,
                            "is_relay": False,
                        }
                    )

    if not rows:
        logger.warning("HY3 file parsed but no valid entries found: %s", filepath)
        return pd.DataFrame(
            columns=["swimmer", "event", "time", "team", "grade", "gender", "is_relay"]
        )

    df = pd.DataFrame(rows)

    # Deduplicate: keep fastest time per swimmer+event
    df = df.sort_values("time").drop_duplicates(
        subset=["swimmer", "event"], keep="first"
    )
    df = df.reset_index(drop=True)

    logger.info(
        "HY3 parsed: %d entries, %d swimmers, %d events, %d teams from %s",
        len(df),
        df["swimmer"].nunique(),
        df["event"].nunique(),
        df["team"].nunique(),
        filepath.name,
    )

    return df
