"""
Tests for meet-type-specific constraint enforcement in AquaOptimizer.

Validates that ScoringProfile.from_rules() and ConstraintEngine correctly
enforce different rules for VCAC vs VISAA vs dual meets, including:
- relay_3_counts_as_individual (VCAC only)
- diving_counts_as_individual (both championships)
- max_entries_per_event (4 dual, 999 championship)
- scoring table accuracy
"""

import pandas as pd
import pytest

from swim_ai_reflex.backend.core.rules import (
    SetonDualRules,
    VCACChampRules,
    VISAAStateRules,
)
from swim_ai_reflex.backend.core.strategies.aqua_optimizer import (
    ConstraintEngine,
    Lineup,
    ScoringProfile,
)

# ─── ScoringProfile.from_rules() tests ────────────────────────────────


class TestScoringProfileFromRules:
    """Verify from_rules() correctly populates all fields from MeetRules."""

    def test_vcac_from_rules_matches_canonical(self):
        """VCAC profile from rules matches canonical MeetRules values."""
        rules = VCACChampRules()
        profile = ScoringProfile.from_rules(rules)

        assert profile.individual_points == rules.individual_points
        assert profile.relay_points == rules.relay_points
        assert profile.max_scorers_per_team == rules.max_scorers_per_team_individual
        assert profile.max_entries_per_event == rules.max_entries_per_team_per_event
        assert profile.max_individual_events == rules.max_individual_events_per_swimmer
        assert profile.max_total_events == rules.max_total_events_per_swimmer
        assert profile.min_scoring_grade == rules.min_scoring_grade
        assert profile.relay_3_counts_as_individual is True
        assert profile.diving_counts_as_individual is True

    def test_visaa_from_rules_matches_canonical(self):
        """VISAA State profile from rules matches canonical MeetRules values."""
        rules = VISAAStateRules()
        profile = ScoringProfile.from_rules(rules)

        assert profile.individual_points == rules.individual_points
        assert profile.relay_points == rules.relay_points
        assert profile.max_scorers_per_team == 4
        assert (
            profile.max_entries_per_event == 999
        )  # Unlimited entries at championships
        assert (
            profile.relay_3_counts_as_individual is False
        )  # VISAA: relay 3 is NOT individual
        assert profile.diving_counts_as_individual is True

    def test_dual_from_rules_matches_canonical(self):
        """Dual meet profile from rules matches canonical MeetRules values."""
        rules = SetonDualRules()
        profile = ScoringProfile.from_rules(rules)

        assert profile.individual_points == [8, 6, 5, 4, 3, 2, 1]
        assert profile.relay_points == [10, 5, 3]
        assert profile.max_scorers_per_team == 4
        assert profile.max_entries_per_event == 4
        assert profile.relay_3_counts_as_individual is False

    def test_from_meet_profile_string(self):
        """from_meet_profile() works with string profile names."""
        vcac = ScoringProfile.from_meet_profile("vcac_championship")
        assert vcac.relay_3_counts_as_individual is True

        visaa = ScoringProfile.from_meet_profile("visaa_state")
        assert visaa.relay_3_counts_as_individual is False

    def test_factory_methods_match_from_rules(self):
        """Convenience factory methods produce same result as from_rules()."""
        vcac_factory = ScoringProfile.vcac_championship()
        vcac_rules = ScoringProfile.from_rules(VCACChampRules())
        assert vcac_factory.individual_points == vcac_rules.individual_points
        assert (
            vcac_factory.relay_3_counts_as_individual
            == vcac_rules.relay_3_counts_as_individual
        )

        visaa_factory = ScoringProfile.visaa_championship()
        visaa_rules = ScoringProfile.from_rules(VISAAStateRules())
        assert visaa_factory.individual_points == visaa_rules.individual_points
        assert (
            visaa_factory.relay_3_counts_as_individual
            == visaa_rules.relay_3_counts_as_individual
        )

    def test_vcac_vs_visaa_key_differences(self):
        """VCAC and VISAA profiles have the expected structural differences."""
        vcac = ScoringProfile.vcac_championship()
        visaa = ScoringProfile.visaa_championship()

        # Relay 3 counts as individual at VCAC only
        assert vcac.relay_3_counts_as_individual is True
        assert visaa.relay_3_counts_as_individual is False

        # VCAC: 12-place scoring, VISAA: 16-place scoring
        assert len(vcac.individual_points) == 12
        assert len(visaa.individual_points) == 16

        # VCAC: 16 top score, VISAA: 20 top score
        assert vcac.individual_points[0] == 16
        assert visaa.individual_points[0] == 20

        # Both have max 4 scorers per team
        assert vcac.max_scorers_per_team == 4
        assert visaa.max_scorers_per_team == 4

        # VISAA allows unlimited entries (999), VCAC also unlimited
        assert vcac.max_entries_per_event == 999
        assert visaa.max_entries_per_event == 999


