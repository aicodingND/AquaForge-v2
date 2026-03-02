#!/usr/bin/env python3
"""
VISAA State Championship 2026 - Entry Optimizer
Runs AquaOptimizer against real psych sheet data scraped from SwimCloud.

Uses the VISAA Championship scoring profile and real opponent fields
to recommend optimal event assignments for each Seton swimmer.
"""

import json
import sys
import time
from pathlib import Path

# Add project root to path so local imports resolve
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd  # noqa: E402

from swim_ai_reflex.backend.core.strategies.aqua_optimizer import (  # noqa: E402
    AquaOptimizer,
    FatigueModel,
    ScoringProfile,
)

# ─── Multi-team swimmer→team lookup ───────────────────────────────────
_SWIMMER_TEAM: dict[str, str] = {}
_TEAM_LOOKUP_PATH = (
    PROJECT_ROOT / "data" / "swimcloud" / "visaa_2026_swimmer_teams.json"
)
if _TEAM_LOOKUP_PATH.exists():
    with open(_TEAM_LOOKUP_PATH) as f:
        _SWIMMER_TEAM.update(json.load(f))


def _get_opponent_team(entry: dict) -> str:
    """Get real team name for an opponent entry."""
    if "team" in entry and entry["team"]:
        return entry["team"]
    return _SWIMMER_TEAM.get(entry["swimmer"], f"UNK_{entry['swimmer']}")


# ═══════════════════════════════════════════════════════════════════════
#  VISAA STATE CHAMPIONSHIP 2026 — FULL PSYCH SHEET DATA
#  Source: SwimCloud Meet 350494, scraped Feb 14, 2026
# ═══════════════════════════════════════════════════════════════════════

