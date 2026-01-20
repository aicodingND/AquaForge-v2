import requests

# Configure base URL
BASE_URL = "http://localhost:8000/api/v1"


def debug_optimization():
    print(f"Testing Optimization API at {BASE_URL}/optimize...")

    # Create sample payload with grades
    payload = {
        "scoring_type": "legal_dual_meet",
        "optimizer_backend": "heuristic",
        "robust_mode": False,
        "enforce_fatigue": False,
        "seton_data": [
            {"swimmer": "S1", "event": "50 Free", "time": "24.50", "grade": "11"},
            {"swimmer": "S2", "event": "100 Free", "time": "54.00", "grade": "10"},
            {"swimmer": "S3", "event": "100 Back", "time": "1:02.00", "grade": "12"},
            {"swimmer": "S4", "event": "100 Breast", "time": "1:10.00", "grade": "9"},
            {"swimmer": "S5", "event": "100 Fly", "time": "58.00", "grade": "11"},
            {"swimmer": "S6", "event": "200 Free", "time": "2:00.00", "grade": "10"},
            {"swimmer": "S7", "event": "200 IM", "time": "2:15.00", "grade": "12"},
            {"swimmer": "S8", "event": "500 Free", "time": "5:30.00", "grade": "9"},
        ],
        "opponent_data": [
            {
                "swimmer": "O1",
                "event": "50 Free",
                "time": "25.00",
                "team": "Opponent",
                "grade": "11",
            },
            {
                "swimmer": "O2",
                "event": "100 Free",
                "time": "55.00",
                "team": "Opponent",
                "grade": "10",
            },
            {
                "swimmer": "O3",
                "event": "100 Back",
                "time": "1:03.00",
                "team": "Opponent",
                "grade": "9",
            },
            {
                "swimmer": "O4",
                "event": "100 Breast",
                "time": "1:11.00",
                "team": "Opponent",
                "grade": "12",
            },
            {
                "swimmer": "O5",
                "event": "100 Fly",
                "time": "59.00",
                "team": "Opponent",
                "grade": "11",
            },
            {
                "swimmer": "O6",
                "event": "200 Free",
                "time": "2:01.00",
                "team": "Opponent",
                "grade": "10",
            },
            {
                "swimmer": "O7",
                "event": "200 IM",
                "time": "2:16.00",
                "team": "Opponent",
                "grade": "9",
            },
            {
                "swimmer": "O8",
                "event": "500 Free",
                "time": "5:31.00",
                "team": "Opponent",
                "grade": "12",
            },
        ],
    }

    try:
        response = requests.post(f"{BASE_URL}/optimize", json=payload)
        print(f"Status: {response.status_code}")

        if response.ok:
            data = response.json()
            print(f"Success: {data.get('success')}")
            print(
                f"Total Score: Seton {data.get('seton_score')} - Opponent {data.get('opponent_score')}"
            )

            results = data.get("results", [])
            print(f"\nEvent Results ({len(results)} events):")
            for res in results:
                evt = res.get("event")
                # Check for event specific scores
                proj = res.get("projected_score", {})
                seton_pts = sum(res.get("seton_points", []))
                opp_pts = sum(res.get("opponent_points", []))

                print(f"Event: {evt}")
                print(
                    f"  Projected Score: Seton {proj.get('seton')} - Opponent {proj.get('opponent')}"
                )
                print(f"  Calculated Points: Seton {seton_pts} - Opponent {opp_pts}")

        else:
            print(f"Error: {response.text}")

    except Exception as e:
        print(f"Exception: {e}")


if __name__ == "__main__":
    debug_optimization()
