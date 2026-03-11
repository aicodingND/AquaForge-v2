# core/normalization.py
import logging
import os
import re
from functools import lru_cache

import pandas as pd

from swim_ai_reflex.backend.core.hytek_pdf_parser import parse_hytek_pdf
from swim_ai_reflex.backend.utils.file_loader import parse_flexible_time

logger = logging.getLogger(__name__)

GRADE_MAP = {"FR": 9, "SO": 10, "JR": 11, "SR": 12, "8": 8}
EVENT_ORDER = [
    "50 Free",
    "100 Free",
    "200 Free",
    "500 Free",
    "100 Back",
    "100 Breast",
    "100 Fly",
    "200 IM",
]


@lru_cache(maxsize=256)
def canonicalize_event_name(col_name: str) -> str:
    """Canonicalize event name with LRU caching for repeated lookups."""
    if not isinstance(col_name, str):
        return str(col_name)
    s = col_name.strip()
    for ev in EVENT_ORDER:
        if s.lower() == ev.lower():
            return ev
    for ev in EVENT_ORDER:
        if ev.split()[0].lower() in s.lower():
            return ev
    s2 = s.replace("Freestyle", "Free").replace(" freestyle", " Free")
    s2 = re.sub(r"\s+", " ", s2).strip()
    return s2


@lru_cache(maxsize=512)
def extract_grade_from_name(name_str: str):
    """Extract grade from swimmer name with LRU caching."""
    if not isinstance(name_str, str):
        return None, name_str
    m = re.match(r"(.+?)\s*\(\s*(FR|SO|JR|SR|8)\s*\)$", name_str, re.I)
    if m:
        clean_name = m.group(1).strip()
        g_str = m.group(2).upper()
        grade = GRADE_MAP.get(g_str)
        if grade is None and g_str.isdigit():
            grade = int(g_str)
        return grade, clean_name
    return None, name_str


def normalize_to_standard(normalized_df, team="seton"):
    if normalized_df is None or normalized_df.empty:
        return pd.DataFrame(
            columns=[
                "swimmer",
                "grade",
                "gender",
                "event",
                "time",
                "team",
                "is_relay",
                "is_diving",
                "dive_score",
            ]
        )

    # Check if already standardized (from PDF parser)
    if (
        "swimmer" in normalized_df.columns
        and "event" in normalized_df.columns
        and "time" in normalized_df.columns
    ):
        # Just ensure all columns exist and fill team if missing
        df = normalized_df.copy()
        if "grade" not in df.columns:
            df["grade"] = None
        if "gender" not in df.columns:
            df["gender"] = None
        if "is_relay" not in df.columns:
            df["is_relay"] = False
        if "is_diving" not in df.columns:
            df["is_diving"] = False
        if "dive_score" not in df.columns:
            df["dive_score"] = None
        if "team" not in df.columns:
            df["team"] = team.lower()
        else:
            df["team"] = df["team"].str.lower()

        clean_names = []
        grades = []

        for idx, row in df.iterrows():
            curr_grade = row["grade"]
            curr_name = row["swimmer"]

            extracted_grade, clean_name = extract_grade_from_name(curr_name)

            clean_names.append(clean_name)

            # Helper to parse atomic grade value
            def parse_grade_value(val):
                if pd.isna(val) or val is None:
                    return None
                s_val = str(val).strip().upper()
                if not s_val:
                    return None
                if s_val in GRADE_MAP:
                    return GRADE_MAP[s_val]
                try:
                    return int(float(val))
                except (ValueError, TypeError):
                    return None

            # Prioritize existing column grade, then extracted grade
            parsed_curr = parse_grade_value(curr_grade)

            if parsed_curr is not None:
                grades.append(parsed_curr)
            elif extracted_grade is not None:
                grades.append(extracted_grade)
            else:
                grades.append(None)

        df["swimmer"] = clean_names
        df["grade"] = grades

        # Identify diving events if not already set
        if "event" in df.columns:
            df.loc[
                df["event"].astype(str).str.lower().str.contains("diving"), "is_diving"
            ] = True

        # Remove entries with empty swimmer names
        df = df[
            df["swimmer"].notna() & (df["swimmer"].astype(str).str.strip() != "")
        ].reset_index(drop=True)

        # GENDER SEPARATION:
        # Normalize gender column if it exists
        if "gender" in df.columns and df["gender"].notna().any():
            # Standardize to M/F
            df["gender"] = df["gender"].astype(str).str.upper().str.strip()
            df.loc[
                df["gender"].str.startswith("M") | df["gender"].str.startswith("B"),
                "gender",
            ] = "M"
            df.loc[
                df["gender"].str.startswith("F") | df["gender"].str.startswith("G"),
                "gender",
            ] = "F"

            # Update event names to include gender (e.g., "Boys 50 Free")
            # Only if gender is M or F
            # Gender values are now standardized to M/F

            # Prepend gender to event name if not already there
            # Check if event already starts with Boys/Girls to avoid double prefix
            def add_gender_prefix(row):
                ev = str(row["event"])
                g = row["gender"]
                if g == "M" and not ev.lower().startswith("boys"):
                    return f"Boys {ev}"
                elif g == "F" and not ev.lower().startswith("girls"):
                    return f"Girls {ev}"
                return ev

            df["event"] = df.apply(add_gender_prefix, axis=1)

        return df[
            [
                "swimmer",
                "grade",
                "gender",
                "event",
                "time",
                "team",
                "is_relay",
                "is_diving",
                "dive_score",
            ]
        ]

    # If not standardized, try to find columns
    cols = [c for c in normalized_df.columns]
    lc = [str(c).strip().lower() for c in cols]

    swimmer_col = None
    gender_col = None
    grade_col = None

    for col, lc_col in zip(cols, lc):
        if lc_col in ("swimmer", "name", "athlete"):
            swimmer_col = col
        elif lc_col in ("gender", "sex", "gen", "m/f"):
            gender_col = col
        elif lc_col in ("grade", "class", "year"):
            grade_col = col

    if swimmer_col is None:
        swimmer_col = cols[0]

    # Event columns are those that are NOT swimmer, gender, or grade
    exclude_cols = {swimmer_col, gender_col, grade_col}
    event_cols = [c for c in cols if c not in exclude_cols]

    logger.debug(f"[NORM] Normalizing raw dataframe with cols: {cols}")
    records = []
    for idx, row in normalized_df.iterrows():
        try:
            swimmer_cell = str(row.get(swimmer_col, "")).strip()
            if swimmer_cell == "" or swimmer_cell.lower().startswith("total"):
                continue

            # Extract grade/gender from row if columns exist
            row_grade = row.get(grade_col) if grade_col else None
            row_gender = row.get(gender_col) if gender_col else None

            # Fallback: extract grade from name if not in column
            if not row_grade:
                extracted_grade, clean_name = extract_grade_from_name(swimmer_cell)
                if extracted_grade:
                    row_grade = extracted_grade
                    name = clean_name
                else:
                    name = swimmer_cell
            else:
                name = swimmer_cell

            for c in event_cols:
                raw_time = row.get(c, None)
                if pd.isna(raw_time) or str(raw_time).strip() == "":
                    continue

                secs = parse_flexible_time(raw_time)
                if secs is None:
                    continue
                ev = canonicalize_event_name(str(c))
                is_relay = "relay" in str(c).lower()
                is_diving = "diving" in str(c).lower()
                dive_score = secs if is_diving else None

                records.append(
                    {
                        "swimmer": name,
                        "grade": row_grade,
                        "gender": row_gender,
                        "event": ev,
                        "time": secs,
                        "team": team,
                        "is_relay": is_relay,
                        "is_diving": is_diving,
                        "dive_score": dive_score,
                    }
                )
        except Exception as e:
            logger.error(f"[NORM] Error processing row {idx}: {e}")
            continue

    if not records:
        return pd.DataFrame(
            columns=[
                "swimmer",
                "grade",
                "gender",
                "event",
                "time",
                "team",
                "is_relay",
                "is_diving",
                "dive_score",
            ]
        )
    return pd.DataFrame.from_records(records)


