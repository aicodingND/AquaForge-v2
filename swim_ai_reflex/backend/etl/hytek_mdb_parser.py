"""
Hy-Tek Meet Manager .mdb Parser

Reads Microsoft Access databases created by Hy-Tek's Meet Manager software
(versions 4, 7, 8) and extracts meet results.

Hy-Tek internal schema:
  Team      -> Team_no, team name
  Athlete   -> Ath_no, Last_name, First_name, Team_no
  Event     -> Event_ptr, Event_no, Event_sex (M/F/X/B/G), Event_dist, Event_stroke (A/B/C/D/E), Ind_Rel (I/R)
  Entry     -> Ath_no, Event_ptr, Fin_Time, Fin_place, Ev_score, ActualSeed_time
  Relay     -> Team_no, Event_ptr, Fin_Time, Fin_place, Ev_score
  RelayNames-> Relay_no, Ath_no, Pos_no (leg order)
  Session   -> course info (Y/L/S = yards/long meters/short meters)

Primary reader: access_parser (bypasses .mdb password protection).
Fallback: pyodbc + Microsoft Access ODBC Driver (Windows, if unprotected).
"""

import logging
import os
from dataclasses import dataclass, field

from swim_ai_reflex.backend.etl.normalizer import (
    normalize_event_name,
    normalize_gender,
    normalize_time,
)

logger = logging.getLogger(__name__)

try:
    from access_parser import (
        AccessParser,  # TODO: port dependency -- pip install access-parser
    )

    HAS_ACCESS_PARSER = True
except ImportError:
    HAS_ACCESS_PARSER = False

try:
    import pyodbc  # TODO: port dependency -- pip install pyodbc (requires unixODBC on macOS)

    HAS_PYODBC = True
except ImportError:
    HAS_PYODBC = False


@dataclass
class ParsedTeam:
    team_no: int
    name: str
    abbreviation: str = ""


@dataclass
class ParsedAthlete:
    ath_no: int
    first_name: str
    last_name: str
    team_no: int
    gender: str | None = None
    initial: str = ""
    school_year: int | None = None  # grade: 9,10,11,12
    birth_date: str | None = None  # ISO string if available
    age: int | None = None
    usa_swimming_id: str | None = None


@dataclass
class ParsedEvent:
    event_ptr: int
    event_no: int
    event_name: str  # Normalized: "100 Free", "200 Medley Relay"
    gender: str | None = None  # M, F, X
    distance: int = 0
    stroke_code: str = ""
    is_relay: bool = False
    is_diving: bool = False


@dataclass
class ParsedEntry:
    ath_no: int
    event_ptr: int
    seed_time: float | None = None
    finals_time: float | None = None
    place: int | None = None
    points: float = 0.0
    heat: int | None = None
    lane: int | None = None
    is_exhibition: bool = False
    is_dq: bool = False
    course: str | None = None  # Y, L, S


@dataclass
class ParsedRelay:
    relay_no: int
    team_no: int
    event_ptr: int
    relay_letter: str = "A"
    seed_time: float | None = None
    finals_time: float | None = None
    place: int | None = None
    points: float = 0.0
    legs: list[tuple[int, int]] = field(default_factory=list)  # (ath_no, leg_order)


@dataclass
class ParsedMeetInfo:
    """Meet-level metadata from the Meet table."""

    name: str | None = None
    location: str | None = None
    city: str | None = None
    state: str | None = None
    start_date: str | None = None  # ISO date string
    end_date: str | None = None
    course: str | None = None  # 25Y, 50M, 25M
    num_lanes: int | None = None
    meet_type: int | None = None  # Hy-Tek code
    ind_max_scorers: int | None = None
    relay_max_scorers: int | None = None


@dataclass
class ParsedSplit:
    """A single split time within an event."""

    event_ptr: int
    ath_no: int  # 0 for relay splits
    relay_no: int  # 0 for individual splits
    split_number: int  # 1, 2, 3...
    split_time: float  # cumulative seconds
    round_code: str = "F"  # F=finals, P=prelims


@dataclass
class ParsedDualPairing:
    """Dual meet team pairing from Dualteams table."""

    team_a_no: int
    team_b_no: int
    gender: str | None = None  # M, F


@dataclass
class ParsedScoringRule:
    """Points per place from Scoring table."""

    place: int
    gender: str | None = None
    ind_points: float = 0.0
    relay_points: float = 0.0