# ─── ConstraintEngine meet-type tests ─────────────────────────────────


class TestConstraintEngineRelay3:
    """Verify relay-3 penalty enforcement varies by meet type."""

    @pytest.fixture
    def vcac_events(self):
        return [
            "Boys 200 Medley Relay",
            "Boys 200 Free",
            "Boys 50 Free",
            "Boys 100 Fly",
            "Boys 200 Free Relay",
            "Boys 100 Back",
            "Boys 400 Free Relay",
        ]

    @pytest.fixture
    def roster_df(self):
        return pd.DataFrame(
            [
                {"swimmer": "Swimmer A", "event": "Boys 200 Free", "time": 120.0},
                {"swimmer": "Swimmer A", "event": "Boys 50 Free", "time": 23.0},
                {"swimmer": "Swimmer A", "event": "Boys 400 Free Relay", "time": 200.0},
            ]
        )

    def test_vcac_relay3_counts_as_individual(self, vcac_events, roster_df):
        """At VCAC: 2 non-adjacent swims + 400 FR relay = 3 individual slots = INVALID."""
        profile = ScoringProfile.vcac_championship()
        engine = ConstraintEngine(
            profile,
            vcac_events,
            relay_3_swimmers={"Swimmer A"},
        )

        # Use non-adjacent events to isolate relay-3 constraint from back-to-back
        lineup = Lineup(
            assignments={
                "Swimmer A": {
                    "Boys 200 Free",
                    "Boys 100 Fly",
                    "Boys 400 Free Relay",
                }
            }
        )

        valid, violations = engine.is_valid(lineup, roster_df)
        assert not valid, (
            "VCAC: 2 swims + relay_3 = 3 individual slots should be INVALID"
        )
        assert any("individual slots" in v for v in violations)

    def test_visaa_relay3_does_not_count(self, vcac_events, roster_df):
        """At VISAA: 2 non-adjacent swims + 400 FR relay = 2 individual slots = VALID."""
        profile = ScoringProfile.visaa_championship()
        engine = ConstraintEngine(
            profile,
            vcac_events,
            relay_3_swimmers={"Swimmer A"},
        )

        # Use non-adjacent events to avoid back-to-back constraint
        lineup = Lineup(
            assignments={
                "Swimmer A": {
                    "Boys 200 Free",
                    "Boys 100 Fly",
                    "Boys 400 Free Relay",
                }
            }
        )

        valid, violations = engine.is_valid(lineup, roster_df)
        assert valid, (
            f"VISAA: 2 swims + relay_3 should be VALID, got violations: {violations}"
        )

    def test_vcac_diver_with_one_swim_and_relay3(self, vcac_events, roster_df):
        """At VCAC: diver + 1 swim + relay_3 = 3 individual slots = INVALID."""
        events = [
            "Boys 200 Medley Relay",
            "Boys 200 Free",
            "Boys 200 IM",
            "Boys 50 Free",
            "Boys 1M Diving",
            "Boys 100 Fly",
            "Boys 200 Free Relay",
            "Boys 100 Back",
            "Boys 400 Free Relay",
        ]
        profile = ScoringProfile.vcac_championship()
        engine = ConstraintEngine(
            profile,
            events,
            divers={"Diver A"},
            relay_3_swimmers={"Diver A"},
        )

        roster = pd.DataFrame(
            [
                {"swimmer": "Diver A", "event": "Boys 1M Diving", "time": 0.0},
                {"swimmer": "Diver A", "event": "Boys 200 Free", "time": 120.0},
                {"swimmer": "Diver A", "event": "Boys 400 Free Relay", "time": 200.0},
            ]
        )

        # Non-adjacent: 200 Free (idx 1) + Diving (idx 4) + 400 FR (idx 8)
        lineup = Lineup(
            assignments={
                "Diver A": {
                    "Boys 1M Diving",
                    "Boys 200 Free",
                    "Boys 400 Free Relay",
                }
            }
        )

        valid, violations = engine.is_valid(lineup, roster)
        assert not valid, (
            "VCAC: dive + swim + relay_3 = 3 individual slots should be INVALID"
        )

    def test_visaa_diver_with_one_swim_and_relay3_is_valid(
        self, vcac_events, roster_df
    ):
        """At VISAA: diver + 1 swim + relay_3 = 2 individual slots = VALID."""
        # Insert diving between non-adjacent events to avoid back-to-back
        events = [
            "Boys 200 Medley Relay",
            "Boys 200 Free",
            "Boys 200 IM",
            "Boys 50 Free",
            "Boys 1M Diving",
            "Boys 100 Fly",
            "Boys 200 Free Relay",
            "Boys 100 Back",
            "Boys 400 Free Relay",
        ]
        profile = ScoringProfile.visaa_championship()
        engine = ConstraintEngine(
            profile,
            events,
            divers={"Diver A"},
            relay_3_swimmers={"Diver A"},
        )

        roster = pd.DataFrame(
            [
                {"swimmer": "Diver A", "event": "Boys 1M Diving", "time": 0.0},
                {"swimmer": "Diver A", "event": "Boys 200 Free", "time": 120.0},
                {"swimmer": "Diver A", "event": "Boys 400 Free Relay", "time": 200.0},
            ]
        )

        lineup = Lineup(
            assignments={
                "Diver A": {
                    "Boys 1M Diving",
                    "Boys 200 Free",
                    "Boys 400 Free Relay",
                }
            }
        )

        valid, violations = engine.is_valid(lineup, roster)
        assert valid, (
            f"VISAA: dive + swim + relay_3 = 2 slots should be VALID, got: {violations}"
        )


