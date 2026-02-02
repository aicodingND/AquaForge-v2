import pandas as pd

from swim_ai_reflex.backend.core.rules import VISAADualRules
from swim_ai_reflex.backend.core.scoring import (
    full_meet_scoring,
    score_event_with_rules,
)


class TestScoring:
    def test_score_event_mixed_case_teams(self):
        """Test that scoring correctly normalizes team names when counting limit."""
        # Scenario: 4 Seton swimmers. Limit is 3. 4th should get 0 points.
        # But team names are messy.
        df = pd.DataFrame(
            [
                {
                    "swimmer": "A",
                    "time": 20.0,
                    "team": "Seton",
                    "is_relay": False,
                    "is_diving": False,
                },  # 1st, 6 pts
                {
                    "swimmer": "B",
                    "time": 21.0,
                    "team": "SETON",
                    "is_relay": False,
                    "is_diving": False,
                },  # 2nd, 4 pts
                {
                    "swimmer": "C",
                    "time": 22.0,
                    "team": "Seton ",
                    "is_relay": False,
                    "is_diving": False,
                },  # 3rd, 3 pts
                {
                    "swimmer": "D",
                    "time": 23.0,
                    "team": "seton",
                    "is_relay": False,
                    "is_diving": False,
                },  # 4th, 2 pts -> 0 pts (Max 3)
                {
                    "swimmer": "E",
                    "time": 24.0,
                    "team": "Opponent",
                    "is_relay": False,
                    "is_diving": False,
                },  # 5th, 1 pt
            ]
        )

        rules = VISAADualRules()
        scored = score_event_with_rules(df, rules)

        # Verify A, B, C got points (Rules: 8, 6, 5, 4...)
        assert scored.iloc[0]["points"] == 8.0  # 1st
        assert scored.iloc[1]["points"] == 6.0  # 2nd
        assert scored.iloc[2]["points"] == 5.0  # 3rd

        # Verify D (4th Seton) got 0 points despite being 4th place (normally 4 pts)
        # If normalization works, D counts as 4th 'seton' swimmer -> >3 limit -> 0 pts.
        assert scored.iloc[3]["points"] == 0.0

        # Verify E (Opponent) gets points (5th place = 4 pts? No, 5th is usually 3 or 2 pts?)
        # 8, 6, 5, 4, 3, 2, 1
        # A(1), B(2), C(3), D(4but0), E(5).
        # Places are assigned 1..5.
        # D is place 4. Points[3] = 4. But Seton limit reached.
        # E is place 5. Points[4] = 3.
        assert scored.iloc[4]["points"] == 3.0

    def test_full_meet_scoring_totals(self):
        # Full meet test with messy names
        df = pd.DataFrame(
            [
                {
                    "event": "50 Free",
                    "swimmer": "A",
                    "time": 20.0,
                    "team": "Seton",
                    "is_relay": False,
                    "is_diving": False,
                },
                {
                    "event": "50 Free",
                    "swimmer": "B",
                    "time": 21.0,
                    "team": "Opponent",
                    "is_relay": False,
                    "is_diving": False,
                },
            ]
        )

        scored, totals = full_meet_scoring(df)
        assert totals["seton"] == 8.0
        assert totals["opponent"] == 6.0
