import pandas as pd

from swim_ai_reflex.backend.core.monte_carlo import fast_monte_carlo_simulation


def test_fast_monte_carlo_basic():
    # Mock Data
    seton_data = [
        {
            "swimmer": "A. Swimmer",
            "event": "Boys 50 Free",
            "time": 25.00,
            "team": "Seton School",
            "is_relay": False,
        },
        {
            "swimmer": "B. Swimmer",
            "event": "Boys 50 Free",
            "time": 26.00,
            "team": "Seton School",
            "is_relay": False,
        },
    ]
    opponent_data = [
        {
            "swimmer": "X. Rival",
            "event": "Boys 50 Free",
            "time": 24.50,
            "team": "Trinity",
            "is_relay": False,
        },
        {
            "swimmer": "Y. Rival",
            "event": "Boys 50 Free",
            "time": 25.50,
            "team": "Trinity",
            "is_relay": False,
        },
    ]

    seton_df = pd.DataFrame(seton_data)
    opponent_df = pd.DataFrame(opponent_data)

    results = fast_monte_carlo_simulation(seton_df, opponent_df, trials=100)

    assert results is not None
    assert "seton_mean" in results
    assert "seton_win_prob" in results

    print("\nMonte Carlo Results:", results)


if __name__ == "__main__":
    test_fast_monte_carlo_basic()
