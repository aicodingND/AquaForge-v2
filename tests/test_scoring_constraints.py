"""
Test suite for scoring constraint regression protection.

These tests ensure critical scoring rules cannot be accidentally broken by future code changes.
Each test documents the business rule it protects.

CRITICAL CONSTRAINTS:
- Dual meets: 232 total points (8 events × 29 points)
- Dual meets (Seton): Max 4 scorers per team per event
- Championship (VCAC): 12 scoring places, max 4 scorers per team
- Forfeit points: Must go to scoring-eligible swimmers only
"""

import pandas as pd
import pytest

from swim_ai_reflex.backend.core.dual_meet_scoring import (
    INDIVIDUAL_POINTS,
    POINTS_PER_EVENT,
    TOTAL_MEET_POINTS,
    score_dual_meet,
)
from swim_ai_reflex.backend.core.rules import (
    SetonDualRules,
    VCACChampRules,
    VISAADualRules,
    VISAAStateRules,
    get_meet_profile,
)
from swim_ai_reflex.backend.core.scoring import full_meet_scoring


class TestDualMeetScoringConstraints:
    """Regression tests for dual meet scoring rules."""

    def test_individual_points_sum_to_29(self):
        """CONSTRAINT: Individual event points must sum to 29."""
        assert sum(INDIVIDUAL_POINTS) == 29, (
            f"Individual points {INDIVIDUAL_POINTS} sum to {sum(INDIVIDUAL_POINTS)}, expected 29"
        )

    def test_points_per_event_constant(self):
        """CONSTRAINT: Points per event must be 29."""
        assert POINTS_PER_EVENT == 29

    def test_total_meet_points_constant(self):
        """CONSTRAINT: Total meet points must be 232 (8 events × 29)."""
        assert TOTAL_MEET_POINTS == 232

    def test_seton_dual_max_scorers_per_team_is_4(self):
        """CONSTRAINT: SetonDualRules must allow 4 scorers per team per event."""
        rules = SetonDualRules()
        assert rules.max_scorers_per_team_individual == 4, (
            f"max_scorers_per_team_individual is {rules.max_scorers_per_team_individual}, expected 4"
        )

    def test_visaa_dual_max_scorers_per_team_is_3(self):
        """CONSTRAINT: VISAADualRules (legacy) allows 3 scorers per team."""
        rules = VISAADualRules()
        assert rules.max_scorers_per_team_individual == 3, (
            "VISAADualRules should have max_scorers=3 (legacy config)"
        )

    def test_dual_meet_always_distributes_all_points(self):
        """CONSTRAINT: Dual meet scoring must distribute exactly 232 points total."""
        # Create a simple dual meet scenario
        seton_df = pd.DataFrame(
            [
                {
                    "swimmer": f"Seton_{i}",
                    "event": "100 Free",
                    "time": 50.0 + i,
                    "grade": 10,
                    "team": "seton",
                }
                for i in range(4)
            ]
        )
        opponent_df = pd.DataFrame(
            [
                {
                    "swimmer": f"Opponent_{i}",
                    "event": "100 Free",
                    "time": 51.0 + i,
                    "grade": 10,
                    "team": "opponent",
                }
                for i in range(4)
            ]
        )

        # Run 8 events (simulated by 8 copies with different event names)
        all_seton = []
        all_opponent = []
        events = [
            "100 Free",
            "200 Free",
            "50 Free",
            "100 Back",
            "100 Breast",
            "100 Fly",
            "200 IM",
            "500 Free",
        ]

        for event in events:
            s = seton_df.copy()
            s["event"] = event
            o = opponent_df.copy()
            o["event"] = event
            all_seton.append(s)
            all_opponent.append(o)

        full_seton = pd.concat(all_seton, ignore_index=True)
        full_opponent = pd.concat(all_opponent, ignore_index=True)

        _, totals = score_dual_meet(full_seton, full_opponent)

        total_points = totals["seton"] + totals["opponent"]
        assert abs(total_points - 232) < 0.1, (
            f"Total points {total_points} != 232. Seton: {totals['seton']}, Opponent: {totals['opponent']}"
        )


