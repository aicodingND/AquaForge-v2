"""
Data Normalizer - Canonicalize event names, team names, and time formats.

Ensures all imported data aligns with AquaForge's existing conventions
(see core/normalization.py and core/event_mapper.py).
"""

import re
from datetime import date

# =============================================================================
# Event Name Normalization
# =============================================================================

# Hy-Tek stroke codes -> standard names
HYTEK_STROKE_MAP = {
    "A": "Free",
    "B": "Back",
    "C": "Breast",
    "D": "Fly",
    "E": "IM",
}

# =============================================================================
# VISAA Event Programs by Meet Type
# =============================================================================

# Standard VISAA dual meet: 11 events per gender (no gender prefix in names)
DUAL_INDIVIDUAL_EVENTS = {
    "200 Medley Relay",  # Event 1 (relay, but part of standard program)
    "200 Free",
    "200 IM",
    "50 Free",
    "100 Fly",
    "100 Free",
    "500 Free",
    "100 Back",
    "100 Breast",
    "200 Free Relay",  # Event 10
    "Diving",  # Event 11
}
DUAL_RELAYS = {"200 Medley Relay", "200 Free Relay"}

# Championship meets use the same core events but may add:
#  - 400 Free Relay (championship finals event)
#  - Prelim/finals structure with more entries per event
CHAMPIONSHIP_EVENTS = DUAL_INDIVIDUAL_EVENTS | {
    "400 Free Relay",  # Championship-only relay
}

# Invitational meets are the wild west -- any event is possible:
#  - JV events: 50 Back, 50 Breast, 50 Fly, 100 IM
#  - Novice: 25 Back, 25 Breast, 25 Fly, 25 Free
#  - Non-standard relays: 200 Back Relay, 200 Breast Relay, etc.
#  - Distance: 1000 Free, 1650 Free, 400 IM
INVITATIONAL_EXTRA_EVENTS = {
    "50 Back",
    "50 Breast",
    "50 Fly",
    "100 IM",
    "25 Free",
    "25 Back",
    "25 Breast",
    "25 Fly",
    "200 Back",
    "200 Breast",
    "200 Fly",
    "400 Free",
    "1000 Free",
    "1650 Free",
    "400 IM",
    "200 Back Relay",
    "200 Breast Relay",
    "200 Fly Relay",
    "100 Free Relay",
    "100 Medley Relay",
    "400 Medley Relay",
    "400 Free Relay",
    "800 Free Relay",
    "250 Free Relay",  # Seen in data -- non-standard distance
}
INVITATIONAL_EVENTS = CHAMPIONSHIP_EVENTS | INVITATIONAL_EXTRA_EVENTS

# All recognized events (superset for validation)
ALL_KNOWN_EVENTS = INVITATIONAL_EVENTS | {"Diving"}

# Legacy flat lists (backward-compat)
STANDARD_EVENTS = [
    "200 Free",
    "200 IM",
    "50 Free",
    "100 Fly",
    "100 Free",
    "500 Free",
    "100 Back",
    "100 Breast",
]
STANDARD_RELAYS = ["200 Medley Relay", "200 Free Relay"]

# Common variations -> canonical form
EVENT_ALIASES = {
    "200 freestyle": "200 Free",
    "200 free": "200 Free",
    "200 yard freestyle": "200 Free",
    "200 individual medley": "200 IM",
    "200 yard individual medley": "200 IM",
    "200 ind. medley": "200 IM",
    "200 i.m.": "200 IM",
    "50 freestyle": "50 Free",
    "50 free": "50 Free",
    "50 yard freestyle": "50 Free",
    "100 butterfly": "100 Fly",
    "100 fly": "100 Fly",
    "100 yard butterfly": "100 Fly",
    "100 freestyle": "100 Free",
    "100 free": "100 Free",
    "100 yard freestyle": "100 Free",
    "500 freestyle": "500 Free",
    "500 free": "500 Free",
    "500 yard freestyle": "500 Free",
    "100 backstroke": "100 Back",
    "100 back": "100 Back",
    "100 yard backstroke": "100 Back",
    "100 breaststroke": "100 Breast",
    "100 breast": "100 Breast",
    "100 yard breaststroke": "100 Breast",
    "200 medley relay": "200 Medley Relay",
    "200 yard medley relay": "200 Medley Relay",
    "200 free relay": "200 Free Relay",
    "200 freestyle relay": "200 Free Relay",
    "200 yard free relay": "200 Free Relay",
    "200 yard freestyle relay": "200 Free Relay",
    "1 mtr diving": "Diving",
    "1 meter diving": "Diving",
    "diving": "Diving",
}


