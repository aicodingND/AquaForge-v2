# Team Management Panel - Location Summary

## 📍 Where to Find It

The **Team Management Panel** is now available on **TWO pages**:

### 1. Dashboard (`/` or home page)

**Location:** Between "Quick Actions" and "System Status"

**Layout:**

```
Dashboard
├── Command Center Header
├── Stats Grid
├── Quick Actions (3 cards)
├── 🗄️ LOADED TEAMS PANEL ← HERE
├── System Status & Test Data
└── Recent Activity Log
```

### 2. Upload/Ingestion Page (`/upload`)

**Location:** Between main upload card and "Next" button

**Layout:**

```
Upload Page
├── Data Ingestion Header
├── Upload Zone + Previously Uploaded Files
├── Progress Bar (when loading)
├── File Status Badges
├── 🗄️ LOADED TEAMS PANEL ← HERE
└── [Next: Deep Strategy] button (floating)
```

## 🎨 What It Shows

### When Teams Are Loaded

```
┌─────────────────────────────────────┐
│ 🗄️ LOADED TEAMS                    │
├─────────────────────────────────────┤
│ ┌─────────────────────────────────┐ │
│ │ Seton                    [SETON]│ │
│ │ seton-roster.pdf                │ │
│ │ Swimmers: 45  |  Entries: 180   │ │
│ │ [🗑️ Remove Team]                │ │
│ └─────────────────────────────────┘ │
│ ┌─────────────────────────────────┐ │
│ │ Trinity Christian  [OPPONENT]   │ │
│ │ trinity-roster.pdf              │ │
│ │ Swimmers: 38  |  Entries: 152   │ │
│ │ [🗑️ Remove Team]                │ │
│ └─────────────────────────────────┘ │
│                                     │
│ [🗑️ Clear All Teams]               │
└─────────────────────────────────────┘
```

### When No Teams Loaded

```
┌─────────────────────────────────────┐
│ 🗄️ LOADED TEAMS                    │
├─────────────────────────────────────┤
│                                     │
│         📭                          │
│    No teams loaded                  │
│  Upload roster files to get started │
│                                     │
└─────────────────────────────────────┘
```

## ✨ Features

### Individual Team Cards Show

- ✅ **Team Name** (e.g., "Seton", "Trinity Christian")
- ✅ **Type Badge** (SETON in gold, OPPONENT in blue)
- ✅ **Filename** (monospace font for clarity)
- ✅ **Swimmer Count** (unique swimmers)
- ✅ **Entry Count** (total entries - may be higher if swimmers have multiple events)
- ✅ **Remove Button** (red, soft variant, trash icon)

### Global Actions

- ✅ **Clear All Teams** button (removes both Seton and Opponent)
- ✅ **Empty State** when no data loaded (helpful message)

## 🔧 Functionality

### Remove Individual Team

```python
# Clicking "Remove Team" on Seton card:
State.remove_team("seton")

# Result:
- Clears seton_data, seton_filename, seton_swimmer_count
- Clears seton_team_name, seton_file_hash
- Sets has_roster = False (if opponent also empty)
- Clears optimization results (now invalid)
- Shows toast: "Seton team data removed"
```

### Clear All Teams

```python
# Clicking "Clear All Teams":
State.clear_all_teams()

# Result:
- Clears ALL Seton data
- Clears ALL Opponent data
- Sets has_roster = False
- Clears optimization results
- Shows toast: "All team data cleared"
```

## 🎯 Use Cases

### Upload Page

1. **Before Upload:** See empty state, know you need to upload
2. **After Upload:** Immediately see what was loaded
3. **Multiple Uploads:** See both teams side-by-side
4. **Mistake Made:** Quickly remove wrong team and re-upload
5. **Start Fresh:** Clear all teams before new meet

### Dashboard

1. **Quick Status Check:** See what's currently loaded
2. **Manage Teams:** Remove teams without going to upload page
3. **Verify Data:** Check swimmer counts match expectations
4. **Clean Up:** Clear old data before starting new analysis

## 🚀 Next Steps

1. **Refresh Browser:** Hard refresh (`Ctrl+Shift+R`) to see changes
2. **Upload Files:** Upload some PDFs to see team cards appear
3. **Test Remove:** Click "Remove Team" to verify it works
4. **Test Clear All:** Click "Clear All Teams" to reset
5. **Check Both Pages:** Verify panel appears on Dashboard AND Upload page

## 📝 Files Modified

- ✅ `components/team_management.py` - Panel component (created)
- ✅ `components/dashboard.py` - Added panel to dashboard
- ✅ `components/upload.py` - Added panel to upload page
- ✅ `state.py` - Added remove_team() and clear_all_teams() methods

---

**Status:** ✅ IMPLEMENTED on both Dashboard and Upload pages!
