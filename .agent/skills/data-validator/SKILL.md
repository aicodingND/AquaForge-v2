---
name: Data Validator
description: Validates psych sheet data integrity, swimmer rosters, and time formats
triggers:
  - data quality issues
  - missing times
  - invalid roster data
  - psych sheet validation
---

# Data Validator Skill 📋

Use this skill to validate psych sheet data and roster integrity.

---

## Quick Data Checks

### Required Columns

**Psych Sheet (Championship):**
```python
required = [
    'swimmer_name',  # or 'name'
    'team',          # or 'team_code'
    'event',         # or 'event_name'
    'seed_time',     # or 'best_time'
    'grade'          # optional but important
]
```

**Team Roster (Dual Meet):**
```python
required = [
    'swimmer_name',
    'grade',
    'times'  # Dict of event: time pairs
]
```

---

## Validation Procedure

### Step 1: Schema Validation

```python
def validate_psych_sheet_schema(df):
    """Validate required columns exist."""
    required = ['swimmer_name', 'team', 'event', 'seed_time']
    missing = [col for col in required if col not in df.columns]
    
    if missing:
        # Try alternate column names
        alternates = {
            'swimmer_name': ['name', 'swimmer'],
            'team': ['team_code', 'team_name'],
            'event': ['event_name', 'event_code'],
            'seed_time': ['best_time', 'time', 'entry_time']
        }
        # Attempt mapping...
```

### Step 2: Time Format Validation

**Valid Formats:**
- `1:23.45` → 83.45 seconds (MM:SS.ss)
- `23.45` → 23.45 seconds (SS.ss)
- `1:23:45.67` → 4425.67 seconds (HH:MM:SS.ss) - rare

**Converter:**
```python
def parse_time(time_str):
    """Convert time string to seconds."""
    if isinstance(time_str, (int, float)):
        return float(time_str)
    
    if ':' in str(time_str):
        parts = str(time_str).split(':')
        if len(parts) == 2:
            minutes, seconds = parts
            return float(minutes) * 60 + float(seconds)
    
    return float(time_str)
```

**Invalid Values:**
- `NT` → No time (should be handled as None or excluded)
- `DQ` → Disqualified (exclude from optimization)
- `NS` → No show (exclude)
- Empty/NaN → Warn and exclude

### Step 3: Event Name Normalization

| Input Variants                        | Normalized         |
| ------------------------------------- | ------------------ |
| `200 Free`, `200 Freestyle`, `200 FR` | `200 Free`         |
| `100 Fly`, `100 Butterfly`, `100 FL`  | `100 Fly`          |
| `200 Medley Relay`, `200 MR`          | `200 Medley Relay` |
| `50 Free`, `50 Freestyle`             | `50 Free`          |

```python
EVENT_NORMALIZATION = {
    '200 freestyle': '200 Free',
    '200 fr': '200 Free',
    '100 butterfly': '100 Fly',
    '100 fl': '100 Fly',
    '100 backstroke': '100 Back',
    '100 bk': '100 Back',
    '100 breaststroke': '100 Breast',
    '100 br': '100 Breast',
    '200 individual medley': '200 IM',
    '200 im': '200 IM',
    # ... etc
}
```

### Step 4: Team Name Normalization

```python
TEAM_MAPPINGS = {
    'seton': 'SST',
    'seton school': 'SST',
    'trinity christian': 'TCS',
    'oakcrest': 'OAK',
    'fredericksburg christian': 'FCS',
    'immanuel christian': 'ICS',
    'st. john paul': 'SJPG',
    'paul vi': 'PVIC'
}
```

### Step 5: Duplicate Detection

```python
def find_duplicates(df):
    """Find duplicate entries."""
    # Same swimmer, same event = potential duplicate
    duplicates = df[df.duplicated(['swimmer_name', 'team', 'event'], keep=False)]
    
    if not duplicates.empty:
        print(f"Found {len(duplicates)} potential duplicates:")
        for _, row in duplicates.iterrows():
            print(f"  {row['swimmer_name']} - {row['event']} - {row['seed_time']}")
```

---

## Data Quality Report

```python
def generate_data_quality_report(df):
    """Generate comprehensive data quality report."""
    report = {
        'total_entries': len(df),
        'unique_swimmers': df['swimmer_name'].nunique(),
        'unique_teams': df['team'].nunique(),
        'unique_events': df['event'].nunique(),
        'missing_times': df['seed_time'].isna().sum(),
        'invalid_times': count_invalid_times(df),
        'duplicates': len(find_duplicates(df)),
        'teams': list(df['team'].unique()),
        'events': list(df['event'].unique())
    }
    
    # Quality score
    issues = (
        report['missing_times'] + 
        report['invalid_times'] + 
        report['duplicates']
    )
    report['quality_score'] = max(0, 100 - (issues / report['total_entries'] * 100))
    
    return report
```

---

## Common Data Issues

### Issue: Mixed Time Formats

**Symptoms:** Some times in MM:SS.ss, some in SS.ss
**Fix:** Apply `parse_time()` to normalize all to seconds

### Issue: Missing Team Codes

**Symptoms:** Full team names instead of codes
**Fix:** Apply team mapping, use codes for optimization

### Issue: Swimmer Name Variations

**Symptoms:** "John Smith" and "Smith, John" as different swimmers
**Fix:** Normalize to "FirstName LastName" format

### Issue: Grade Data Missing

**Symptoms:** Can't identify exhibition swimmers
**Fix:** Cross-reference with known roster, mark unknown as varsity

---

## Integration with Pipelines

Before optimization:
```python
# Validate and prepare data
from data_contracts import validate_psych_sheet

validated_df = validate_psych_sheet(raw_df)
if validated_df.quality_score < 80:
    print("WARNING: Data quality below threshold")
```

---

_Skill: data-validator | Version: 1.0_