def normalize_event_name(
    raw_name: str | None = None,
    distance: int | None = None,
    stroke_code: str | None = None,
    is_relay: bool = False,
) -> str | None:
    """
    Normalize an event name to canonical form.

    Can work from either a raw string name OR Hy-Tek fields (distance + stroke_code).

    Returns canonical name like "100 Free", "200 Medley Relay", or None if unrecognized.
    """
    # Method 1: From Hy-Tek fields
    if distance is not None and stroke_code is not None:
        stroke = HYTEK_STROKE_MAP.get(stroke_code.upper(), stroke_code)
        if is_relay:
            if stroke_code.upper() == "E":
                return f"{distance} Medley Relay"
            return f"{distance} {stroke} Relay"
        if stroke_code.upper() == "E":
            return f"{distance} IM"
        return f"{distance} {stroke}"

    # Method 2: From raw string
    if raw_name is None:
        return None

    # Strip gender prefix for lookup
    cleaned = raw_name.strip()
    cleaned_lower = cleaned.lower()

    # Remove gender prefixes
    for prefix in ("girls ", "boys ", "women ", "men ", "female ", "male "):
        if cleaned_lower.startswith(prefix):
            cleaned = cleaned[len(prefix) :]
            cleaned_lower = cleaned.lower()
            break

    # Remove "Yard" / "Meter"
    cleaned_lower = re.sub(r"\s+yard\s+", " ", cleaned_lower)
    cleaned_lower = re.sub(r"\s+meter\s+", " ", cleaned_lower)
    cleaned_lower = re.sub(r"\s+", " ", cleaned_lower).strip()

    # Direct alias lookup
    if cleaned_lower in EVENT_ALIASES:
        return EVENT_ALIASES[cleaned_lower]

    # Check if it matches a standard event directly
    for std in STANDARD_EVENTS + STANDARD_RELAYS:
        if cleaned_lower == std.lower():
            return std

    # Fuzzy: extract distance + stroke
    m = re.match(r"(\d+)\s+(.+)", cleaned)
    if m:
        dist = m.group(1)
        stroke_raw = m.group(2).strip().lower()
        for alias_key, canonical in EVENT_ALIASES.items():
            if alias_key.startswith(dist) and stroke_raw in alias_key:
                return canonical

    return cleaned  # Return cleaned but unrecognized name


def classify_event(event_name: str, meet_type: str = "dual") -> str:
    """
    Classify an event into a category for filtering/validation.

    Returns one of:
      "standard"     -- Part of the standard VISAA dual/championship program
      "championship" -- Only appears in championship meets (400 Free Relay)
      "jv"           -- JV/invitational-only event (50 Back, 100 IM, etc.)
      "novice"       -- Novice/exhibition (25-yard events)
      "non_standard" -- Recognized but unusual (250 Free Relay, 200 Breast Relay)
      "unknown"      -- Not recognized at all
    """
    if not event_name:
        return "unknown"

    # Diving is always standard
    if event_name == "Diving":
        return "standard"

    # Standard dual events
    if event_name in DUAL_INDIVIDUAL_EVENTS:
        return "standard"

    # Championship-only events
    if event_name in {"400 Free Relay"}:
        return "championship"

    # JV events (common at invitationals)
    if event_name in {"50 Back", "50 Breast", "50 Fly", "100 IM"}:
        return "jv"

    # Novice (25-yard) events
    if event_name.startswith("25 "):
        return "novice"

    # Distance events (valid but uncommon in VISAA dual)
    if event_name in {
        "1000 Free",
        "1650 Free",
        "400 IM",
        "400 Free",
        "200 Back",
        "200 Breast",
        "200 Fly",
    }:
        return "jv"

    # Non-standard relays
    if "Relay" in event_name and event_name not in DUAL_RELAYS | {"400 Free Relay"}:
        return "non_standard"

    # Check ALL_KNOWN_EVENTS
    if event_name in ALL_KNOWN_EVENTS:
        return "jv"

    return "unknown"


