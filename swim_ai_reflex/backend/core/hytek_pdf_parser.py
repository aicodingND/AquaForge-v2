import re

import pandas as pd
import pdfplumber

from swim_ai_reflex.backend.utils.file_loader import parse_flexible_time


def parse_hytek_pdf(pdf_path):
    """
    Improved Hytek PDF Parser (Admiral Koehr Edition).
    Handles multiple report formats (Meet Results, Top Times, etc.)
    with robust identity and grade extraction.
    """
    data = []

    # --- Regex Definitions ---
    # Event Line: "Event 1 Girls 200 Yard Medley Relay"
    re_event = re.compile(
        r"(?:Event\s+\#?\d+\s+)?(Girls|Boys|Women|Men|Female|Male|Mixed)\s+(.+)",
        re.IGNORECASE,
    )

    # Time Pattern: 1:23.45, 23.45, 1:23.45Y, 23.45L
    re_time = re.compile(r"(\d{1,2}:)?\d{1,2}\.\d{2}[YLS]?")

    # Date Pattern: 12/12/2023
    re_date = re.compile(r"\d{1,2}/\d{1,2}/\d{2,4}")

    # Grade Keywords
    grade_map = {
        "FR": 9,
        "SO": 10,
        "JR": 11,
        "SR": 12,
        "06": 6,
        "07": 7,
        "08": 8,
        "09": 9,
        "10": 10,
        "11": 11,
        "12": 12,
        "6": 6,
        "7": 7,
        "8": 8,
        "9": 9,
    }

    # Known Teams for guessing
    TEAM_KEYWORDS = {
        "SETON": "Seton",
        "SST": "Seton",
        "TRINITY": "Trinity",
        "TCS": "Trinity",
        "CHRS": "Trinity",
        "OAK": "Oakcrest",
        "OAKC": "Oakcrest",
    }

    current_event = None
    current_gender = None

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue

                lines = text.split("\n")
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue

                    # --- A. Event Detection ---
                    ev_match = re_event.search(line)
                    if ev_match:
                        gender_str = ev_match.group(1).lower()
                        # Normalize Gender
                        if gender_str in ("girls", "women", "female"):
                            current_gender = "F"
                        elif gender_str in ("boys", "men", "male"):
                            current_gender = "M"
                        else:
                            current_gender = "X"

                        current_event = ev_match.group(2).strip()
                        # Clean "Yard" / "Meter" / "Free" repetitions if needed
                        continue

                    # --- B. Swimmer Detection ---
                    if not current_event:
                        continue

                    # Does this line look like a results line? (Contains a time)
                    time_match = re_time.search(line)
                    if not time_match:
                        continue

                    # Tokenize for detailed analysis
                    parts = line.split()

                    # HY-TEK Format Detection
                    # Format A: Rank Time Name Grade Team Date ...
                    # Format B: Name Grade Team Time ...
                    # Format C: Time Rank Name Grade Team ...

                    time_str = time_match.group(0)
                    time_idx = -1
                    for i, p in enumerate(parts):
                        if time_str in p:
                            time_idx = i
                            break

                    # Heuristic: If time is early (index 0-2), it's likely Result/Rank-First
                    is_result_first = time_idx <= 2

                    name = None
                    grade = None
                    team = "Unknown"
                    found_time = parse_flexible_time(time_str.rstrip("YLS"))

                    if found_time is None or found_time <= 0:
                        continue

                    # --- Extraction Logic ---
                    if is_result_first:
                        # Skip rank and time
                        remaining = parts[time_idx + 1 :]

                        # Strip flags (Y, F, P, x, r)
                        while remaining and (
                            len(remaining[0]) <= 2
                            or remaining[0].lower() in ("y", "l", "s", "x", "f", "p")
                        ):
                            if remaining[0].upper() in grade_map:
                                break  # Stop if it's a grade
                            remaining.pop(0)

                        # Now we expect Name, Grade, Team, Date
                        # Extract Name (usually up to grade or date)
                        name_parts = []
                        for i, p in enumerate(remaining):
                            # Stop at grade, date, or team
                            p_clean = p.replace("(", "").replace(")", "").upper()
                            if (
                                p_clean in grade_map
                                or re_date.match(p)
                                or any(k in p_clean for k in TEAM_KEYWORDS)
                            ):
                                # The rest are Grade/Team/Date
                                tail = remaining[i:]
                                break
                            name_parts.append(p)
                        else:
                            tail = []

                        name = " ".join(name_parts).replace(",", "").strip()

                        # Extract Grade and Team from tail
                        for p in tail:
                            p_clean = p.replace("(", "").replace(")", "").upper()
                            if not grade and p_clean in grade_map:
                                grade = grade_map[p_clean]
                            for k, v in TEAM_KEYWORDS.items():
                                if k in p_clean:
                                    team = v
                                    break

                    else:
                        # Name First Format
                        # [Name] [Grade] [Team] [Time] ...
                        name_parts = []
                        for i, p in enumerate(parts[:time_idx]):
                            p_clean = p.replace("(", "").replace(")", "").upper()
                            if p_clean in grade_map:
                                grade = grade_map[p_clean]
                                # Rest before time might be team
                                team_parts = parts[i + 1 : time_idx]
                                if team_parts:
                                    potential_team = " ".join(team_parts).upper()
                                    for k, v in TEAM_KEYWORDS.items():
                                        if k in potential_team:
                                            team = v
                                            break
                                break
                            name_parts.append(p)

                        name = " ".join(name_parts).replace(",", "").strip()

                    # Final Cleanup & Validation
                    if not name or len(name) < 3:
                        continue

                    # Sanitize name
                    if name.upper() in ("NAME", "TEAM", "EVENT", "RELAY", "TIME"):
                        continue

                    # Overwrite team if filename suggests it
                    filename_lower = pdf_path.lower()
                    if "seton" in filename_lower:
                        team = "Seton"
                    elif "trinity" in filename_lower:
                        team = "Trinity"

                    data.append(
                        {
                            "swimmer": name,
                            "grade": grade,
                            "gender": current_gender,
                            "event": current_event,
                            "time": found_time,
                            "team": team,
                            "is_relay": "Relay" in current_event,
                        }
                    )

    except Exception as e:
        print(f"Error parsing PDF: {e}")
        return pd.DataFrame()

    return pd.DataFrame(data)
