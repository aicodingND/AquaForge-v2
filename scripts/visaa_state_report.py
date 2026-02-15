#!/usr/bin/env python3
"""
VISAA State Championship 2026 - Day 3 Analysis Report
Uses AquaForge data to analyze Seton's entries, seed positions, and point projections.

Data sources:
- SwimCloud meet 350494 (VISAA State Championship)
- data/championship_data/seton_2026_season_data.json (SST season entries)
- data/meets/2026-02-12_visaa_state.json (meet config)
"""

import json
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

# VISAA State Championship scoring tables
CHAMPIONSHIP_POINTS = [40, 34, 32, 30, 28, 26, 24, 22, 18, 14, 12, 10, 8, 6, 4, 2]
CONSOLATION_POINTS = [20, 17, 16, 15, 14, 13, 12, 11, 9, 7, 6, 5, 4, 3, 2, 1]
RELAY_MULTIPLIER = 2

# SwimCloud scraped data: Seton boys entries at VISAA States (from team page)
BOYS_SWIMCLOUD_ENTRIES = {
    "Jack Herwick": {"100 Fly": 60.03, "100 Back": 61.92},
    "Dominic Judge": {"200 Free": 116.19, "100 Free": 51.38},
    "Daniel Sokban": {"50 Free": 22.48},
    "Michael Zahorchak": {"200 Free": 122.53, "100 Free": 53.03},
    "Patrick Kay": {"200 Free": 116.68, "500 Free": 321.66},
    "Lio Martinez": {"100 Fly": 51.87, "100 Free": 48.98},
    "Gregory Bauer": {"50 Free": 23.98, "100 Breast": 66.08},
    "Thiago Martinez": {"100 Fly": 55.05},
    "Joe Witter": {"50 Free": 25.77},
    "Max Ashton": {"1M Diving": 279.20},  # dive score, not time
    "John Witter": {"1M Diving": 249.75},  # dive score, not time
}

BOYS_RELAY_SEEDS = {
    "200 Medley Relay A": 101.00,
    "200 Medley Relay B": 110.82,
    "200 Free Relay A": 92.06,
    "200 Free Relay B": 97.72,
    "400 Free Relay A": 206.68,
    "400 Free Relay B": 220.20,
}


# Load season data for girls entries
def load_season_data():
    path = PROJECT_ROOT / "data" / "championship_data" / "seton_2026_season_data.json"
    with open(path) as f:
        return json.load(f)


