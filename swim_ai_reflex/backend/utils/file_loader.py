# utils/file_loader.py
import math
import re
from functools import lru_cache

import pandas as pd

_RE_TIME_SIMPLE = re.compile(r"^(?:(\d+):)?(\d+(?:\.\d+)?)$")
_RE_TIME_HMS = re.compile(r"^(\d+):(\d{2}):(\d+(?:\.\d+)?)$")


@lru_cache(maxsize=1024)
def parse_flexible_time(val):
    if val is None:
        return None
    try:
        if isinstance(val, (int, float)) and not (
            isinstance(val, float) and math.isnan(val)
        ):
            return float(val)
    except Exception:
        pass
    s = str(val)
    # Remove common swimming suffixes (Y=Yards, S/L=Meters, etc.)
    # e.g. "59.54Y", "1:02.33 S"
    s = re.sub(r"[a-zA-Z]+$", "", s).strip()

    m = _RE_TIME_HMS.match(s)
    if m:
        h = int(m.group(1))
        mm = int(m.group(2))
        sec = float(m.group(3))
        return h * 3600 + mm * 60 + sec
    m = _RE_TIME_SIMPLE.match(s)
    if m:
        if m.group(1):
            return int(m.group(1)) * 60 + float(m.group(2))
        else:
            return float(m.group(2))
    # fallback numeric token
    m = re.search(r"(\d+\.\d+|\d+)", s)
    if m:
        return float(m.group(1))
    return None


def load_file_dynamic(file_like_or_path):
    """Reads an excel file (file-like or path), picks best sheet, maps columns flexibly and returns a cleaned DataFrame and diagnostic dict."""
    diag = {"sheets": [], "chosen_sheet": None, "cols": {}, "dropped": 0}

    # Check if CSV
    is_csv = False
    if isinstance(file_like_or_path, str) and file_like_or_path.lower().endswith(
        ".csv"
    ):
        is_csv = True

    if is_csv:
        try:
            # Use python engine with sep=None to auto-detect delimiter (comma or tab)
            df_raw = pd.read_csv(file_like_or_path, sep=None, engine="python")
            diag["sheets"] = ["csv_data"]
            diag["chosen_sheet"] = "csv_data"
        except Exception as e:
            raise RuntimeError(f"Cannot open CSV: {e}")
    else:
        try:
            xl = pd.ExcelFile(file_like_or_path, engine="openpyxl")
            diag["sheets"] = xl.sheet_names
        except Exception as e:
            raise RuntimeError(f"Cannot open workbook: {e}")

        keywords = [
            "roster",
            "swim",
            "times",
            "results",
            "entries",
            "seton",
            "opponent",
            "team",
        ]
        chosen = None
        for s in xl.sheet_names:
            s_low = s.lower()
            if any(k in s_low for k in keywords):
                chosen = s
                break
        if not chosen:
            chosen = xl.sheet_names[0]
        diag["chosen_sheet"] = chosen

        # HEADER DETECTION LOGIC
        # 1. Read first 20 rows without header to scan content
        df_preview = xl.parse(chosen, header=None, nrows=20, dtype=object)

        best_header_row = 0
        max_matches = 0
        # Expanded keywords for better detection
        header_keywords = [
            "swimmer",
            "athlete",
            "name",
            "last name",
            "first name",
            "event",
            "time",
            "seed",
            "result",
            "team",
            "school",
        ]

        for i, row in df_preview.iterrows():
            # Convert row to string and lower case
            row_str = " ".join([str(x).lower() for x in row if pd.notnull(x)])
            matches = sum(1 for k in header_keywords if k in row_str)
            if matches > max_matches:
                max_matches = matches
                best_header_row = i

        # If we found a good candidate (at least 2 keywords), use it. Otherwise default to 0.
        if max_matches >= 2:
            print(
                f"DEBUG: Detailed Header Detection - Using row {best_header_row} as header (matches={max_matches})"
            )
            df_raw = xl.parse(chosen, header=best_header_row, dtype=object)
        else:
            print(
                "DEBUG: Detailed Header Detection - No clear header row found, defaulting to row 0"
            )
            df_raw = xl.parse(chosen, header=0, dtype=object)

    cols = [str(c).strip() for c in df_raw.columns]
    df_raw.columns = cols
    col_map = {}

    def find_col(tokens):
        for c in cols:
            cl = c.lower()
            # prioritization: prefer exact match first
            if cl in tokens:
                return c
            # then substring
            for t in tokens:
                if t in cl:
                    return c
        return None

    col_map["name"] = find_col(["name", "swimmer", "athlete", "combined name"])
    col_map["last_name"] = find_col(["last name", "lastname"])
    col_map["first_name"] = find_col(["first name", "firstname"])

    col_map["event"] = find_col(["event", "race", "stroke"])
    col_map["time"] = find_col(["time", "seed", "entry", "result", "finals"])
    col_map["team"] = find_col(["team", "school", "club"])
    col_map["opponent"] = find_col(
        ["opponent", "opponent team", "visitor", "visitor team", "vs", "vs team"]
    )
    col_map["grade"] = find_col(["grade", "class", "year"])
    col_map["gender"] = find_col(["gender", "sex"])

    # Composite Name Synthesis
    if not col_map["name"] and col_map["last_name"] and col_map["first_name"]:
        print("DEBUG: Synthesizing 'swimmer' column from Last/First name columns")
        df_raw["Synthesized_Name"] = (
            df_raw[col_map["last_name"]].astype(str)
            + ", "
            + df_raw[col_map["first_name"]].astype(str)
        )
        col_map["name"] = "Synthesized_Name"

    diag["cols"] = col_map
    if not col_map["name"] or not col_map["event"] or not col_map["time"]:
        raise RuntimeError(f"Required columns not detected. Found mapping: {col_map}")

    keep_cols = [col_map["name"], col_map["event"], col_map["time"]]
    if col_map.get("grade"):
        keep_cols.append(col_map["grade"])
    if col_map.get("team"):
        keep_cols.append(col_map["team"])
    if col_map.get("opponent"):
        keep_cols.append(col_map["opponent"])
    if col_map.get("gender"):
        keep_cols.append(col_map["gender"])

    df = df_raw[keep_cols].copy()
    rename_map = {
        col_map["name"]: "swimmer",
        col_map["event"]: "event",
        col_map["time"]: "time",
    }
    if col_map.get("grade"):
        rename_map[col_map["grade"]] = "grade"
    if col_map.get("team"):
        rename_map[col_map["team"]] = "team"
    if col_map.get("opponent"):
        rename_map[col_map["opponent"]] = "opponent"
    if col_map.get("gender"):
        rename_map[col_map["gender"]] = "gender"

    df = df.rename(columns=rename_map)
    df["swimmer"] = df["swimmer"].astype(str).str.strip()
    df["time"] = df["time"].apply(parse_flexible_time)
    before = len(df)
    df = df[df["swimmer"].notna() & df["event"].notna() & df["time"].notna()]
    diag["dropped"] = before - len(df)
    return df, diag