@dataclass
class MeetData:
    """All extracted data from a single .mdb file."""

    source_path: str
    meet_info: ParsedMeetInfo | None = None
    teams: list[ParsedTeam] = field(default_factory=list)
    athletes: list[ParsedAthlete] = field(default_factory=list)
    events: list[ParsedEvent] = field(default_factory=list)
    entries: list[ParsedEntry] = field(default_factory=list)
    relays: list[ParsedRelay] = field(default_factory=list)
    splits: list[ParsedSplit] = field(default_factory=list)
    dual_pairings: list[ParsedDualPairing] = field(default_factory=list)
    scoring_rules: list[ParsedScoringRule] = field(default_factory=list)
    pool_course: str = "25Y"
    errors: list[str] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return len(self.entries) == 0 and len(self.relays) == 0


# Hy-Tek event stroke code mapping
STROKE_MAP = {"A": "Free", "B": "Back", "C": "Breast", "D": "Fly", "E": "IM"}


# ---------------------------------------------------------------------------
# Helpers for access_parser (returns dict-of-lists)
# ---------------------------------------------------------------------------


def _col(table_data: dict, name: str, index: int, default=None):
    """Get a column value at row index from access_parser dict-of-lists format."""
    col_vals = table_data.get(name)
    if col_vals is None or index >= len(col_vals):
        return default
    val = col_vals[index]
    return val if val is not None else default


def _col_int(table_data: dict, name: str, index: int, default: int = 0) -> int:
    """Get an integer column value."""
    val = _col(table_data, name, index)
    if val is None:
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def _col_float(table_data: dict, name: str, index: int) -> float | None:
    """Get a float column value."""
    val = _col(table_data, name, index)
    if val is None:
        return None
    try:
        f = float(val)
        return f if f != 0.0 else None
    except (ValueError, TypeError):
        return None


def _col_str(table_data: dict, name: str, index: int, default: str = "") -> str:
    """Get a string column value, stripped."""
    val = _col(table_data, name, index, default)
    return str(val).strip() if val is not None else default


def _col_bool(table_data: dict, name: str, index: int) -> bool:
    """Get a boolean column value. Strict: only True/1/-1 are truthy.
    access_parser sometimes returns non-zero ints for non-boolean fields."""
    val = _col(table_data, name, index, False)
    if val is True:
        return True
    if isinstance(val, (int, float)):
        return val == 1 or val == -1  # Hy-Tek uses -1 for True in some fields
    return False


def _n_rows(table_data: dict) -> int:
    """Count rows in an access_parser table result."""
    if not table_data:
        return 0
    first_col = next(iter(table_data.values()), [])
    return len(first_col)


def _get_best_time(table_data: dict, index: int, prefix: str = "Fin") -> float | None:
    """
    Get the best available time from multiple columns.
    Hy-Tek stores times in Fin_Time, Fin_pad, and Fin_back1.
    Some MDB versions only populate certain columns.
    """
    # Try official time first, then pad (touchpad), then backup
    for col_name in [
        f"{prefix}_Time",
        f"{prefix}_pad",
        f"{prefix}_back1",
        f"{prefix}_back2",
    ]:
        val = _col_float(table_data, col_name, index)
        if val is not None and val > 0:
            # Sanity check: times should be < 10000 seconds (no swim takes > 2.7 hours)
            if val < 10000:
                return val
    return None


def _get_seed_time(table_data: dict, index: int) -> float | None:
    """Get seed time from ActualSeed_time or ConvSeed_time.
    Filters out Hy-Tek "NT" placeholders (599.99+, 510.0, 1800.0, etc.)."""
    for col_name in ["ActualSeed_time", "ConvSeed_time"]:
        val = _col_float(table_data, col_name, index)
        if val is not None and 0 < val < 10000:
            # Filter NT placeholders: 599.99+, 510.00 (8:30), 570.00 (9:30), 600.25+ (10:00.25)
            if val >= 599.0:
                return None
            return val
    return None


# ---------------------------------------------------------------------------
# Main parse function
# ---------------------------------------------------------------------------


def parse_mdb(mdb_path: str) -> MeetData:
    """
    Parse a Hy-Tek Meet Manager .mdb file and extract all meet data.

    Uses access_parser (bypasses password protection) as primary reader.
    Falls back to pyodbc if access_parser is unavailable.

    Args:
        mdb_path: Path to the .mdb file

    Returns:
        MeetData with teams, athletes, events, entries, and relays
    """
    result = MeetData(source_path=mdb_path)

    if not os.path.exists(mdb_path):
        result.errors.append(f"File not found: {mdb_path}")
        return result

    if HAS_ACCESS_PARSER:
        return _parse_with_access_parser(mdb_path, result)
    elif HAS_PYODBC:
        return _parse_with_pyodbc(mdb_path, result)
    else:
        result.errors.append(
            "No MDB reader available. Install access-parser: pip install access-parser"
        )
        return result


