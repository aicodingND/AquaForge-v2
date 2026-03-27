"""
Complete Roster Conversion Script
Combines Coach Koehr's Excel + HyTek PDFs to create ideal format with ALL grades (6-12)
"""

import os
import sys

import pandas as pd

# Add the backend to path for PDF parsing
sys.path.insert(0, r"c:\Users\Michael\Desktop\SwimAi\swim_ai_reflex")

from swim_ai_reflex.backend.core.hytek_pdf_parser import parse_hytek_pdf

# File paths
COACH_EXCEL = r"c:\Users\Michael\Desktop\SwimAi\uploads\Girls Seton and Trinity Christian Swimming Times-no 7th graders W GenderTab.xlsx"
SETON_PDF = r"c:\Users\Michael\Desktop\SwimAi\uploads\Dual Meet Option A Demo Hytek Files\seton swimming individual times-no manipulation-nov23,25.pdf"
TRINITY_PDF = r"c:\Users\Michael\Desktop\SwimAi\uploads\Dual Meet Option A Demo Hytek Files\Trinity Christian swimming individual times-no manipulation-nov23,25.pdf"
OUTPUT_DIR = r"c:\Users\Michael\Desktop\SwimAi\swim_ai_reflex\uploads"


def parse_pdf_to_df(pdf_path, team_name):
    """Parse HyTek PDF and return DataFrame."""
    print(f"\n▸ Parsing {team_name} PDF...")
    try:
        df = parse_hytek_pdf(pdf_path)
        print(f"✓ Extracted {len(df)} entries")
        return df
    except Exception as e:
        print(f"✗ Error: {e}")
        return pd.DataFrame()


def normalize_event_name(event):
    """Normalize event names to standard format."""
    if pd.isna(event) or not event:
        return ""

    event = str(event).strip()
    event_lower = event.lower()

    # Determine gender prefix
    gender_prefix = ""
    if "girls" in event_lower or "women" in event_lower:
        gender_prefix = "Girls "
    elif "boys" in event_lower or "men" in event_lower:
        gender_prefix = "Boys "

    # Remove existing gender prefix for normalization
    event_clean = (
        event_lower.replace("girls", "")
        .replace("boys", "")
        .replace("women", "")
        .replace("men", "")
        .strip()
    )

    # Map to standard names
    if "50" in event_clean and "free" in event_clean:
        return f"{gender_prefix}50 Yard Freestyle"
    elif "100" in event_clean and "free" in event_clean:
        return f"{gender_prefix}100 Yard Freestyle"
    elif "200" in event_clean and "free" in event_clean and "relay" not in event_clean:
        return f"{gender_prefix}200 Yard Freestyle"
    elif "500" in event_clean and "free" in event_clean:
        return f"{gender_prefix}500 Yard Freestyle"
    elif "100" in event_clean and (
        "back" in event_clean or "backstroke" in event_clean
    ):
        return f"{gender_prefix}100 Yard Backstroke"
    elif "100" in event_clean and (
        "breast" in event_clean or "breaststroke" in event_clean
    ):
        return f"{gender_prefix}100 Yard Breaststroke"
    elif "100" in event_clean and ("fly" in event_clean or "butterfly" in event_clean):
        return f"{gender_prefix}100 Yard Butterfly"
    elif "200" in event_clean and "im" in event_clean:
        return f"{gender_prefix}200 Yard IM"
    elif "diving" in event_clean or "dive" in event_clean:
        return "Diving"
    elif "200" in event_clean and "medley" in event_clean and "relay" in event_clean:
        return f"{gender_prefix}200 Medley Relay"
    elif "200" in event_clean and "free" in event_clean and "relay" in event_clean:
        return f"{gender_prefix}200 Free Relay"
    elif "400" in event_clean and "free" in event_clean and "relay" in event_clean:
        return f"{gender_prefix}400 Free Relay"

    return event  # Return original if no match


def convert_time_to_seconds(time_val):
    """Convert time to decimal seconds."""
    if pd.isna(time_val):
        return None

    # Already a number
    if isinstance(time_val, (int, float)):
        return float(time_val)

    # String format like "0:23.45" or "1:05.23"
    if isinstance(time_val, str):
        time_val = time_val.strip()
        if ":" in time_val:
            parts = time_val.split(":")
            if len(parts) == 2:
                minutes = float(parts[0])
                seconds = float(parts[1])
                return minutes * 60 + seconds
        else:
            try:
                return float(time_val)
            except Exception:
                return None

    return None


