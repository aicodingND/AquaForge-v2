from typing import Any, Dict, Tuple

import pandas as pd

from swim_ai_reflex.backend.core.optimizer_utils import validate_lineup_constraints


def ensure_full_lineup(
    optimized_lineup: pd.DataFrame, full_roster: pd.DataFrame, rules: Any
) -> Tuple[pd.DataFrame, Dict]:
    lineup = optimized_lineup.copy()
    max_per_event = rules.max_entries_per_team_per_event
    team = lineup["team"].iloc[0] if len(lineup) > 0 else "unknown"

    suggestions = {}  # Track events needing manual selection

    events = lineup["event"].unique()

    for event in events:
        event_lineup = lineup[lineup["event"] == event]
        current_count = len(event_lineup)

        if current_count >= max_per_event:
            continue

        needed = max_per_event - current_count
        swimmers_in_event = set(event_lineup["swimmer"].unique())

        # Get eligible swimmers from roster
        event_roster = full_roster[
            (full_roster["event"] == event) & (~full_roster["is_relay"])
        ].copy()
        event_roster = event_roster.sort_values("time", ascending=True)

        # Try to add swimmers within constraints
        added = 0
        for idx, row in event_roster.iterrows():
            if added >= needed:
                break

            swimmer = row["swimmer"]
            if swimmer in swimmers_in_event:
                continue

            test_lineup = pd.concat([lineup, pd.DataFrame([row])], ignore_index=True)
            is_valid, _ = validate_lineup_constraints(
                test_lineup, rules, min_grade=None
            )

            if is_valid:
                lineup = test_lineup
                swimmers_in_event.add(swimmer)
                added += 1

        # If still short, handle based on team
        if added < needed:
            remaining = needed - added

            if team == "seton":
                # For Seton: provide suggestions for coach to choose
                # Get swimmers who would violate constraints (sorted by time)
                potential_swimmers = []

                for idx, row in event_roster.iterrows():
                    swimmer = row["swimmer"]
                    if swimmer in swimmers_in_event:
                        continue

                    # Check what constraint would be violated
                    test_lineup = pd.concat(
                        [lineup, pd.DataFrame([row])], ignore_index=True
                    )
                    is_valid, violations = validate_lineup_constraints(
                        test_lineup, rules, min_grade=None
                    )

                    if not is_valid:
                        # This swimmer would violate constraints
                        potential_swimmers.append(
                            {
                                "swimmer": swimmer,
                                "time": row["time"],
                                "grade": row.get("grade", "?"),
                                "violations": violations,
                            }
                        )

                    if len(potential_swimmers) >= 5:  # Show top 5 suggestions
                        break

                suggestions[event] = {
                    "needed": remaining,
                    "suggestions": potential_swimmers[:5],
                }

            else:
                # For opponent: add FORFEIT placeholders
                for i in range(remaining):
                    forfeit_entry = {
                        "swimmer": "FORFEIT",
                        "event": event,
                        "time": float("inf"),
                        "grade": None,
                        "is_relay": False,
                        "is_diving": False,
                        "dive_score": None,
                        "team": team,
                        "gender": None,
                    }
                    lineup = pd.concat(
                        [lineup, pd.DataFrame([forfeit_entry])], ignore_index=True
                    )

    return lineup.reset_index(drop=True), suggestions