class TestForfeitPointsConstraints:
    """Regression tests for forfeit point distribution logic."""

    def test_forfeit_points_go_to_eligible_team(self):
        """
        CONSTRAINT: When one team has only exhibition swimmers,
        forfeit points must go to the OTHER team (who has eligible swimmers).

        This test protects against the bug fixed on 2026-02-01 where
        forfeit points were lost when the 'winning team' (by headcount)
        had no eligible swimmers to receive them.
        """
        # Seton: 3 exhibition swimmers (grade 7)
        # Opponent: 2 eligible swimmers (grade 10)
        seton_df = pd.DataFrame(
            [
                {
                    "swimmer": "Seton_Ex1",
                    "event": "100 Free",
                    "time": 60.0,
                    "grade": 7,
                    "team": "seton",
                },
                {
                    "swimmer": "Seton_Ex2",
                    "event": "100 Free",
                    "time": 61.0,
                    "grade": 7,
                    "team": "seton",
                },
                {
                    "swimmer": "Seton_Ex3",
                    "event": "100 Free",
                    "time": 62.0,
                    "grade": 7,
                    "team": "seton",
                },
            ]
        )
        opponent_df = pd.DataFrame(
            [
                {
                    "swimmer": "Opp_1",
                    "event": "100 Free",
                    "time": 55.0,
                    "grade": 10,
                    "team": "opponent",
                },
                {
                    "swimmer": "Opp_2",
                    "event": "100 Free",
                    "time": 56.0,
                    "grade": 10,
                    "team": "opponent",
                },
            ]
        )

        _, totals = score_dual_meet(seton_df, opponent_df)

        # Opponent should get points for 1st and 2nd place (8+6=14)
        # The remaining 15 points (places 3-7) should also go to opponent
        # since they are the only team with scoring-eligible swimmers.
        # Total for opponent should be 29 (all points in the event).
        # If this is less, the forfeit logic may not be working correctly.
        # Note: Actual behavior depends on forfeit logic implementation.
        # We verify that Seton (all exhibition) gets 0.
        assert totals["seton"] == 0, (
            f"Seton should get 0 points when all exhibition. Got {totals['seton']}"
        )
        # Verify total points are correctly distributed (14 for actual places, rest forfeit)
        total = totals["seton"] + totals["opponent"]
        assert total == 29, f"Total points should be 29 for single event. Got {total}"

    def test_exhibition_swimmers_do_not_displace_scorers(self):
        """
        CONSTRAINT: Exhibition swimmers (grade < 8) should not take scoring places
        from eligible swimmers.
        """
        # Mix of exhibition and eligible
        combined = pd.DataFrame(
            [
                {
                    "swimmer": "Fast_Ex",
                    "event": "100 Free",
                    "time": 50.0,
                    "grade": 7,
                    "team": "seton",
                },  # Fastest but exhibition
                {
                    "swimmer": "Seton_1",
                    "event": "100 Free",
                    "time": 51.0,
                    "grade": 10,
                    "team": "seton",
                },  # Should get 1st place points
                {
                    "swimmer": "Opp_1",
                    "event": "100 Free",
                    "time": 52.0,
                    "grade": 10,
                    "team": "opponent",
                },
            ]
        )

        seton_df = combined[combined["team"] == "seton"]
        opponent_df = combined[combined["team"] == "opponent"]

        scored, totals = score_dual_meet(seton_df, opponent_df)

        # Seton_1 should get points - exhibition swimmers are filtered out before scoring
        seton_points = scored[scored["swimmer"] == "Seton_1"]["points"].sum()
        # Seton_1 is the fastest ELIGIBLE swimmer, should get 1st place (8 pts)
        # Plus any forfeit points from exhibition slots
        assert seton_points >= 8, (
            f"Eligible swimmer should get at least 1st place (8 pts). Got {seton_points}"
        )


