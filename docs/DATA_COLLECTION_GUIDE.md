# AquaForge Championship Module - Data Collection Guide

**Purpose:** Comprehensive checklist for collecting real swimming data to build accurate parsers and modules  
**Target:** VCAC Championship (Feb 7, 2026) and VISAA State Championship (Feb 12-14, 2026)  
**Created:** January 15, 2026

---

## 🎯 Objective

Collect **actual** data exports from swimming management systems to:

1. Build accurate psych sheet parsers with real field mappings
2. Develop point projection engine with actual scoring tables
3. Create entry optimization based on real constraints
4. Configure relay optimizer with actual split time data

---

## 📋 Data Collection Checklist

### Priority 1: Psych Sheets (Critical - Do First)

| Item                     | Source              | File Type        | Download Path         | Status |
| ------------------------ | ------------------- | ---------------- | --------------------- | ------ |
| VCAC 2026 Psych Sheet    | Hy-Tek Meet Manager | `.csv` or `.cl2` | Export → CSV/SDIF     | ☐      |
| VCAC 2025 Results        | SwimCloud or Hy-Tek | `.csv` or `.pdf` | Historical comparison | ☐      |
| VISAA State 2025 Results | VISAA website       | `.pdf` or `.csv` | visaa.org → Swimming  | ☐      |
| Sample Hy-Tek CSV Export | Meet Manager        | `.csv`           | File → Export → CSV   | ☐      |

#### Psych Sheet Fields Needed:

```
Required columns (map these exactly as they appear):
- [Column Name] → swimmer_name
- [Column Name] → team
- [Column Name] → event
- [Column Name] → seed_time (format: SS.ss or MM:SS.ss)
- [Column Name] → gender (M/F)
- [Column Name] → grade (7-12 or age)
- [Column Name] → personal_best (if available)
- [Column Name] → dive_score (for diving events)
```

**How to Export from Hy-Tek:**

1. Open Meet Manager with championship meet loaded
2. File → Export → Entries (or Events)
3. Choose CSV format
4. Select "All Events" and "All Teams"
5. Include: Name, Team, Entry Time, Age/Grade

---

### Priority 2: Team Roster Data

| Item                             | Source                    | File Type         | Status |
| -------------------------------- | ------------------------- | ----------------- | ------ |
| Seton Full Roster 2025-26        | Team Unify / SwimCloud    | `.csv` or `.xlsx` | ☐      |
| Swimmer Best Times (all strokes) | SwimCloud or USA Swimming | `.csv`            | ☐      |
| Relay Split Times                | Hy-Tek or manual entry    | `.csv`            | ☐      |
| Grade/Eligibility Info           | School records            | `.xlsx`           | ☐      |

#### Roster Fields Needed:

```json
{
  "swimmer_name": "Last, First",
  "gender": "M/F",
  "grade": 9-12,
  "age": 14-18,
  "primary_stroke": "Free/Back/Breast/Fly",
  "events": {
    "50 Free": { "best_time": 24.56, "season_best": 24.89 },
    "100 Free": { "best_time": 53.12, "season_best": 54.23 },
    "100 Back": { "best_time": 59.45, "season_best": null },
    // ... all events swimmer has times for
  },
  "relay_splits": {
    "50 Free": 23.45,  // faster than individual 50 time
    "100 Free": 52.10  // relay split for 100 leg
  },
  "is_diver": false,
  "dive_scores": null
}
```

---

### Priority 3: Meet Rules & Scoring Tables

| Item                         | Source          | File Type           | Status |
| ---------------------------- | --------------- | ------------------- | ------ |
| VCAC Scoring Table           | VCAC Handbook   | Manual copy or scan | ☐      |
| VISAA Championship Scoring   | VISAA Rules     | visaa.org           | ☐      |
| Entry Limits per Event       | Meet invitation | `.pdf`              | ☐      |
| Individual Event Limits      | Rule book       | Manual              | ☐      |
| Relay-3 Rule (if applicable) | Meet invitation | Check               | ☐      |

#### Scoring Tables to Capture:

**VCAC Championship (12 places):**

```python
VCAC_INDIVIDUAL_POINTS = [32, 26, 24, 22, 20, 18, 14, 10, 8, 6, 4, 2]
VCAC_RELAY_POINTS = [32, 26, 24, 22, 20, 18, 14, 10, 8, 6, 4, 2]  # or double?
```

**VISAA State Championship (16 places):**

```python
VISAA_CHAMP_FINALS = [40, 34, 32, 30, 28, 26, 24, 22, 18, 14, 12, 10, 8, 6, 4, 2]
VISAA_CONSOLATION = [20, 17, 16, 15, 14, 13, 12, 11, 9, 7, 6, 5, 4, 3, 2, 1]
```

