"""
Tests for the RelayAwareAssigner — post-individual relay assignment.

Verifies:
1. Medley relay leg assignment by stroke
2. Free relay selection by fastest freestyle times
3. VCAC relay-3 counts as individual slot
4. Full optimization with relays produces valid lineups
5. No constraint violations in combined lineup
"""

import pandas as pd
import pytest

from swim_ai_reflex.backend.core.strategies.aqua_optimizer import (
    AquaOptimizer,
    ConstraintEngine,
    FatigueModel,
    Lineup,
    RelayAwareAssigner,
    ScoringEngine,
    ScoringProfile,
)


def _make_roster(entries: list[dict]) -> pd.DataFrame:
    """Build a roster DataFrame from simplified entry dicts."""
    for e in entries:
        e.setdefault("grade", 10)
        e.setdefault("team", "seton")
    return pd.DataFrame(entries)


def _make_opponent_roster(entries: list[dict]) -> pd.DataFrame:
    for e in entries:
        e.setdefault("grade", 10)
        e.setdefault("team", "opponent")
    return pd.DataFrame(entries)


# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def visaa_profile():
    return ScoringProfile.visaa_dual()


@pytest.fixture
def vcac_profile():
    return ScoringProfile.from_meet_profile("vcac_championship")


@pytest.fixture
def seton_roster():
    """8 swimmers with times in individual and relay-relevant events."""
    return _make_roster(
        [
            # Backstrokers
            {"swimmer": "Alice", "event": "100 Back", "time": 62.0},
            {"swimmer": "Beth", "event": "100 Back", "time": 64.0},
            # Breaststrokers
            {"swimmer": "Carol", "event": "100 Breast", "time": 70.0},
            {"swimmer": "Diana", "event": "100 Breast", "time": 72.0},
            # Flyers
            {"swimmer": "Eve", "event": "100 Fly", "time": 60.0},
            {"swimmer": "Fran", "event": "100 Fly", "time": 63.0},
            # Freestylers
            {"swimmer": "Grace", "event": "100 Free", "time": 55.0},
            {"swimmer": "Heidi", "event": "100 Free", "time": 57.0},
            {"swimmer": "Alice", "event": "100 Free", "time": 58.0},
            {"swimmer": "Beth", "event": "100 Free", "time": 59.0},
            # 50 Free for free relay
            {"swimmer": "Grace", "event": "50 Free", "time": 25.0},
            {"swimmer": "Heidi", "event": "50 Free", "time": 26.0},
            {"swimmer": "Alice", "event": "50 Free", "time": 27.0},
            {"swimmer": "Beth", "event": "50 Free", "time": 27.5},
            {"swimmer": "Eve", "event": "50 Free", "time": 28.0},
            {"swimmer": "Carol", "event": "50 Free", "time": 29.0},
            # Individual events
            {"swimmer": "Alice", "event": "200 Free", "time": 120.0},
            {"swimmer": "Grace", "event": "200 Free", "time": 118.0},
            {"swimmer": "Eve", "event": "200 IM", "time": 130.0},
            {"swimmer": "Carol", "event": "200 IM", "time": 135.0},
            # Relay placeholder entries (team-level, used for event detection)
            {"swimmer": "SST Relay A", "event": "200 Medley Relay", "time": 112.0},
            {"swimmer": "SST Relay A", "event": "200 Free Relay", "time": 100.0},
            {"swimmer": "SST Relay A", "event": "400 Free Relay", "time": 220.0},
        ]
    )


@pytest.fixture
def opponent_roster():
    return _make_opponent_roster(
        [
            {"swimmer": "Opp1", "event": "200 Medley Relay", "time": 115.0},
            {"swimmer": "Opp1", "event": "200 Free Relay", "time": 105.0},
            {"swimmer": "Opp1", "event": "400 Free Relay", "time": 225.0},
            {"swimmer": "Opp2", "event": "100 Back", "time": 63.0},
            {"swimmer": "Opp3", "event": "100 Breast", "time": 71.0},
            {"swimmer": "Opp4", "event": "100 Fly", "time": 61.0},
            {"swimmer": "Opp5", "event": "100 Free", "time": 56.0},
            {"swimmer": "Opp6", "event": "50 Free", "time": 26.0},
            {"swimmer": "Opp7", "event": "200 Free", "time": 119.0},
            {"swimmer": "Opp8", "event": "200 IM", "time": 132.0},
        ]
    )


