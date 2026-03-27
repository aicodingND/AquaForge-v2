from typing import Any

import pandas as pd

from swim_ai_reflex.backend.core.rules import get_rules


def analyze_lineup(
    scored_lineup: list[dict[str, Any]], meet_type: str
) -> dict[str, Any]:
    """
    Analyzes a scored lineup to provide insights, swing events, and coach's notes.
    PERFORMANCE OPTIMIZED: Early returns, minimal DataFrame operations
    """
    # PERFORMANCE: Early return for empty data
    if not scored_lineup:
        return {}

    df = pd.DataFrame(scored_lineup)
    if df.empty or "team" not in df.columns:
        return {}

    rules = get_rules(meet_type)

    # Constants from rules
    FIRST_PLACE_PTS = rules.individual_points[0] if rules.individual_points else 0
    rules.individual_points[1] if len(rules.individual_points) > 1 else 0

    # Swing threshold: roughly the difference between 1st and 2nd place
    # e.g. 6-4=2. So 4 points swing is significant (1st<->3rd or 1st-2nd)
    SWING_THRESHOLD = 4

    insights = {
        "swing_events": [],
        "key_matchups": [],
        "coach_notes": [],
        "score_breakdown": {},
        "summary_text": "",
    }

    # 1. Score Breakdown by Event
    if "team" not in df.columns:
        return insights  # minimal valid

    event_scores = df.groupby(["event", "team"])["points"].sum().unstack(fill_value=0)
    for team in ["seton", "opponent"]:
        if team not in event_scores.columns:
            event_scores[team] = 0

    event_scores["diff"] = event_scores["seton"] - event_scores["opponent"]
    event_scores["abs_diff"] = event_scores["diff"].abs()

    # 2. Identify Swing Events
    swing_df = event_scores[event_scores["abs_diff"] <= SWING_THRESHOLD].sort_values(
        "abs_diff"
    )

    for event, row in swing_df.iterrows():
        insights["swing_events"].append(
            {
                "event": event,
                "seton_pts": int(row["seton"]),
                "opp_pts": int(row["opponent"]),
                "diff": int(row["diff"]),
                "status": "Winning"
                if row["diff"] > 0
                else "Losing"
                if row["diff"] < 0
                else "Tied",
            }
        )

    # 3. Key Matchups / Reasoning
    if "points" in df.columns:
        # "Heroes": Seton swimmers taking 1st place (>= 1st place pts)
        # Note: Relay points are higher, so this check works for both (8>6)
        first_place_wins = df[
            (df["team"] == "seton") & (df["points"] >= FIRST_PLACE_PTS)
        ]

        for _, row in first_place_wins.iterrows():
            metric = row.get("time", row.get("dive_score", ""))
            insights["coach_notes"].append(
                f"{row['swimmer']} is projected to WIN the {row['event']} ({metric}), securing {row['points']} points."
            )

    # Identify "Close Losses" (Seton 2nd place, behind Opponent 1st)
    if "points" in df.columns:
        for event in df["event"].unique():
            event_df = df[df["event"] == event]
            event_df = event_df.sort_values("points", ascending=False)

            if len(event_df) >= 2:
                top_2 = event_df.head(2).to_dict("records")
                winner = top_2[0]
                runner_up = top_2[1]

                if winner["team"] == "opponent" and runner_up["team"] == "seton":
                    desc = (
                        f"{runner_up['swimmer']} (Seton) vs {winner['swimmer']} (Opp)"
                    )
                    matchup_type = "Chasing 1st"

                    if "time" in runner_up and "time" in winner:
                        try:
                            t1 = float(winner["time"])
                            t2 = float(runner_up["time"])
                            if abs(t2 - t1) < 1.0:
                                matchup_type = "Close Race (< 1s)"
                        except (ValueError, TypeError):
                            pass

                    insights["key_matchups"].append(
                        {"event": event, "description": desc, "type": matchup_type}
                    )

    # 4. Summary
    total_seton = df[df["team"] == "seton"]["points"].sum()
    total_opp = df[df["team"] == "opponent"]["points"].sum()

    margin = abs(total_seton - total_opp)

    if total_seton > total_opp:
        insights["summary_text"] = (
            f"Seton is projected to WIN by {margin} points. "
            f"Key factors: {len(first_place_wins)} projected wins and performance in {len(insights['swing_events'])} swing events."
        )
    else:
        insights["summary_text"] = (
            f"Seton is trailing by {margin} points. "
            f"Focus on the {len(insights['swing_events'])} swing events to close the gap."
        )

    return insights