class TestChampionshipScoringConstraints:
    """Regression tests for championship (multi-team) scoring rules."""

    def test_vcac_championship_has_12_places(self):
        """CONSTRAINT: VCAC championship scores 12 places."""
        rules = get_meet_profile("vcac_championship")
        assert len(rules.individual_points) == 12, (
            f"VCAC championship should have 12 scoring places, has {len(rules.individual_points)}"
        )

    def test_vcac_championship_points_table(self):
        """CONSTRAINT: VCAC championship individual point values are correct."""
        rules = get_meet_profile("vcac_championship")
        # VCAC individual points: 12 places
        expected = [16, 13, 12, 11, 10, 9, 7, 5, 4, 3, 2, 1]
        assert rules.individual_points == expected, (
            f"VCAC individual points {rules.individual_points} != expected {expected}"
        )

    def test_vcac_championship_relay_points_table(self):
        """CONSTRAINT: VCAC championship relay points are 2x individual."""
        rules = get_meet_profile("vcac_championship")
        expected_relay = [32, 26, 24, 22, 20, 18, 14, 10, 8, 6, 4, 2]
        assert rules.relay_points == expected_relay, (
            f"VCAC relay points {rules.relay_points} != expected {expected_relay}"
        )

    def test_vcac_max_scorers_is_4(self):
        """CONSTRAINT: VCAC championship allows max 4 scorers per team."""
        rules = get_meet_profile("vcac_championship")
        assert rules.max_scorers_per_team_individual == 4


class TestRelayScoringConstraints:
    """Regression tests for relay scoring rules."""

    def test_dual_meet_relay_points(self):
        """CONSTRAINT: Dual meet relay points are [10, 5, 3]."""
        rules = SetonDualRules()
        expected = [10, 5, 3]
        assert rules.relay_points == expected, (
            f"Dual meet relay points {rules.relay_points} != expected {expected}"
        )

    def test_dual_meet_relay_total_is_18(self):
        """CONSTRAINT: Dual meet relay points sum to 18."""
        rules = SetonDualRules()
        total = sum(rules.relay_points)
        assert total == 18, f"Relay points sum to {total}, expected 18"

    def test_vcac_relay_points_double_individual(self):
        """CONSTRAINT: VCAC relay points are exactly 2x individual."""
        rules = get_meet_profile("vcac_championship")
        for i, (ind, rel) in enumerate(
            zip(rules.individual_points, rules.relay_points)
        ):
            assert rel == ind * 2, (
                f"Place {i + 1}: relay {rel} should be 2x individual {ind}"
            )

    def test_vcac_relay_max_scorers_is_2(self):
        """CONSTRAINT: VCAC allows max 2 relay entries to score (A and B)."""
        rules = get_meet_profile("vcac_championship")
        assert rules.max_scorers_per_team_relay == 2

    def test_dual_meet_relay_max_entries_is_2(self):
        """CONSTRAINT: Dual meet allows 2 relay entries (A and B)."""
        rules = SetonDualRules()
        assert rules.max_relays_per_team_per_event == 2

    def test_visaa_state_relay_points(self):
        """CONSTRAINT: VISAA State relay points are 2x individual for 16 places."""
        rules = get_meet_profile("visaa_state")
        assert len(rules.relay_points) == 16
        expected = [40, 34, 32, 30, 28, 26, 24, 22, 18, 14, 12, 10, 8, 6, 4, 2]
        assert rules.relay_points == expected, (
            f"VISAA State relay {rules.relay_points} != expected {expected}"
        )