# ─── SETON ENTRIES (from SwimCloud team page + season data) ──────────
SETON_ENTRIES = [
    # BOYS INDIVIDUAL
    {"swimmer": "Lio Martinez", "event": "Boys 100 Fly", "time": 51.87, "grade": 12},
    {"swimmer": "Lio Martinez", "event": "Boys 100 Free", "time": 48.98, "grade": 12},
    {"swimmer": "Daniel Sokban", "event": "Boys 50 Free", "time": 22.48, "grade": 12},
    {"swimmer": "Daniel Sokban", "event": "Boys 200 Free", "time": 128.96, "grade": 12},
    {"swimmer": "Dominic Judge", "event": "Boys 200 Free", "time": 116.19, "grade": 11},
    {"swimmer": "Dominic Judge", "event": "Boys 100 Free", "time": 51.38, "grade": 11},
    {"swimmer": "Dominic Judge", "event": "Boys 200 IM", "time": 133.15, "grade": 11},
    {"swimmer": "Dominic Judge", "event": "Boys 50 Free", "time": 24.09, "grade": 11},
    {"swimmer": "Patrick Kay", "event": "Boys 200 Free", "time": 116.68, "grade": 11},
    {"swimmer": "Patrick Kay", "event": "Boys 500 Free", "time": 321.66, "grade": 11},
    {"swimmer": "Patrick Kay", "event": "Boys 100 Back", "time": 63.79, "grade": 11},
    {"swimmer": "Patrick Kay", "event": "Boys 200 IM", "time": 137.90, "grade": 11},
    {
        "swimmer": "Michael Zahorchak",
        "event": "Boys 200 Free",
        "time": 122.53,
        "grade": 11,
    },
    {
        "swimmer": "Michael Zahorchak",
        "event": "Boys 100 Free",
        "time": 53.03,
        "grade": 11,
    },
    {
        "swimmer": "Michael Zahorchak",
        "event": "Boys 50 Free",
        "time": 24.79,
        "grade": 11,
    },
    {"swimmer": "Jack Herwick", "event": "Boys 100 Fly", "time": 60.03, "grade": 11},
    {"swimmer": "Jack Herwick", "event": "Boys 100 Back", "time": 61.92, "grade": 11},
    {"swimmer": "Gregory Bauer", "event": "Boys 50 Free", "time": 23.98, "grade": 10},
    {
        "swimmer": "Gregory Bauer",
        "event": "Boys 100 Breast",
        "time": 66.08,
        "grade": 10,
    },
    {"swimmer": "Gregory Bauer", "event": "Boys 500 Free", "time": 370.02, "grade": 10},
    {"swimmer": "Thiago Martinez", "event": "Boys 100 Fly", "time": 55.05, "grade": 10},
    {"swimmer": "Thiago Martinez", "event": "Boys 200 IM", "time": 125.96, "grade": 10},
    {
        "swimmer": "Thiago Martinez",
        "event": "Boys 500 Free",
        "time": 312.07,
        "grade": 10,
    },
    {"swimmer": "Joey Lynch", "event": "Boys 100 Free", "time": 58.95, "grade": 10},
    {"swimmer": "Joey Lynch", "event": "Boys 100 Back", "time": 71.58, "grade": 10},
    {
        "swimmer": "Bennett Ellis",
        "event": "Boys 100 Breast",
        "time": 74.63,
        "grade": 10,
    },
    {"swimmer": "Bennett Ellis", "event": "Boys 200 Free", "time": 159.35, "grade": 10},
    {"swimmer": "Joe Witter", "event": "Boys 50 Free", "time": 25.77, "grade": 10},
    {"swimmer": "JJ Garvey", "event": "Boys 100 Fly", "time": 78.97, "grade": 9},
    {"swimmer": "JJ Garvey", "event": "Boys 100 Back", "time": 73.22, "grade": 9},
    {
        "swimmer": "Joel Bookwalter",
        "event": "Boys 100 Free",
        "time": 60.58,
        "grade": 10,
    },
    {
        "swimmer": "Joel Bookwalter",
        "event": "Boys 100 Breast",
        "time": 81.14,
        "grade": 10,
    },
    {
        "swimmer": "Paul Partridge",
        "event": "Boys 100 Breast",
        "time": 79.23,
        "grade": 10,
    },
    {
        "swimmer": "Paul Partridge",
        "event": "Boys 500 Free",
        "time": 387.60,
        "grade": 10,
    },
    {
        "swimmer": "Aidan McCardell",
        "event": "Boys 100 Breast",
        "time": 84.29,
        "grade": 10,
    },
    {"swimmer": "Jonas Wilson", "event": "Boys 100 Fly", "time": 72.88, "grade": 10},
    {"swimmer": "Jonas Wilson", "event": "Boys 500 Free", "time": 376.17, "grade": 10},
    # BOYS DIVING
    {"swimmer": "Max Ashton", "event": "Boys 1M Diving", "time": 279.20, "grade": 11},
    {"swimmer": "John Witter", "event": "Boys 1M Diving", "time": 249.75, "grade": 10},
    # BOYS RELAYS
    {
        "swimmer": "Seton Boys MR-A",
        "event": "Boys 200 Medley Relay",
        "time": 101.00,
        "grade": 12,
    },
    {
        "swimmer": "Seton Boys FR-A",
        "event": "Boys 200 Free Relay",
        "time": 92.06,
        "grade": 12,
    },
    {
        "swimmer": "Seton Boys 4FR-A",
        "event": "Boys 400 Free Relay",
        "time": 206.68,
        "grade": 12,
    },
    # GIRLS INDIVIDUAL
    {
        "swimmer": "Melissa Paradise",
        "event": "Girls 100 Back",
        "time": 56.68,
        "grade": 12,
    },
    {
        "swimmer": "Melissa Paradise",
        "event": "Girls 100 Fly",
        "time": 62.08,
        "grade": 12,
    },
    {
        "swimmer": "Therese Paradise",
        "event": "Girls 100 Breast",
        "time": 72.87,
        "grade": 11,
    },
    {
        "swimmer": "Therese Paradise",
        "event": "Girls 200 Free",
        "time": 123.83,
        "grade": 11,
    },
    {
        "swimmer": "Ariana Aldeguer",
        "event": "Girls 100 Free",
        "time": 54.21,
        "grade": 12,
    },
    {
        "swimmer": "Ariana Aldeguer",
        "event": "Girls 200 IM",
        "time": 128.35,
        "grade": 12,
    },
    {"swimmer": "Maggie Schroer", "event": "Girls 50 Free", "time": 25.67, "grade": 11},
    {
        "swimmer": "Maggie Schroer",
        "event": "Girls 100 Back",
        "time": 68.82,
        "grade": 11,
    },
    {"swimmer": "Philomena Kay", "event": "Girls 100 Free", "time": 60.49, "grade": 11},
    {
        "swimmer": "Philomena Kay",
        "event": "Girls 200 Free",
        "time": 139.54,
        "grade": 11,
    },
    {
        "swimmer": "Anastasia Garvey",
        "event": "Girls 100 Fly",
        "time": 66.99,
        "grade": 11,
    },
    {
        "swimmer": "Anastasia Garvey",
        "event": "Girls 100 Breast",
        "time": 77.15,
        "grade": 11,
    },
    {"swimmer": "Sophia Halisky", "event": "Girls 50 Free", "time": 28.64, "grade": 11},
    {
        "swimmer": "Sophia Halisky",
        "event": "Girls 100 Breast",
        "time": 79.05,
        "grade": 11,
    },
    {"swimmer": "Betsy Arnold", "event": "Girls 100 Back", "time": 77.11, "grade": 10},
    {"swimmer": "Betsy Arnold", "event": "Girls 100 Fly", "time": 68.28, "grade": 10},
    {"swimmer": "Avila Mantooth", "event": "Girls 200 IM", "time": 164.17, "grade": 10},
    {"swimmer": "Avila Mantooth", "event": "Girls 100 Fly", "time": 71.42, "grade": 10},
    {"swimmer": "Katie Bauer", "event": "Girls 500 Free", "time": 415.83, "grade": 10},
    {"swimmer": "Katie Bauer", "event": "Girls 200 Free", "time": 148.18, "grade": 10},
    {
        "swimmer": "Kyleigh Fifield",
        "event": "Girls 500 Free",
        "time": 405.53,
        "grade": 10,
    },
    {
        "swimmer": "Kyleigh Fifield",
        "event": "Girls 200 IM",
        "time": 165.99,
        "grade": 10,
    },
    {"swimmer": "Lily Waldron", "event": "Girls 100 Free", "time": 67.13, "grade": 10},
    {"swimmer": "Lily Waldron", "event": "Girls 50 Free", "time": 28.99, "grade": 10},
    {"swimmer": "Jane Judge", "event": "Girls 100 Back", "time": 75.90, "grade": 10},
    {"swimmer": "Jane Judge", "event": "Girls 100 Free", "time": 68.09, "grade": 10},
    {
        "swimmer": "Gabriella Russo",
        "event": "Girls 500 Free",
        "time": 427.33,
        "grade": 10,
    },
    {
        "swimmer": "Gabriella Russo",
        "event": "Girls 50 Free",
        "time": 29.93,
        "grade": 10,
    },
    {"swimmer": "Annie Dusek", "event": "Girls 500 Free", "time": 411.87, "grade": 10},
    {
        "swimmer": "Aoife Haggerty",
        "event": "Girls 100 Breast",
        "time": 87.47,
        "grade": 10,
    },
    {
        "swimmer": "Elizabeth Hurley",
        "event": "Girls 200 Free",
        "time": 159.20,
        "grade": 10,
    },
    {
        "swimmer": "Charlotte Meadows",
        "event": "Girls 200 IM",
        "time": 168.69,
        "grade": 10,
    },
    # GIRLS DIVING
    {
        "swimmer": "Meghan Condon",
        "event": "Girls 1M Diving",
        "time": 350.85,
        "grade": 12,
    },
    {
        "swimmer": "Maria Miller",
        "event": "Girls 1M Diving",
        "time": 315.40,
        "grade": 11,
    },
    {"swimmer": "Clare Kay", "event": "Girls 1M Diving", "time": 288.00, "grade": 10},
    {
        "swimmer": "Bella Gorman",
        "event": "Girls 1M Diving",
        "time": 272.55,
        "grade": 10,
    },
    # GIRLS RELAYS
    {
        "swimmer": "Seton Girls MR-A",
        "event": "Girls 200 Medley Relay",
        "time": 109.71,
        "grade": 12,
    },
    {
        "swimmer": "Seton Girls FR-A",
        "event": "Girls 200 Free Relay",
        "time": 109.84,
        "grade": 12,
    },
    {
        "swimmer": "Seton Girls 4FR-A",
        "event": "Girls 400 Free Relay",
        "time": 221.18,
        "grade": 12,
    },
]

