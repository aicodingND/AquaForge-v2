# VCAC Championship Meet - February 7, 2026

**Event**: 5th Annual Virginia Christian Athletic Conference Championship Meet
**Date**: Saturday, February 7, 2026
**Location**: Freedom Fitness and Aquatic Center, Manassas, VA
**Type**: Conference Championship (Timed Finals)
**Last Updated**: January 15, 2026
**Source**: setonswimming.org

---

## 📋 Schedule

| Time     | Activity                                         |
| -------- | ------------------------------------------------ |
| 9:00 AM  | Diving Warm-ups                                  |
| 9:55 AM  | Prayer & National Anthem                         |
| 10:00 AM | Diving Competition (11-dive championship format) |
| 12:39 PM | Seton Swimmers Warm-up (Racquetball Courts)      |
| 1:00 PM  | Swimming Warm-ups                                |
| 2:05 PM  | Senior Parade                                    |
| 2:20 PM  | Swimming Competition Begins                      |

**Entries Due**: 6:00 PM on Wednesday before meet (Feb 4, 2026)
**Livestream**: Seton Swimming Highlights YouTube Channel

---

## 🏫 VCAC Member Teams

| School                                             | Location           | Notes                            |
| -------------------------------------------------- | ------------------ | -------------------------------- |
| **Seton School**                                   | Manassas, VA       | 2025 Boys & Girls Champion, Host |
| **Trinity Christian School**                       | Fairfax, VA        | Strong relay program             |
| **Oakcrest School**                                | McLean, VA         | Elizabeth Bryan - record holder  |
| **Fredericksburg Christian School**                | Fredericksburg, VA |                                  |
| **Immanuel Christian School**                      | Springfield, VA    |                                  |
| **Saint John Paul the Great Catholic High School** | Dumfries, VA       | Gianna Davis - 50 Free record    |

**Total Teams**: 6 schools

---

## 📊 Scoring System

> **Standard 12-place championship scoring**: Relay = 2x Individual (same as NCAA/NFHS)

### Individual/Diving Events (Top 12 Score)

| Place | Points |
| ----- | ------ |
| 1st   | **16** |
| 2nd   | 13     |
| 3rd   | 12     |
| 4th   | 11     |
| 5th   | 10     |
| 6th   | 9      |
| 7th   | 7      |
| 8th   | 5      |
| 9th   | 4      |
| 10th  | 3      |
| 11th  | 2      |
| 12th  | 1      |

### Relay Events (2x Individual at each placement)

| Place | Points |
| ----- | ------ |
| 1st   | **32** |
| 2nd   | 26     |
| 3rd   | 24     |
| 4th   | 22     |
| 5th   | 20     |
| 6th   | 18     |
| 7th   | 14     |
| 8th   | 10     |
| 9th   | 8      |
| 10th  | 6      |
| 11th  | 4      |
| 12th  | 2      |

**Source**: NCAA Rule 7 (12-place scoring), NFHS, setonswimming.org
**Corrected**: 2026-02-02 — previous version had individual/relay tables swapped

---

## ⚖️ Entry Constraints (CRITICAL FOR VALIDATION)

### The Complete Rule

```text
THE RULES:
1. Max 2 INDIVIDUAL events per swimmer
2. DIVING COUNTS AS 1 INDIVIDUAL EVENT
3. There are only 3 RELAYS (200 Medley, 200 Free, 400 Free)
4. First 2 relays are FREE (don't count toward individual limit)
5. Relay 3 COUNTS AS 1 individual event

FORMULA:
  individual_slots_used = swim_individual_count + (1 if diving else 0)
  relay_penalty = max(0, relay_count - 2)  # only relay 3 costs a slot
  total_effective_individual = individual_slots_used + relay_penalty

  VALID if: total_effective_individual <= 2
```

### Valid Entry Examples

| Swim | Dive | Relays | Eff. Indiv | Valid? | Reason                 |
| ---- | ---- | ------ | ---------- | ------ | ---------------------- |
| 2    | No   | 2      | 2          | ✅ Yes | Max normal swimmer     |
| 1    | Yes  | 2      | 2          | ✅ Yes | 1 swim + dive = 2      |
| 2    | Yes  | 0      | 3          | ❌ NO  | Dive puts over limit   |
| 1    | No   | 3      | 2          | ✅ Yes | 1 swim + relay3 = 2    |
| 2    | No   | 3      | 3          | ❌ NO  | 2 swim + relay3 = 3    |
| 0    | Yes  | 3      | 2          | ✅ Yes | Dive + relay3 = 2      |
| 1    | Yes  | 3      | 3          | ❌ NO  | 1 swim + dive + R3 = 3 |
| 0    | No   | 3      | 1          | ✅ Yes | Relay3 only = 1        |

