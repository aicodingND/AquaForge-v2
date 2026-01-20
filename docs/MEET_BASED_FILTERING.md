# Meet-Based Data Filtering - Design Document

## 🎯 **Problem Statement**

**Current Issue:**

- PDF contains data from MULTIPLE meets (Seton vs Team A, Seton vs Team B)
- App loads ALL data from PDF
- Optimization mixes swimmers from different meets
- Score is inflated because it's counting multiple meets

**Example:**

```
PDF Contents:
- Seton vs Trinity (Meet 1, Nov 15)
  - John Smith, 50 Free, 23.5
  - Mike Jones, 100 Free, 52.0
  
- Seton vs Bishop (Meet 2, Nov 20)
  - John Smith, 50 Free, 23.8  (different time)
  - Sarah Davis, 100 Back, 62.0  (new swimmer)

Current Behavior (WRONG):
- Loads ALL 4 entries
- Optimization uses mixed data
- Score: Inflated

Desired Behavior (CORRECT):
- User selects: "Seton vs Trinity"
- Loads ONLY 2 entries from that meet
- Optimization uses only that meet's data
- Score: Realistic
```

## ✅ **Solution: Meet Selection**

### Option 1: Automatic Meet Detection (Recommended)

**How it works:**

1. Parse PDF
2. Detect distinct meets based on:
   - Date (if available)
   - Opponent team name
   - Event groupings
3. Present user with meet selector:

   ```
   Select Meet:
   ○ Seton vs Trinity (Nov 15, 2024) - 90 entries
   ○ Seton vs Bishop (Nov 20, 2024) - 95 entries
   ```

4. Load ONLY selected meet's data

### Option 2: Manual Opponent Selection

**How it works:**

1. Parse PDF
2. Extract unique opponent names
3. User selects opponent:

   ```
   Select Opponent:
   ○ Trinity Christian
   ○ Bishop O'Connell
   ```

4. Filter data to ONLY include that opponent

### Option 3: Date-Based Filtering

**How it works:**

1. Parse PDF with dates
2. User selects date:

   ```
   Select Meet Date:
   ○ November 15, 2024
   ○ November 20, 2024
   ```

3. Load ONLY that date's data

## 🔧 **Implementation Plan**

### Phase 1: Detect Meets in PDF

**Add to parser:**

```python
def detect_meets(df: pd.DataFrame) -> List[Dict]:
    """
    Detect distinct meets in the dataframe.
    
    Returns:
        List of meet info dicts with:
        - opponent: str
        - date: str (if available)
        - entry_count: int
        - events: List[str]
    """
    meets = []
    
    # Group by opponent (if 'opponent' column exists)
    if 'opponent' in df.columns:
        for opponent, group in df.groupby('opponent'):
            meets.append({
                'opponent': opponent,
                'entry_count': len(group),
                'events': group['event'].unique().tolist()
            })
    
    return meets
```

### Phase 2: Add Meet Selector UI

**Upload Page - After file upload:**

```
┌─────────────────────────────────────┐
│ 📅 SELECT MEET                      │
├─────────────────────────────────────┤
│ Multiple meets detected in PDF:     │
│                                     │
│ ○ Seton vs Trinity Christian       │
│   90 entries, 12 events             │
│                                     │
│ ○ Seton vs Bishop O'Connell        │
│   95 entries, 12 events             │
│                                     │
│ [Apply Selection]                   │
└─────────────────────────────────────┘
```

### Phase 3: Filter Data by Selected Meet

**After selection:**

```python
def filter_by_meet(df: pd.DataFrame, opponent: str) -> pd.DataFrame:
    """Filter dataframe to only include selected meet."""
    if 'opponent' in df.columns:
        return df[df['opponent'] == opponent].copy()
    return df
```

## 🎯 **Immediate Workaround**

### Manual Approach (Until Feature is Built)

**Step 1: Identify Opponent**

- Look at your PDF
- Note the opponent name (e.g., "Trinity Christian")

**Step 2: Use Data Filters**

- After upload, use the data filter panel
- Manually exclude unwanted data

**Step 3: Verify Entry Count**

- Check swimmer count matches expected for ONE meet
- Typical dual meet: 80-100 entries per team
- If you see 180+, you have multiple meets loaded

## 📊 **Detection Logic**

### How to Detect Multiple Meets

**Indicator 1: Entry Count**

```
Single meet: 80-100 entries
Multiple meets: 160-200+ entries
```

**Indicator 2: Duplicate Swimmers with Different Times**

```
John Smith, 50 Free, 23.5  ← Meet 1
John Smith, 50 Free, 23.8  ← Meet 2 (DIFFERENT TIME)
```

**Indicator 3: Different Opponent Names**

```
Team column shows:
- Trinity Christian (50 entries)
- Bishop O'Connell (50 entries)
= 2 meets in same PDF
```

## ✅ **Quick Fix (Manual)**

### Until we build meet selector

**Option A: Separate PDFs**

- Get separate PDF for each meet
- Upload only the meet you want to analyze

**Option B: Manual Filtering**

1. Upload combined PDF
2. Note the entry count
3. If 2x expected → You have 2 meets
4. **Clear and re-upload with single-meet PDF**

**Option C: Post-Processing**

- After optimization, manually verify results
- Check that all swimmers are from same meet
- If mixed, clear and start over

## 🚀 **Future Enhancement**

### Full Meet Management

```
┌─────────────────────────────────────┐
│ 📅 MEET LIBRARY                     │
├─────────────────────────────────────┤
│ Loaded Meets:                       │
│                                     │
│ ✓ Seton vs Trinity (Nov 15)        │
│   [Analyze] [Remove]                │
│                                     │
│ ✓ Seton vs Bishop (Nov 20)         │
│   [Analyze] [Remove]                │
│                                     │
│ [+ Add New Meet]                    │
└─────────────────────────────────────┘
```

## 📝 **Summary**

**Problem:** PDF contains multiple meets, app loads all data

**Root Cause:** No meet-level filtering

**Current Fix:**

- ✅ Deduplication removes EXACT duplicates (swimmer+event+time)
- ⚠️ Does NOT remove same swimmer with different times (different meets)

**Proper Solution:**

- 🔨 Build meet selector UI
- 🔨 Detect meets in PDF
- 🔨 Filter data by selected meet

**Workaround:**

- 📄 Use separate PDFs for each meet
- 🧹 Clear data between meets
- ✅ Verify entry counts match expectations

---

**Status:** This is a FEATURE REQUEST, not a bug. The deduplication fixes handle exact duplicates, but meet-based filtering requires new UI/logic.

**Priority:** HIGH - This is likely the root cause of 158-294 scores if PDFs contain multiple meets.