# ─── OPPONENT ENTRIES (top competitors from SwimCloud psych sheet) ────
# Compiled from scraped event pages — top ~16 per event (scoring positions)
OPPONENT_ENTRIES = [
    # BOYS 50 FREE (top 16 non-Seton)
    {"swimmer": "Aidin Muminovic", "event": "Boys 50 Free", "time": 20.80, "grade": 12},
    {"swimmer": "Ryan Smith", "event": "Boys 50 Free", "time": 21.29, "grade": 12},
    {"swimmer": "Todd Landwehr", "event": "Boys 50 Free", "time": 21.87, "grade": 12},
    {"swimmer": "Taylor Hoffer", "event": "Boys 50 Free", "time": 21.88, "grade": 12},
    {"swimmer": "Taylor Starr", "event": "Boys 50 Free", "time": 21.89, "grade": 12},
    {"swimmer": "Graham Rowan", "event": "Boys 50 Free", "time": 21.97, "grade": 12},
    {"swimmer": "Townsend Sexton", "event": "Boys 50 Free", "time": 22.08, "grade": 12},
    {"swimmer": "Max Alger", "event": "Boys 50 Free", "time": 22.09, "grade": 12},
    {"swimmer": "Elijah Soto", "event": "Boys 50 Free", "time": 22.14, "grade": 12},
    {"swimmer": "Caleb Fiala", "event": "Boys 50 Free", "time": 22.24, "grade": 12},
    {"swimmer": "Theo Gwyer", "event": "Boys 50 Free", "time": 22.27, "grade": 12},
    {
        "swimmer": "Jermaine Worthen",
        "event": "Boys 50 Free",
        "time": 22.44,
        "grade": 12,
    },
    {"swimmer": "Jack Lentini", "event": "Boys 50 Free", "time": 22.46, "grade": 12},
    {"swimmer": "Preston DeFeo", "event": "Boys 50 Free", "time": 22.49, "grade": 12},
    {"swimmer": "John Miranda", "event": "Boys 50 Free", "time": 22.52, "grade": 12},
    {"swimmer": "Zachary Tan", "event": "Boys 50 Free", "time": 22.55, "grade": 12},
    # BOYS 100 FREE (top 16 non-Seton)
    {"swimmer": "Tyler Phillips", "event": "Boys 100 Free", "time": 47.00, "grade": 12},
    {
        "swimmer": "Aidin Muminovic",
        "event": "Boys 100 Free",
        "time": 48.19,
        "grade": 12,
    },
    {"swimmer": "Preston DeFeo", "event": "Boys 100 Free", "time": 48.48, "grade": 12},
    {"swimmer": "Taylor Starr", "event": "Boys 100 Free", "time": 48.59, "grade": 12},
    {"swimmer": "Taylor Hoffer", "event": "Boys 100 Free", "time": 48.63, "grade": 12},
    {"swimmer": "Jamie Arcarese", "event": "Boys 100 Free", "time": 48.84, "grade": 12},
    {"swimmer": "Max Alger", "event": "Boys 100 Free", "time": 49.33, "grade": 12},
    {
        "swimmer": "Townsend Sexton",
        "event": "Boys 100 Free",
        "time": 49.55,
        "grade": 12,
    },
    {"swimmer": "Jack Lentini", "event": "Boys 100 Free", "time": 49.58, "grade": 12},
    {"swimmer": "Jack Byrne", "event": "Boys 100 Free", "time": 49.78, "grade": 12},
    {
        "swimmer": "Justinas Petkauskas",
        "event": "Boys 100 Free",
        "time": 50.00,
        "grade": 12,
    },
    {"swimmer": "Davis Pelton", "event": "Boys 100 Free", "time": 50.08, "grade": 12},
    {"swimmer": "Eric Koler", "event": "Boys 100 Free", "time": 50.56, "grade": 12},
    {"swimmer": "James Kinsella", "event": "Boys 100 Free", "time": 50.58, "grade": 12},
    {"swimmer": "Theo Gwyer", "event": "Boys 100 Free", "time": 50.88, "grade": 12},
    {"swimmer": "Oscar Eshenour", "event": "Boys 100 Free", "time": 51.14, "grade": 12},
    # BOYS 200 FREE (top 16 non-Seton)
    {"swimmer": "Will Charlton", "event": "Boys 200 Free", "time": 101.50, "grade": 12},
    {"swimmer": "Henry Rossman", "event": "Boys 200 Free", "time": 102.57, "grade": 12},
    {"swimmer": "Paul Mullen", "event": "Boys 200 Free", "time": 102.91, "grade": 12},
    {"swimmer": "Ben Franks", "event": "Boys 200 Free", "time": 106.42, "grade": 12},
    {"swimmer": "Grant Hewett", "event": "Boys 200 Free", "time": 107.09, "grade": 12},
    {"swimmer": "John Ackerly", "event": "Boys 200 Free", "time": 107.76, "grade": 12},
    {
        "swimmer": "Jaedan Council",
        "event": "Boys 200 Free",
        "time": 108.73,
        "grade": 12,
    },
    {"swimmer": "Keaghan Fahle", "event": "Boys 200 Free", "time": 109.12, "grade": 12},
    {"swimmer": "Nate Jurutka", "event": "Boys 200 Free", "time": 109.28, "grade": 12},
    {
        "swimmer": "Ryan Mariscalco",
        "event": "Boys 200 Free",
        "time": 109.96,
        "grade": 12,
    },
    {"swimmer": "Jack Fuqua", "event": "Boys 200 Free", "time": 111.49, "grade": 12},
    {"swimmer": "Mason Sever", "event": "Boys 200 Free", "time": 112.00, "grade": 12},
    {
        "swimmer": "Justinas Petkauskas",
        "event": "Boys 200 Free",
        "time": 112.46,
        "grade": 12,
    },
    {"swimmer": "Dylan Noriega", "event": "Boys 200 Free", "time": 112.76, "grade": 12},
    {"swimmer": "Will Franks", "event": "Boys 200 Free", "time": 113.21, "grade": 12},
    {
        "swimmer": "Crawford Craig",
        "event": "Boys 200 Free",
        "time": 113.72,
        "grade": 12,
    },
    # BOYS 200 IM (top 16 non-Seton)
    {"swimmer": "JD Chen", "event": "Boys 200 IM", "time": 111.31, "grade": 12},
    {
        "swimmer": "Rawlings Leachman",
        "event": "Boys 200 IM",
        "time": 112.44,
        "grade": 12,
    },
    {"swimmer": "Charlie Taylor", "event": "Boys 200 IM", "time": 114.11, "grade": 12},
    {
        "swimmer": "Jackson Carpenter",
        "event": "Boys 200 IM",
        "time": 114.18,
        "grade": 12,
    },
    {"swimmer": "Moses Wolf", "event": "Boys 200 IM", "time": 114.26, "grade": 12},
    {"swimmer": "Edward Johnson", "event": "Boys 200 IM", "time": 115.13, "grade": 12},
    {"swimmer": "Luke Hottle", "event": "Boys 200 IM", "time": 115.85, "grade": 12},
    {"swimmer": "Owen Cullaty", "event": "Boys 200 IM", "time": 121.91, "grade": 12},
    {"swimmer": "Beckett Cummins", "event": "Boys 200 IM", "time": 122.00, "grade": 12},
    {"swimmer": "Keagan Murdock", "event": "Boys 200 IM", "time": 123.77, "grade": 12},
    {"swimmer": "Caleb Coyne", "event": "Boys 200 IM", "time": 123.95, "grade": 12},
    {
        "swimmer": "Preston Broderick",
        "event": "Boys 200 IM",
        "time": 124.14,
        "grade": 12,
    },
    {
        "swimmer": "Broderick Nelson",
        "event": "Boys 200 IM",
        "time": 124.45,
        "grade": 12,
    },
    {"swimmer": "Aiden Danis", "event": "Boys 200 IM", "time": 125.35, "grade": 12},
    {"swimmer": "Zach Choi", "event": "Boys 200 IM", "time": 127.58, "grade": 12},
    {"swimmer": "Tyler Kerrigan", "event": "Boys 200 IM", "time": 127.96, "grade": 12},
    # BOYS 1M DIVING (top non-Seton)
    {"swimmer": "Rai Detten", "event": "Boys 1M Diving", "time": 422.35, "grade": 12},
    {"swimmer": "Levi Jones", "event": "Boys 1M Diving", "time": 416.60, "grade": 12},
    {"swimmer": "Eli Edwards", "event": "Boys 1M Diving", "time": 408.15, "grade": 12},
    {
        "swimmer": "Chris Stensland",
        "event": "Boys 1M Diving",
        "time": 343.55,
        "grade": 12,
    },
    {
        "swimmer": "Kellen Colevas",
        "event": "Boys 1M Diving",
        "time": 339.45,
        "grade": 12,
    },
    {"swimmer": "Jack Pinkus", "event": "Boys 1M Diving", "time": 337.95, "grade": 12},
    {"swimmer": "Joseph Adair", "event": "Boys 1M Diving", "time": 282.35, "grade": 12},
    {
        "swimmer": "Sam Winowiecki",
        "event": "Boys 1M Diving",
        "time": 271.65,
        "grade": 12,
    },
    {"swimmer": "Wade Winslow", "event": "Boys 1M Diving", "time": 252.40, "grade": 12},
    {"swimmer": "Jonah Bakkar", "event": "Boys 1M Diving", "time": 230.00, "grade": 12},
    # GIRLS 200 IM (top non-Seton)
    {"swimmer": "Olivia Taylor", "event": "Girls 200 IM", "time": 122.87, "grade": 12},
    {
        "swimmer": "Elizabeth Bryan",
        "event": "Girls 200 IM",
        "time": 123.82,
        "grade": 12,
    },
    {"swimmer": "Liza Cutchins", "event": "Girls 200 IM", "time": 126.20, "grade": 12},
    {
        "swimmer": "Brantley Patterson",
        "event": "Girls 200 IM",
        "time": 126.48,
        "grade": 12,
    },
    {"swimmer": "Hayes Williams", "event": "Girls 200 IM", "time": 127.08, "grade": 12},
    {"swimmer": "Kalyn O'Hara", "event": "Girls 200 IM", "time": 128.22, "grade": 12},
    {
        "swimmer": "Kendall Kryszon",
        "event": "Girls 200 IM",
        "time": 130.12,
        "grade": 12,
    },
    {"swimmer": "Rio Walther", "event": "Girls 200 IM", "time": 132.62, "grade": 12},
    {"swimmer": "Haley Baker", "event": "Girls 200 IM", "time": 133.71, "grade": 12},
    {"swimmer": "Natalie Tang", "event": "Girls 200 IM", "time": 134.72, "grade": 12},
    {
        "swimmer": "Avery Vanlandingham",
        "event": "Girls 200 IM",
        "time": 134.73,
        "grade": 12,
    },
    {
        "swimmer": "Margaret Hepper",
        "event": "Girls 200 IM",
        "time": 136.19,
        "grade": 12,
    },
    {"swimmer": "Abby Paullin", "event": "Girls 200 IM", "time": 137.16, "grade": 12},
    {"swimmer": "Abby Harders", "event": "Girls 200 IM", "time": 137.48, "grade": 12},
    {
        "swimmer": "Madeleine Steves",
        "event": "Girls 200 IM",
        "time": 137.55,
        "grade": 12,
    },
    {"swimmer": "Lilly Wahl", "event": "Girls 200 IM", "time": 137.66, "grade": 12},
    # GIRLS 200 FREE (top non-Seton)
    {
        "swimmer": "Emory DeGuenther",
        "event": "Girls 200 Free",
        "time": 110.66,
        "grade": 12,
    },
    {
        "swimmer": "Claire Dobrydney",
        "event": "Girls 200 Free",
        "time": 110.98,
        "grade": 12,
    },
    {
        "swimmer": "McKinley Busen",
        "event": "Girls 200 Free",
        "time": 111.03,
        "grade": 12,
    },
    {"swimmer": "Anne Scherer", "event": "Girls 200 Free", "time": 111.79, "grade": 12},
    {"swimmer": "Kate Boutry", "event": "Girls 200 Free", "time": 114.43, "grade": 12},
    {"swimmer": "Leah Eubanks", "event": "Girls 200 Free", "time": 116.29, "grade": 12},
    {"swimmer": "Lila Brock", "event": "Girls 200 Free", "time": 117.24, "grade": 12},
    {
        "swimmer": "Madeline Schulz",
        "event": "Girls 200 Free",
        "time": 117.69,
        "grade": 12,
    },
    {"swimmer": "Erin Kass", "event": "Girls 200 Free", "time": 118.36, "grade": 12},
    {"swimmer": "Asmara Pina", "event": "Girls 200 Free", "time": 118.80, "grade": 12},
    {"swimmer": "Piper Strach", "event": "Girls 200 Free", "time": 118.83, "grade": 12},
    {
        "swimmer": "Lila Kate Robinson",
        "event": "Girls 200 Free",
        "time": 119.85,
        "grade": 12,
    },
    {
        "swimmer": "Kylie Kryszon",
        "event": "Girls 200 Free",
        "time": 119.94,
        "grade": 12,
    },
    {
        "swimmer": "Anna Sullivan",
        "event": "Girls 200 Free",
        "time": 120.63,
        "grade": 12,
    },
    {
        "swimmer": "Claire Fioravanti",
        "event": "Girls 200 Free",
        "time": 120.67,
        "grade": 12,
    },
    {
        "swimmer": "Elizabeth Cribbs",
        "event": "Girls 200 Free",
        "time": 120.93,
        "grade": 12,
    },
    # GIRLS 50 FREE (top 16 non-Seton)
    {"swimmer": "Jasper Jones", "event": "Girls 50 Free", "time": 23.62, "grade": 12},
    {"swimmer": "Kate Douglas", "event": "Girls 50 Free", "time": 23.82, "grade": 12},
    {
        "swimmer": "Valentina Linkonis",
        "event": "Girls 50 Free",
        "time": 24.24,
        "grade": 12,
    },
    {"swimmer": "Lydia Foster", "event": "Girls 50 Free", "time": 24.27, "grade": 12},
    {
        "swimmer": "Campbell Totton",
        "event": "Girls 50 Free",
        "time": 24.45,
        "grade": 12,
    },
    {"swimmer": "Blair Parker", "event": "Girls 50 Free", "time": 24.53, "grade": 12},
    {"swimmer": "Ellie Wertzler", "event": "Girls 50 Free", "time": 24.57, "grade": 12},
    {"swimmer": "Kylee Smith", "event": "Girls 50 Free", "time": 24.64, "grade": 12},
    {"swimmer": "Eve Frost", "event": "Girls 50 Free", "time": 24.75, "grade": 12},
    {
        "swimmer": "Savannah Harris",
        "event": "Girls 50 Free",
        "time": 25.16,
        "grade": 12,
    },
    {"swimmer": "Isa Willis", "event": "Girls 50 Free", "time": 25.28, "grade": 12},
    {"swimmer": "Rianna Scott", "event": "Girls 50 Free", "time": 25.30, "grade": 12},
    {"swimmer": "Gabby Carvalho", "event": "Girls 50 Free", "time": 25.37, "grade": 12},
    {
        "swimmer": "Marcella Forrer",
        "event": "Girls 50 Free",
        "time": 25.49,
        "grade": 12,
    },
    {
        "swimmer": "Ella Stufflebeem",
        "event": "Girls 50 Free",
        "time": 25.56,
        "grade": 12,
    },
    {"swimmer": "Anna King", "event": "Girls 50 Free", "time": 25.69, "grade": 12},
    # GIRLS 1M DIVING (top non-Seton)
    {
        "swimmer": "Charlotte Hill",
        "event": "Girls 1M Diving",
        "time": 352.40,
        "grade": 12,
    },
    {
        "swimmer": "Carter Palmer",
        "event": "Girls 1M Diving",
        "time": 325.05,
        "grade": 12,
    },
    {
        "swimmer": "Teagen Rauschelbach",
        "event": "Girls 1M Diving",
        "time": 296.90,
        "grade": 12,
    },
    {
        "swimmer": "Addison Barnes",
        "event": "Girls 1M Diving",
        "time": 295.40,
        "grade": 12,
    },
    {"swimmer": "Addie Cook", "event": "Girls 1M Diving", "time": 280.70, "grade": 12},
    {
        "swimmer": "Ruby Shellock",
        "event": "Girls 1M Diving",
        "time": 272.50,
        "grade": 12,
    },
    # GIRLS MEDLEY RELAY (top non-Seton)
    {
        "swimmer": "Potomac MR-A",
        "event": "Girls 200 Medley Relay",
        "time": 105.85,
        "grade": 12,
    },
    {
        "swimmer": "Collegiate MR-A",
        "event": "Girls 200 Medley Relay",
        "time": 106.21,
        "grade": 12,
    },
    {
        "swimmer": "Bishop OConnell MR-A",
        "event": "Girls 200 Medley Relay",
        "time": 107.78,
        "grade": 12,
    },
    {
        "swimmer": "Cape Henry MR-A",
        "event": "Girls 200 Medley Relay",
        "time": 109.39,
        "grade": 12,
    },
    {
        "swimmer": "St Catherines MR-A",
        "event": "Girls 200 Medley Relay",
        "time": 110.00,
        "grade": 12,
    },
    {
        "swimmer": "SSAS MR-A",
        "event": "Girls 200 Medley Relay",
        "time": 111.71,
        "grade": 12,
    },
    {
        "swimmer": "Norfolk Academy MR-A",
        "event": "Girls 200 Medley Relay",
        "time": 112.29,
        "grade": 12,
    },
    # BOYS MEDLEY RELAY (top non-Seton)
    {
        "swimmer": "St Christophers MR-A",
        "event": "Boys 200 Medley Relay",
        "time": 94.02,
        "grade": 12,
    },
    {
        "swimmer": "Collegiate MR-A",
        "event": "Boys 200 Medley Relay",
        "time": 94.41,
        "grade": 12,
    },
    {
        "swimmer": "Flint Hill MR-A",
        "event": "Boys 200 Medley Relay",
        "time": 97.18,
        "grade": 12,
    },
    {
        "swimmer": "Covenant MR-A",
        "event": "Boys 200 Medley Relay",
        "time": 97.21,
        "grade": 12,
    },
    {
        "swimmer": "Bishop OConnell MR-A",
        "event": "Boys 200 Medley Relay",
        "time": 98.16,
        "grade": 12,
    },
    {
        "swimmer": "Potomac MR-A",
        "event": "Boys 200 Medley Relay",
        "time": 100.66,
        "grade": 12,
    },
    {
        "swimmer": "Immanuel MR-A",
        "event": "Boys 200 Medley Relay",
        "time": 101.15,
        "grade": 12,
    },
]


