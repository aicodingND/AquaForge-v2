import json
import csv
import os
import random
import glob


def format_time(seconds):
    """Convert seconds to MM:SS.ss or SS.ss"""
    if not seconds:
        return "NT"

    minutes = int(seconds // 60)
    rem_seconds = seconds % 60

    if minutes > 0:
        return f"{minutes}:{rem_seconds:05.2f}"
    else:
        return f"{rem_seconds:.2f}"


def clean_event(event_name):
    """Remove gender prefix"""
    return event_name.replace("Boys ", "").replace("Girls ", "")


def load_json(filepath):
    with open(filepath, "r") as f:
        return json.load(f)


def generate_relays(team_code):
    """Generate synthetic relay entries"""
    relays = []
    for gender in ["Boys", "Girls"]:
        # 200 Medley Relay
        relays.append(
            {
                "swimmer": f"{team_code} {gender} A",
                "team": team_code,
                "event": f"{gender} 200 Medley Relay",
                "time": format_time(100.0 + random.uniform(0, 10)),
                "grade": "12",
            }
        )
        # 200 Free Relay
        relays.append(
            {
                "swimmer": f"{team_code} {gender} A",
                "team": team_code,
                "event": f"{gender} 200 Free Relay",
                "time": format_time(90.0 + random.uniform(0, 10)),
                "grade": "12",
            }
        )
        # 400 Free Relay
        relays.append(
            {
                "swimmer": f"{team_code} {gender} A",
                "team": team_code,
                "event": f"{gender} 400 Free Relay",
                "time": format_time(200.0 + random.uniform(0, 20)),
                "grade": "12",
            }
        )
    return relays


def generate_diving(team_code):
    """Generate synthetic diving entries"""
    divers = []
    for i in range(2):
        divers.append(
            {
                "swimmer": f"{team_code} Diver {i + 1}",
                "team": team_code,
                "event": "Boys Diving",
                "time": f"{random.uniform(150, 300):.1f}",
                "grade": "11",
            }
        )
        divers.append(
            {
                "swimmer": f"{team_code} Diver {i + 1}",
                "team": team_code,
                "event": "Girls Diving",
                "time": f"{random.uniform(150, 300):.1f}",
                "grade": "11",
            }
        )
    return divers


def process_file(json_data, team_override=None, name_override=None):
    entries = []
    team_code = team_override if team_override else json_data.get("team_code", "UNK")
    (
        name_override if name_override else json_data.get("team_name", "Unknown")
    )

    # Process Individual Times
    for time_entry in json_data.get("times", []):
        swimmer = time_entry.get("swimmer_name")
        event_raw = time_entry.get("event")
        seed_time = time_entry.get("seed_time")

        # Determine grade from roster
        grade = ""
        for roster_entry in json_data.get("roster", []):
            if roster_entry.get("name") == swimmer:
                grade = roster_entry.get("classYear", "")
                break

        # Map grade levels to numbers if possible
        grade_map = {"FR": "9", "SO": "10", "JR": "11", "SR": "12", "8": "8"}
        grade = grade_map.get(grade, grade)

        # Skip events without time
        if not seed_time:
            continue

        entries.append(
            {
                "swimmer": swimmer,
                "team": team_code,
                "event": event_raw,  # Keep raw for now, clean later if needed but backend expects format
                "time": format_time(float(seed_time)),
                "grade": grade,
            }
        )

    # Add Relays and Diving
    entries.extend(generate_relays(team_code))
    entries.extend(generate_diving(team_code))

    return entries


def main():
    base_dir = "/Users/mpage1/Desktop/AquaForge/AquaForge_v1.0.0-next_2026-01-10/data"
    scraped_dir = os.path.join(base_dir, "scraped")
    sample_dir = os.path.join(base_dir, "sample")

    os.makedirs(sample_dir, exist_ok=True)

    # 1. Dual Meet: Seton (simulated from TCS) vs DJO
    print("Generating Dual Meet files...")

    # Seton (via TCS)
    tcs_data = load_json(os.path.join(scraped_dir, "TCS_swimcloud.json"))
    seton_entries = process_file(
        tcs_data, team_override="SST", name_override="Seton Swimming"
    )

    with open(
        os.path.join(sample_dir, "dual_meet_seton_team.csv"), "w", newline=""
    ) as f:
        writer = csv.DictWriter(
            f, fieldnames=["swimmer", "team", "event", "time", "grade"]
        )
        writer.writeheader()
        # For dual meet, we can drop 'team' column if we want, but keeping it is safer.
        # The prompt examples showed 'team' for championship but not necessarily for dual.
        # But 'team' column handles all cases. However, let's stick to the prompt's implied simple format for dual if possible.
        # Actually, the user's sample output for dual didn't have 'team', but I'll include it for robustness or just ignore it.
        # Let's write columns: swimmer, event, time, grade
        writer_dual = csv.DictWriter(
            f, fieldnames=["swimmer", "event", "time", "grade"], extrasaction="ignore"
        )
        writer_dual.writeheader()
        writer_dual.writerows(seton_entries)

    # Opponent (DJO)
    djo_data = load_json(os.path.join(scraped_dir, "DJO_swimcloud.json"))
    djo_entries = process_file(djo_data)

    with open(
        os.path.join(sample_dir, "dual_meet_opponent_team.csv"), "w", newline=""
    ) as f:
        writer_dual = csv.DictWriter(
            f, fieldnames=["swimmer", "event", "time", "grade"], extrasaction="ignore"
        )
        writer_dual.writeheader()
        writer_dual.writerows(djo_entries)

    # 2. Championship Meet: All Teams
    print("Generating Championship Psych Sheet...")
    all_entries = []

    # Process all JSONs in scraped dir
    json_files = glob.glob(os.path.join(scraped_dir, "*.swimcloud.json"))
    for json_file in json_files:
        data = load_json(json_file)
        if "TCS" in json_file:
            # Use TCS data as SST for championship too? Or keep as TCS and create a copy?
            # Let's include TCS as TCS, and also duplicate it as SST for the sample so we have a Home Team.
            all_entries.extend(process_file(data))  # Add real TCS
            all_entries.extend(
                process_file(data, team_override="SST", name_override="Seton Swimming")
            )  # Add fake SST
        else:
            all_entries.extend(process_file(data))

    with open(
        os.path.join(sample_dir, "championship_psych_sheet_vcac.csv"), "w", newline=""
    ) as f:
        writer = csv.DictWriter(
            f, fieldnames=["swimmer", "team", "event", "time", "grade"]
        )
        writer.writeheader()
        writer.writerows(all_entries)

    print("Done!")


if __name__ == "__main__":
    main()
