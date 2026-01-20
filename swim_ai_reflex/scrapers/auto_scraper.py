#!/usr/bin/env python3
"""
Parallel SwimCloud Scraper
Efficiently scrapes multiple teams using concurrent browser tabs
"""

import json
import time
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed


def parse_time_to_seconds(time_str: str) -> float:
    """Convert time string (MM:SS.ss or SS.ss) to seconds."""
    if not time_str or time_str in ["NT", "NS", "--", ""]:
        return 0.0

    time_str = time_str.strip()

    if ":" in time_str:
        parts = time_str.split(":")
        try:
            return float(parts[0]) * 60 + float(parts[1])
        except (ValueError, IndexError):
            return 0.0

    try:
        return float(time_str)
    except ValueError:
        return 0.0


# All VCAC/VISAA teams to scrape
TEAMS_TO_SCRAPE = {
    "ICS": {"id": 10026495, "name": "Immanuel Christian High School"},
    "TCS": {"id": 10009031, "name": "Trinity Christian School"},
    "FCS": {"id": 6854, "name": "Fredericksburg Christian"},
    "OAK": {"id": 6884, "name": "Oakcrest School"},
    "DJO": {"id": 6850, "name": "Bishop O'Connell"},
    "PVI": {"id": 6889, "name": "Paul VI"},
    "BI": {"id": 6841, "name": "Bishop Ireton"},
}

# Events to scrape
SWIMMING_EVENTS = [
    ("1|50|1", "50 Free"),
    ("1|100|1", "100 Free"),
    ("1|200|1", "200 Free"),
    ("1|500|1", "500 Free"),
    ("2|100|1", "100 Back"),
    ("3|100|1", "100 Breast"),
    ("4|100|1", "100 Fly"),
    ("5|200|1", "200 IM"),
]

GENDERS = ["M", "F"]


def scrape_single_team(team_code: str, team_id: int, team_name: str) -> dict:
    """Scrape a single team's data. Runs in its own browser context."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {"error": "Playwright not installed"}

    print(f"  🏊 Starting {team_code}...")

    all_times = []
    roster = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
            ],
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
        )
        page = context.new_page()
        page.set_default_timeout(30000)

        # Scrape roster
        try:
            page.goto(f"https://www.swimcloud.com/team/{team_id}/roster/?season_id=29")
            page.wait_for_load_state("networkidle")
            time.sleep(1)

            roster = page.evaluate("""
                () => {
                    const rows = Array.from(document.querySelectorAll('table tbody tr'));
                    return rows.map(row => {
                        const cells = row.querySelectorAll('td');
                        if (cells.length < 4) return null;
                        const name = cells[1]?.innerText.trim() || '';
                        const hometown = cells[2]?.innerText.trim() || '';
                        const classYear = cells[3]?.innerText.trim() || '';
                        return { name, classYear, hometown };
                    }).filter(r => r !== null && r.name && isNaN(r.name));
                }
            """)
        except Exception as e:
            print(f"    ⚠ {team_code} roster error: {str(e)[:50]}")

        # Scrape times for each gender and event
        for gender in GENDERS:
            for event_code, event_name in SWIMMING_EVENTS:
                url = f"https://www.swimcloud.com/team/{team_id}/times/?event={event_code}&gender={gender}&event_course=Y&season_id=29"

                try:
                    page.goto(url)
                    page.wait_for_load_state("networkidle")
                    time.sleep(0.8)

                    # Click SCY button
                    page.evaluate("""
                        () => {
                            const scyButton = Array.from(document.querySelectorAll('button')).find(
                                b => b.textContent.trim() === 'SCY'
                            );
                            if (scyButton && !scyButton.classList.contains('active')) {
                                scyButton.click();
                            }
                        }
                    """)
                    time.sleep(0.3)

                    results = page.evaluate("""
                        () => {
                            const rows = Array.from(document.querySelectorAll('table tbody tr'));
                            return rows.map(row => {
                                const nameLink = row.querySelector('td:nth-child(2) a');
                                const timeLink = row.querySelector('td:nth-child(4) a');
                                return {
                                    name: nameLink ? nameLink.textContent.trim() : null,
                                    time: timeLink ? timeLink.textContent.trim() : null
                                };
                            }).filter(r => r.name && r.time);
                        }
                    """)

                    for result in results:
                        all_times.append(
                            {
                                "swimmer_name": result["name"],
                                "team": team_code,
                                "event": f"{'Boys' if gender == 'M' else 'Girls'} {event_name}",
                                "seed_time": parse_time_to_seconds(result["time"]),
                                "gender": gender,
                            }
                        )

                except Exception:
                    continue

        # Close browser to free resources
        context.close()
        browser.close()

    print(f"  ✅ {team_code}: {len(roster)} roster, {len(all_times)} times")

    return {
        "team_code": team_code,
        "team_name": team_name,
        "team_id": team_id,
        "source": "swimcloud",
        "scraped_at": datetime.now().strftime("%Y-%m-%d"),
        "season": "2025-2026",
        "roster": roster,
        "times": all_times,
    }


def scrape_all_teams_parallel(max_workers: int = 3):
    """Scrape all teams in parallel using ThreadPoolExecutor."""
    print("🚀 Starting Parallel SwimCloud Scraper")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Teams: {len(TEAMS_TO_SCRAPE)} | Workers: {max_workers}")
    print("=" * 60)

    output_dir = Path("data/scraped")
    output_dir.mkdir(parents=True, exist_ok=True)

    results = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_team = {
            executor.submit(
                scrape_single_team, team_code, info["id"], info["name"]
            ): team_code
            for team_code, info in TEAMS_TO_SCRAPE.items()
        }

        # Process as they complete
        for future in as_completed(future_to_team):
            team_code = future_to_team[future]
            try:
                data = future.result()
                results[team_code] = data

                # Save immediately to preserve data
                output_path = output_dir / f"{team_code}_swimcloud.json"
                with open(output_path, "w") as f:
                    json.dump(data, f, indent=2)

            except Exception as e:
                print(f"  ❌ {team_code} failed: {str(e)[:80]}")
                results[team_code] = {"error": str(e)}

    # Summary
    print("\n" + "=" * 60)
    print("📊 SCRAPING SUMMARY")
    print("=" * 60)

    total_times = 0
    total_roster = 0

    for team_code, data in results.items():
        if "error" not in data:
            times_count = len(data.get("times", []))
            roster_count = len(data.get("roster", []))
            total_times += times_count
            total_roster += roster_count
            print(f"  {team_code}: {roster_count} swimmers, {times_count} times ✓")
        else:
            print(f"  {team_code}: FAILED - {data['error'][:50]}")

    print("-" * 60)
    print(f"  TOTAL: {total_roster} swimmers, {total_times} times")
    print("=" * 60)
    print("✅ All data saved to data/scraped/")

    return results


def main():
    """Main entry point."""
    # Use 3 concurrent workers to balance speed and rate limiting
    scrape_all_teams_parallel(max_workers=3)


if __name__ == "__main__":
    main()