def _parse_with_access_parser(mdb_path: str, result: MeetData) -> MeetData:
    """Parse using access_parser library (handles password-protected .mdb files)."""
    try:
        db = AccessParser(mdb_path)
    except Exception as e:
        result.errors.append(f"access_parser failed to open: {e}")
        # Fall back to pyodbc if available
        if HAS_PYODBC:
            return _parse_with_pyodbc(mdb_path, result)
        return result

    tables = set(db.catalog.keys())

    try:
        # =================================================================
        # 1. Read Teams
        # =================================================================
        if "Team" in tables:
            try:
                tdata = db.parse_table("Team")
                for i in range(_n_rows(tdata)):
                    team_no = _col_int(tdata, "Team_no", i, 0)
                    name = (
                        _col_str(tdata, "Team_name", i)
                        or _col_str(tdata, "Team_short", i)
                        or _col_str(tdata, "Team_abbr", i)
                    )
                    abbr = _col_str(tdata, "Team_abbr", i, "")
                    # Use abbreviation as name if no real name found
                    if not name and abbr:
                        name = abbr
                    if team_no > 0 or name:
                        result.teams.append(
                            ParsedTeam(
                                team_no=team_no,
                                name=name,
                                abbreviation=abbr,
                            )
                        )
            except Exception as e:
                result.errors.append(f"Error reading Team table: {e}")

        # =================================================================
        # 2. Read Athletes
        # =================================================================
        if "Athlete" in tables:
            try:
                adata = db.parse_table("Athlete")
                for i in range(_n_rows(adata)):
                    ath_no = _col_int(adata, "Ath_no", i, 0)
                    first = _col_str(adata, "First_name", i)
                    last = _col_str(adata, "Last_name", i)
                    team_no = _col_int(adata, "Team_no", i, 0)
                    initial = _col_str(adata, "Initial", i)
                    gender_raw = _col_str(adata, "Ath_Sex", i)
                    gender = normalize_gender(gender_raw) if gender_raw else None

                    # Grade / school year
                    schl_yr_raw = _col(adata, "Schl_yr", i)
                    school_year = None
                    if schl_yr_raw is not None:
                        try:
                            sy = int(schl_yr_raw)
                            school_year = sy if 1 <= sy <= 12 else None
                        except (ValueError, TypeError):
                            pass

                    # Birth date
                    birth_raw = _col(adata, "Birth_date", i)
                    birth_str = None
                    if birth_raw is not None and str(birth_raw).strip():
                        birth_str = str(birth_raw).strip()

                    # Age
                    age_raw = _col(adata, "Ath_age", i)
                    age = None
                    if age_raw is not None:
                        try:
                            a = int(age_raw)
                            age = a if 5 <= a <= 99 else None
                        except (ValueError, TypeError):
                            pass

                    # USA Swimming registration number
                    reg_no = _col_str(adata, "Reg_no", i) or None

                    if ath_no > 0 and (first or last):
                        result.athletes.append(
                            ParsedAthlete(
                                ath_no=ath_no,
                                first_name=first,
                                last_name=last,
                                team_no=team_no,
                                gender=gender,
                                initial=initial,
                                school_year=school_year,
                                birth_date=birth_str,
                                age=age,
                                usa_swimming_id=reg_no,
                            )
                        )
            except Exception as e:
                result.errors.append(f"Error reading Athlete table: {e}")

        # =================================================================
        # 3. Read Events
        # =================================================================
        if "Event" in tables:
            try:
                edata = db.parse_table("Event")
                for i in range(_n_rows(edata)):
                    event_ptr = _col_int(edata, "Event_ptr", i, 0)
                    event_no = _col_int(edata, "Event_no", i, 0)
                    event_dist = _col_int(edata, "Event_dist", i, 0)
                    # Event_dist may be stored as float in some versions
                    if event_dist == 0:
                        dist_f = _col_float(edata, "Event_dist", i)
                        if dist_f:
                            event_dist = int(dist_f)

                    event_stroke = _col_str(edata, "Event_stroke", i, "A")
                    ind_rel = _col_str(edata, "Ind_rel", i, "I").upper()
                    is_relay = ind_rel == "R"

                    # Validate stroke code -- warn on unrecognized codes
                    VALID_STROKE_CODES = {"A", "B", "C", "D", "E", ""}
                    if event_stroke.upper() not in VALID_STROKE_CODES:
                        result.errors.append(
                            f"Unknown stroke code '{event_stroke}' for event #{event_no} "
                            f"(dist={event_dist}), treating as freestyle"
                        )
                        event_stroke = "A"  # Default to freestyle

                    # Gender: Event_sex can be B/G/M/F/X; also check Event_gender
                    event_sex = _col_str(edata, "Event_sex", i, "X")
                    if not event_sex or event_sex == "X":
                        event_sex = _col_str(edata, "Event_gender", i, "X")
                    gender = normalize_gender(event_sex)

                    # Gender X: try to infer from event_no (odd = girls, even = boys
                    # in standard VISAA dual meets). This is a heuristic.
                    if gender == "X" and event_no:
                        if event_no % 2 == 1:
                            gender = "F"
                        elif event_no % 2 == 0:
                            gender = "M"

                    # Diving detection
                    event_desc = _col_str(edata, "Event_Type", i)
                    is_diving = "diving" in event_desc.lower() if event_desc else False
                    if event_dist == 0 and event_stroke in ("", "A") and not is_relay:
                        is_diving = True

                    # Skip garbage events: distance=0 and not diving
                    if event_dist == 0 and not is_diving:
                        continue

                    event_name = normalize_event_name(
                        distance=event_dist,
                        stroke_code=event_stroke,
                        is_relay=is_relay,
                    )
                    if is_diving:
                        event_name = "Diving"

                    result.events.append(
                        ParsedEvent(
                            event_ptr=event_ptr,
                            event_no=event_no,
                            event_name=event_name or f"{event_dist} {event_stroke}",
                            gender=gender,
                            distance=event_dist,
                            stroke_code=event_stroke,
                            is_relay=is_relay,
                            is_diving=is_diving,
                        )
                    )
            except Exception as e:
                result.errors.append(f"Error reading Event table: {e}")

        # =================================================================
        # 4. Read Individual Entries
        # =================================================================
        entry_table = (
            "Entry" if "Entry" in tables else ("Result" if "Result" in tables else None)
        )
        if entry_table:
            try:
                endata = db.parse_table(entry_table)
                n = _n_rows(endata)

                # Check if linkage columns are populated
                # Some MDB versions have Ath_no/Event_ptr = 0 due to access_parser binary parsing issues
                sample_ath = [_col_int(endata, "Ath_no", i) for i in range(min(n, 10))]
                has_linkage = any(v > 0 for v in sample_ath)

                for i in range(n):
                    ath_no = _col_int(endata, "Ath_no", i, 0)
                    event_ptr = _col_int(endata, "Event_ptr", i, 0)

                    # Get times: try Fin_Time first, then Fin_pad, then Fin_back1
                    finals_time = _get_best_time(endata, i, "Fin")
                    seed_time = _get_seed_time(endata, i)

                    place_raw = _col(endata, "Fin_place", i)
                    place = None
                    if place_raw is not None:
                        try:
                            p = int(place_raw)
                            # Sanity: places should be 1-999
                            place = p if 0 < p < 1000 else None
                        except (ValueError, TypeError):
                            pass

                    points_raw = _col(endata, "Ev_score", i)
                    points = 0.0
                    if points_raw is not None:
                        try:
                            p = float(points_raw)
                            # Sanity: individual event points max ~20
                            points = p if 0 <= p <= 100 else 0.0
                        except (ValueError, TypeError):
                            pass

                    heat = _col_int(endata, "Fin_heat", i, 0) or None
                    lane = _col_int(endata, "Fin_lane", i, 0) or None
                    is_exh = _col_bool(endata, "Fin_exh", i)

                    # DQ detection
                    fin_stat = _col_str(endata, "Fin_stat", i)
                    is_dq = (
                        fin_stat.upper() in ("DQ", "D", "DSQ") if fin_stat else False
                    )

                    # Course per entry -- normalize to match meet format
                    course_raw = _col_str(endata, "Fin_course", i) or None
                    ENTRY_COURSE_MAP = {"Y": "25Y", "L": "50M", "S": "25M"}
                    course = (
                        ENTRY_COURSE_MAP.get(course_raw, course_raw)
                        if course_raw
                        else None
                    )

                    # Skip entries with no linkage AND no time (nothing useful)
                    if (
                        not has_linkage
                        and ath_no == 0
                        and finals_time is None
                        and seed_time is None
                    ):
                        continue

                    result.entries.append(
                        ParsedEntry(
                            ath_no=ath_no,
                            event_ptr=event_ptr,
                            seed_time=seed_time,
                            finals_time=finals_time,
                            place=place,
                            points=points,
                            heat=heat,
                            lane=lane,
                            is_exhibition=is_exh,
                            is_dq=is_dq,
                            course=course,
                        )
                    )

            except Exception as e:
                result.errors.append(f"Error reading {entry_table} table: {e}")

        # =================================================================
        # 5. Read Relays
        # =================================================================
        if "Relay" in tables:
            try:
                rdata = db.parse_table("Relay")
                relays_map: dict[int, ParsedRelay] = {}

                for i in range(_n_rows(rdata)):
                    relay_no = _col_int(rdata, "Relay_no", i, 0)
                    team_no = _col_int(rdata, "Team_no", i, 0)
                    event_ptr = _col_int(rdata, "Event_ptr", i, 0)
                    relay_letter = (
                        _col_str(rdata, "Team_ltr", i)
                        or _col_str(rdata, "Relay_alpha", i)
                        or "A"
                    )

                    finals_time = _get_best_time(rdata, i, "Fin")
                    seed_time = _get_seed_time(rdata, i)

                    place_raw = _col(rdata, "Fin_place", i)
                    place = None
                    if place_raw is not None:
                        try:
                            p = int(place_raw)
                            place = p if 0 < p < 1000 else None
                        except (ValueError, TypeError):
                            pass

                    points_raw = _col(rdata, "Ev_score", i)
                    points = 0.0
                    if points_raw is not None:
                        try:
                            p = float(points_raw)
                            points = p if 0 <= p <= 100 else 0.0
                        except (ValueError, TypeError):
                            pass

                    # DQ detection
                    fin_stat = _col_str(rdata, "Fin_stat", i)
                    is_dq = (
                        fin_stat.upper() in ("DQ", "D", "DSQ") if fin_stat else False
                    )

                    if relay_no > 0 or (team_no > 0 and event_ptr > 0):
                        relay = ParsedRelay(
                            relay_no=relay_no if relay_no > 0 else i + 1,
                            team_no=team_no,
                            event_ptr=event_ptr,
                            relay_letter=relay_letter,
                            seed_time=seed_time,
                            finals_time=finals_time,
                            place=place,
                            points=points,
                        )
                        relays_map[relay.relay_no] = relay

                # Read relay leg assignments
                if "RelayNames" in tables:
                    try:
                        rndata = db.parse_table("RelayNames")
                        for i in range(_n_rows(rndata)):
                            relay_no = _col_int(rndata, "Relay_no", i, 0)
                            ath_no = _col_int(rndata, "Ath_no", i, 0)
                            pos_no = _col_int(rndata, "Pos_no", i, 1)

                            if relay_no in relays_map and ath_no > 0:
                                relays_map[relay_no].legs.append((ath_no, pos_no))
                    except Exception as e:
                        result.errors.append(f"Error reading RelayNames table: {e}")

                result.relays = list(relays_map.values())

            except Exception as e:
                result.errors.append(f"Error reading Relay table: {e}")

        # =================================================================
        # 6. Read Session info (pool course)
        # =================================================================
        if "Session" in tables:
            try:
                sdata = db.parse_table("Session")
                if _n_rows(sdata) > 0:
                    course = _col_str(sdata, "Sess_course", 0, "Y")
                    course_map = {"Y": "25Y", "L": "50M", "S": "25M"}
                    result.pool_course = course_map.get(course.upper(), "25Y")
            except Exception:
                pass  # Non-critical

        # =================================================================
        # 7. Read Meet metadata
        # =================================================================
        if "Meet" in tables:
            try:
                mdata = db.parse_table("Meet")
                if _n_rows(mdata) > 0:
                    COURSE_MAP = {1: "25Y", 2: "25M", 3: "25Y", 4: "50M"}
                    # Meet_meettype: 1=dual, 2=invitational, etc.
                    course_code = _col_int(mdata, "Meet_course", 0, 3)
                    result.meet_info = ParsedMeetInfo(
                        name=_col_str(mdata, "Meet_name1", 0) or None,
                        location=_col_str(mdata, "Meet_location", 0) or None,
                        city=_col_str(mdata, "Meet_city", 0) or None,
                        state=_col_str(mdata, "Meet_state", 0) or None,
                        start_date=_col_str(mdata, "Meet_start", 0) or None,
                        end_date=_col_str(mdata, "Meet_end", 0) or None,
                        course=COURSE_MAP.get(course_code, "25Y"),
                        num_lanes=_col_int(mdata, "meet_numlanes", 0) or None,
                        meet_type=_col_int(mdata, "Meet_meettype", 0) or None,
                        ind_max_scorers=_col_int(mdata, "indmaxscorers_perteam", 0)
                        or None,
                        relay_max_scorers=_col_int(mdata, "relmaxscorers_perteam", 0)
                        or None,
                    )
                    # Override pool_course with Meet table if Session didn't have it
                    if result.meet_info.course:
                        result.pool_course = result.meet_info.course
            except Exception as e:
                result.errors.append(f"Error reading Meet table: {e}")

        # =================================================================
        # 8. Read Split times
        # =================================================================
        if "Split" in tables:
            try:
                spdata = db.parse_table("Split")
                for i in range(_n_rows(spdata)):
                    event_ptr = _col_int(spdata, "Event_ptr", i, 0)
                    ath_no = _col_int(spdata, "Ath_no", i, 0)
                    relay_no = _col_int(spdata, "Relay_no", i, 0)
                    split_no = _col_int(spdata, "Split_no", i, 0)
                    split_time = _col_float(spdata, "Split_Time", i)
                    rnd = _col_str(spdata, "Rnd_ltr", i, "F")

                    if split_time is not None and split_time > 0 and split_no > 0:
                        result.splits.append(
                            ParsedSplit(
                                event_ptr=event_ptr,
                                ath_no=ath_no,
                                relay_no=relay_no,
                                split_number=split_no,
                                split_time=split_time,
                                round_code=rnd,
                            )
                        )
            except Exception as e:
                result.errors.append(f"Error reading Split table: {e}")

        # =================================================================
        # 9. Read Dual meet pairings
        # =================================================================
        if "Dualteams" in tables:
            try:
                dtdata = db.parse_table("Dualteams")
                seen_pairs = set()
                for i in range(_n_rows(dtdata)):
                    a = _col_int(dtdata, "ateam_no", i, 0)
                    b = _col_int(dtdata, "bteam_no", i, 0)
                    g = _col_str(dtdata, "team_gender", i)
                    gender = normalize_gender(g) if g else None
                    pair_key = (min(a, b), max(a, b), gender)
                    if a > 0 and b > 0 and pair_key not in seen_pairs:
                        seen_pairs.add(pair_key)
                        result.dual_pairings.append(
                            ParsedDualPairing(
                                team_a_no=a,
                                team_b_no=b,
                                gender=gender,
                            )
                        )
            except Exception as e:
                result.errors.append(f"Error reading Dualteams table: {e}")

        # =================================================================
        # 10. Read Scoring rules
        # =================================================================
        if "Scoring" in tables:
            try:
                scdata = db.parse_table("Scoring")
                for i in range(_n_rows(scdata)):
                    place = _col_int(scdata, "score_place", i, 0)
                    gender_raw = _col_str(scdata, "score_sex", i)
                    gender = normalize_gender(gender_raw) if gender_raw else None
                    ind_pts = _col_float(scdata, "ind_score", i) or 0.0
                    rel_pts = _col_float(scdata, "rel_score", i) or 0.0
                    if place > 0 and (ind_pts > 0 or rel_pts > 0):
                        result.scoring_rules.append(
                            ParsedScoringRule(
                                place=place,
                                gender=gender,
                                ind_points=ind_pts,
                                relay_points=rel_pts,
                            )
                        )
            except Exception as e:
                result.errors.append(f"Error reading Scoring table: {e}")

    except Exception as e:
        result.errors.append(f"Parse error: {e}")

    return result