def process_excel_sheet(df, team_name, opponent_name):
    """Process Excel sheet to ideal format."""
    print(f"\n▸ Processing {team_name} Excel data...")

    ideal_data = []

    for _, row in df.iterrows():
        # Try different column name variations
        swimmer = None
        for col in ["swimmer", "Swimmer", "Name", "name", "SWIMMER"]:
            if col in df.columns and pd.notna(row.get(col)):
                swimmer = str(row[col]).strip()
                break

        if not swimmer:
            continue

        # Extract other fields
        grade = None
        for col in ["grade", "Grade", "Gr", "gr", "GRADE"]:
            if col in df.columns and pd.notna(row.get(col)):
                try:
                    grade = int(row[col])
                except Exception:
                    pass
                break

        gender = None
        for col in ["gender", "Gender", "Sex", "sex", "GENDER"]:
            if col in df.columns and pd.notna(row.get(col)):
                gender = str(row[col]).strip().upper()[0]
                break

        event = None
        for col in ["event", "Event", "EVENT"]:
            if col in df.columns and pd.notna(row.get(col)):
                event = str(row[col]).strip()
                break

        time = None
        for col in ["time", "Time", "TIME"]:
            if col in df.columns and pd.notna(row.get(col)):
                time = convert_time_to_seconds(row[col])
                break

        # Skip if missing critical data
        if not all([swimmer, event, time]):
            continue

        ideal_row = {
            "swimmer": swimmer,
            "grade": grade if grade else "",
            "gender": gender if gender else "F",  # Default to F for girls file
            "event": normalize_event_name(event),
            "time": time,
            "team": team_name,
            "opponent": opponent_name,
            "meet_date": "2024-11-23",
        }

        ideal_data.append(ideal_row)

    print(f"✓ Processed {len(ideal_data)} entries")
    return pd.DataFrame(ideal_data)


def extract_lower_grades(pdf_df, team_name, opponent_name):
    """Extract 6th and 7th graders from PDF data."""
    print(f"\n▸ Extracting 6th and 7th graders from {team_name} PDF...")

    if pdf_df.empty:
        print("No PDF data available")
        return pd.DataFrame()

    # Filter for grades 6 and 7
    lower_grades = pdf_df[pdf_df["grade"].isin([6, 7])].copy()

    if lower_grades.empty:
        print("No 6th or 7th graders found")
        return pd.DataFrame()

    # Convert to ideal format
    ideal_data = []
    for _, row in lower_grades.iterrows():
        ideal_row = {
            "swimmer": str(row.get("swimmer", "")).strip(),
            "grade": int(row.get("grade", 0)),
            "gender": str(row.get("gender", "F")).strip().upper()[0],
            "event": normalize_event_name(row.get("event", "")),
            "time": convert_time_to_seconds(row.get("time")),
            "team": team_name,
            "opponent": opponent_name,
            "meet_date": "2024-11-23",
        }

        # Skip if missing critical data
        if ideal_row["swimmer"] and ideal_row["event"] and ideal_row["time"]:
            ideal_data.append(ideal_row)

    result_df = pd.DataFrame(ideal_data)
    print(f"✓ Found {len(result_df)} entries (6th/7th graders)")
    return result_df


