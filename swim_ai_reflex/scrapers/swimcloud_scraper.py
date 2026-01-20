"""
SwimCloud Data Scraper for VCAC Teams

Scrapes swimmer rosters and times from SwimCloud for championship analysis.

Team IDs discovered:
- Trinity Christian School (VA): 10009031
- Fredericksburg Christian: 6854
- Immanuel Christian (VA): 10026495
- Oakcrest School (VA): 6884
- Seton Swimming: 3605

URL Structure:
- Team page: https://www.swimcloud.com/team/{team_id}/
- Times: https://www.swimcloud.com/team/{team_id}/times/
- Roster: https://www.swimcloud.com/team/{team_id}/roster/
"""

import json
from dataclasses import dataclass, asdict
from pathlib import Path


# Team configuration
VCAC_TEAMS = {
    "TCS": {"id": 10009031, "name": "Trinity Christian School", "state": "VA"},
    "FCS": {"id": 6854, "name": "Fredericksburg Christian High School", "state": "VA"},
    "ICS": {"id": 10026495, "name": "Immanuel Christian High School", "state": "VA"},
    "OAK": {"id": 6884, "name": "Oakcrest School", "state": "VA"},
    "SST": {"id": 3605, "name": "Seton Swimming", "state": "VA"},
    # Additional VISAA teams for broader analysis
    "DJO": {"id": 6850, "name": "Bishop O'Connell High School", "state": "VA"},
    "PVI": {"id": 6889, "name": "Paul VI High School", "state": "VA"},
    "BI": {"id": 6841, "name": "Bishop Ireton High School", "state": "VA"},
}


@dataclass
class SwimmerEntry:
    """A swimmer's entry for a specific event."""

    swimmer_name: str
    team: str
    event: str
    seed_time: float
    gender: str
    grade: str = ""
    source: str = "swimcloud"


@dataclass
class ScrapedTeamData:
    """Complete scraped data for a team."""

    team_code: str
    team_name: str
    team_id: int
    scraped_at: str
    swimmers: list[dict]
    times: list[dict]
    meet_history: list[dict]


def parse_time_to_seconds(time_str: str) -> float:
    """Convert time string to seconds."""
    if not time_str or time_str in ["NT", "NS", "--", ""]:
        return 0.0

    time_str = time_str.strip()

    # Handle minute:second format
    if ":" in time_str:
        parts = time_str.split(":")
        try:
            return float(parts[0]) * 60 + float(parts[1])
        except ValueError:
            return 0.0

    # Handle plain seconds
    try:
        return float(time_str)
    except ValueError:
        return 0.0


def format_event_name(event_code: str, gender: str) -> str:
    """Format event code to standard event name."""
    gender_prefix = "Boys" if gender == "M" else "Girls"

    # Common event mappings
    event_map = {
        "50 Free": f"{gender_prefix} 50 Free",
        "100 Free": f"{gender_prefix} 100 Free",
        "200 Free": f"{gender_prefix} 200 Free",
        "500 Free": f"{gender_prefix} 500 Free",
        "100 Back": f"{gender_prefix} 100 Back",
        "200 Back": f"{gender_prefix} 200 Back",
        "100 Breast": f"{gender_prefix} 100 Breast",
        "200 Breast": f"{gender_prefix} 200 Breast",
        "100 Fly": f"{gender_prefix} 100 Fly",
        "200 Fly": f"{gender_prefix} 200 Fly",
        "200 IM": f"{gender_prefix} 200 IM",
        "400 IM": f"{gender_prefix} 400 IM",
        "200 Free Relay": f"{gender_prefix} 200 Free Relay",
        "400 Free Relay": f"{gender_prefix} 400 Free Relay",
        "200 Medley Relay": f"{gender_prefix} 200 Medley Relay",
    }

    return event_map.get(event_code, f"{gender_prefix} {event_code}")


class SwimCloudScraper:
    """
    Scraper for SwimCloud team data.

    Note: SwimCloud blocks automated requests with 403 errors.
    This scraper is designed to work with a browser-based approach
    or cached HTML files.
    """

    def __init__(self, cache_dir: str = "data/scraped"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_team_url(self, team_id: int, section: str = "") -> str:
        """Generate SwimCloud URL for a team."""
        base = f"https://www.swimcloud.com/team/{team_id}/"
        if section:
            return f"{base}{section}/"
        return base

    def save_scraped_data(self, team_code: str, data: ScrapedTeamData):
        """Save scraped data to JSON file."""
        filepath = self.cache_dir / f"{team_code}_swimcloud.json"
        with open(filepath, "w") as f:
            json.dump(asdict(data), f, indent=2)
        return filepath


# Export configuration for reference
def get_scrape_urls() -> dict:
    """Get all URLs that need to be scraped."""
    urls = {}
    for code, info in VCAC_TEAMS.items():
        urls[code] = {
            "home": f"https://www.swimcloud.com/team/{info['id']}/",
            "times": f"https://www.swimcloud.com/team/{info['id']}/times/",
            "roster": f"https://www.swimcloud.com/team/{info['id']}/roster/",
            "meets": f"https://www.swimcloud.com/team/{info['id']}/results/",
        }
    return urls


if __name__ == "__main__":
    print("SwimCloud VCAC Team URLs:")
    print("=" * 60)
    for code, urls in get_scrape_urls().items():
        team_name = VCAC_TEAMS[code]["name"]
        print(f"\n{team_name} ({code}):")
        for section, url in urls.items():
            print(f"  {section}: {url}")