class TestConstraintEngineMaxEntries:
    """Verify max_entries_per_event varies correctly by meet type."""

    def test_championship_allows_many_entries(self):
        """Championship meets should allow more than 4 entries per event."""
        profile = ScoringProfile.visaa_championship()
        events = ["Boys 50 Free"]
        engine = ConstraintEngine(profile, events)

        # 6 swimmers in one event — should be valid at championships (999 limit)
        lineup = Lineup(assignments={f"S{i}": {"Boys 50 Free"} for i in range(6)})
        roster = pd.DataFrame(
            [
                {"swimmer": f"S{i}", "event": "Boys 50 Free", "time": 22.0 + i}
                for i in range(6)
            ]
        )

        valid, violations = engine.is_valid(lineup, roster)
        assert valid, (
            f"Championship should allow 6 entries, got violations: {violations}"
        )

    def test_dual_caps_at_4_entries(self):
        """Dual meets should cap at 4 entries per event."""
        profile = ScoringProfile.visaa_dual()
        events = ["Boys 50 Free"]
        engine = ConstraintEngine(profile, events)

        # 5 swimmers in one event — should be invalid at dual (4 limit)
        lineup = Lineup(assignments={f"S{i}": {"Boys 50 Free"} for i in range(5)})
        roster = pd.DataFrame(
            [
                {"swimmer": f"S{i}", "event": "Boys 50 Free", "time": 22.0 + i}
                for i in range(5)
            ]
        )

        valid, violations = engine.is_valid(lineup, roster)
        assert not valid, "Dual meet should cap at 4 entries per event"


# ─── OptimizationRouter tests ─────────────────────────────────────────


class TestOptimizationRouter:
    """Verify the router correctly passes meet_profile through."""

    def test_aqua_visaa_profile_has_correct_relay3(self):
        """When forced to Aqua with VISAA profile, relay_3 should be False."""
        from swim_ai_reflex.backend.core.strategies.optimization_router import (
            get_optimizer,
        )

        optimizer = get_optimizer(
            meet_type="championship",
            quality_mode="fast",
            meet_profile="visaa_state",
        )
        assert hasattr(optimizer, "profile")
        assert optimizer.profile.relay_3_counts_as_individual is False

    def test_aqua_vcac_profile_has_correct_relay3(self):
        """When forced to Aqua with VCAC profile, relay_3 should be True."""
        from swim_ai_reflex.backend.core.strategies.optimization_router import (
            get_optimizer,
        )

        optimizer = get_optimizer(
            meet_type="championship",
            quality_mode="fast",
            meet_profile="vcac_championship",
        )
        assert hasattr(optimizer, "profile")
        assert optimizer.profile.relay_3_counts_as_individual is True
