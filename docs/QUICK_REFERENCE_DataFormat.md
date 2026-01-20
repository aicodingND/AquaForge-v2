# 🎯 Quick Reference: Perfect Data Input

## ✅ Required Columns (6)

| Column | Type | Example | Notes |
|--------|------|---------|-------|
| `swimmer` | Text | "John Smith" | Full name |
| `grade` | Number | `11` | 6-12 (8-12 score, 6-7 exhibition) |
| `gender` | Letter | `M` or `F` | M=Boys, F=Girls |
| `event` | Text | "Boys 50 Free" | Standard event names |
| `time` | Decimal | `23.45` | Seconds (or dive score) |
| `team` | Text | "Seton" | Team name |

## 🌟 Optional but Helpful (2)

| Column | Type | Example | Why? |
|--------|------|---------|------|
| `opponent` | Text | "Trinity Christian" | Prevents multi-meet confusion |
| `meet_date` | Date | `2024-11-15` | Track which meet |

---

## 📋 Standard Events (Individual)

**Freestyle:**

- 50 Yard Freestyle (50 Free)
- 100 Yard Freestyle (100 Free)
- 200 Yard Freestyle (200 Free)
- 500 Yard Freestyle (500 Free)

**Strokes:**

- 100 Yard Backstroke (100 Back)
- 100 Yard Breaststroke (100 Breast)
- 100 Yard Butterfly (100 Fly)

**IM:**

- 200 Yard IM (200 IM)

**Other:**

- Diving

**Relays (Optional):**

- 200 Medley Relay
- 200 Free Relay
- 400 Free Relay

---

## ⚡ Quick Tips

1. **One meet per file** - Don't mix multiple meets
2. **Consistent naming** - Pick one event format and stick to it
3. **Include gender prefix** - "Boys 50 Free" vs "Girls 50 Free"
4. **Times in seconds** - 23.45 not "0:23.45"
5. **Numeric grades** - 11 not "Junior"
6. **Similar entry counts** - Both teams should have ~80-120 entries

---

## 🚨 Red Flags

❌ **Entry count mismatch** - Seton: 180, Trinity: 90 → Multi-meet data!  
❌ **Missing grades** - Can't determine scoring eligibility  
❌ **Text times** - "23.45" should be 23.45 (number)  
❌ **Mixed event names** - "50 Free" and "50 Freestyle" in same file  
❌ **No opponent column** - Risk of multi-meet confusion  

---

## 📁 File Formats

**Best:** Excel (.xlsx) - One sheet per team  
**Good:** CSV (.csv) - One file per team  
**Works:** HyTek PDF - Auto-parsed but verify results  

---

## ✅ Pre-Upload Checklist

- [ ] One meet only (or opponent column included)
- [ ] All 6 required columns present
- [ ] Grades are numbers (6-12)
- [ ] Times are decimals (23.45)
- [ ] Events are standardized
- [ ] No duplicate rows
- [ ] Entry counts reasonable (~80-120)
- [ ] Both teams similar counts

---

**File:** `TEMPLATE_SwimMeet.csv` - Use this as starting point!
