# Meet Registry — Single Source of Truth

**Purpose**: Canonical record of all championship meet details. **Always check this file first** when a session references an upcoming or recent meet. Do NOT rely on docs/ or data/meets/ alone — they may contain stale info from initial research.

**Update Protocol**: When meet details are confirmed (venue change, date shift, rule update), update this file AND the corresponding `data/meets/*.json` file. This registry is the human-verified truth; JSON files are the machine-readable copy.

---

## 2025-2026 Season Championship Meets

### VCAC Championship (Conference)

| Field | Value |
|-------|-------|
| **Full Name** | 5th Annual VCAC Championship |
| **Dates** | February 7, 2026 (Saturday, single day) |
| **Venue** | Freedom Aquatic and Fitness Center |
| **Address** | 9100 Freedom Center Blvd, Manassas, VA 20110 |
| **Meet File** | `data/meets/2026-02-07_vcac_championship.json` |
| **Teams** | SST, TCS, OAK, FCS, ICS, SJP, PVI (7 teams) |
| **Format** | Timed finals, single session |
| **Scoring** | Individual: 16-13-12-11-10-9-7-5-4-3-2-1, Relay: 2x |
| **Max Scorers** | 4 per event |
| **Key Rules** | Max 2 individual events, diving = 1 individual slot, Relay 3 (400 FR) = 1 individual slot |
| **Status** | COMPLETED |

### VISAA State Swim & Dive Championships (State)

| Field | Value |
|-------|-------|
| **Full Name** | VISAA State Swim & Dive Championships |
| **Dates** | February 12–14, 2026 (Thursday–Saturday) |
| **Swim Venue** | Collegiate Aquatic Center (SwimRVA), 5050 Ridgedale Pkwy, Richmond VA 23234 |
| **Dive Venue** | St Catherines Kenny Center Pool, 6001 Grove Ave, Richmond VA 23226 |
| **Venue Note** | Pools are about 20 min apart |
| **Meet File** | `data/meets/2026-02-12_visaa_state.json` |
| **Division** | Division II |
| **Format** | Prelims/Finals (Championship + Consolation) |
| **Scoring** | Championship: 40-34-32-30-28-26-24-22-18-14-12-10-8-6-4-2 |
| **Consolation** | 20-17-16-15-14-13-12-11-9-7-6-5-4-3-2-1 |
| **Max Scorers** | 16 per event |
| **Key Rules** | Max 2 individual events, diving = 1 individual slot, Relay 3 does NOT count as individual |
| **Status** | IN PROGRESS (Feb 14 = Day 3, Finals) |

#### Livestreams
- Swimming: Woodberry Forest School (WFS) streams SwimRVA
- Diving: St Catherines and/or St Christophers (check both links)

#### Team Houses
- **Girls Swim**: 1622 West Grace St, Richmond VA 23220 (22-25 min to SwimRVA, tolls)
- **Boys Swim**: 9 North Arthur Ashe Blvd, Richmond VA 23220 (16-20 min to SwimRVA, tolls)
- **Girls Dive**: 3032 Windsorview Dr, Richmond VA 23225

#### Schedule Highlights
- **Tue Feb 10**: Team Dinner, Hectors Nokesville, 6 PM (rugby shirts, cone signing)
- **Thu Feb 12**: Travel day. 3:10 PM team picture at SwimRVA.
- **Fri Feb 13**: Swim prelims 9:15 AM, Dive prelims/semis, Swim finals evening
- **Sat Feb 14**: Swim prelims AM, Dive finals, Swim finals PM. Senior Parade. Dinner at PBR (2553 W Cary St, Richmond 23220)

#### Coach Notes
- Saturday is very tiring. Best performance requires proper SLEEP and nutrition Wed-Fri.
- Follow Coach Bohmans Nutrition Guide.

---

## Lookup Protocol for AI Sessions

When a user mentions "this weekend's meet", "upcoming meet", or "championship":

1. Check today's date against the meet dates above
2. Return the correct meet with verified venue/dates
3. Do NOT guess or use cached info from docs/ — use this registry
4. If no match, ask the user which meet they mean

---

## Correction Log

| Date | What Changed | Old Value | New Value | Source |
|------|-------------|-----------|-----------|--------|
| 2026-02-14 | VISAA venue (pass 1) | SwimRVA, Richmond VA | Hampton Virginia Aquaplex | User msg (incorrect) |
| 2026-02-14 | VISAA venue (pass 2) | Hampton Virginia Aquaplex | Collegiate Aquatic Center (SwimRVA), 5050 Ridgedale Pkwy, Richmond 23234 | Seton meet info page |
| 2026-02-14 | VISAA diving venue | (none) | St Catherines Kenny Center Pool, 6001 Grove Ave, Richmond 23226 | Seton meet info page |
| 2026-02-14 | VISAA meet name | VISAA State Championships | VISAA State Swim and Dive Championships | User-confirmed |
| 2026-02-14 | Full logistics | (none) | Houses, streams, schedule, team dinners | Seton meet info page |

---

_Last verified: 2026-02-14 (from Seton Swimming meet information page)_
