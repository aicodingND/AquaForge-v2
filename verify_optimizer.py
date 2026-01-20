
import asyncio
import pandas as pd
from swim_ai_reflex.backend.services.optimization_service import optimization_service

async def verify():
    print("Verifying OptimizationService with Factory...")
    
    # Dummy Roster Data
    seton_data = [
        {'swimmer': 'Swimmer A', 'event': '50 Free', 'time': 25.0, 'team': 'Seton', 'is_relay': False},
        {'swimmer': 'Swimmer B', 'event': '100 Free', 'time': 55.0, 'team': 'Seton', 'is_relay': False}
    ]
    seton_df = pd.DataFrame(seton_data)
    
    opp_data = [
        {'swimmer': 'Opponent X', 'event': '50 Free', 'time': 24.5, 'team': 'Opponent', 'is_relay': False},
        {'swimmer': 'Opponent Y', 'event': '100 Free', 'time': 54.0, 'team': 'Opponent', 'is_relay': False}
    ]
    opp_df = pd.DataFrame(opp_data)
    
    # Test Heuristic
    print("Testing 'heuristic' strategy...")
    result = await optimization_service.predict_best_lineups(
        seton_roster=seton_df,
        opponent_roster=opp_df,
        method="heuristic",
        max_iters=10
    )
    
    if result.get("success"):
        print("✅ Heuristic optimization successful!")
        print(f"Seton Score: {result['data']['seton_score']}")
    else:
        print(f"❌ Heuristic optimization failed: {result}")

    # Test Gurobi (Expect failure or success depending on install, but should handle gracefully)
    print("\nTesting 'gurobi' strategy (checking graceful handling)...")
    result_g = await optimization_service.predict_best_lineups(
        seton_roster=seton_df,
        opponent_roster=opp_df,
        method="gurobi",
        max_iters=10
    )
    
    if result_g.get("success"):
        print("✅ Gurobi optimization successful (Gurobi is installed!)")
    else:
        # It might fail if Gurobi not installed, which is expected behavior for now
        print(f"ℹ️ Gurobi result: {result_g.get('message')} (Error: {result_g.get('error')})")
        
    print("\nVerification Complete.")

if __name__ == "__main__":
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(verify())
    except Exception as e:
        print(f"❌ Script failed: {e}")