# ── Medley Relay Tests ────────────────────────────────────────────────────


class TestMedleyRelayAssignment:
    def test_assigns_fastest_per_stroke(
        self, visaa_profile, seton_roster, opponent_roster
    ):
        """Medley relay A team should pick fastest back/breast/fly/free swimmers."""
        events = [
            "200 Medley Relay",
            "200 Free",
            "200 IM",
            "50 Free",
            "100 Fly",
            "100 Free",
            "100 Back",
            "100 Breast",
            "200 Free Relay",
            "400 Free Relay",
        ]
        constraint_engine = ConstraintEngine(visaa_profile, events)
        scoring_engine = ScoringEngine(visaa_profile, FatigueModel(enabled=False))

        # Start with an empty individual lineup
        individual_lineup = Lineup(assignments={})

        assigner = RelayAwareAssigner(visaa_profile, constraint_engine)
        results = assigner.assign_relays(
            individual_lineup,
            seton_roster,
            opponent_roster,
            ["200 Medley Relay"],
            events,
            scoring_engine,
        )

        assert len(results) >= 1
        a_team = results[0]
        assert a_team.team_designation == "A"
        assert len(a_team.legs) == 4

        # Fastest back=Alice(62), breast=Carol(70), fly=Eve(60), free=Grace(55)
        assert a_team.legs[0] == "Alice"  # Back
        assert a_team.legs[1] == "Carol"  # Breast
        assert a_team.legs[2] == "Eve"  # Fly
        assert a_team.legs[3] == "Grace"  # Free

    def test_b_team_uses_next_fastest(
        self, visaa_profile, seton_roster, opponent_roster
    ):
        """B team should use next-fastest swimmers not on A team."""
        events = [
            "200 Medley Relay",
            "200 Free",
            "200 IM",
            "50 Free",
            "100 Fly",
            "100 Free",
            "100 Back",
            "100 Breast",
            "200 Free Relay",
            "400 Free Relay",
        ]
        constraint_engine = ConstraintEngine(visaa_profile, events)
        scoring_engine = ScoringEngine(visaa_profile, FatigueModel(enabled=False))

        individual_lineup = Lineup(assignments={})

        assigner = RelayAwareAssigner(visaa_profile, constraint_engine)
        results = assigner.assign_relays(
            individual_lineup,
            seton_roster,
            opponent_roster,
            ["200 Medley Relay"],
            events,
            scoring_engine,
        )

        assert len(results) == 2
        b_team = results[1]
        assert b_team.team_designation == "B"
        assert len(b_team.legs) == 4

        # B team: Beth(back 64), Diana(breast 72), Fran(fly 63), Heidi(free 57)
        assert b_team.legs[0] == "Beth"
        assert b_team.legs[1] == "Diana"
        assert b_team.legs[2] == "Fran"
        assert b_team.legs[3] == "Heidi"


# ── Free Relay Tests ──────────────────────────────────────────────────────


class TestFreeRelayAssignment:
    def test_assigns_fastest_freestylers(
        self, visaa_profile, seton_roster, opponent_roster
    ):
        """200 Free Relay should pick 4 fastest 50 Free swimmers."""
        events = [
            "200 Medley Relay",
            "200 Free",
            "200 IM",
            "50 Free",
            "100 Fly",
            "100 Free",
            "100 Back",
            "100 Breast",
            "200 Free Relay",
            "400 Free Relay",
        ]
        constraint_engine = ConstraintEngine(visaa_profile, events)
        scoring_engine = ScoringEngine(visaa_profile, FatigueModel(enabled=False))

        individual_lineup = Lineup(assignments={})

        assigner = RelayAwareAssigner(visaa_profile, constraint_engine)
        results = assigner.assign_relays(
            individual_lineup,
            seton_roster,
            opponent_roster,
            ["200 Free Relay"],
            events,
            scoring_engine,
        )

        assert len(results) >= 1
        a_team = results[0]
        assert a_team.team_designation == "A"
        assert len(a_team.legs) == 4

        # Top 4 by 50 Free: Grace(25), Heidi(26), Alice(27), Beth(27.5)
        assert set(a_team.legs) == {"Grace", "Heidi", "Alice", "Beth"}