# ---------------------------------------------------------------------------
# Fallback: pyodbc-based parser (for non-password-protected databases)
# ---------------------------------------------------------------------------

HYTEK_PASSWORDS = [None, "", "cl4mm", "CLMM"]


def _connect_pyodbc(mdb_path: str):
    """Connect to an .mdb file using pyodbc. Tries multiple drivers and passwords."""
    drivers = []
    for d in pyodbc.drivers():
        if "access" in d.lower() or "mdb" in d.lower():
            drivers.append(d)
    for d in [
        "Microsoft Access Driver (*.mdb, *.accdb)",
        "Microsoft Access Driver (*.mdb)",
    ]:
        if d not in drivers:
            drivers.append(d)

    last_error = None
    for driver in drivers:
        for password in HYTEK_PASSWORDS:
            try:
                conn_str = f"DRIVER={{{driver}}};DBQ={mdb_path};"
                if password:
                    conn_str += f"PWD={password};"
                return pyodbc.connect(conn_str)
            except Exception as e:
                last_error = e
                continue

    raise ConnectionError(f"Cannot connect via pyodbc: {last_error}")


def _parse_with_pyodbc(mdb_path: str, result: MeetData) -> MeetData:
    """Fallback parser using pyodbc (requires Access ODBC driver + no password)."""
    try:
        conn = _connect_pyodbc(mdb_path)
    except ConnectionError as e:
        result.errors.append(str(e))
        return result

    cursor = conn.cursor()

    def table_exists(name):
        try:
            cursor.execute(f"SELECT TOP 1 * FROM [{name}]")
            return True
        except Exception:
            return False

    def get_cols(name):
        try:
            cursor.execute(f"SELECT TOP 1 * FROM [{name}]")
            return [desc[0] for desc in cursor.description]
        except Exception:
            return []

    def safe_get(row, idx, default=None):
        try:
            val = row[idx]
            return val if val is not None else default
        except (IndexError, KeyError):
            return default

    try:
        # Teams
        if table_exists("Team"):
            cols = get_cols("Team")
            cursor.execute("SELECT * FROM [Team]")
            for row in cursor.fetchall():
                cm = {c.lower(): i for i, c in enumerate(cols)}
                team_no = safe_get(row, cm.get("team_no", 0), 0)
                name = (
                    safe_get(row, cm.get("team_name", -1))
                    or safe_get(row, cm.get("team_short", -1))
                    or f"Team_{team_no}"
                )
                abbr = safe_get(row, cm.get("team_abbr", -1), "")
                result.teams.append(
                    ParsedTeam(
                        team_no=int(team_no),
                        name=str(name).strip(),
                        abbreviation=str(abbr).strip() if abbr else "",
                    )
                )

        # Athletes
        if table_exists("Athlete"):
            cols = get_cols("Athlete")
            cursor.execute("SELECT * FROM [Athlete]")
            for row in cursor.fetchall():
                cm = {c.lower(): i for i, c in enumerate(cols)}
                ath_no = int(safe_get(row, cm.get("ath_no", 0), 0))
                first = str(safe_get(row, cm.get("first_name", -1), "")).strip()
                last = str(safe_get(row, cm.get("last_name", -1), "")).strip()
                team_no = int(safe_get(row, cm.get("team_no", -1), 0))
                gender_raw = safe_get(row, cm.get("ath_sex", -1))
                gender = normalize_gender(str(gender_raw)) if gender_raw else None
                result.athletes.append(
                    ParsedAthlete(
                        ath_no=ath_no,
                        first_name=first,
                        last_name=last,
                        team_no=team_no,
                        gender=gender,
                    )
                )

        # Events
        if table_exists("Event"):
            cols = get_cols("Event")
            cursor.execute("SELECT * FROM [Event]")
            for row in cursor.fetchall():
                cm = {c.lower(): i for i, c in enumerate(cols)}
                event_ptr = int(safe_get(row, cm.get("event_ptr", 0), 0))
                event_no = int(safe_get(row, cm.get("event_no", -1), 0))
                event_sex = str(safe_get(row, cm.get("event_sex", -1), "X")).strip()
                event_dist = int(safe_get(row, cm.get("event_dist", -1), 0))
                event_stroke = str(
                    safe_get(row, cm.get("event_stroke", -1), "A")
                ).strip()
                ind_rel = str(safe_get(row, cm.get("ind_rel", -1), "I")).strip().upper()
                is_relay = ind_rel == "R"
                is_diving = (
                    "diving" in str(safe_get(row, cm.get("event_type", -1), "")).lower()
                )
                if event_dist == 0 and event_stroke in ("", "A") and not is_relay:
                    is_diving = True
                event_name = normalize_event_name(
                    distance=event_dist, stroke_code=event_stroke, is_relay=is_relay
                )
                if is_diving:
                    event_name = "Diving"
                gender = normalize_gender(event_sex)
                result.events.append(
                    ParsedEvent(
                        event_ptr=event_ptr,
                        event_no=event_no,
                        event_name=event_name or f"{event_dist} {event_stroke}",
                        gender=gender,
                        distance=event_dist,
                        stroke_code=event_stroke,
                        is_relay=is_relay,
                        is_diving=is_diving,
                    )
                )

        # Entries
        entry_table = (
            "Entry"
            if table_exists("Entry")
            else ("Result" if table_exists("Result") else None)
        )
        if entry_table:
            cols = get_cols(entry_table)
            cursor.execute(f"SELECT * FROM [{entry_table}]")
            for row in cursor.fetchall():
                cm = {c.lower(): i for i, c in enumerate(cols)}
                ath_no = int(safe_get(row, cm.get("ath_no", 0), 0))
                event_ptr = int(safe_get(row, cm.get("event_ptr", -1), 0))
                seed_raw = safe_get(row, cm.get("actualseed_time", -1)) or safe_get(
                    row, cm.get("seed_time", -1)
                )
                finals_raw = safe_get(row, cm.get("fin_time", -1))
                if finals_raw is None or finals_raw == 0:
                    finals_raw = safe_get(row, cm.get("fin_pad", -1))
                if finals_raw is None or finals_raw == 0:
                    finals_raw = safe_get(row, cm.get("fin_back1", -1))
                place = safe_get(row, cm.get("fin_place", -1))
                points = safe_get(row, cm.get("ev_score", -1), 0)
                heat = safe_get(row, cm.get("fin_heat", -1))
                lane = safe_get(row, cm.get("fin_lane", -1))
                is_exh = bool(safe_get(row, cm.get("fin_exh", -1), 0))
                fin_stat = str(safe_get(row, cm.get("fin_stat", -1), "")).strip()
                is_dq = fin_stat.upper() in ("DQ", "D", "DSQ")
                result.entries.append(
                    ParsedEntry(
                        ath_no=ath_no,
                        event_ptr=event_ptr,
                        seed_time=normalize_time(seed_raw),
                        finals_time=normalize_time(finals_raw),
                        place=int(place) if place else None,
                        points=float(points) if points else 0.0,
                        heat=int(heat) if heat else None,
                        lane=int(lane) if lane else None,
                        is_exhibition=is_exh,
                        is_dq=is_dq,
                    )
                )

        # Relays
        if table_exists("Relay"):
            cols = get_cols("Relay")
            cursor.execute("SELECT * FROM [Relay]")
            relays_map = {}
            for row in cursor.fetchall():
                cm = {c.lower(): i for i, c in enumerate(cols)}
                relay_no = int(safe_get(row, cm.get("relay_no", 0), 0))
                team_no = int(safe_get(row, cm.get("team_no", -1), 0))
                event_ptr = int(safe_get(row, cm.get("event_ptr", -1), 0))
                relay_letter = str(
                    safe_get(row, cm.get("team_ltr", -1))
                    or safe_get(row, cm.get("relay_alpha", -1), "A")
                ).strip()
                seed_raw = safe_get(row, cm.get("actualseed_time", -1))
                finals_raw = safe_get(row, cm.get("fin_time", -1))
                if finals_raw is None or finals_raw == 0:
                    finals_raw = safe_get(row, cm.get("fin_pad", -1))
                place = safe_get(row, cm.get("fin_place", -1))
                points = safe_get(row, cm.get("ev_score", -1), 0)
                relay = ParsedRelay(
                    relay_no=relay_no,
                    team_no=team_no,
                    event_ptr=event_ptr,
                    relay_letter=relay_letter or "A",
                    seed_time=normalize_time(seed_raw),
                    finals_time=normalize_time(finals_raw),
                    place=int(place) if place else None,
                    points=float(points) if points else 0.0,
                )
                relays_map[relay_no] = relay

            if table_exists("RelayNames"):
                cols = get_cols("RelayNames")
                cursor.execute("SELECT * FROM [RelayNames]")
                for row in cursor.fetchall():
                    cm = {c.lower(): i for i, c in enumerate(cols)}
                    relay_no = int(safe_get(row, cm.get("relay_no", 0), 0))
                    ath_no = int(safe_get(row, cm.get("ath_no", -1), 0))
                    pos_no = int(safe_get(row, cm.get("pos_no", -1), 1))
                    if relay_no in relays_map:
                        relays_map[relay_no].legs.append((ath_no, pos_no))

            result.relays = list(relays_map.values())

        # Session
        if table_exists("Session"):
            cols = get_cols("Session")
            cursor.execute("SELECT TOP 1 * FROM [Session]")
            row = cursor.fetchone()
            if row:
                cm = {c.lower(): i for i, c in enumerate(cols)}
                course = str(safe_get(row, cm.get("sess_course", -1), "Y")).strip()
                course_map = {"Y": "25Y", "L": "50M", "S": "25M"}
                result.pool_course = course_map.get(course.upper(), "25Y")

    except Exception as e:
        result.errors.append(f"pyodbc parse error: {e}")
    finally:
        try:
            conn.close()
        except Exception:
            pass

    return result
