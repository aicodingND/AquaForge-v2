import os
import sys

import pandas as pd

# Add project root to path
sys.path.insert(0, os.getcwd())

from swim_ai_reflex.backend.core.opponent_model import greedy_opponent_best_lineup


def test_greedy_opponent():
    print("Testing greedy_opponent_best_lineup...")

    # Mock opponent roster
    data = {
        "swimmer": ["Swimmer A", "Swimmer A", "Swimmer B", "Swimmer B"],
        "event": ["50 Free", "100 Free", "50 Free", "100 Back"],
        "time": [25.0, 55.0, 26.0, 60.0],
        "team": ["Opponent", "Opponent", "Opponent", "Opponent"],
    }
    roster = pd.DataFrame(data)

    print("Input Roster:")
    print(roster)

    try:
        lineup = greedy_opponent_best_lineup(roster)
        print("\nGenerated Lineup:")
        print(lineup)

        if lineup.empty:
            print("\nFAIL: Lineup is empty!")
        else:
            print(f"\nSUCCESS: Lineup has {len(lineup)} entries.")

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_greedy_opponent()
