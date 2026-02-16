#!/usr/bin/env python3
"""
Scrape missing VISAA 2026 opponent data from SwimCloud.

Meet: 350494 (VISAA State Swim & Dive Championships 2026)

Uses deterministic event-number-to-name mapping learned from the meet page.
Each event has a known SwimCloud event number and gender. We directly visit
each event URL and parse the results table for top-16 non-Seton entries.

Deduplication: keeps only each swimmer's best time per event.
"""

import json
import re
import sys
import time

from playwright.sync_api import sync_playwright

MEET_ID = 350494
BASE_URL = f"https://www.swimcloud.com/results/{MEET_ID}"

# Known event numbers from SwimCloud meet page (discovered via first scrape run)
# Format: event_num -> (gender, canonical_event_name)
EVENTS = {
    1: ("Girls", "200 Medley Relay"),
    2: ("Boys", "200 Medley Relay"),
    3: ("Girls", "200 Free"),
    4: ("Boys", "200 Free"),
    5: ("Girls", "200 IM"),
    6: ("Boys", "200 IM"),
    7: ("Girls", "50 Free"),
    8: ("Boys", "50 Free"),
    9: ("Girls", "1M Diving"),
    10: ("Boys", "1M Diving"),
    11: ("Girls", "100 Fly"),
    12: ("Boys", "100 Fly"),
    13: ("Girls", "100 Free"),
    14: ("Boys", "100 Free"),
    15: ("Girls", "500 Free"),
    16: ("Boys", "500 Free"),
    17: ("Girls", "200 Free Relay"),
    18: ("Boys", "200 Free Relay"),
    19: ("Girls", "100 Back"),
    20: ("Boys", "100 Back"),
    21: ("Girls", "100 Breast"),
    22: ("Boys", "100 Breast"),
    23: ("Girls", "400 Free Relay"),
    24: ("Boys", "400 Free Relay"),
}

# Events we already have opponent data for
EXISTING_EVENTS = {
    "Boys 50 Free",
    "Boys 100 Free",
    "Boys 200 Free",
    "Boys 200 IM",
    "Boys 1M Diving",
    "Boys 200 Medley Relay",
    "Girls 50 Free",
    "Girls 100 Free",
    "Girls 200 Free",
    "Girls 200 IM",
    "Girls 1M Diving",
    "Girls 200 Medley Relay",
}

SETON_NAMES = {"Seton", "SST", "Seton School", "Seton Swimming"}


def parse_time(time_str: str) -> float:
    """Convert time string to seconds. Handles MM:SS.ss and SS.ss formats."""
    time_str = time_str.strip()
    if not time_str or time_str in ("NT", "NS", "DQ", "SCR", "--"):
        return 0.0
    try:
        if ":" in time_str:
            parts = time_str.split(":")
            return float(parts[0]) * 60 + float(parts[1])
        return float(time_str)
    except (ValueError, IndexError):
        return 0.0


def is_seton(team_name: str) -> bool:
    """Check if team name refers to Seton."""
    if not team_name:
        return False
    t = team_name.strip().lower()
    return any(s.lower() in t for s in SETON_NAMES)


def scrape_meet():
    print(f"Scraping VISAA 2026 (Meet {MEET_ID}) from SwimCloud...")
    print()

    # Determine which events we need
    events_to_scrape = {}
    for num, (gender, event_name) in sorted(EVENTS.items()):
        full = f"{gender} {event_name}"
        if full in EXISTING_EVENTS:
            print(f"  [SKIP] Event #{num:2d}: {full} (already have data)")
        elif "Relay" in event_name:
            print(f"  [SKIP] Event #{num:2d}: {full} (relay — separate parsing)")
        else:
            events_to_scrape[num] = (gender, event_name, full)
            print(f"  [NEED] Event #{num:2d}: {full}")
    print()

    if not events_to_scrape:
        print("All individual events already have data!")
        return []

    all_new_entries = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page = context.new_page()

        for num, (gender, event_name, full_event) in sorted(events_to_scrape.items()):
            url = f"{BASE_URL}/event/{num}/"
            print(f"  Scraping: {full_event} (Event #{num}) ...")
            print(f"    URL: {url}")

            page.goto(url, timeout=30000)
            page.wait_for_load_state("networkidle", timeout=15000)
            time.sleep(2)

            # Parse the results table
            entries = []
            seen = set()  # (swimmer_name) -> deduplicate to best time

            rows = page.query_selector_all("tr")
            for row in rows:
                cells = row.query_selector_all("td")
                if len(cells) < 3:
                    continue

                name_el = row.query_selector("a[href*='/swimmer/']")
                team_el = row.query_selector("a[href*='/team/']")

                swimmer_name = name_el.inner_text().strip() if name_el else ""
                team_name = team_el.inner_text().strip() if team_el else ""

                if not swimmer_name:
                    continue

                # Find time — look for a cell with a swim time pattern
                swim_time = 0.0
                for td in cells:
                    text = td.inner_text().strip()
                    if re.match(r"^\d+[:.]\d", text):
                        parsed = parse_time(text)
                        if parsed > 0:
                            swim_time = parsed
                            break

                if swim_time <= 0:
                    continue

                if is_seton(team_name):
                    continue

                # Deduplicate: keep only best time per swimmer
                if swimmer_name in seen:
                    continue
                seen.add(swimmer_name)

                entries.append(
                    {
                        "swimmer": swimmer_name,
                        "event": full_event,
                        "time": round(swim_time, 2),
                        "grade": 12,
                        "team": team_name,
                    }
                )

            # Sort by time, take top 16
            entries.sort(key=lambda e: e["time"])
            top_entries = entries[:16]

            print(
                f"    Found {len(entries)} unique non-Seton swimmers, keeping top {len(top_entries)}"
            )
            for e in top_entries[:5]:
                print(f"      {e['swimmer']:30s}  {e['time']:>8.2f}  ({e['team']})")
            if len(top_entries) > 5:
                print(f"      ... and {len(top_entries) - 5} more")

            all_new_entries.extend(top_entries)
            print()

        browser.close()

    # Output results
    print("=" * 80)
    print(f"  TOTAL NEW ENTRIES: {len(all_new_entries)}")
    print("=" * 80)
    print()

    if all_new_entries:
        output_path = "data/swimcloud/visaa_2026_missing_opponents.json"
        with open(output_path, "w") as f:
            json.dump(all_new_entries, f, indent=2)
        print(f"  Saved to: {output_path}")
        print()

        # Print Python format for easy pasting
        print("  # Python format for run_visaa_optimizer.py OPPONENT_ENTRIES:")
        print()
        current_event = ""
        for e in sorted(all_new_entries, key=lambda x: (x["event"], x["time"])):
            if e["event"] != current_event:
                current_event = e["event"]
                print(f"    # {current_event.upper()}")
            print(
                f'    {{"swimmer": "{e["swimmer"]}", '
                f'"event": "{e["event"]}", '
                f'"time": {e["time"]}, '
                f'"grade": 12}},'
            )

    return all_new_entries


if __name__ == "__main__":
    entries = scrape_meet()
    if not entries:
        print("\nNo new entries scraped. Try running with --headed for debugging.")
        sys.exit(1)