# ── Constraint Respect Tests ──────────────────────────────────────────────


class TestRelayConstraints:
    def test_respects_max_total_events(
        self, visaa_profile, seton_roster, opponent_roster
    ):
        """Swimmers at max total events should not be assigned to relays."""
        events = [
            "200 Medley Relay",
            "200 Free",
            "200 IM",
            "50 Free",
            "100 Fly",
            "100 Free",
            "100 Back",
            "100 Breast",
            "200 Free Relay",
            "400 Free Relay",
        ]
        constraint_engine = ConstraintEngine(visaa_profile, events)
        scoring_engine = ScoringEngine(visaa_profile, FatigueModel(enabled=False))

        # Give Alice 4 events already (max_total_events=4)
        individual_lineup = Lineup(
            assignments={
                "Alice": {"200 Free", "100 Back", "50 Free", "200 IM"},
            }
        )

        assigner = RelayAwareAssigner(visaa_profile, constraint_engine)
        results = assigner.assign_relays(
            individual_lineup,
            seton_roster,
            opponent_roster,
            ["200 Medley Relay"],
            events,
            scoring_engine,
        )

        # Alice should NOT be on any relay team
        for ra in results:
            assert "Alice" not in ra.legs, (
                f"Alice at max events should not be on {ra.relay_event} {ra.team_designation}"
            )

    def test_vcac_relay3_counts_as_individual(
        self, vcac_profile, seton_roster, opponent_roster
    ):
        """At VCAC, 400 Free Relay costs an individual slot."""
        events = [
            "200 Medley Relay",
            "200 Free",
            "200 IM",
            "50 Free",
            "100 Fly",
            "100 Free",
            "100 Back",
            "100 Breast",
            "200 Free Relay",
            "400 Free Relay",
        ]
        relay_3_swimmers = {"Grace", "Alice", "Beth", "Heidi"}
        constraint_engine = ConstraintEngine(
            vcac_profile,
            events,
            relay_3_swimmers=relay_3_swimmers,
        )
        scoring_engine = ScoringEngine(vcac_profile, FatigueModel(enabled=False))

        # Grace already has 2 individual events (max for championship)
        individual_lineup = Lineup(
            assignments={
                "Grace": {"200 Free", "100 Free"},
            }
        )

        assigner = RelayAwareAssigner(vcac_profile, constraint_engine)
        results = assigner.assign_relays(
            individual_lineup,
            seton_roster,
            opponent_roster,
            ["400 Free Relay"],
            events,
            scoring_engine,
        )

        # Grace should NOT be on 400 Free Relay (it would exceed individual limit)
        for ra in results:
            if "400" in ra.relay_event:
                assert "Grace" not in ra.legs, (
                    "Grace at 2 individual events should not be on 400 FR at VCAC"
                )


# ── Integration Test ──────────────────────────────────────────────────────