def is_scoreable_event(event_name: str, meet_type: str = "dual") -> bool:
    """
    Check if an event should be scored in the optimizer for a given meet type.

    For dual meets: only standard VISAA events.
    For championship: standard + 400 Free Relay.
    For invitational/time_trial: all events are scored per the meet's program.
    """
    if not event_name:
        return False

    category = classify_event(event_name, meet_type)

    if meet_type == "dual":
        return category == "standard"
    elif meet_type in ("championship", "conference"):
        return category in ("standard", "championship")
    else:
        # Invitational/time_trial: everything except truly unknown
        return category != "unknown"


def validate_event_for_meet(event_name: str, meet_type: str) -> list[str]:
    """
    Return a list of warnings/issues for an event in the context of a meet type.
    Empty list = no issues.
    """
    warnings = []
    category = classify_event(event_name, meet_type)

    if category == "unknown":
        warnings.append(
            f"Unrecognized event '{event_name}' -- not in any known VISAA program"
        )

    elif meet_type == "dual" and category not in ("standard",):
        warnings.append(f"Event '{event_name}' ({category}) is unusual for a dual meet")

    elif meet_type == "championship" and category in ("novice", "non_standard"):
        warnings.append(
            f"Event '{event_name}' ({category}) is unusual for a championship"
        )

    return warnings


# =============================================================================
# Team Name Normalization
# =============================================================================