def main():
    """Main execution."""
    print("\n" + "=" * 70)
    print("▸ COMPLETE ROSTER CONVERSION")
    print("Combining Excel (8-12 grades) + PDF (6-7 grades)")
    print("=" * 70)

    # Step 1: Parse Coach's Excel file
    print("\n" + "=" * 70)
    print("STEP 1: Parse Coach Koehr's Excel File")
    print("=" * 70)

    try:
        all_sheets = pd.read_excel(COACH_EXCEL, sheet_name=None)
        print("\n✓ Excel file loaded!")
        print(f"▸ Found {len(all_sheets)} sheet(s): {list(all_sheets.keys())}")
    except Exception as e:
        print(f"✗ Error loading Excel: {e}")
        return

    # Step 2: Parse HyTek PDFs
    print("\n" + "=" * 70)
    print("STEP 2: Parse HyTek PDFs for 6th/7th Graders")
    print("=" * 70)

    seton_pdf_df = parse_pdf_to_df(SETON_PDF, "Seton")
    trinity_pdf_df = parse_pdf_to_df(TRINITY_PDF, "Trinity Christian")

    # Step 3: Process each team
    print("\n" + "=" * 70)
    print("STEP 3: Combine Data and Create Ideal Format Files")
    print("=" * 70)

    # Determine which sheet is which team
    seton_sheet = None
    trinity_sheet = None

    for sheet_name, df in all_sheets.items():
        if "seton" in sheet_name.lower():
            seton_sheet = df
        elif "trinity" in sheet_name.lower():
            trinity_sheet = df
        elif seton_sheet is None:
            seton_sheet = df  # First sheet is Seton
        elif trinity_sheet is None:
            trinity_sheet = df  # Second sheet is Trinity

    # Process Seton
    if seton_sheet is not None:
        seton_excel_df = process_excel_sheet(seton_sheet, "Seton", "Trinity Christian")
        seton_lower_df = extract_lower_grades(
            seton_pdf_df, "Seton", "Trinity Christian"
        )
        seton_complete = pd.concat([seton_excel_df, seton_lower_df], ignore_index=True)

        # Save
        seton_output = os.path.join(
            OUTPUT_DIR, "IDEAL_Seton_vs_Trinity_Christian_COMPLETE.csv"
        )
        seton_complete.to_csv(seton_output, index=False)
        print("\n✓ Seton Complete File Saved:")
        print(f"{seton_output}")
        print(f"▸ Total entries: {len(seton_complete)}")
        print(f"- Grades 8-12: {len(seton_excel_df)}")
        print(f"- Grades 6-7: {len(seton_lower_df)}")

        # Grade breakdown
        if "grade" in seton_complete.columns:
            grade_counts = seton_complete["grade"].value_counts().sort_index()
            print("▸ Grade breakdown:")
            for grade, count in grade_counts.items():
                scoring = " ✓ Scoring" if grade >= 8 else " Exhibition"
                print(f"- Grade {grade}: {count} entries ({scoring})")

    # Process Trinity
    if trinity_sheet is not None:
        trinity_excel_df = process_excel_sheet(
            trinity_sheet, "Trinity Christian", "Seton"
        )
        trinity_lower_df = extract_lower_grades(
            trinity_pdf_df, "Trinity Christian", "Seton"
        )
        trinity_complete = pd.concat(
            [trinity_excel_df, trinity_lower_df], ignore_index=True
        )

        # Save
        trinity_output = os.path.join(
            OUTPUT_DIR, "IDEAL_Trinity_Christian_vs_Seton_COMPLETE.csv"
        )
        trinity_complete.to_csv(trinity_output, index=False)
        print("\n✓ Trinity Complete File Saved:")
        print(f"{trinity_output}")
        print(f"▸ Total entries: {len(trinity_complete)}")
        print(f"- Grades 8-12: {len(trinity_excel_df)}")
        print(f"- Grades 6-7: {len(trinity_lower_df)}")

        # Grade breakdown
        if "grade" in trinity_complete.columns:
            grade_counts = trinity_complete["grade"].value_counts().sort_index()
            print("▸ Grade breakdown:")
            for grade, count in grade_counts.items():
                scoring = " ✓ Scoring" if grade >= 8 else " Exhibition"
                print(f"- Grade {grade}: {count} entries ({scoring})")

    # Final summary
    print("\n" + "=" * 70)
    print("✓ CONVERSION COMPLETE!")
    print("=" * 70)
    print(f"\nOutput files saved to: {OUTPUT_DIR}")
    print("\n→ Files ready for SwimAI upload:")
    print("1. IDEAL_Seton_vs_Trinity_Christian_COMPLETE.csv")
    print("2. IDEAL_Trinity_Christian_vs_Seton_COMPLETE.csv")
    print("\n* These files include:")
    print("✓ All grades 6-12 (6-7 exhibition, 8-12 scoring)")
    print("✓ Standardized event names")
    print("✓ Opponent column (prevents multi-meet confusion)")
    print("✓ Meet date (2024-11-23)")
    print("✓ Ideal template format")


if __name__ == "__main__":
    main()
