# SwimCloud Scraping System Design

## Overview

This document describes the scraping system designed to collect competitor swim data from SwimCloud for AquaForge championship projections.

## Data Sources Discovered

### Primary Source: SwimCloud

- **URL Pattern**: `https://www.swimcloud.com/team/{team_id}/`
- **Blocking**: Direct HTTP requests blocked (403), browser-based scraping works
- **Data Available**:
  - Roster (all swimmers with class year)
  - Times (best times by event, filterable by gender/course/season)
  - Meet history (past competition results)
  - Diving data (where applicable)

### SwimCloud Team IDs (VCAC & VISAA)

| Team                     | Code | SwimCloud ID | Roster | Times | Status                             |
| ------------------------ | ---- | ------------ | ------ | ----- | ---------------------------------- |
| Seton Swimming           | SST  | 3605         | 40+    | 200+  | 🏠 Home team (use coach data)      |
| Immanuel Christian       | ICS  | 10026495     | 25     | 196   | ✅ SCRAPED                         |
| Trinity Christian School | TCS  | 10009031     | 8      | 162   | ✅ SCRAPED                         |
| Fredericksburg Christian | FCS  | 6854         | 18     | 96    | ✅ SCRAPED                         |
| Bishop O'Connell         | DJO  | 6850         | 24     | 62    | ✅ SCRAPED                         |
| Oakcrest School          | OAK  | 6884         | 0      | 165   | ✅ SCRAPED                         |
| Bishop Ireton            | BI   | 6841         | 5      | 6     | ✅ SCRAPED                         |
| Paul VI                  | PVI  | 6889         | 0      | 0     | ⚠️ No data (may need manual entry) |

**Note**: Seton data is sourced directly from Coach Koehr's Excel files, not SwimCloud.

## URL Structure

### Times Page (Primary Data Source)

```
https://www.swimcloud.com/team/{team_id}/times/?event={event_code}&gender={M|F}&event_course=Y&season_id=29
```

### Event Codes

| Event        | Code | Distance Format |
| ------------ | ---- | --------------- | --- | ---- | --- | ---- | --- | ---- | --- | --- |
| Freestyle    | 1    | 1               | 50  | 1, 1 | 100 | 1, 1 | 200 | 1, 1 | 500 | 1   |
| Backstroke   | 2    | 2               | 100 | 1    |
| Breaststroke | 3    | 3               | 100 | 1    |
| Butterfly    | 4    | 4               | 100 | 1    |
| IM           | 5    | 5               | 200 | 1    |
| Diving       | 9    | 9               | 1   | 1    |

## Scraping JavaScript

### 3.2 Headless Browser Configuration (CRITICAL)

- **User-Agent**: Takes `headless=True` but MUST provide a real `User-Agent` string (e.g., Chrome on MacOS) to avoid being blocked (receiving 0 results).
- **Automation Flags**: Must disable automation flags (`--disable-blink-features=AutomationControlled`).
- **SCY Tab**: The page defaults to an unpredictable state. You MUST explicitly find and click the "SCY" button (Yards) to ensure valid data.
- **Dynamic Loading**: Wait for `networkidle` AND explicit selectors (`table tbody tr`) before parsing.

### 3.3 Data Extraction Logic

- **Roster**: `https://www.swimcloud.com/team/{ID}/roster/?season_id={SEASON}`
- **Times**: `https://www.swimcloud.com/team/{ID}/times/?event={EVENT}&gender={GENDER}&event_course=Y&season_id={SEASON}`
  - Even with `event_course=Y` in URL, **click the SCY button** via JS.
- **Parsing**: Use `document.querySelectorAll('table tbody tr')` and extract from the 2nd (Name) and 4th (Time) columns.

```javascript
(() => {
  const rows = Array.from(document.querySelectorAll("table tbody tr"));
  const eventSelect = document.getElementById("select_1");
  const eventName = eventSelect
    ? eventSelect.options[eventSelect.selectedIndex].text
    : "Unknown";
  const gender =
    document
      .querySelector(".btn-group .btn-primary.active")
      ?.innerText.trim() || "Unknown";

  return rows
    .map((row) => {
      const cells = row.querySelectorAll("td");
      if (cells.length < 4) return null;
      const name = cells[1].innerText.trim();
      const time = cells[3].innerText.trim();
      return { name, event: eventName, time, gender };
    })
    .filter((r) => r !== null);
})();
```

## Data Scraped (2026-01-16)

### Trinity Christian School (TCS)

- **Men**: 5 swimmers
  - Tyler Phillips (22.23 50 Free - TOP SWIMMER)
  - Jo Witdoeckt (22.43 50 Free)
  - Ryan Ma, John Zhu, Luke Gilbert
- **Women**: 20+ swimmers
  - Allie Wiggins (26.33 50 Free)
  - Audrey Schlieter (26.74 50 Free)
  - Alexa Kriz (26.67 50 Free)

### Fredericksburg Christian (FCS)

- **Men**: 15 swimmers
  - Nathan Ryan (24.43 50 Free - TOP SWIMMER)
  - Andrew Ross (25.51 50 Free)
- **Women**: 25+ swimmers
  - Hannah Ellis (25.91 50 Free - TOP SWIMMER)
  - Evie Miller (26.80 50 Free)

## Key Findings

### Trinity vs Seton Comparison (Girls 50 Free)

| Seton          | Time  | Trinity       | Time  |
| -------------- | ----- | ------------- | ----- |
| Maggie Schroer | 26.29 | Allie Wiggins | 26.33 |
|                |       | Shoshana Feng | 26.38 |

**Implication**: Trinity's girls are competitive with Seton's best sprinters.

### Trinity vs Seton Comparison (Boys 50 Free)

| Seton         | Time  | Trinity        | Time  |
| ------------- | ----- | -------------- | ----- |
| Daniel Sokban | 23.59 | Tyler Phillips | 22.23 |
|               |       | Jo Witdoeckt   | 22.43 |

**Implication**: Trinity has faster male sprinters than Seton.

## Implementation Notes

1. **Rate Limiting**: SwimCloud may rate limit repeated requests. Add delays between page loads.
2. **Season ID**: Current season (2025-2026) uses `season_id=29`
3. **Course**: Use `event_course=Y` for yards (high school default)
4. **Browser Required**: Must use browser automation due to 403 blocks on direct requests

## Files Created

```
data/scraped/
├── TCS_swimcloud.json   # Trinity Christian - 160+ time entries
├── FCS_swimcloud.json   # Fredericksburg Christian - 40+ time entries
└── [future files]
```

## Next Steps

1. ✅ Scrape remaining VCAC teams (ICS, JPII if on SwimCloud)
2. ✅ Merge scraped data with HY3 data
3. ✅ Create unified psych sheet for VCAC projection
4. ⏳ Automate scraping with scheduled runs

## Scraper Module Location

```
swim_ai_reflex/scrapers/swimcloud_scraper.py
```
