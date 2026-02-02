# 🏊 AquaForge CSV Template Guide for Coach Koehr

## Quick Start

Upload **two CSV files** - one for Seton and one for the opponent.

---

## Required Columns

| Column | Format | Example | Notes |
|--------|--------|---------|-------|
| **swimmer** | Text | John Smith | Full name |
| **grade** | Number | 11 | 6-7 = exhibition, 8-12 = scoring |
| **gender** | Letter | M or F | Single character |
| **event** | Text | Boys 50 Free | Include Boys/Girls prefix |
| **time** | Seconds | 23.45 | Decimal seconds (diving = score e.g. 285.50) |
| **team** | Text | Seton | Keep consistent |

## Optional (Recommended) Columns

| Column | Format | Example |
|--------|--------|---------|
| **opponent** | Text | Trinity |
| **meet_date** | Date | 2024-12-15 |

---

## VISAA Dual Meet Events (in order)

### Individual Events
1. Boys/Girls 200 Free
2. Boys/Girls 200 IM
3. Boys/Girls 50 Free
4. Boys/Girls Diving
5. Boys/Girls 100 Fly
6. Boys/Girls 100 Free
7. Boys/Girls 500 Free
8. Boys/Girls 100 Back
9. Boys/Girls 100 Breast

### Relay Events
1. Boys/Girls 200 Medley Relay
2. Boys/Girls 200 Free Relay
3. Boys/Girls 400 Free Relay

---

## Time Format

- **Swimming events**: Decimal seconds
  - 50 Free: `23.45` (not 0:23.45)
  - 100 Free: `52.18`
  - 200 Free: `118.45`
  - 500 Free: `305.30`

- **Diving**: Use score directly
  - `285.50` (score, not time)

---

## Grade Levels

| Grade | Scoring Status |
|-------|----------------|
| 6-7 | Exhibition (no points, but can swim) |
| 8-12 | Scoring (earns points) |

---

## Entry Limits per VISAA Rules

- Max 4 swimmers per team per individual event
- Max 2 individual events per swimmer
- Max 4 total events per swimmer (NFHS Rule 3-2-1: 2 indiv + 2 relay, or 1 indiv + 3 relay)
- No back-to-back events

---

## Sample Row

```csv
swimmer,grade,gender,event,time,team,opponent,meet_date
John Smith,11,M,Boys 50 Free,23.45,Seton,Trinity,2024-12-15
```

---

## Common Mistakes to Avoid

❌ Time format like `0:23.45` → Use `23.45`
❌ Gender as "Male" → Use `M`
❌ Missing grade column → App can't determine scoring
❌ Mixing multiple meets in one file → Create separate files
❌ Event names like "50 Freestyle" and "50 Free" in same file → Be consistent

---

## Files Created

1. `Seton_Team_Template.csv` - Sample Seton roster with all events
2. `Opponent_Team_Template.csv` - Sample opponent roster

Located in: `c:\Users\Michael\Desktop\AquaForgeFinal\`

---

Questions? The app auto-normalizes most event name variations, but consistent formatting gives best results!
