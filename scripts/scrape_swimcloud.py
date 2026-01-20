import argparse
import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict, Optional, Set

from playwright.async_api import Page, async_playwright

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("scrape_swimcloud.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Constants
BASE_URL = "https://www.swimcloud.com"
DATA_DIR = "data/swimcloud"
TEAMS_DIR = os.path.join(DATA_DIR, "teams")
MEETS_DIR = os.path.join(DATA_DIR, "meets")
MAX_CONCURRENCY = 8

# Ensure data directories exist
os.makedirs(TEAMS_DIR, exist_ok=True)
os.makedirs(MEETS_DIR, exist_ok=True)


class SwimCloudScraper:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.semaphore = asyncio.Semaphore(MAX_CONCURRENCY)
        self.browser = None
        self.playwright = None
        self.context = None
        self.processed_teams: Set[str] = set()
        self.processed_meets: Set[str] = set()

    async def start(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        self.context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

    async def stop(self):
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def get_page(self) -> Page:
        return await self.context.new_page()

    async def search_team(self, team_name: str) -> Optional[Dict]:
        """Search for a team and return its name and ID/URL."""
        async with self.semaphore:
            page = await self.get_page()
            try:
                logger.info(f"Searching for team: {team_name}")
                await page.goto(f"{BASE_URL}/teams/")

                # Type in search box
                selectors = [
                    "#global-search-select",
                    'input[placeholder="Search for a team"]',
                    'input[type="search"]',
                    ".c-navbar-search__input",
                ]

                input_found = False
                for selector in selectors:
                    try:
                        if await page.query_selector(selector):
                            await page.fill(selector, team_name)
                            input_found = True
                            logger.info(f"Found search input with selector: {selector}")
                            break
                    except:
                        continue

                if not input_found:
                    logger.error("Could not find search input")
                    await page.screenshot(path="debug_no_search_input.png")
                    return None

                # Wait for results
                await page.wait_for_timeout(2000)

                # Check for results in the dropdown
                try:
                    await page.wait_for_selector('[id^="react-select-"]', timeout=5000)
                    options = await page.query_selector_all('[id^="react-select-"]')
                    for option in options:
                        text = await option.inner_text()
                        if team_name.lower() in text.lower():
                            logger.info(f"Found match in dropdown: {text}")
                            await option.click()
                            await page.wait_for_load_state("networkidle")
                            url = page.url
                            if "/team/" in url:
                                team_id = url.split("/team/")[1].split("/")[0]
                                return {"name": text.strip(), "id": team_id, "url": url}
                except Exception as e:
                    logger.warning(f"Dropdown interaction failed: {e}")

                await page.keyboard.press("Enter")
                await page.wait_for_timeout(3000)
                logger.warning(f"Team not found via search: {team_name}")
                return None

            except Exception as e:
                logger.error(f"Error searching for team {team_name}: {e}")
                await page.screenshot(path="debug_search_failure.png")
                return None
            finally:
                await page.close()

    async def scrape_team(self, team_id: str):
        """Scrape team roster and schedule."""
        if team_id in self.processed_teams:
            return

        async with self.semaphore:
            page = await self.get_page()
            try:
                team_url = f"{BASE_URL}/team/{team_id}"
                logger.info(f"Scraping team: {team_id}")
                await page.goto(team_url, timeout=60000)

                # Scrape Basic Info
                try:
                    team_name = await page.title()
                except:
                    team_name = "Unknown"

                # Scrape Roster
                await page.goto(f"{team_url}/roster", timeout=60000)
                roster_data = []
                try:
                    await page.wait_for_selector("table tbody tr", timeout=10000)
                    swimmers = await page.query_selector_all("table tbody tr")
                    for row in swimmers:
                        name_el = await row.query_selector("td a.u-text-semi")
                        if name_el:
                            name = await name_el.inner_text()
                            roster_data.append({"name": name.strip()})
                        else:
                            cols = await row.query_selector_all("td")
                            if len(cols) >= 3:
                                name_el = await cols[0].query_selector("a")
                                name = (
                                    await name_el.inner_text() if name_el else "Unknown"
                                )
                                if name != "Unknown":
                                    roster_data.append({"name": name.strip()})
                except Exception as e:
                    logger.warning(f"Could not parse roster for {team_id}: {e}")

                # Save Team Data
                team_data = {
                    "team_id": team_id,
                    "team_name": team_name,
                    "roster": roster_data,
                    "scraped_at": datetime.now().isoformat(),
                }

                filename = os.path.join(TEAMS_DIR, f"{team_id}.json")
                with open(filename, "w") as f:
                    json.dump(team_data, f, indent=2)

                self.processed_teams.add(team_id)
                logger.info(f"Saved team data for {team_id}")

            except Exception as e:
                logger.error(f"Error scraping team {team_id}: {e}")
                await page.screenshot(path=f"debug_team_{team_id}_failure.png")
            finally:
                await page.close()

        # Trigger meet scraping separately to re-use semaphore correctly
        await self.scrape_meets_for_team(team_id)

    async def scrape_meets_for_team(self, team_id: str):
        """Find meets for a team and scrape them."""
        async with self.semaphore:
            page = await self.get_page()
            try:
                results_url = f"{BASE_URL}/team/{team_id}/results"
                logger.info(f"Looking for meets for team {team_id} at {results_url}")
                await page.goto(results_url, timeout=60000)

                # Wait for meet list
                meets_to_scrape = []
                try:
                    await page.wait_for_selector("a.c-list-grid__item", timeout=10000)
                    meet_links = await page.query_selector_all("a.c-list-grid__item")

                    for link in meet_links:
                        href = await link.get_attribute("href")
                        name_el = await link.query_selector("h3")
                        name_text = (
                            await name_el.inner_text() if name_el else "Unknown Meet"
                        )
                        if href and "/results/" in href:
                            meet_id = href.split("/results/")[1].split("/")[0]
                            meets_to_scrape.append(
                                {
                                    "id": meet_id,
                                    "name": name_text,
                                    "url": f"{BASE_URL}{href}",
                                }
                            )

                    logger.info(
                        f"Found {len(meets_to_scrape)} meets for team {team_id}"
                    )

                except Exception as e:
                    logger.warning(f"Could not find meets for team {team_id}: {e}")

            except Exception as e:
                logger.error(f"Error finding meets for {team_id}: {e}")
                return
            finally:
                await page.close()

        # Scrape each meet (limited concurrency)
        for meet in meets_to_scrape[:5]:  # LIMIT to 5 recent meets
            await self.scrape_meet(meet["id"], meet["url"])

    async def scrape_meet(self, meet_id: str, meet_url: str):
        """Scrape full results for a meet."""
        if meet_id in self.processed_meets:
            return

        async with self.semaphore:
            page = await self.get_page()
            try:
                logger.info(f"Scraping meet: {meet_id}")
                await page.goto(meet_url, timeout=60000)

                # Get Events List
                events = []
                try:
                    await page.wait_for_timeout(2000)
                    # Try to get events from side drawer if present, or dropdown
                    event_items = await page.query_selector_all(".js-event-item")

                    # If empty, try clicking "Events"
                    if not event_items:
                        buttons = await page.query_selector_all("button")
                        for btn in buttons:
                            try:
                                txt = await btn.inner_text()
                                if "Events" in txt:
                                    await btn.click()
                                    await page.wait_for_timeout(1000)
                                    event_items = await page.query_selector_all(
                                        ".js-event-item"
                                    )
                                    break
                            except:
                                continue

                    for el in event_items:
                        href = await el.get_attribute("href")
                        if href:
                            events.append(f"{BASE_URL}{href}")

                except Exception as e:
                    logger.warning(f"Could not parse events for meet {meet_id}: {e}")

                logger.info(f"Found {len(events)} events for meet {meet_id}")

                meet_results = []
                # Scrape each event
                for event_url in events:
                    try:
                        await page.goto(event_url, timeout=30000)
                        try:
                            await page.wait_for_selector(
                                "table.c-table-clean tbody tr", timeout=5000
                            )
                        except:
                            # Skip if no results table
                            continue

                        # Get Event Name
                        event_name = "Unknown"
                        try:
                            header = await page.query_selector(
                                ".c-meet-toolbar__event-name, .c-toolbar__title, h1, h2"
                            )
                            if header:
                                event_name = await header.inner_text()
                        except:
                            pass

                        # Scrape Rows
                        rows = await page.query_selector_all(
                            "table.c-table-clean tbody tr"
                        )
                        for row in rows:
                            cols = await row.query_selector_all("td")
                            # Heuristic: Name is usually in a link in column 1 or 2
                            row_data = {"event": event_name}

                            if len(cols) >= 4:
                                try:
                                    # Name
                                    name_el = await row.query_selector(
                                        "a"
                                    )  # First link is usually name
                                    # Or check specific columns
                                    # Usually col 0 is rank, col 1 is name
                                    # But sometimes col 0 is name

                                    # Let's try to find the name link specifically
                                    # Agent said: Rank, Name, Team, Time
                                    name_el = await cols[1].query_selector("a")
                                    row_data["swimmer"] = (
                                        await name_el.inner_text()
                                        if name_el
                                        else (await cols[1].inner_text()).strip()
                                    )

                                    team_el = await cols[2].query_selector("a")
                                    row_data["team"] = (
                                        await team_el.inner_text()
                                        if team_el
                                        else (await cols[2].inner_text()).strip()
                                    )

                                    row_data["time"] = (
                                        await cols[3].inner_text()
                                    ).strip()

                                    meet_results.append(row_data)
                                except Exception:
                                    continue
                    except Exception:
                        continue

                # Save Meet Data
                meet_data = {
                    "meet_id": meet_id,
                    "meet_name": "Unknown",
                    "results": meet_results,
                    "scraped_at": datetime.now().isoformat(),
                }

                filename = os.path.join(MEETS_DIR, f"{meet_id}.json")
                with open(filename, "w") as f:
                    json.dump(meet_data, f, indent=2)

                self.processed_meets.add(meet_id)
                logger.info(
                    f"Saved meet data for {meet_id} with {len(meet_results)} results"
                )

            except Exception as e:
                logger.error(f"Error scraping meet {meet_id}: {e}")
            finally:
                await page.close()

    async def main(
        self, target_team_name: str, limit: int, team_id: Optional[str] = None
    ):
        await self.start()
        try:
            if team_id:
                logger.info(f"Using provided Team ID: {team_id}")
                await self.scrape_team(team_id)
            else:
                team_info = await self.search_team(target_team_name)
                if team_info:
                    await self.scrape_team(team_info["id"])
                else:
                    logger.error(f"Could not find team: {target_team_name}")
        finally:
            await self.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape SwimCloud Data")
    parser.add_argument(
        "--team", type=str, required=False, help="Name of the team to scrape"
    )
    parser.add_argument(
        "--id", type=str, required=False, help="Direct ID of the team to scrape"
    )
    parser.add_argument(
        "--limit", type=int, default=5, help="Limit number of items to scrape"
    )
    parser.add_argument(
        "--headless", action="store_true", default=True, help="Run headless"
    )
    parser.add_argument(
        "--no-headless",
        action="store_false",
        dest="headless",
        help="Run visible browser",
    )

    args = parser.parse_args()

    if not args.team and not args.id:
        parser.error("At least one of --team or --id must be provided")

    scraper = SwimCloudScraper(headless=args.headless)
    asyncio.run(scraper.main(args.team, args.limit, args.id))