def format_time(seconds):
    if seconds >= 60:
        mins = int(seconds // 60)
        secs = seconds % 60
        return f"{mins}:{secs:05.2f}"
    return f"{seconds:.2f}"


def run_optimizer():
    print("=" * 80)
    print("  AQUAFORGE OPTIMIZER - VISAA STATE CHAMPIONSHIP 2026")
    print("  Running AquaOptimizer with VISAA Championship Scoring Profile")
    print("=" * 80)
    print()

    # Build DataFrames
    seton_df = pd.DataFrame(SETON_ENTRIES)
    seton_df["team"] = "seton"

    opponent_df = pd.DataFrame(OPPONENT_ENTRIES)
    # Assign real team names for multi-team scoring
    opponent_df["team"] = opponent_df.apply(
        lambda row: _get_opponent_team(row.to_dict()), axis=1
    )

    print(
        f"  Seton entries:    {len(seton_df)} (across {seton_df['swimmer'].nunique()} swimmers)"
    )
    print(
        f"  Opponent entries: {len(opponent_df)} (across {opponent_df['swimmer'].nunique()} swimmers)"
    )
    print()

    # Create optimizer with VISAA profile
    profile = ScoringProfile.visaa_championship()
    fatigue = FatigueModel(enabled=True)

    aqua = AquaOptimizer(
        profile=profile,
        fatigue=fatigue,
        quality_mode="thorough",
    )

    print("  Profile: VISAA Championship")
    print(
        f"  Individual scoring: {profile.individual_points[:5]}... ({len(profile.individual_points)} places)"
    )
    print(
        f"  Relay scoring: {profile.relay_points[:5]}... ({len(profile.relay_points)} places)"
    )
    print("  Quality mode: thorough")
    print("  Fatigue model: enabled")
    print()

    # Run optimization
    print("  Running optimization...")
    start = time.time()

    try:
        best_lineup_df, scored_df, totals, details = aqua.optimize(
            seton_roster=seton_df,
            opponent_roster=opponent_df,
            scoring_fn=None,
            rules=None,
        )
        elapsed = time.time() - start

        print(f"  Completed in {elapsed:.2f}s")
        print()

        # ─── RESULTS ─────────────────────────────────────────────
        print("=" * 80)
        print("  OPTIMIZED LINEUP - SETON ENTRY RECOMMENDATIONS")
        print("=" * 80)
        print()

        # Group by swimmer
        if best_lineup_df is not None and len(best_lineup_df) > 0:
            # Sort by swimmer then event
            lineup = best_lineup_df.sort_values(["swimmer", "event"])

            current_swimmer = None
            swimmer_events = []

            for _, row in lineup.iterrows():
                swimmer = row.get("swimmer", "Unknown")
                event = row.get("event", "Unknown")
                t = row.get("time", 0)

                if swimmer != current_swimmer:
                    if current_swimmer and swimmer_events:
                        events_str = " + ".join(swimmer_events)
                        print(f"    {current_swimmer:30s}  {events_str}")
                    current_swimmer = swimmer
                    swimmer_events = []

                swimmer_events.append(f"{event} ({format_time(t)})")

            # Print last swimmer
            if current_swimmer and swimmer_events:
                events_str = " + ".join(swimmer_events)
                print(f"    {current_swimmer:30s}  {events_str}")

            print()

        # ─── SCORING SUMMARY ─────────────────────────────────────
        print("=" * 80)
        print("  SCORING PROJECTION")
        print("=" * 80)
        print()
        seton_score = totals.get("seton", 0)
        opp_score = totals.get("opponent", 0)
        margin = seton_score - opp_score
        print(f"  Seton (SST):    {seton_score:>8.0f} pts")
        print(f"  Field:          {opp_score:>8.0f} pts")
        print(f"  Margin:         {margin:>+8.0f} pts")
        print()

        # Print details/explanations
        if details and len(details) > 0:
            explanations = details[0].get("explanations", [])
            if explanations:
                print("  Event-by-event breakdown:")
                print(f"  {'─' * 70}")
                for exp in explanations[:30]:  # Limit output
                    print(f"    {exp}")
                print()

        # ─── COMPARISON: OPTIMIZER vs COACH ──────────────────────
        print("=" * 80)
        print("  OPTIMIZER RECOMMENDATIONS vs ACTUAL ENTRIES")
        print("=" * 80)
        print()
        print("  The optimizer may suggest different event assignments than what")
        print("  the coach entered. Key differences highlight opportunities.")
        print()

        # Show the actual SwimCloud entries vs optimizer picks
        actual_entries = {}
        for entry in SETON_ENTRIES:
            if "Relay" not in entry["event"] and "Seton" not in entry["swimmer"]:
                s = entry["swimmer"]
                if s not in actual_entries:
                    actual_entries[s] = []
                actual_entries[s].append(entry["event"])

        if best_lineup_df is not None and len(best_lineup_df) > 0:
            optimizer_entries = {}
            for _, row in best_lineup_df.iterrows():
                s = row.get("swimmer", "")
                e = row.get("event", "")
                if "Relay" not in e and "Seton" not in s:
                    if s not in optimizer_entries:
                        optimizer_entries[s] = []
                    optimizer_entries[s].append(e)

            all_swimmers = sorted(
                set(list(actual_entries.keys()) + list(optimizer_entries.keys()))
            )
            changes = 0
            for swimmer in all_swimmers:
                actual = set(actual_entries.get(swimmer, []))
                optimized = set(optimizer_entries.get(swimmer, []))
                if actual != optimized:
                    changes += 1
                    actual_str = (
                        ", ".join(sorted(actual)) if actual else "(not entered)"
                    )
                    opt_str = (
                        ", ".join(sorted(optimized)) if optimized else "(not entered)"
                    )
                    print(f"  {swimmer}:")
                    print(f"    Coach:     {actual_str}")
                    print(f"    Optimizer: {opt_str}")
                    print()

            if changes == 0:
                print("  No changes recommended — coach's entries are optimal!")

    except Exception as e:
        elapsed = time.time() - start
        print(f"  ERROR after {elapsed:.2f}s: {e}")
        print()
        import traceback

        traceback.print_exc()

    print()
    print("=" * 80)
    print("  Generated by AquaForge v1.0.0-next | AquaOptimizer (thorough mode)")
    print("  Data: SwimCloud Meet 350494 | VISAA Championship Profile")
    print("=" * 80)


if __name__ == "__main__":
    run_optimizer()
