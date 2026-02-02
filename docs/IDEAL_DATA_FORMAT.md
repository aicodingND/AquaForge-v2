# 📊 AquaForge Data Input Guide

> **Goal**: Get your swim meet data into AquaForge with zero issues.

---

## 🎯 The Perfect CSV Row

**Minimum (works fine):**

```csv
swimmer,grade,gender,event,time,team
John Smith,11,M,Boys 50 Free,23.45,Seton
```

**Recommended (with optional columns):**

```csv
swimmer,grade,gender,event,time,team,opponent,meet_date
John Smith,11,M,Boys 50 Free,23.45,Seton,Trinity,2024-12-15
```

Six required columns + two optional. Let's break each one down.

---

## 📋 Required Columns (6)

### 1. `swimmer` — Who is swimming?

| ✅ Good | ❌ Bad | Why |
|---------|--------|-----|
| `John Smith` | `J. Smith` | Need full name for accuracy |
| `Smith, John` | `Johnny` | Nicknames cause duplicates |

### 2. `grade` — Are they scoring-eligible?

| Grade | Status | Points? |
|-------|--------|---------|
| **8-12** | Scoring | ✅ Earns points |
| **6-7** | Exhibition | ❌ Swims but no points |

```csv
Tom Wilson,12,M,Boys 50 Free,23.45,Seton    ← Scores (grade 12)
Peter Young,7,M,Boys 50 Free,32.50,Seton    ← Exhibition (grade 7)
```

### 3. `gender` — M or F

| ✅ Use | ❌ Don't Use |
|--------|-------------|
| `M` | `Male`, `Boys`, `B` |
| `F` | `Female`, `Girls`, `G` |

### 4. `event` — What are they swimming?

**Individual Events** (standard dual meet):

```
Boys 50 Free       Girls 50 Free
Boys 100 Free      Girls 100 Free
Boys 200 Free      Girls 200 Free
Boys 500 Free      Girls 500 Free
Boys 100 Back      Girls 100 Back
Boys 100 Breast    Girls 100 Breast
Boys 100 Fly       Girls 100 Fly
Boys 200 IM        Girls 200 IM
Boys Diving        Girls Diving
```

**Relay Events**:

```
Boys 200 Medley Relay    Girls 200 Medley Relay
Boys 200 Free Relay      Girls 200 Free Relay
Boys 400 Free Relay      Girls 400 Free Relay
```

> 💡 **Tip**: Include "Boys" or "Girls" prefix. The app handles variations like "50 Freestyle" → "50 Free" automatically.

### 5. `time` — How fast? (in seconds)

| Event | Format | Example |
|-------|--------|---------|
| 50 Free | Seconds | `23.45` |
| 100 Free | Seconds | `52.18` |
| 200 Free | Seconds | `118.45` (not 1:58.45) |
| 500 Free | Seconds | `305.30` (not 5:05.30) |
| Diving | Score | `285.50` (total points, not time) |

**Converting MM:SS.ss to seconds:**

```
1:58.45 → 60 + 58.45 = 118.45
5:05.30 → 300 + 5.30 = 305.30
```

### 6. `team` — Which team?

```csv
John Smith,11,M,Boys 50 Free,23.45,Seton      ← Seton swimmer
Alex Lee,12,M,Boys 50 Free,24.80,Trinity      ← Opponent swimmer
```

The `team` column determines which side each swimmer is on.

---

## 📋 Optional Columns (Recommended)

### 7. `opponent` — Who are you racing against?

```csv
swimmer,grade,gender,event,time,team,opponent
John Smith,11,M,Boys 50 Free,23.45,Seton,Trinity
```

**Why include it?**

- Helps filter data when your file contains multiple meets
- Prevents mixing swimmers from different matchups
- Makes historical analysis easier

### 8. `meet_date` — When was this meet?

```csv
swimmer,grade,gender,event,time,team,opponent,meet_date
John Smith,11,M,Boys 50 Free,23.45,Seton,Trinity,2024-12-15
```

| Format | Example |
|--------|---------|
| `YYYY-MM-DD` | `2024-12-15` ✅ (preferred) |
| `MM/DD/YYYY` | `12/15/2024` ✅ |

**Why include it?**

- Track performance over season
- Use most recent times for optimization
- Filter by date range

---

## 📁 Two Ways to Organize Your Files

### Option A: Two Separate Files (Recommended)

**File 1: `Seton_Roster.csv`**

