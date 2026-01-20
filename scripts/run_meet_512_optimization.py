import os
import sys
import time

import pandas as pd

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from swim_ai_reflex.backend.core.strategies.aqua_optimizer import AquaOptimizer

DATA_DIR = "/Users/mpage1/Desktop/AquaForge/AquaForge_v1.0.0-next_2026-01-10/data/backtest/meet_512"


def load_roster_as_long_format(filename):
    df = pd.read_csv(os.path.join(DATA_DIR, filename))
    # Melt from Wide to Long
    # ID cols: name, gender, id
    # Value vars: events
    id_vars = ["name", "gender", "id"]
    value_vars = [c for c in df.columns if c not in id_vars]

    long_df = df.melt(
        id_vars=id_vars, value_vars=value_vars, var_name="event", value_name="time"
    )
    # Filter out NaNs (swimmer doesn't swim that event)
    long_df = long_df.dropna(subset=["time"])

    # Rename cols to match AquaOptimizer expectations
    # Expects: 'swimmer', 'event', 'time' (maybe 'id'?)
    # Let's check AquaOptimizer expectation.
    # It uses row["swimmer"] in the loop I saw.
    # Let's map 'name' -> 'swimmer', 'id' -> 'swimmer_id' just in case.
    long_df["swimmer"] = long_df[
        "name"
    ]  # Using name as ID for consistency in logs, but id is safer
    # Actually, let's use ID if we can, but visual logs need names.
    # For now, let's assume 'swimmer' column is the identifier.

    return long_df


def calculate_actual_score(results_df, events):
    # Simple scoring: 6-4-3-2-1 for individual events? Or dual meet scoring?
    # VCAC Regular Season Championship might be multi-team.
    # If standard dual, 6-4-3-2-1. Relay 8-4-2.
    # But wait, results_df has strictly INDIVIDUAL times in the CSV I generated?
    # The actual_results CSV I generated has specific events.
    # Let's assume standard dual meet scoring for this specific backtest vs 1 opponent?
    # Or is it a multi-team meet?
    # Opponent IDs: [ 30 199 158  48  29] -> Multi-team!
    # AquaOptimizer currently optimizes for DUAL meets (Seton vs Opponent).
    # If this is a championship, we need "Championship Mode".
    # The Task says "VCAC Regular Season Championship".
    # If I run standard AquaOptimizer, it optimizes as a Dual Meet.
    # This comparison might be flawed if I treat it as a Dual Meet vs ALL.
    # But usually, we optimize to maximize points.

    # For now, let's just run the optimizer and seeing what it produces.
    # We can refine scoring later.
    pass


def main():
    print("Preparing Meet 512 Backtest...")

    # 1. Load Data
    seton_df = load_roster_as_long_format("seton_roster_512.csv")
    opponent_df = load_roster_as_long_format("opponent_roster_512.csv")

    print(f"Seton Swims: {len(seton_df)}")
    print(f"Opponent Swims: {len(opponent_df)}")

    events = [
        "50 Free",
        "100 Free",
        "200 Free",
        "500 Free",
        "100 Back",
        "100 Breast",
        "100 Fly",
        "200 IM",
    ]

    # 2. Init Optimizer
    # Fast mode for quick check
    optimizer = AquaOptimizer(quality_mode="fast", use_parallel=False)

    # 3. Optimize
    print("Starting Optimization...")
    start_time = time.time()
    # Pass None for scoring_fn and rules as they are instantiated internally
    best_df, scored_df, totals, details = optimizer.optimize(
        seton_df, opponent_df, None, None
    )
    duration = time.time() - start_time

    print(f"Optimization Completed in {duration:.2f}s")

    seton_score = totals.get("seton_score", 0)
    opponent_score = totals.get("opponent_score", 0)
    print(f"Projected Score: Seton {seton_score} - {opponent_score} Opponent")

    # 4. Print Lineup (Top few assignments)
    print("\nOptimization Assignments:")
    if best_df.empty:
        print("WARNING: Optimized lineup is empty!")
    else:
        for event in events:
            print(f"--- {event} ---")
            event_entries = best_df[best_df["event"] == event]
            if event_entries.empty:
                print("  (No entries)")
            else:
                for _, row in event_entries.iterrows():
                    print(f"  {row['swimmer']} ({row['time']})")

    # Save to CSV for inspection
    best_df.to_csv("optimized_results.csv", index=False)
    print("\nSaved optimized lineup to optimized_results.csv")


if __name__ == "__main__":
    main()
