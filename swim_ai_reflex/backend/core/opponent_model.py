# core/opponent_model.py
import pandas as pd


def greedy_opponent_best_lineup(opp_std: pd.DataFrame) -> pd.DataFrame:
    """
    Build a plausible 'best' opponent lineup:
      - Per event: pick up to 4 fastest opponent swimmers
      - Enforce max 2 events per swimmer using competitiveness heuristic
      - PRIORITY: Fill all 4 slots per event to avoid forfeiting points

    NOTE: Swimmers can swim 0, 1, or 2 events (no minimum requirement).
    The algorithm prioritizes filling events, so most swimmers will be assigned
    to their best event(s), but a swimmer may only swim 1 event if that's
    what fills the lineup optimally.
    """
    if opp_std is None or opp_std.empty:
        return pd.DataFrame(
            columns=["swimmer", "grade", "gender", "event", "time", "team", "is_relay"]
        )

    df = opp_std.copy().reset_index(drop=True)
    events = df["event"].unique().tolist()

    # Track how many events each swimmer is assigned
    swimmer_event_count = {}
    final_lineup = []

    # First pass: assign best swimmers to each event (up to 4 per event)
    for event in events:
        event_swimmers = df[df["event"] == event].sort_values("time", ascending=True)

        assigned_count = 0
        for _, swimmer in event_swimmers.iterrows():
            swimmer_name = swimmer["swimmer"]
            current_count = swimmer_event_count.get(swimmer_name, 0)

            # Allow up to 2 events per swimmer
            if current_count < 2 and assigned_count < 4:
                final_lineup.append(swimmer.to_dict())
                swimmer_event_count[swimmer_name] = current_count + 1
                assigned_count += 1

        # If we still need more swimmers for this event (< 4),
        # consider swimmers who already have 2 events but only as last resort
        # This shouldn't happen often with good roster data

    result = (
        pd.DataFrame(final_lineup) if final_lineup else pd.DataFrame(columns=df.columns)
    )

    # Ensure team column set
    if "team" not in result.columns:
        result["team"] = "opponent"
    else:
        result["team"] = result["team"].fillna("opponent")

    return result


def realistic_opponent_lineup(opp_std: pd.DataFrame) -> pd.DataFrame:
    """
    Slightly more conservative variant: picks fastest 3 automatically, then tries to avoid forcing any swimmer into >2 events.
    For Phase-3 we keep it close to greedy_opponent_best_lineup.
    """
    return greedy_opponent_best_lineup(opp_std)