```csv
swimmer,grade,gender,event,time,team
John Smith,11,M,Boys 50 Free,23.45,Seton
John Smith,11,M,Boys 100 Free,52.18,Seton
Sarah Davis,12,F,Girls 50 Free,27.10,Seton
```

**File 2: `Trinity_Roster.csv`**

```csv
swimmer,grade,gender,event,time,team
Alex Lee,12,M,Boys 50 Free,24.80,Trinity
Amanda White,11,F,Girls 50 Free,28.20,Trinity
```

Upload each to the respective team slot.

### Option B: One Combined File

**File: `Meet_Data.csv`**

```csv
swimmer,grade,gender,event,time,team
John Smith,11,M,Boys 50 Free,23.45,Seton
Sarah Davis,12,F,Girls 50 Free,27.10,Seton
Alex Lee,12,M,Boys 50 Free,24.80,Trinity
Amanda White,11,F,Girls 50 Free,28.20,Trinity
```

The app splits by `team` column automatically.

---

## 🏊 Complete Meet Example

A swimmer typically swims **2 individual events + 1 relay**:

```csv
swimmer,grade,gender,event,time,team
John Smith,11,M,Boys 200 Medley Relay,112.50,Seton
John Smith,11,M,Boys 50 Free,23.45,Seton
John Smith,11,M,Boys 100 Free,52.18,Seton
```

**Per VISAA Rules:**

- Max 2 individual events per swimmer
- Max 4 total events per swimmer (NFHS Rule 3-2-1: 2 indiv + 2 relay, or 1 indiv + 3 relay)
- No back-to-back events allowed

---

## 🎯 Relay Format

For relays, list **each swimmer** on the relay with the **same relay time**:

```csv
swimmer,grade,gender,event,time,team
John Smith,11,M,Boys 200 Medley Relay,112.50,Seton
Mike Johnson,10,M,Boys 200 Medley Relay,112.50,Seton
Tom Wilson,12,M,Boys 200 Medley Relay,112.50,Seton
Chris Lee,11,M,Boys 200 Medley Relay,112.50,Seton
```

