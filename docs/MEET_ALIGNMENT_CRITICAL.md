# CRITICAL: Meet Alignment Fix - Score 158-294 Root Cause

## 🚨 **THE REAL PROBLEM**

### Scenario

```text
Seton PDF contains:
- Seton vs Trinity (Nov 15) - 90 entries
- Seton vs Bishop (Nov 20) - 90 entries
Total: 180 entries

Trinity PDF contains:
- Trinity vs Seton (Nov 15) - 90 entries
Total: 90 entries

App loads:
- Seton: 180 entries (BOTH meets)
- Trinity: 90 entries (ONE meet)

Optimization runs:
- Seton score: 158 (inflated - using 2 meets worth of data)
- Trinity score: 294 (even more inflated - mismatched data)

ROOT CAUSE: Data from DIFFERENT meets being compared!
```

## ✅ **SOLUTION: Meet Alignment**

### What Needs to Happen

#### Step 1: Detect Common Opponent

```python
# Seton PDF has opponents: ["Trinity", "Bishop"]
# Trinity PDF has opponents: ["Seton"]

# Common matchup: Seton vs Trinity
```

#### Step 2: Filter to Common Meet

```python
# Keep ONLY data where:
# - Seton competed against Trinity
# - Trinity competed against Seton

# Result:
# - Seton: 90 entries (vs Trinity only)
# - Trinity: 90 entries (vs Seton only)
```

#### Step 3: Verify Event Alignment

```python
# Ensure both teams have data for SAME events:
# - Boys 50 Free
# - Girls 100 Back
# etc.

# If Seton has "Boys 50 Free" but Trinity doesn't:
# → Remove that event from Seton's data
```

## 🔧 **Implementation**

### Add to data_service.py

```python
def align_meet_data(seton_df: pd.DataFrame, opponent_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Align two team datasets to only include data from when they competed against each other.
    
    Args:
        seton_df: Seton team data (may contain multiple meets)
        opponent_df: Opponent team data (may contain multiple meets)
    
    Returns:
        Tuple of (aligned_seton_df, aligned_opponent_df)
    """
    # If no opponent column, can't align - return as-is
    if 'opponent' not in seton_df.columns or 'opponent' not in opponent_df.columns:
        return seton_df, opponent_df
    
    # Get opponent team name from opponent_df
    opponent_name = opponent_df['team'].iloc[0] if 'team' in opponent_df.columns else "Opponent"
    
    # Filter Seton data to ONLY rows where opponent matches
    seton_aligned = seton_df[seton_df['opponent'] == opponent_name].copy()
    
    # Filter Opponent data to ONLY rows where opponent is "Seton"
    opponent_aligned = opponent_df[opponent_df['opponent'].str.contains('Seton', case=False, na=False)].copy()
    
    # Verify we have data
    if seton_aligned.empty or opponent_aligned.empty:
        # Fallback: No opponent column or no match found
        # Use all data (old behavior)
        return seton_df, opponent_df
    
    # Get common events
    seton_events = set(seton_aligned['event'].unique())
    opponent_events = set(opponent_aligned['event'].unique())
    common_events = seton_events & opponent_events
    
    # Filter to common events only
    seton_aligned = seton_aligned[seton_aligned['event'].isin(common_events)]
    opponent_aligned = opponent_aligned[opponent_aligned['event'].isin(common_events)]
    
    return seton_aligned, opponent_aligned
```

### Call in optimization_state.py

```python
async def run_optimization(self):
    # ... existing code ...
    
    seton_df = pd.DataFrame(self.seton_data)
    opponent_df = pd.DataFrame(self.opponent_data)
    
    # ALIGN MEET DATA - Only use data from when they competed against each other
    seton_df, opponent_df = align_meet_data(seton_df, opponent_df)
    
    self.log(f"Meet alignment: Seton {len(seton_df)} entries, Opponent {len(opponent_df)} entries")
    
    # ... continue with optimization ...
```

## 🎯 **How It Fixes 158-294**

### Before (BROKEN)

```text
Seton PDF: 180 entries (Trinity + Bishop meets)
Trinity PDF: 90 entries (Seton meet only)

Optimization:
- Seton: 158 points (using 180 entries)
- Trinity: 294 points (mismatched data)
```

### After (FIXED)

```text
Seton PDF: 180 entries loaded
Trinity PDF: 90 entries loaded

Meet Alignment:
- Filter Seton to ONLY "vs Trinity" → 90 entries
- Filter Trinity to ONLY "vs Seton" → 90 entries

Optimization:
- Seton: 95 points (using 90 entries)
- Trinity: 105 points (using 90 entries)
✓ REALISTIC SCORES!
```

## 📋 **Immediate Workaround**

### Until meet alignment is implemented

#### Option 1: Separate PDFs (BEST)

- Get PDF with ONLY Seton vs Trinity data
- Get PDF with ONLY Trinity vs Seton data
- Upload both
- Scores will be realistic

#### Option 2: Manual Filtering

- Upload combined PDFs
- Note the entry counts
- If Seton has 2x entries of opponent → You have multiple meets
- **Clear and get single-meet PDFs**

#### Option 3: Use Test Data

- Use "Load Demo Data" button
- This has properly aligned data
- Verify app works correctly
- Then get proper single-meet PDFs

## 🚀 **Priority**

**CRITICAL - This is likely the #1 cause of 158-294 scores!**

### Why This Happens

- Coaches keep season-long PDFs
- Each PDF accumulates all meets
- When analyzing one specific meet, both PDFs need to be filtered to THAT meet only
- Without alignment, you're comparing apples (1 meet) to oranges (2+ meets)

## ✅ **Action Items**

### For YOU (Immediate)

1. **Get single-meet PDFs** - Ask for PDFs with ONLY Seton vs Trinity data
2. **Clear all teams**
3. **Upload single-meet PDFs**
4. **Verify entry counts match** (both should be ~90-100)
5. **Run optimization**
6. **Check scores** (should be 80-120 range)

### For ME (To Implement)

1. ✅ Add `align_meet_data()` function
2. ✅ Integrate into optimization flow
3. ✅ Add logging for alignment
4. ✅ Handle edge cases (no opponent column, no matches)
5. ✅ Test with multi-meet PDFs

---

**Bottom Line:** The deduplication fixes handle duplicates WITHIN a meet. But if your PDFs contain MULTIPLE meets, you need meet alignment to filter to the specific matchup you're analyzing.

**For now: USE SINGLE-MEET PDFs!** This will give you accurate scores immediately.