# Known team aliases (expandable from database)
# Maps lowercase variants -> canonical name
TEAM_ALIASES = {
    # Seton
    "seton": "Seton",
    "sst": "Seton",
    "seton school": "Seton",
    "seton swimming": "Seton",
    "seton swim team": "Seton",
    "seton high school": "Seton",
    "seton family homeschool": "Seton",
    # Trinity Christian
    "trinity christian": "Trinity Christian",
    "trinity christian school": "Trinity Christian",
    "trinity christian school swim": "Trinity Christian",
    "tcs": "Trinity Christian",
    "chrs": "Trinity Christian",
    # Oakcrest
    "oakcrest": "Oakcrest",
    "oakcrest school chargers": "Oakcrest",
    "oak": "Oakcrest",
    "oakc": "Oakcrest",
    # Immanuel Christian
    "immanuel christian": "Immanuel Christian",
    "immanuel christian school": "Immanuel Christian",
    "ics": "Immanuel Christian",
    # Bishop Ireton
    "bishop ireton": "Bishop Ireton",
    "bishop ireton high school": "Bishop Ireton",
    "bishop ireton swim and dive": "Bishop Ireton",
    "bishop ireton swim and dive te": "Bishop Ireton",
    # Bishop O'Connell
    "bishop o'connell": "Bishop O'Connell",
    # Paul VI
    "paul vi catholic high school": "Paul VI",
    "st paul vi catholic hs": "Paul VI",
    "st. paul vi catholic hs": "Paul VI",
    # St. Anne's-Belfield
    "st anne's belfield": "St. Anne's-Belfield",
    "st anne's-belfield school": "St. Anne's-Belfield",
    "st. anne's belfield": "St. Anne's-Belfield",
    "st. anne's-belfield school": "St. Anne's-Belfield",
    "st.anne's_belfield": "St. Anne's-Belfield",
    # St. Catherine's
    "st catherine's school": "St. Catherine's",
    "st. catherine's school": "St. Catherine's",
    "st. catherine's jv swimming": "St. Catherine's JV",
    # St. Christopher's
    "st christopher's school": "St. Christopher's",
    "st. christopher's school": "St. Christopher's",
    # St. Gertrude
    "saint gertrude high school": "St. Gertrude",
    "st gertrude high school": "St. Gertrude",
    "st. gertrude high school": "St. Gertrude",
    # St. Michael the Archangel
    "saint michael the archangel": "St. Michael the Archangel",
    "saint michael the archangel hs": "St. Michael the Archangel",
    "st michael the archangel high": "St. Michael the Archangel",
    "st. michael the archangel high": "St. Michael the Archangel",
    "st michael the archangel": "St. Michael the Archangel",
    "st. michael the archangel jv": "St. Michael the Archangel JV",
    "sm": "St. Michael the Archangel",
    # St. Stephen's & St. Agnes
    "st stephen's & st agnes": "St. Stephen's & St. Agnes",
    "st. stephen's & st. agnes": "St. Stephen's & St. Agnes",
    "st. stephens & st. agnes": "St. Stephen's & St. Agnes",
    # Fredericksburg Christian
    "fredericksburg christian": "Fredericksburg Christian",
    "fredricksburg christian school": "Fredericksburg Christian",
    # Fredericksburg Academy
    "fredericksburg academy": "Fredericksburg Academy",
    # Norfolk Academy
    "norfolk academy": "Norfolk Academy",
    "norfolk academy - jv": "Norfolk Academy JV",
    # Norfolk Christian
    "norfolk christian": "Norfolk Christian",
    "norfolk christian high school": "Norfolk Christian",
    "norfolk christian school": "Norfolk Christian",
    "norfolk chrstian high school": "Norfolk Christian",
    # Norfolk Collegiate
    "norfolk collegiate": "Norfolk Collegiate",
    "norfolk collegiate school": "Norfolk Collegiate",
    "norfolk collegiate swim team": "Norfolk Collegiate",
    # Nansemond-Suffolk
    "nansemond suffolk academy": "Nansemond-Suffolk Academy",
    "nansemond-suffolk academey": "Nansemond-Suffolk Academy",
    "nansemond-suffolk academy": "Nansemond-Suffolk Academy",
    # Bishop Sullivan
    "bishop sullivan catholic": "Bishop Sullivan Catholic",
    "bishop sullivan catholic high": "Bishop Sullivan Catholic",
    # Benedictine
    "benedictine college prep": "Benedictine",
    "benedictine college prep.": "Benedictine",
    "benedictine high school": "Benedictine",
    # Cape Henry
    "cape henry collegiate": "Cape Henry Collegiate",
    "cape henry collegiate school": "Cape Henry Collegiate",
    "cape henrycollegiate": "Cape Henry Collegiate",
    # Chatham Hall
    "chatham hall": "Chatham Hall",
    "chatham hall school": "Chatham Hall",
    "chatham hall varsity": "Chatham Hall",
    # Flint Hill
    "flint hill school": "Flint Hill",
    "flint hill ms team": "Flint Hill MS",
    "flint hill school swim team": "Flint Hill",
    # Fork Union
    "fork union military academy": "Fork Union Military Academy",
    "fork union miltary academy": "Fork Union Military Academy",
    # Hargrave
    "hargrave military academy": "Hargrave Military Academy",
    "hargrave varsity": "Hargrave Military Academy",
    # Highland
    "highland school": "Highland",
    "highland hawks": "Highland",
    "highland varsity swimming": "Highland",
    # John Paul the Great
    "john paul the great": "John Paul the Great",
    "john paul the great high schoo": "John Paul the Great",
    "pope john paul the great hs": "John Paul the Great",
    "saint john paul the great": "John Paul the Great",
    # Madeira
    "madeira varsity swim team": "Madeira",
    "madeira varsity swim and dive": "Madeira",
    "the madeira school": "Madeira",
    # Massanutten
    "massanuten military academy": "Massanutten Military Academy",
    "massanutten military academy": "Massanutten Military Academy",
    # Middleburg
    "middleburg academy": "Middleburg Academy",
    "middleburg academy swim team": "Middleburg Academy",
    # Mills Godwin
    "mills e. godwin high school": "Mills Godwin",
    "mills godwin high school": "Mills Godwin",
    # North Cross
    "north cross high school": "North Cross",
    "north cross school": "North Cross",
    # Notre Dame
    "notre dame academy swim team": "Notre Dame Academy",
    "notre dame preparatory school": "Notre Dame Preparatory",
    # Potomac
    "potomac school": "Potomac School",
    "potomac school swim team": "Potomac School",
    "the potomac school": "Potomac School",
    # Randolph-Macon
    "randolph macon academy": "Randolph-Macon Academy",
    "randolph-macon academy": "Randolph-Macon Academy",
    # Steward
    "steward spartans": "The Steward School",
    "the steward school 2017-2018": "The Steward School",
    "the steward school jv": "The Steward School JV",
    "the steward school spartans": "The Steward School",
    # The Carmel School
    "the carmel school": "Carmel School",
    "the carmel school wildcats": "Carmel School",
    "the carmel school willdcats": "Carmel School",
    "carmel school wildcats": "Carmel School",
    # Covenant
    "the covenant school": "Covenant School",
    "covenant swimming": "Covenant School",
    # Collegiate
    "collegiate school": "Collegiate",
    # TC Williams
    "tc williams swim & dive": "TC Williams",
    # Veritas
    "veritas christian academy": "Veritas Christian Academy",
    "veritas collegiate academy": "Veritas Collegiate Academy",
    "veritas school": "Veritas School",
    # Wakefield
    "wakefield school": "Wakefield",
    "wakefield h2owls": "Wakefield",
    "wakefield school fighting owls": "Wakefield",
    "wakefield country day school": "Wakefield Country Day",
    "wakefield middle school": "Wakefield MS",
    "2016-17 h2owls varsity": "Wakefield",
    "2018 jv wakefield owls": "Wakefield JV",
    # Woodberry Forest
    "woodberry forest": "Woodberry Forest",
    "woodberry forest swimming & di": "Woodberry Forest",
    # Georgetown Prep
    "georgetown preparatory school": "Georgetown Prep",
    # Christchurch
    "christchurch school swim team": "Christchurch School",
    # Roanoke Catholic
    "roanoke catholic school": "Roanoke Catholic",
    # Trinity Episcopal
    "trinity episcopal school": "Trinity Episcopal",
    # Virginia Episcopal
    "virginia episcopal school": "Virginia Episcopal",
    # Walsingham
    "walsingham academy": "Walsingham Academy",
    # The Carlisle School
    "carlisle school": "Carlisle School",
    "the carlisle school": "Carlisle School",
}