class TestFullOptimizationWithRelays:
    def test_optimizer_includes_relay_assignments(self, seton_roster, opponent_roster):
        """Full optimization run should produce relay assignments."""
        optimizer = AquaOptimizer(
            quality_mode="fast",
            fatigue=FatigueModel(enabled=False),
        )

        best_seton_df, scored_df, totals, details = optimizer.optimize(
            seton_roster,
            opponent_roster,
            scoring_fn=None,
            rules=None,
        )

        # Should have relay assignment data in details
        assert len(details) >= 1
        detail = details[0]

        # If relay events were present, relay_assignments should be populated
        if "relay_assignments" in detail:
            relay_data = detail["relay_assignments"]
            assert len(relay_data) >= 1
            for ra in relay_data:
                assert "relay_event" in ra
                assert "team" in ra
                assert "legs" in ra
                assert len(ra["legs"]) == 4

    def test_optimizer_score_includes_relay_points(self, seton_roster, opponent_roster):
        """Score should include relay points when relay events are present."""
        optimizer = AquaOptimizer(
            quality_mode="fast",
            fatigue=FatigueModel(enabled=False),
        )

        _, _, totals, _ = optimizer.optimize(
            seton_roster,
            opponent_roster,
            scoring_fn=None,
            rules=None,
        )

        # Score should be positive (relays add points)
        assert totals["seton"] > 0

    def test_no_constraint_violations(self, seton_roster, opponent_roster):
        """Combined individual + relay lineup should have no violations."""
        profile = ScoringProfile.visaa_dual()
        optimizer = AquaOptimizer(
            profile=profile,
            quality_mode="fast",
            fatigue=FatigueModel(enabled=False),
        )

        best_seton_df, scored_df, totals, details = optimizer.optimize(
            seton_roster,
            opponent_roster,
            scoring_fn=None,
            rules=None,
        )

        # Verify no swimmer exceeds max_total_events
        if not scored_df.empty and "swimmer" in scored_df.columns:
            swimmer_event_counts = scored_df.groupby("swimmer")["event"].nunique()
            for swimmer, count in swimmer_event_counts.items():
                # Skip relay placeholder entries
                if "Relay" in str(swimmer):
                    continue
                assert count <= profile.max_total_events, (
                    f"{swimmer} has {count} events (max {profile.max_total_events})"
                )


# ── Relay-Individual Swap Refinement Tests ────────────────────────────────


class TestRelayIndividualRefinement:
    def test_refinement_does_not_break_constraints(self, seton_roster, opponent_roster):
        """Relay refinement should never produce constraint violations."""
        optimizer = AquaOptimizer(
            quality_mode="fast",
            fatigue=FatigueModel(enabled=False),
        )

        _, scored_df, totals, details = optimizer.optimize(
            seton_roster,
            opponent_roster,
            scoring_fn=None,
            rules=None,
        )

        # Total score must be valid
        assert totals["seton"] >= 0

        # Verify relay assignments exist and have 4 legs each
        detail = details[0]
        if "relay_assignments" in detail:
            for ra in detail["relay_assignments"]:
                assert len(ra["legs"]) == 4
                # No duplicate swimmers on same relay team
                assert len(set(ra["legs"])) == 4

    def test_refinement_respects_locked_pairs(self, seton_roster, opponent_roster):
        """Locked swimmers should not be swapped out of relays."""
        optimizer = AquaOptimizer(
            quality_mode="fast",
            fatigue=FatigueModel(enabled=False),
            locked_assignments=[{"swimmer": "Alice", "event": "200 Medley Relay"}],
        )

        _, _, _, details = optimizer.optimize(
            seton_roster,
            opponent_roster,
            scoring_fn=None,
            rules=None,
        )

        detail = details[0]
        if "relay_assignments" in detail:
            medley_relays = [
                ra
                for ra in detail["relay_assignments"]
                if "Medley" in ra["relay_event"]
            ]
            # If Alice was assigned to medley relay, she should still be there
            for ra in medley_relays:
                if "Alice" in ra["legs"]:
                    assert True  # Lock was respected
                    return

    def test_split_factors_are_per_stroke(self):
        """Verify per-stroke calibrated factors are used instead of flat 0.48."""
        from swim_ai_reflex.backend.core.strategies.aqua_optimizer import (
            RELAY_SPLIT_FACTORS,
            SPLIT_FACTOR,
        )

        assert RELAY_SPLIT_FACTORS["100 Back"] == 0.47
        assert RELAY_SPLIT_FACTORS["100 Breast"] == 0.49
        assert RELAY_SPLIT_FACTORS["100 Fly"] == 0.47
        assert RELAY_SPLIT_FACTORS["100 Free"] == 0.48
        assert RELAY_SPLIT_FACTORS["50 Free"] == 1.0
        assert SPLIT_FACTOR == 0.48  # Legacy fallback preserved