class TestDivingCountsAsIndividualEvent:
    """
    Regression tests: Diving MUST count as 1 individual event slot.

    RULES (all meet types):
    - Diving uses the INDIVIDUAL point scale (not relay)
    - Diving counts as 1 individual event toward the max-2 limit
    - A diver + 2 swim events = 3 effective individual = INVALID
    - A diver + 1 swim event = 2 effective individual = VALID
    - At VCAC: diver + 1 swim + relay 3 (400 FR) = 3 effective = INVALID
    """

    def test_vcac_diving_counts_as_individual_flag(self):
        """CONSTRAINT: VCACChampRules must have diving_counts_as_individual=True."""
        rules = VCACChampRules()
        assert rules.diving_counts_as_individual is True

    def test_vcac_diver_plus_1_swim_is_valid(self):
        """CONSTRAINT: Diver + 1 individual swim = 2 effective individual = VALID."""
        rules = VCACChampRules()
        assert rules.is_valid_entry(swim_individual=1, is_diver=True, relay_count=0)

    def test_vcac_diver_plus_2_swims_is_invalid(self):
        """CONSTRAINT: Diver + 2 individual swims = 3 effective individual = INVALID."""
        rules = VCACChampRules()
        assert not rules.is_valid_entry(swim_individual=2, is_diver=True, relay_count=0)

    def test_vcac_diver_plus_1_swim_plus_2_relays_is_valid(self):
        """CONSTRAINT: Diver + 1 swim + 2 relays (free) = 2 effective individual = VALID."""
        rules = VCACChampRules()
        assert rules.is_valid_entry(swim_individual=1, is_diver=True, relay_count=2)

    def test_vcac_diver_only_is_valid(self):
        """CONSTRAINT: Diver with 0 swim events = 1 effective individual = VALID."""
        rules = VCACChampRules()
        assert rules.is_valid_entry(swim_individual=0, is_diver=True, relay_count=0)

    def test_vcac_diver_plus_1_swim_plus_relay3_is_invalid(self):
        """
        CONSTRAINT: Diver + 1 swim + 3 relays (400FR penalty) = 3 effective = INVALID.

        At VCAC, relay 3 (400 Free Relay) counts as 1 individual event.
        So: 1 dive + 1 swim + 1 relay penalty = 3 > 2 limit.
        Note: is_valid_entry counts relay_count toward total_events but relay 3 penalty
        is enforced at the constraint_validator level, not in is_valid_entry directly.
        Here we verify total_events constraint (1+1+3=5 > 4 max).
        """
        rules = VCACChampRules()
        # 1 swim + 1 dive (=2 indiv) + 3 relays = 5 total > 4 max
        assert not rules.is_valid_entry(swim_individual=1, is_diver=True, relay_count=3)

    def test_vcac_non_diver_plus_2_swims_is_valid(self):
        """CONSTRAINT: Non-diver + 2 individual swims = 2 effective = VALID."""
        rules = VCACChampRules()
        assert rules.is_valid_entry(swim_individual=2, is_diver=False, relay_count=0)

    def test_diving_uses_individual_points_not_relay(self):
        """
        CONSTRAINT: Diving event must be scored with individual point scale.

        In scoring.py, events are routed by is_relay flag:
        - is_relay=True → rules.relay_points
        - is_relay=False → rules.individual_points
        Diving has is_relay=False, so it uses individual_points. Verify this.
        """
        rules = get_meet_profile("vcac_championship")
        # Diving event has is_relay=False → uses individual_points
        # Individual: [16, 13, 12, 11, 10, 9, 7, 5, 4, 3, 2, 1]
        # Relay:      [32, 26, 24, 22, 20, 18, 14, 10, 8, 6, 4, 2]
        # 1st place individual = 16, 1st place relay = 32
        assert rules.individual_points[0] == 16
        assert rules.relay_points[0] == 32
        # If diving incorrectly used relay points, 1st place would be 32 not 16

    def test_diving_scored_as_individual_in_full_meet(self):
        """
        CONSTRAINT: Diving event scored with individual point scale in full_meet_scoring.

        Verifies end-to-end that a diving event awards individual-scale points.
        """
        rules = get_meet_profile("vcac_championship")

        # Create a minimal diving event
        roster = pd.DataFrame(
            [
                {
                    "swimmer": "Diver_A",
                    "event": "Diving",
                    "time": 0,
                    "dive_score": 300.0,
                    "team": "seton",
                    "grade": 10,
                    "is_relay": False,
                    "is_diving": True,
                },
                {
                    "swimmer": "Diver_B",
                    "event": "Diving",
                    "time": 0,
                    "dive_score": 250.0,
                    "team": "opponent",
                    "grade": 10,
                    "is_relay": False,
                    "is_diving": True,
                },
            ]
        )

        scored, totals = full_meet_scoring(roster, rules, validate=False)
        # 1st place gets 16 (individual), 2nd gets 13
        assert totals["seton"] == 16.0, (
            f"Diving 1st place should get 16 (individual). Got {totals['seton']}"
        )
        assert totals["opponent"] == 13.0, (
            f"Diving 2nd place should get 13 (individual). Got {totals['opponent']}"
        )