All 4 swimmers get the same time (the relay's total time).

---

## ⚠️ Common Mistakes

### ❌ Wrong Time Format

```csv
❌ John Smith,11,M,Boys 200 Free,1:58.45,Seton    ← MM:SS format
✅ John Smith,11,M,Boys 200 Free,118.45,Seton     ← Decimal seconds
```

### ❌ Inconsistent Team Names

```csv
❌ John Smith,11,M,Boys 50 Free,23.45,Seton
❌ Mike Johnson,10,M,Boys 100 Free,54.30,Seton Swimming   ← Different name!
✅ Mike Johnson,10,M,Boys 100 Free,54.30,Seton            ← Same name
```

### ❌ Missing Grade

```csv
❌ John Smith,,M,Boys 50 Free,23.45,Seton     ← No grade = can't determine scoring
✅ John Smith,11,M,Boys 50 Free,23.45,Seton   ← Grade 11 = scoring eligible
```

### ❌ Multiple Meets in One File

```csv
❌ File contains Seton vs Trinity AND Seton vs Bishop
   This causes duplicate entries and wrong optimization!

✅ Create separate files:
   - Seton_vs_Trinity.csv
   - Seton_vs_Bishop.csv
```

---

## ✅ Pre-Upload Checklist

Before uploading, verify:

- [ ] All 6 required columns present
- [ ] Times in decimal seconds (not MM:SS)
- [ ] Grades are numbers 6-12
- [ ] Gender is M or F
- [ ] Team name is consistent throughout
- [ ] One meet per file
- [ ] ~80-100 entries per team (typical dual meet)

---

## 📊 Sample Data Summary

| Metric | Typical Value |
|--------|---------------|
| Entries per team | 80-100 |
| Swimmers per team | 20-30 |
| Events (boys + girls) | 22 total |
| Entries per individual event | 4 max |
| Relay entries | 4 swimmers each |

---

## 🔧 Quick Reference

| Column | Type | Example | Notes |
|--------|------|---------|-------|
| swimmer | Text | John Smith | Full name |
| grade | Number | 11 | 6-7=exhibition, 8-12=scoring |
| gender | Letter | M | M or F only |
| event | Text | Boys 50 Free | Include gender prefix |
| time | Decimal | 23.45 | Seconds (diving=score) |
| team | Text | Seton | Your team or opponent |

---

## 💡 Pro Tips

1. **Export from HyTek**: Reports → Individual Results → Excel format
2. **Use Excel first**: Clean data, then Save As CSV
3. **Sort by event, then time**: Quickly spot fastest swimmers
4. **Color-code grades**: Green=scoring (8-12), Yellow=exhibition (6-7)
5. **Keep a master file**: All meets, then filter for specific matchups

---

## 🧹 Coach's Data Prep Checklist (Before Uploading)

**Filter OUT this data before sending — the simpler the file, the better!**

### ❌ Remove Before Uploading

| What to Remove | Why |
|----------------|-----|
| **JV events** (50 Breast, 50 Back, 100 IM) | Not in varsity dual meets |
| **Time trial entries** | Not part of the meet scoring |
| **Scratched swimmers** | They didn't compete |
| **DQ entries** | No valid time |
| **Previous meets** | Only include the meet you're optimizing for |
| **Relay splits** | Only need final relay time, not individual splits |
| **Blank rows** | Can cause parsing errors |

### ✅ Keep In Your File

| What to Keep | Why |
|--------------|-----|
| **All varsity swimmers** | Even slow ones — they might be strategic placements |
| **Exhibition swimmers (grades 6-7)** | Can absorb places without scoring |
| **All 22 varsity events** | Both Boys and Girls, individuals + relays |
| **Best time per swimmer per event** | Use season best or most recent |

### 🎯 Ideal File Size

| Metric | Target |
|--------|--------|
| Rows per team | 80-100 |
| Swimmers per team | 20-30 |
| Events covered | All 22 (11 per gender) |

**If your file has 200+ rows, you probably have multiple meets or extra data that should be filtered.**

### 📋 5-Minute Data Cleanup in Excel

1. **Delete non-varsity events**: Filter by event, delete JV rows
2. **Delete DQ/NS entries**: Filter by time, delete blank or "DQ" rows
3. **Check team names**: Find & Replace to make consistent (e.g., "Seton Swimming" → "Seton")
4. **Verify grades**: Any blanks? Fill them in
5. **Save As CSV**: File → Save As → CSV (Comma delimited)

---

## ⚙️ Nuances & Edge Cases

### Time Format Details

**The app expects times in total seconds (decimal):**

| Display Time | → | CSV Value |
|--------------|---|-----------|
| 23.45 | → | `23.45` |
| 58.92 | → | `58.92` |
| 1:02.45 | → | `62.45` |
| 1:58.30 | → | `118.30` |
| 5:15.80 | → | `315.80` |

**Quick conversion formula:**

```
Minutes × 60 + Seconds = Total Seconds

Example: 1:58.30
1 × 60 + 58.30 = 118.30
```

**HyTek typically exports as MM:SS.ss** — you may need to convert in Excel:

```excel
=MINUTE(A1)*60 + SECOND(A1)
```

---

### Team Name Standardization

**The problem:** HyTek exports might have variations in how a team is named.

| ❌ Inconsistent | ✅ Pick One |
|-----------------|-------------|
| `Seton` | `Seton` |
| `Seton Swimming` | `Seton` |
| `SETON` | `Seton` |
| `Seton School` | `Seton` |

**Multi-word team names are fine** — just keep them consistent:

| Team | CSV Value |
|------|-----------|
| Trinity Christian | `Trinity Christian` ✅ |
| Bishop O'Connell | `Bishop O'Connell` ✅ |
| St. Mary's | `St. Mary's` ✅ |
| Paul VI Catholic | `Paul VI Catholic` ✅ |

**The rule:** Every row for the same team must have the **exact same text** in the `team` column.

**Quick fix in Excel:**

1. Select team column
2. Ctrl+H (Find & Replace)
3. Find: `Seton Swimming` → Replace: `Seton`
4. Click "Replace All"

---

### Swimmer Name Formatting

**Multi-word names are fine:**

| Name | CSV Value |
|------|-----------|
| John Smith | `John Smith` ✅ |
| Mary Jane Watson | `Mary Jane Watson` ✅ |
| John Smith Jr. | `John Smith Jr.` ✅ |
| O'Brien, Kate | `O'Brien, Kate` ✅ |

**Just be consistent** — if HyTek exports "LastName, FirstName", keep all names that way.

---

### Diving Scores (Not Times)

Diving is the only event measured in **points, not seconds**:

```csv
swimmer,grade,gender,event,time,team
Mark Taylor,11,M,Boys Diving,285.50,Seton
```

The `285.50` is a dive score, not a time. The app handles this automatically because the event name contains "Diving".

---

## 🎯 Bottom Line

**Minimum viable CSV:**

```csv
swimmer,grade,gender,event,time,team
John Smith,11,M,Boys 50 Free,23.45,Seton
```

**The cleaner your data, the better your optimization!**