def load_roster_file(file_path, team_name):
    """Loads a roster from Excel or PDF."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        df = parse_hytek_pdf(file_path)
        return normalize_to_standard(df, team=team_name)
    else:
        # Assume Excel
        # Use flexible loader from backend.utils
        from swim_ai_reflex.backend.utils.file_loader import load_file_dynamic

        df, _diag = load_file_dynamic(file_path)
        return normalize_to_standard(df, team=team_name)


def load_first_two_sheets_as_standard(uploaded_file, team_names=("seton", "opponent")):
    """Legacy support for combined excel file."""
    xls = pd.ExcelFile(uploaded_file)
    if len(xls.sheet_names) < 2:
        raise RuntimeError("Workbook must contain at least two sheets")

    def read_sheet_robust(sheet_name):
        # Read first few rows to find header
        df_preview = pd.read_excel(
            uploaded_file, sheet_name=sheet_name, header=None, nrows=10
        )
        header_row_idx = 0

        for i, row in df_preview.iterrows():
            row_str = row.astype(str).str.lower().tolist()
            # 1. Look for explicit 'swimmer'/'name'
            if any(x in row_str for x in ["swimmer", "name", "athlete"]):
                header_row_idx = i
                break
            # 2. Look for event keywords if explicit name not found
            # Check if at least 2 columns contain 'free', 'back', 'breast', 'fly', 'im'
            event_matches = sum(
                1
                for x in row_str
                if any(k in x for k in ["free", "back", "breast", "fly", "im"])
            )
            if event_matches >= 2:
                header_row_idx = i
                break

        # Read actual df with correct header
        df = pd.read_excel(
            uploaded_file, sheet_name=sheet_name, header=header_row_idx, dtype=object
        )

        # If the header row had a NaN/empty first column (common in this format), rename it to 'swimmer'
        if len(df.columns) > 0:
            first_col = df.columns[0]
            if (
                str(first_col).startswith("Unnamed")
                or pd.isna(first_col)
                or str(first_col).strip() == ""
            ):
                df.rename(columns={first_col: "swimmer"}, inplace=True)
            elif "swimmer" not in [str(c).lower() for c in df.columns]:
                df.rename(columns={first_col: "swimmer"}, inplace=True)

        return df

    s0 = read_sheet_robust(xls.sheet_names[0])
    s1 = read_sheet_robust(xls.sheet_names[1])

    std0 = normalize_to_standard(s0, team=team_names[0])
    std1 = normalize_to_standard(s1, team=team_names[1])
    return std0, std1