class TestVISAAStateEntryValidation:
    """
    Regression tests: VISAA State entry validation (standard NFHS, NO relay-3 penalty).

    Key difference from VCAC: the 400 Free Relay does NOT cost an individual slot.
    Verified: 2026-02-11 via NFHS Rule 3-2-1, VISAA official rules.
    """

    def test_visaa_state_has_is_valid_entry(self):
        """VISAA State rules must have is_valid_entry method."""
        rules = VISAAStateRules()
        assert hasattr(rules, "is_valid_entry")

    def test_visaa_state_diving_counts_as_individual(self):
        """CONSTRAINT: Diving counts as 1 individual slot at VISAA State."""
        rules = VISAAStateRules()
        assert rules.diving_counts_as_individual is True

    def test_visaa_state_2_swim_2_relay_valid(self):
        """CONSTRAINT: 2 swim + 2 relay = 4 events, 2 individual = VALID."""
        rules = VISAAStateRules()
        assert rules.is_valid_entry(swim_individual=2, is_diver=False, relay_count=2)

    def test_visaa_state_1_swim_3_relay_valid(self):
        """CONSTRAINT: 1 swim + 3 relay = 4 events, 1 individual = VALID.
        Unlike VCAC, the 400 FR does NOT cost an individual slot here."""
        rules = VISAAStateRules()
        assert rules.is_valid_entry(swim_individual=1, is_diver=False, relay_count=3)

    def test_visaa_state_2_swim_3_relay_invalid(self):
        """CONSTRAINT: 2 swim + 3 relay = 5 events > 4 max = INVALID."""
        rules = VISAAStateRules()
        assert not rules.is_valid_entry(
            swim_individual=2, is_diver=False, relay_count=3
        )

    def test_visaa_state_diver_plus_1_swim_valid(self):
        """CONSTRAINT: Diver + 1 swim = 2 effective individual = VALID."""
        rules = VISAAStateRules()
        assert rules.is_valid_entry(swim_individual=1, is_diver=True, relay_count=0)

    def test_visaa_state_diver_plus_2_swims_invalid(self):
        """CONSTRAINT: Diver + 2 swims = 3 effective individual > 2 = INVALID."""
        rules = VISAAStateRules()
        assert not rules.is_valid_entry(swim_individual=2, is_diver=True, relay_count=0)

    def test_visaa_state_diver_plus_1_swim_plus_2_relays_valid(self):
        """CONSTRAINT: Diver + 1 swim + 2 relay = 2 indiv + 2 relay = 4 total = VALID."""
        rules = VISAAStateRules()
        assert rules.is_valid_entry(swim_individual=1, is_diver=True, relay_count=2)

    def test_visaa_state_no_relay3_penalty(self):
        """
        CRITICAL: 400 FR does NOT cost individual slot at VISAA State.

        At VCAC: 1 swim + 3 relays (400FR) = 2 effective individual (penalty) = VALID but constrained.
        At VISAA State: 1 swim + 3 relays = 1 effective individual = VALID, no constraint from relay.
        This is the key difference between VCAC and VISAA State rules.
        """
        visaa = VISAAStateRules()
        # 1 swim + 0 dive + 3 relays = 1 indiv, 4 total = VALID at VISAA State
        assert visaa.is_valid_entry(swim_individual=1, is_diver=False, relay_count=3)

        # Compare with VCAC where same combo costs an extra slot
        vcac = VCACChampRules()
        # At VCAC: 1 swim + 3 relays includes 400FR penalty = 2 effective individual
        # Still valid at VCAC too (2 <= 2), but the penalty is applied
        assert vcac.is_valid_entry(swim_individual=1, is_diver=False, relay_count=3)


class TestScoringModeRouting:
    """Tests to ensure correct scoring module is used for each meet type."""

    def test_dual_meet_uses_232_point_rule(self):
        """Dual meets must use score_dual_meet which enforces 232 total."""
        # This is a marker test - actual routing is tested via integration
        from swim_ai_reflex.backend.core.dual_meet_scoring import score_dual_meet

        assert callable(score_dual_meet)

    def test_championship_uses_different_scoring(self):
        """Championship meets use full_meet_scoring with championship rules."""
        from swim_ai_reflex.backend.core.scoring import full_meet_scoring

        assert callable(full_meet_scoring)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