### Validation Function

```python
def is_valid_entry(swim_individual: int, is_diver: bool, relay_count: int) -> bool:
    """Check if swimmer entry is valid per VCAC rules."""
    if swim_individual > 2:
        return False
    if relay_count > 3:
        return False

    individual_used = swim_individual + (1 if is_diver else 0)
    relay_penalty = max(0, relay_count - 2)
    effective_individual = individual_used + relay_penalty

    return effective_individual <= 2
```

### Team-Level Constraints

| Constraint                          | Limit                       |
| ----------------------------------- | --------------------------- |
| Entries per team per event          | **Unlimited**               |
| Scoring swimmers per team per event | **Top 4**                   |
| Scoring relays per team             | **A and B**                 |
| Non-scoring entries                 | Must be marked "Exhibition" |

### Diving

| Constraint    | Value                  |
| ------------- | ---------------------- |
| Format        | 11-dive championship   |
| Warm-up       | 9:00 AM                |
| Competition   | ~10:00 AM              |
| **Counts as** | **1 individual event** |

---

## 🏊 Standard Event Order

| #   | Event                  |
| --- | ---------------------- |
| 1   | 200 Medley Relay       |
| 2   | 200 Freestyle          |
| 3   | 200 Individual Medley  |
| 4   | 50 Freestyle           |
| 5   | Diving (if concurrent) |
| 6   | 100 Butterfly          |
| 7   | 100 Freestyle          |
| 8   | 500 Freestyle          |
| 9   | 200 Freestyle Relay    |
| 10  | 100 Backstroke         |
| 11  | 100 Breaststroke       |
| 12  | 400 Freestyle Relay    |

---

## 📈 2025 Results (4th Annual Championship)

| Division | Champion         | Notes               |
| -------- | ---------------- | ------------------- |
| Boys     | **Seton School** | Conference Champion |
| Girls    | **Seton School** | Conference Champion |

### 2025 Meet Records Set

| Event                  | Swimmer                      | School            | Time    |
| ---------------------- | ---------------------------- | ----------------- | ------- |
| Girls 200 IM           | Elizabeth Bryan              | Oakcrest          | 2:04.75 |
| Girls 100 Breaststroke | Elizabeth Bryan              | Oakcrest          | 1:05.06 |
| Girls 50 Freestyle     | Gianna Davis                 | St. John Paul     | 24.05   |
| Girls 500 Freestyle    | Ariana Aldeguer              | Seton             | 5:07.81 |
| Girls 400 Free Relay   | Feng/Hsieh/Schlieter/Wiggins | Trinity Christian | 3:44.17 |

### 2025 Individual Gold Medalists

- **Tyler Phillips** (Trinity Christian) - 200 Free, 100 Butterfly
- **Meghan Condon** (Seton) - Girls Diving
- **Connor Koehr** (Seton) - Boys Diving

---

## 🔧 AquaForge Optimization Notes

### Key Differences from Dual Meets

| Factor                    | Dual Meet      | VCAC Championship |
| ------------------------- | -------------- | ----------------- |
| **Opponents**             | 1 team         | 5 teams           |
| **Scoring places**        | Top 6          | Top 12            |
| **Scoring per event**     | Top 3 per team | Top 4 per team    |
| **Relay scoring**         | A only         | A and B           |
| **Individual points 1st** | 6              | 16                |
| **Format**                | Timed finals   | Timed finals      |

### What This Means for AquaForge

1. **Multi-team format** - Can't optimize against single opponent
2. **Deeper scoring** - More positions score (12 vs 6)
3. **More scorers per team** - Top 4 vs top 3
4. **Higher point values** - 1st = 16 pts (vs 6 in dual)
5. **B relay scores** - Extra relay strategy opportunity

### Possible Approach

Since VCAC uses **timed finals** (not prelims/finals), AquaForge could:

1. Use psych sheet / seed times to predict placements
2. Calculate expected points per swimmer per event
3. Optimize entry selection (which 2 events per swimmer)
4. Optimize relay configurations (A and B relays)

---

## 📚 Source Documents

- Meet Announcement: "Meet Announcement-5th Annual VCAC Conference Championship-Feb7,26-v6"
- Posted: September 29, 2025 (updated December 22, 2025)
- Website: setonswimming.org

---

_Data researched January 15, 2026 via Ralph Wiggum iterative research method_
