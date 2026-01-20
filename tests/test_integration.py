import sys
import os
import pandas as pd
import asyncio

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from swim_ai_reflex.backend.services.optimization_service import (
        optimization_service,
    )

    print("[TEST] Imports successful.")
except ImportError as e:
    print(f"[TEST] Import Error: {e}")
    sys.exit(1)


async def test_full_flow():
    print("\n--- Starting Deep Walkthrough Integration Test ---")

    # 1. Simulate Parsing Result (Data Ingestion)
    print("\n[Step 1] Simulating Data Ingestion (Parse Hytek PDF)...")
    # Real data shape from hytek parser: ['swimmer', 'grade', 'gender', 'event', 'time', 'team', 'is_relay']

    seton_data = [
        {
            "swimmer": "Joe Swimmer",
            "grade": 11,
            "gender": "M",
            "event": "Boys 50 Free",
            "time": 24.5,
            "team": "Seton",
            "is_relay": False,
        },
        {
            "swimmer": "Joe Swimmer",
            "grade": 11,
            "gender": "M",
            "event": "Boys 100 Free",
            "time": 54.5,
            "team": "Seton",
            "is_relay": False,
        },
        {
            "swimmer": "Fast Freshman",
            "grade": 9,
            "gender": "M",
            "event": "Boys 50 Free",
            "time": 25.5,
            "team": "Seton",
            "is_relay": False,
        },
        {
            "swimmer": "Diver Dan",
            "grade": 10,
            "gender": "M",
            "event": "Boys 1 Meter Diving",
            "time": 0.0,
            "dive_score": 150.0,
            "team": "Seton",
            "is_relay": False,
            "is_diving": True,
        },
    ]

    opponent_data = [
        {
            "swimmer": "Rival Rob",
            "grade": 10,
            "gender": "M",
            "event": "Boys 50 Free",
            "time": 24.0,
            "team": "Opponent",
            "is_relay": False,
        },
    ]

    seton_df = pd.DataFrame(seton_data)
    opponent_df = pd.DataFrame(opponent_data)
    print(
        f"[TEST] Loaded {len(seton_df)} Seton entries and {len(opponent_df)} Opponent entries."
    )

    # 2. Test Heuristic Optimization
    print("\n[Step 2] Testing Heuristic Strategy Generation...")
    result_heuristic = await optimization_service.predict_best_lineups(
        seton_df, opponent_df, method="heuristic", max_iters=100
    )

    if not result_heuristic.get("success", False):
        print(
            f"[FAIL] Heuristic Service Error: {result_heuristic.get('message')} - {result_heuristic.get('error')}"
        )
    else:
        data = result_heuristic["data"]
        print(
            f"[SUCCESS] Heuristic Result: Seton {data['seton_score']} - Opp {data['opponent_score']}"
        )
        print(f"Details: {len(data['details'])} assignments made.")

    # 3. Test Gurobi Optimization (Mock check if license fails gracefully or works)
    print("\n[Step 3] Testing Gurobi Engine Connection...")
    # This might fail if no license, but we want to see it handle the error gracefully or succeed.
    result_gurobi = await optimization_service.predict_best_lineups(
        seton_df, opponent_df, method="gurobi"
    )

    if not result_gurobi.get("success", False):
        print(
            f"[INFO] Gurobi Engine State: {result_gurobi.get('message')} - {result_gurobi.get('error')}"
        )
        # This is acceptable if license is missing, but ensuring it doesn't crash the app
    else:
        data = result_gurobi["data"]
        print(
            f"[SUCCESS] Gurobi Result: Seton {data['seton_score']} - Opp {data['opponent_score']}"
        )

    print("\n--- Walkthrough Complete ---")


if __name__ == "__main__":
    asyncio.run(test_full_flow())