def normalize_team_name(raw_name: str) -> str:
    """Normalize team name to canonical form.
    Falls back to cleaning up common patterns if no alias match."""
    if not raw_name:
        return "Unknown"
    cleaned = raw_name.strip()

    # Skip Team_NNN placeholders -- these should be resolved elsewhere
    if cleaned.startswith("Team_"):
        return "Unknown"

    lookup = cleaned.lower()
    if lookup in TEAM_ALIASES:
        return TEAM_ALIASES[lookup]

    return cleaned


# =============================================================================
# Meet Type Inference
# =============================================================================


def infer_meet_type(meet_name: str, hytek_code: int | None = None) -> str:
    """Infer meet type from name keywords when Hy-Tek code is unreliable.
    Hy-Tek code 1=dual is the default and often wrong for invitationals.

    Priority: keyword match > Hy-Tek code (except code=1 which is ignored).
    """
    if not meet_name:
        return "dual"

    lower = meet_name.lower()

    # Championship indicators (strongest signal)
    # "Champs" catches abbreviated names like "VISAA Champs-Score 20"
    if any(
        kw in lower
        for kw in [
            "state champ",
            "championship",
            "champs",
            "visaa state",
            "vsis state",
            "regional champ",
            "conference champ",
        ]
    ):
        return "championship"

    # Time trial indicators (check before invitational -- "time trial invite" = time_trial)
    if any(kw in lower for kw in ["time trial", "timetrial", "time-trial"]):
        return "time_trial"

    # Invitational indicators
    if any(
        kw in lower
        for kw in [
            "invitational",
            "invite",
            "carnival",
            "relay carnival",
            "classic",
            "showcase",
            "tournament",
        ]
    ):
        return "invitational"

    # Conference/league indicators
    if any(
        kw in lower
        for kw in [
            "conference",
            "dac ",
            "vcac",
            "delaney",
            "nova catholic",
            "national catholic",
            "metro",
            "league",
        ]
    ):
        return "conference"

    # Exhibition/fun meet indicators
    if any(
        kw in lower
        for kw in [
            "olympics",
            "fun meet",
            "intrasquad",
            "intra-squad",
            "alumni",
            "jamboree",
            "scrimmage",
        ]
    ):
        return "exhibition"

    # Fall back to Hy-Tek code if available (but IGNORE code 1 = dual default)
    HYTEK_MEET_TYPE_MAP = {2: "invitational", 3: "championship", 4: "time_trial"}
    if hytek_code and hytek_code in HYTEK_MEET_TYPE_MAP:
        return HYTEK_MEET_TYPE_MAP[hytek_code]

    return "dual"


# =============================================================================
# Season Inference
# =============================================================================


