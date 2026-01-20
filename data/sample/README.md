# AquaForge Sample Data Files

This folder contains sample data files for testing AquaForge optimization.

## Dual Meet Files

Use these files to test the standard dual meet optimization workflow:

| File                          | Description                                                       |
| ----------------------------- | ----------------------------------------------------------------- |
| `dual_meet_seton_team.csv`    | Seton team roster with 12 swimmers including relays and diving    |
| `dual_meet_opponent_team.csv` | Opponent team roster with 11 swimmers including relays and diving |

### Usage

1. Go to **Meet Setup** in AquaForge
2. Upload `dual_meet_seton_team.csv` as the Seton team
3. Upload `dual_meet_opponent_team.csv` as the Opponent team
4. Navigate to **Optimizer** and run optimization

---

## Championship Meet Files

Use these files to test championship/multi-team meet functionality:

| File                                | Description                                |
| ----------------------------------- | ------------------------------------------ |
| `championship_psych_sheet_vcac.csv` | VCAC Championship psych sheet with 6 teams |

### Teams Included

- **SST** - Seton Swimming (home team)
- **TCS** - Trinity Christian School
- **ICS** - Immanuel Christian School
- **DJO** - Bishop O'Connell
- **OAK** - Oakcrest School
- **FCS** - Fredericksburg Christian School

---

## File Format

All files use CSV format with the following columns:

### Dual Meet Format

```
swimmer,event,time,grade
Michael Chen,50 Free,22.34,12
```

### Championship Format (includes team column)

```
swimmer,team,event,time,grade
Ariana Aldeguer,SST,50 Free,24.12,12
```

## Events Included

- **Individual**: 50 Free, 100 Free, 200 Free, 500 Free, 100 Back, 100 Breast, 100 Fly, 200 IM
- **Relays**: 200 Medley Relay, 200 Free Relay, 400 Free Relay
- **Diving**: Diving (score-based event)

## Notes

- Times are in standard swim format (MM:SS.ss or SS.ss)
- Diving scores are total points (typically 0-300 range)
- Grade is swimmer's grade level (9-12)
