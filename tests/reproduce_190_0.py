import asyncio
import os
import sys

import pandas as pd

# Ensure project root is in path
sys.path.insert(0, os.getcwd())

try:
    from swim_ai_reflex.backend.services.optimization_service import (
        optimization_service,
    )
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)


async def reproduce_glitch():
    print("--- Clearing Optimization Cache ---")
    optimization_service.clear_cache()

    # Mock data mimicking the issue
    seton_roster = pd.DataFrame(
        [
            {"swimmer": "Swimmer A", "event": "50 Free", "time": 25.0, "team": "Seton"},
            {"swimmer": "Swimmer B", "event": "50 Free", "time": 26.0, "team": "Seton"},
        ]
    )

    # Opponent data with a team name that might cause issues if not normalized
    opponent_roster = pd.DataFrame(
        [
            {
                "swimmer": "Opponent X",
                "event": "50 Free",
                "time": 24.5,
                "team": "Random High School",
            },  # Faster, should win
            {
                "swimmer": "Opponent Y",
                "event": "50 Free",
                "time": 25.5,
                "team": "Random High School",
            },
        ]
    )

    print("--- Running Optimization with 'Random High School' ---")
    try:
        result = await optimization_service.predict_best_lineups(
            seton_roster=seton_roster,
            opponent_roster=opponent_roster,
            method="heuristic",
            max_iters=10,
        )

        success = result.get("success", False)
        print(f"Success: {success}")

        if success:
            data = result.get("data", {})
            print(f"Data Keys: {data.keys()}")

            seton_score = data.get("seton_score")
            opp_score = data.get("opponent_score")

            print(f"Seton Score: {seton_score}")
            print(f"Opponent Score: {opp_score}")

            # Handle None scores for comparison
            s_score = seton_score if seton_score is not None else 0
            o_score = opp_score if opp_score is not None else 0

            if o_score == 0 and s_score > 0:
                print("✗ BUG REPRODUCED: Opponent score is 0 despite faster swimmers!")
            elif o_score > 0:
                print("✓ Bug not reproduced (Opponent scored points)")
            else:
                print(f"! Unexpected scores: Seton={s_score}, Opp={o_score}")
        else:
            error = result.get("error")
            print(f"✗ Optimization Failed with error: {error}")

    except Exception as e:
        print(f"✗ Exception during optimization: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(reproduce_glitch())
