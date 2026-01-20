import unittest

from swim_ai_reflex.backend.core.strategies.championship_strategy import (
    ChampionshipEntry,
    ChampionshipGurobiStrategy,
)


class TestRelayConstraints(unittest.TestCase):
    def test_relay_blocks_individual(self):
        """Test that being on 400 Free Relay blocks 100 Breast."""
        strategy = ChampionshipGurobiStrategy("vcac_championship")

        # Swimmer A is fast at 100 Breast (would normally be picked)
        entries = [
            ChampionshipEntry(
                swimmer_name="Swimmer A",
                team="Seton",
                event="100 Breast",
                seed_time=60.0,  # Very fast
            ),
            ChampionshipEntry(
                swimmer_name="Swimmer A",
                team="Seton",
                event="50 Free",
                seed_time=25.0,  # Decent
            ),
        ]

        # CASE 1: No relay assignment -> Should swim 100 Breast
        result1 = strategy.optimize_entries(
            all_entries=entries,
            target_team="Seton",
            relay_3_swimmers=set(),  # Not on relay
        )
        assigned1 = result1.assignments.get("Swimmer A", [])
        self.assertIn("100 Breast", assigned1, "Should swim 100 Breast when free")

        # CASE 2: On 400 Free Relay -> Should NOT swim 100 Breast (Back-to-back)
        result2 = strategy.optimize_entries(
            all_entries=entries,
            target_team="Seton",
            relay_3_swimmers={"Swimmer A"},  # On relay
        )
        assigned2 = result2.assignments.get("Swimmer A", [])
        self.assertNotIn(
            "100 Breast", assigned2, "Should NOT swim 100 Breast when on 400 Free Relay"
        )
        self.assertIn("50 Free", assigned2, "Should still swim 50 Free")

        print("\nTest passed: Relay constraints enforced correctly.")


if __name__ == "__main__":
    unittest.main()