---

### Priority 4: Historical Data for Validation

| Item                       | Source           | Purpose            | Status |
| -------------------------- | ---------------- | ------------------ | ------ |
| VCAC 2025 Final Results    | Hy-Tek/SwimCloud | Validation         | ☐      |
| VCAC 2024 Final Results    | Archive          | Trend analysis     | ☐      |
| VISAA 2025 DII Results     | visaa.org        | Scoring validation | ☐      |
| Seton's 2025 Final Entries | Coach records    | Entry pattern      | ☐      |

---

## 📂 One-Shot Download Package

### Files to Copy to Project Folder

Create folder: `AquaForge_v1.0.0-next_2026-01-10/data/real_exports/`

```
data/real_exports/
├── psych_sheets/
│   ├── vcac_2026_psych.csv          # Current meet psych sheet
│   ├── vcac_2025_psych.csv          # Last year for comparison
│   └── visaa_state_2025.csv         # State championship
├── rosters/
│   ├── seton_roster_2026.csv        # Full team roster
│   ├── seton_best_times.csv         # All-time bests per swimmer
│   └── seton_relay_splits.csv       # Relay split times
├── results/
│   ├── vcac_2025_results.csv        # Final results for validation
│   ├── visaa_2025_dii_results.csv   # State results
│   └── recent_dual_meets.csv        # Any recent meet results
├── rules/
│   ├── vcac_scoring_table.md        # Manual transcription
│   ├── visaa_scoring_table.md       # From rulebook
│   └── entry_rules.md               # Max entries, limits, etc.
└── screenshots/
    ├── hytek_export_dialog.png      # For parser documentation
    ├── swimcloud_page.png           # UI reference
    └── sample_psych_pdf_page.png    # PDF format reference
```

---

## 🖥️ System Access Needed

### Hy-Tek Meet Manager (Primary)

- [ ] Open existing VCAC 2026 meet file
- [ ] Export psych sheet (File → Export → CSV)
- [ ] Export lane assignments if available
- [ ] Screenshot export dialogs for column mapping reference

### SwimCloud

- [ ] Navigate to Seton team page
- [ ] Export roster with times
- [ ] Download psych sheet if available
- [ ] Screenshot data format

### Team Unify (if used)

- [ ] Export roster with all times
- [ ] Export relay configurations
- [ ] Check for split time data

### USA Swimming Database

- [ ] Look up official times for validation
- [ ] SWIMS database access if available

---

## 📊 Example: Actual Psych Sheet CSV Format

After exporting, document the **actual column headers** found:

```csv
# Example Hy-Tek Export (fill in real headers after export)
"Event","Heat","Lane","ID","Last Name","First Name","Team","Seed Time","Age","Gender"
"1","2","4","12345","Smith","John","SETON","23.45","16","M"
```

**Mapping Table (fill in after viewing real export):**
| Hy-Tek Column | AquaForge Field | Notes |
|---------------|-----------------|-------|
| "Last Name" + "First Name" | swimmer_name | Combine |
| "Team" | team | May need normalization |
| "Event" | event | Map to standard names |
| "Seed Time" | seed_time | Parse MM:SS.ss format |
| "Age" | grade | May need to convert |

---

## ✅ Quick Actions for Data Grab Session

### Step-by-Step in 15 Minutes:

1. **Hy-Tek (5 min)**
   - Open VCAC 2026 meet
   - File → Export → Entries to CSV
   - Save to USB/project folder
2. **SwimCloud (3 min)**
   - Go to Seton team page
   - Export roster/times if option exists
   - Screenshot the page with times visible
3. **VCAC Results (2 min)**
   - Find 2025 VCAC results file
   - Copy to project folder
4. **Scoring Rules (2 min)**
   - Photo/copy of VCAC scoring table
   - Note any special rules (Relay-3, exhibition, etc.)
5. **Transfer (3 min)**
   - Copy all files to: `data/real_exports/`
   - Create README noting date collected

---

## 🔧 Post-Collection: Parser Development Workflow

With real data in hand:

1. **Analyze CSV structure** → Update `psych_sheet_parser.py`
2. **Map column names** → Build column mapping dict
3. **Handle time formats** → `_parse_time()` function
4. **Normalize team names** → Team alias dictionary
5. **Validate with results** → Compare projected vs actual points
6. **Test edge cases** → NT times, scratches, diving scores

---

## 📝 Data Privacy Note

All swimmer data should be handled appropriately:

- Use for team optimization only
- Don't share raw files publicly
- Swimmer names can be anonymized for testing

---

**Ready to collect? Print this checklist and work through it systematically!**