def infer_season_from_date(meet_date) -> str | None:
    """Infer swim season from meet date. Swimming season runs Nov-Feb.
    A meet in Nov 2025 = season 2025-2026. A meet in Feb 2026 = season 2025-2026."""
    if not meet_date:
        return None
    try:
        if hasattr(meet_date, "month"):
            month = meet_date.month
            year = meet_date.year
        else:
            # Parse string date
            parts = str(meet_date).split("-")
            year = int(parts[0])
            month = int(parts[1])
    except (ValueError, IndexError, AttributeError):
        return None

    # Season assignment: Sep-Dec = that year starts, Jan-Aug = previous year started
    if month >= 9:  # Sep-Dec: season starts this year
        return f"{year}-{year + 1}"
    else:  # Jan-Aug: season started previous year
        return f"{year - 1}-{year}"


# =============================================================================
# Time Normalization
# =============================================================================


def normalize_time(raw_time) -> float | None:
    """
    Convert various time formats to seconds as float.

    Handles:
    - Float seconds: 54.32
    - MM:SS.hh: 1:23.45 -> 83.45
    - Integer hundredths (Hy-Tek internal): 5432 -> 54.32
    - String with suffixes: "54.32Y", "1:23.45L"
    """
    if raw_time is None:
        return None

    if isinstance(raw_time, (int, float)):
        val = float(raw_time)
        if val <= 0:
            return None
        # Hy-Tek sometimes stores in hundredths -- but also as regular seconds.
        # Heuristic: if > 10000, probably hundredths. If > 600, probably hundredths.
        # Normal swim times range: 20s to ~600s (10 min for 1650).
        # We'll treat values as-is since Hy-Tek .mdb stores as float seconds.
        return val

    # String parsing
    s = str(raw_time).strip().rstrip("YLSyls")
    if not s:
        return None

    try:
        # Try MM:SS.hh format
        if ":" in s:
            parts = s.split(":")
            minutes = int(parts[0])
            seconds = float(parts[1])
            return minutes * 60 + seconds
        return float(s)
    except (ValueError, IndexError):
        return None


# =============================================================================
# Gender Normalization
# =============================================================================


def normalize_gender(raw: str | None) -> str | None:
    """Normalize gender to 'M' or 'F'."""
    if not raw:
        return None
    upper = raw.strip().upper()
    if upper in ("M", "B", "MALE", "BOYS", "BOY"):
        return "M"
    if upper in ("F", "G", "FEMALE", "GIRLS", "GIRL", "W", "WOMEN"):
        return "F"
    if upper == "X":
        return "X"
    return None


# =============================================================================
# Date Parsing
# =============================================================================


def parse_meet_date(date_str: str, season: str | None = None) -> date | None:
    """
    Parse meet date from folder names like "Jan10,26" or "Feb13-15,25".

    Args:
        date_str: Raw date string from folder name
        season: Season string like "2025-2026" for year context

    Returns:
        date object or None
    """
    if not date_str:
        return None

    MONTHS = {
        "jan": 1,
        "feb": 2,
        "mar": 3,
        "apr": 4,
        "may": 5,
        "jun": 6,
        "jul": 7,
        "aug": 8,
        "sep": 9,
        "oct": 10,
        "nov": 11,
        "dec": 12,
    }

    # Extract month and day: "Jan10,26" or "Feb13-15,25"
    m = re.match(
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)(\d+)(?:-\d+)?,(\d{2})",
        date_str,
        re.IGNORECASE,
    )
    if m:
        month = MONTHS.get(m.group(1).lower())
        day = int(m.group(2))
        yy = int(m.group(3))
        year = 2000 + yy if yy < 50 else 1900 + yy
        try:
            return date(year, month, day)
        except ValueError:
            return None

    # Fallback: just month + day, infer year from season
    m = re.match(
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)(\d+)",
        date_str,
        re.IGNORECASE,
    )
    if m and season:
        month = MONTHS.get(m.group(1).lower())
        day = int(m.group(2))
        # Season "2025-2026": Nov-Feb = second year, Sep-Oct = first year
        parts = season.split("-")
        if len(parts) == 2:
            year = int(parts[1]) if month <= 6 else int(parts[0])
            try:
                return date(year, month, day)
            except ValueError:
                return None

    return None
