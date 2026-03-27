"""
Parse Coach Koehr's actual Excel file and analyze the structure
"""

import sys
from pathlib import Path

import pandas as pd

# File path
COACH_FILE = r"c:\Users\Michael\Desktop\SwimAi\uploads\Girls Seton and Trinity Christian Swimming Times-no 7th graders W GenderTab.xlsx"

print("\n" + "=" * 80)
print("ANALYZING COACH JIM KOEHR'S ACTUAL EXCEL FILE")
print("=" * 80)

try:
    # Read all sheets
    xl = pd.ExcelFile(COACH_FILE)

    print(f"\n▸ Excel File: {Path(COACH_FILE).name}")
    print(f"▸ Number of sheets: {len(xl.sheet_names)}")
    print(f"▸ Sheet names: {xl.sheet_names}\n")

    # Analyze each sheet
    for sheet_name in xl.sheet_names:
        print("\n" + "=" * 80)
        print(f"SHEET: {sheet_name}")
        print("=" * 80)

        df = pd.read_excel(xl, sheet_name)

        print(f"\n▸ Dimensions: {len(df)} rows × {len(df.columns)} columns")
        print(f"▸ Columns: {list(df.columns)}\n")

        print("First 5 rows:")
        print(df.head(5).to_string(index=False))

        # Analyze data types
        print("\n▸ Data Types:")
        for col in df.columns:
            unique_count = df[col].nunique()
            sample = df[col].dropna().iloc[0] if len(df[col].dropna()) > 0 else "N/A"
            print(
                f"- {col}: {df[col].dtype} ({unique_count} unique values, sample: {sample})"
            )

        # Check for specific columns we care about
        expected_cols = ["swimmer", "grade", "gender", "event", "time", "team"]
        print("\n✓ Required columns present:")
        for col in expected_cols:
            # Check case-insensitive
            found = any(col.lower() in c.lower() for c in df.columns)
            print(f"  - {col}: {'✓' if found else '✗'}")

        # Grade distribution
        if any("grade" in col.lower() for col in df.columns):
            grade_col = [c for c in df.columns if "grade" in c.lower()][0]
            print("\n▸ Grade Distribution:")
            print(df[grade_col].value_counts().sort_index().to_string())

        # Gender distribution
        if any("gender" in col.lower() or "sex" in col.lower() for col in df.columns):
            gender_col = [
                c for c in df.columns if "gender" in c.lower() or "sex" in c.lower()
            ][0]
            print("\n▸ Gender Distribution:")
            print(df[gender_col].value_counts().to_string())

        # Event types
        if any("event" in col.lower() for col in df.columns):
            event_col = [c for c in df.columns if "event" in c.lower()][0]
            print(f"\n▸ Event Types ({df[event_col].nunique()} unique):")
            for event in sorted(df[event_col].unique()[:10]):  # Show first 10
                count = len(df[df[event_col] == event])
                print(f"- {event}: {count} entries")

        # Team column
        if any("team" in col.lower() for col in df.columns):
            team_col = [c for c in df.columns if "team" in c.lower()][0]
            print("\n▸ Team Distribution:")
            print(df[team_col].value_counts().to_string())

        print("\n")

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)

    # Save summary to file
    summary_file = (
        r"c:\Users\Microsoft\Desktop\SwimAi\swim_ai_reflex\COACH_EXCEL_ANALYSIS.txt"
    )
    with open(summary_file, "w") as f:
        f.write(f"Analysis of: {COACH_FILE}\n")
        f.write(f"Sheets: {xl.sheet_names}\n")
        for sheet in xl.sheet_names:
            df = pd.read_excel(xl, sheet)
            f.write(f"\n{sheet}: {len(df)} rows, {list(df.columns)}\n")

    print(f"\n✓ Summary saved to: {summary_file}")

except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