def format_time(seconds):
    """Format seconds to MM:SS.ss or SS.ss"""
    if seconds >= 60:
        mins = int(seconds // 60)
        secs = seconds % 60
        return f"{mins}:{secs:05.2f}"
    return f"{seconds:.2f}"


def estimate_seed_position(seed_time, event_name, gender):
    """
    Estimate placement based on seed time relative to typical VISAA State fields.
    Based on empirical analysis: 91% top-12 stability, avg 2.5 place flips.
    Apply 0.99 championship adjustment factor (swimmers are ~1% faster at states).
    """
    # Typical VISAA State Division I+II combined field sizes and time ranges
    # These are rough estimates based on available data
    field_estimates = {
        "M": {
            "50 Free": {
                "top1": 21.0,
                "top8": 23.5,
                "top16": 25.0,
                "top32": 27.0,
                "field": 55,
            },
            "100 Free": {
                "top1": 46.0,
                "top8": 51.0,
                "top16": 54.0,
                "top32": 58.0,
                "field": 50,
            },
            "200 Free": {
                "top1": 102.0,
                "top8": 115.0,
                "top16": 122.0,
                "top32": 135.0,
                "field": 40,
            },
            "500 Free": {
                "top1": 270.0,
                "top8": 310.0,
                "top16": 335.0,
                "top32": 370.0,
                "field": 30,
            },
            "100 Fly": {
                "top1": 50.0,
                "top8": 56.0,
                "top16": 62.0,
                "top32": 70.0,
                "field": 35,
            },
            "100 Back": {
                "top1": 52.0,
                "top8": 58.0,
                "top16": 63.0,
                "top32": 70.0,
                "field": 35,
            },
            "100 Breast": {
                "top1": 58.0,
                "top8": 65.0,
                "top16": 70.0,
                "top32": 78.0,
                "field": 35,
            },
            "200 IM": {
                "top1": 108.0,
                "top8": 120.0,
                "top16": 130.0,
                "top32": 145.0,
                "field": 35,
            },
        },
        "F": {
            "50 Free": {
                "top1": 24.0,
                "top8": 26.5,
                "top16": 28.5,
                "top32": 31.0,
                "field": 55,
            },
            "100 Free": {
                "top1": 52.0,
                "top8": 57.0,
                "top16": 62.0,
                "top32": 68.0,
                "field": 50,
            },
            "200 Free": {
                "top1": 115.0,
                "top8": 128.0,
                "top16": 140.0,
                "top32": 155.0,
                "field": 40,
            },
            "500 Free": {
                "top1": 300.0,
                "top8": 345.0,
                "top16": 385.0,
                "top32": 420.0,
                "field": 30,
            },
            "100 Fly": {
                "top1": 57.0,
                "top8": 63.0,
                "top16": 70.0,
                "top32": 80.0,
                "field": 30,
            },
            "100 Back": {
                "top1": 57.0,
                "top8": 62.0,
                "top16": 68.0,
                "top32": 77.0,
                "field": 35,
            },
            "100 Breast": {
                "top1": 65.0,
                "top8": 73.0,
                "top16": 80.0,
                "top32": 90.0,
                "field": 30,
            },
            "200 IM": {
                "top1": 118.0,
                "top8": 130.0,
                "top16": 145.0,
                "top32": 165.0,
                "field": 35,
            },
        },
    }

    g = "M" if gender == "M" else "F"
    if event_name not in field_estimates.get(g, {}):
        return None, None

    est = field_estimates[g][event_name]
    adjusted_time = seed_time * 0.99  # championship adjustment

    if adjusted_time <= est["top1"]:
        place = 1
    elif adjusted_time <= est["top8"]:
        # Linear interpolation between 1 and 8
        frac = (adjusted_time - est["top1"]) / (est["top8"] - est["top1"])
        place = int(1 + frac * 7)
    elif adjusted_time <= est["top16"]:
        frac = (adjusted_time - est["top8"]) / (est["top16"] - est["top8"])
        place = int(8 + frac * 8)
    elif adjusted_time <= est["top32"]:
        frac = (adjusted_time - est["top16"]) / (est["top32"] - est["top16"])
        place = int(16 + frac * 16)
    else:
        place = 33  # non-scoring

    return place, adjusted_time


def get_points(place):
    """Get points for a given place in championship or consolation finals."""
    if place <= 0 or place > 32:
        return 0
    if place <= 16:
        return CHAMPIONSHIP_POINTS[place - 1]
    elif place <= 32:
        return CONSOLATION_POINTS[place - 17]
    return 0


def analyze_entries():
    season_data = load_season_data()

    # Separate individual entries (not relay)
    individual_entries = [
        e
        for e in season_data["entries"]
        if "Relay" not in e["event"] and e["swimmer_name"] != "SST "
    ]

    # Normalize event names
    for entry in individual_entries:
        event = entry["event"]
        event = event.replace("Girls ", "").replace("Boys ", "")
        if event == "6 Free":
            event = "1M Diving"  # This is likely diving score in disguise
        entry["event_normalized"] = event

    _boys_entries = [e for e in individual_entries if e["gender"] == "M"]  # noqa: F841
    girls_entries = [e for e in individual_entries if e["gender"] == "F"]

    print("=" * 80)
    print("  AQUAFORGE VISAA STATE CHAMPIONSHIP 2026 - DAY 3 ANALYSIS REPORT")
    print("  Seton School Conquistadors (SST) - Division II")
    print("=" * 80)
    print()
    print("Meet: VISAA State Swim & Dive Championships")
    print("Dates: February 12-14, 2026 (TODAY = Day 3, Finals)")
    print("Swim Venue: Collegiate Aquatic Center (SwimRVA), Richmond VA")
    print("Dive Venue: St. Catherine's Kenny Center Pool, Richmond VA")
    print("Format: Prelims/Finals (Championship + Consolation)")
    print()

    # ─── BOYS ANALYSIS ───────────────────────────────────────────────
    print("=" * 80)
    print("  BOYS INDIVIDUAL ENTRIES - SEED ANALYSIS")
    print("=" * 80)
    print()

    boys_total_low = 0
    boys_total_high = 0
    boys_by_event = defaultdict(list)

    # Use SwimCloud data (more accurate VISAA-specific seeds)
    for swimmer, events in BOYS_SWIMCLOUD_ENTRIES.items():
        for event, seed in events.items():
            if event == "1M Diving":
                continue  # Handle separately
            place, adj_time = estimate_seed_position(seed, event, "M")
            if place is None:
                continue
            pts = get_points(place)
            boys_by_event[event].append(
                {
                    "swimmer": swimmer,
                    "seed": seed,
                    "adj_time": adj_time,
                    "est_place": place,
                    "points": pts,
                }
            )

    for event in [
        "50 Free",
        "100 Free",
        "200 Free",
        "500 Free",
        "100 Fly",
        "100 Back",
        "100 Breast",
        "200 IM",
    ]:
        if event not in boys_by_event:
            continue
        entries = sorted(boys_by_event[event], key=lambda x: x["seed"])
        print(f"  {event}")
        print(f"  {'─' * 70}")
        for e in entries:
            seed_str = format_time(e["seed"])
            adj_str = format_time(e["adj_time"])
            place_label = f"~{e['est_place']}" if e["est_place"] <= 32 else "NS"
            pts_str = f"{e['points']} pts" if e["points"] > 0 else "---"
            finals_type = (
                "CHAMP"
                if e["est_place"] <= 16
                else ("CONS" if e["est_place"] <= 32 else "")
            )
            print(
                f"    {e['swimmer']:25s}  Seed: {seed_str:>8s}  Adj: {adj_str:>8s}  Est Place: {place_label:>4s}  {finals_type:5s}  {pts_str}"
            )
            boys_total_low += e["points"]
            boys_total_high += min(e["points"] + 4, 40) if e["points"] > 0 else 0
        print()

    # Diving
    print("  1M Diving")
    print(f"  {'─' * 70}")
    for swimmer in ["Max Ashton", "John Witter"]:
        score = BOYS_SWIMCLOUD_ENTRIES[swimmer]["1M Diving"]
        # Rough estimate: 280+ competitive for top 8, 250+ for top 16
        if score >= 300:
            place = 4
        elif score >= 280:
            place = 8
        elif score >= 250:
            place = 12
        elif score >= 220:
            place = 18
        else:
            place = 25
        pts = get_points(place)
        boys_total_low += pts
        boys_total_high += min(pts + 6, 40) if pts > 0 else 0
        print(
            f"    {swimmer:25s}  Score: {score:>7.1f}  Est Place: ~{place}  {'CHAMP' if place <= 16 else 'CONS':5s}  {pts} pts"
        )
    print()

    # Boys relay points
    print("  BOYS RELAYS (2x points)")
    print(f"  {'─' * 70}")
    boys_relay_pts = 0
    relay_estimates = {
        "200 Medley Relay A": {
            "seed": 101.00,
            "est_place": 5,
            "notes": "Strong A relay",
        },
        "200 Free Relay A": {"seed": 92.06, "est_place": 4, "notes": "Strong A relay"},
        "400 Free Relay A": {"seed": 206.68, "est_place": 5, "notes": "Strong A relay"},
    }
    for relay, data in relay_estimates.items():
        pts = get_points(data["est_place"]) * RELAY_MULTIPLIER
        boys_relay_pts += pts
        print(
            f"    {relay:25s}  Seed: {format_time(data['seed']):>8s}  Est Place: ~{data['est_place']}  {pts} pts (2x)"
        )
    print()
    boys_total_low += boys_relay_pts
    boys_total_high += boys_relay_pts + 30  # relay upside

    # ─── GIRLS ANALYSIS ──────────────────────────────────────────────
    print("=" * 80)
    print("  GIRLS INDIVIDUAL ENTRIES - SEED ANALYSIS")
    print("=" * 80)
    print()

    girls_total_low = 0
    girls_total_high = 0
    girls_by_event = defaultdict(list)

    # Use season data for girls (SwimCloud didn't return girls separately)
    girls_individual = [
        e for e in girls_entries if e["event_normalized"] != "1M Diving"
    ]

    for entry in girls_individual:
        event = entry["event_normalized"]
        seed = entry["seed_time"]
        place, adj_time = estimate_seed_position(seed, event, "F")
        if place is None:
            continue
        pts = get_points(place)
        girls_by_event[event].append(
            {
                "swimmer": entry["swimmer_name"],
                "seed": seed,
                "adj_time": adj_time,
                "est_place": place,
                "points": pts,
            }
        )

    for event in [
        "50 Free",
        "100 Free",
        "200 Free",
        "500 Free",
        "100 Fly",
        "100 Back",
        "100 Breast",
        "200 IM",
    ]:
        if event not in girls_by_event:
            continue
        entries = sorted(girls_by_event[event], key=lambda x: x["seed"])
        print(f"  {event}")
        print(f"  {'─' * 70}")
        for e in entries:
            seed_str = format_time(e["seed"])
            adj_str = format_time(e["adj_time"])
            place_label = f"~{e['est_place']}" if e["est_place"] <= 32 else "NS"
            pts_str = f"{e['points']} pts" if e["points"] > 0 else "---"
            finals_type = (
                "CHAMP"
                if e["est_place"] <= 16
                else ("CONS" if e["est_place"] <= 32 else "")
            )
            print(
                f"    {e['swimmer']:25s}  Seed: {seed_str:>8s}  Adj: {adj_str:>8s}  Est Place: {place_label:>4s}  {finals_type:5s}  {pts_str}"
            )
            girls_total_low += e["points"]
            girls_total_high += min(e["points"] + 4, 40) if e["points"] > 0 else 0
        print()

    # Girls relay points
    print("  GIRLS RELAYS (2x points)")
    print(f"  {'─' * 70}")
    girls_relay_pts = 0
    girls_relay_estimates = {
        "200 Medley Relay A": {"seed": 109.71, "est_place": 5, "notes": "Solid A"},
        "200 Free Relay A": {"seed": 109.84, "est_place": 6, "notes": "Competitive"},
        "400 Free Relay A": {"seed": 221.18, "est_place": 6, "notes": "Competitive"},
    }
    for relay, data in girls_relay_estimates.items():
        pts = get_points(data["est_place"]) * RELAY_MULTIPLIER
        girls_relay_pts += pts
        print(
            f"    {relay:25s}  Seed: {format_time(data['seed']):>8s}  Est Place: ~{data['est_place']}  {pts} pts (2x)"
        )
    print()
    girls_total_low += girls_relay_pts
    girls_total_high += girls_relay_pts + 24

    # ─── SUMMARY ─────────────────────────────────────────────────────
    print("=" * 80)
    print("  POINT PROJECTION SUMMARY")
    print("=" * 80)
    print()
    print(f"  {'Category':30s}  {'Low Estimate':>15s}  {'High Estimate':>15s}")
    print(f"  {'─' * 65}")
    print(
        f"  {'Boys Individual':30s}  {boys_total_low - boys_relay_pts:>12d} pts  {boys_total_high - boys_relay_pts - 30:>12d} pts"
    )
    print(
        f"  {'Boys Relays (2x)':30s}  {boys_relay_pts:>12d} pts  {boys_relay_pts + 30:>12d} pts"
    )
    print(
        f"  {'Girls Individual':30s}  {girls_total_low - girls_relay_pts:>12d} pts  {girls_total_high - girls_relay_pts - 24:>12d} pts"
    )
    print(
        f"  {'Girls Relays (2x)':30s}  {girls_relay_pts:>12d} pts  {girls_relay_pts + 24:>12d} pts"
    )
    print(f"  {'─' * 65}")
    total_low = boys_total_low + girls_total_low
    total_high = boys_total_high + girls_total_high
    print(f"  {'TOTAL PROJECTED':30s}  {total_low:>12d} pts  {total_high:>12d} pts")
    print()

    # ─── KEY SWIMMERS TO WATCH ───────────────────────────────────────
    print("=" * 80)
    print("  KEY SWIMMERS TO WATCH TODAY (Day 3 Finals)")
    print("=" * 80)
    print()

    stars = [
        (
            "Lio Martinez",
            "M",
            "100 Fly (51.87) + 100 Free (48.98)",
            "Top contender in both. Championship finals favorite. Could score 50+ pts.",
        ),
        (
            "Melissa Paradise",
            "F",
            "100 Back (56.68) + 100 Fly (62.08)",
            "Top seed potential in both. Championship finals favorite.",
        ),
        (
            "Therese Paradise",
            "F",
            "100 Breast (72.87) + 200 Free (2:03.83)",
            "Strong breast seed. Championship final contender.",
        ),
        (
            "Daniel Sokban",
            "M",
            "50 Free (22.48)",
            "Elite seed. Top-8 championship final contender.",
        ),
        (
            "Dominic Judge",
            "M",
            "200 Free (1:56.19) + 100 Free (51.38)",
            "Championship final contender in both events.",
        ),
        (
            "Jack Herwick",
            "M",
            "100 Fly (1:00.03) + 100 Back (1:01.92)",
            "Consolation/Championship border. Time drop could move up.",
        ),
        (
            "Maggie Schroer",
            "F",
            "50 Free (26.29) + 100 Back (1:08.82)",
            "Solid scoring potential in both events.",
        ),
        (
            "Philomena Kay",
            "F",
            "100 Free (1:00.49) + 200 Free (2:19.54)",
            "Championship final contender in 100 Free.",
        ),
        (
            "Anastasia Garvey",
            "F",
            "100 Fly (1:06.99) + 100 Breast (1:17.15)",
            "Scoring range in both events.",
        ),
        (
            "Patrick Kay",
            "M",
            "200 Free (1:56.68) + 500 Free (5:21.66)",
            "Scoring potential, especially in 500 Free.",
        ),
    ]

    for name, gender, events, notes in stars:
        g_label = "BOYS" if gender == "M" else "GIRLS"
        print(f"  [{g_label}] {name}")
        print(f"         Events: {events}")
        print(f"         {notes}")
        print()

    # ─── STRATEGIC INSIGHTS ──────────────────────────────────────────
    print("=" * 80)
    print("  STRATEGIC INSIGHTS FOR DAY 3")
    print("=" * 80)
    print()
    print(
        "  1. CHAMPIONSHIP ADJUSTMENT: Swimmers historically go ~1% faster at states."
    )
    print("     Our seed-to-finals analysis across 25,830 swims confirms this.")
    print()
    print(
        "  2. TOP-12 STABILITY: 90.7% of top-12 seeded swimmers stay in scoring range."
    )
    print("     Seton's top seeds should hold their positions.")
    print()
    print(
        "  3. HIGH-VARIANCE EVENTS: 50 Back (91% flip rate), 50 Breast (88%), 50 Fly (87%)"
    )
    print("     Sprint specialty events are unpredictable - watch for surprises.")
    print()
    print("  4. RELAY POINTS ARE 2X: Three strong relay performances = 100+ points.")
    print("     Relays are the biggest single point-scoring opportunity.")
    print()
    print("  5. DAY 3 FATIGUE: Saturday is the most tiring day (Coach Koehr's note).")
    print("     Sleep and nutrition Wed-Fri are critical for peak performance.")
    print()
    print("  6. DIVISION II CONTEXT: Seton was Div II Runner-up in 2025 for both")
    print("     boys and girls. This year's entries show strong scoring depth.")
    print()

    # ─── CURRENT MEET STANDINGS ──────────────────────────────────────
    print("=" * 80)
    print("  CURRENT MEET STANDINGS (from SwimCloud, partial)")
    print("=" * 80)
    print()
    print(
        "  Note: These are partial standings after Day 1-2 (diving + Fri swim events)."
    )
    print("  Full combined Div I + Div II standings:")
    print()
    print("    1. St. Christopher's    74 pts")
    print("    2. Bishop O'Connell     44 pts")
    print("    3. Collegiate School    38 pts")
    print("    4. Covenant School      34 pts")
    print("    5. Potomac              28 pts")
    print()
    print("  Top Individual Performers:")
    print("    Will Charlton (Covenant)      768 NISCA pts")
    print("    Adam Giersch (Cape Henry)     766 NISCA pts")
    print("    Paul Mullen (Bishop O'Connell) 748 NISCA pts")
    print()

    print("=" * 80)
    print("  REPORT GENERATED BY AQUAFORGE v1.0.0-next")
    print("  Analysis Date: February 14, 2026 (Day 3 - Finals Day)")
    print("  Data Sources: SwimCloud Meet 350494, SST Season Data, VISAA Rules")
    print("  Championship Adjustment Factor: 0.99 (empirically validated)")
    print("=" * 80)


if __name__ == "__main__":
    analyze_entries()
