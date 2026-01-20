"""
Test Strategy Selection API and Types

Verifies that the /strategies endpoint returns expected data structure
and that strategies.py module works correctly.
"""

import pytest


def test_strategies_api_structure():
    """Test that strategies API returns expected structure."""
    from swim_ai_reflex.backend.services.championship.strategies import (
        get_strategies_for_api,
    )

    strategies = get_strategies_for_api()

    # Should have 5 strategies
    assert len(strategies) == 5, f"Expected 5 strategies, got {len(strategies)}"

    # Check structure of each strategy
    required_fields = [
        "key",
        "name",
        "description",
        "when_to_use",
        "example_scenario",
        "pros",
        "cons",
        "recommended_for",
        "is_implemented",
        "status",
    ]

    for strategy in strategies:
        for field in required_fields:
            assert field in strategy, (
                f"Missing field '{field}' in strategy {strategy.get('key', 'unknown')}"
            )

    # Check only one is implemented
    implemented = [s for s in strategies if s["is_implemented"]]
    assert len(implemented) == 1, f"Expected 1 implemented, got {len(implemented)}"
    assert implemented[0]["key"] == "maximize_individual"


def test_implemented_strategies_contains_maximize_individual():
    """Test that 'maximize_individual' is in implemented strategies."""
    from swim_ai_reflex.backend.services.championship.strategies import (
        ChampionshipStrategy,
        get_implemented_strategies,
    )

    implemented = get_implemented_strategies()
    assert len(implemented) == 1
    assert implemented[0].key == ChampionshipStrategy.MAXIMIZE_INDIVIDUAL


def test_coming_soon_has_four_strategies():
    """Test that 4 strategies are marked as coming soon."""
    from swim_ai_reflex.backend.services.championship.strategies import (
        get_coming_soon_strategies,
    )

    coming_soon = get_coming_soon_strategies()
    assert len(coming_soon) == 4

    expected_names = {
        "Balanced Approach",
        "Relay-Focused Strategy",
        "Conservative Strategy",
        "Aggressive Strategy",
    }
    actual_names = {s.name for s in coming_soon}
    assert actual_names == expected_names


def test_strategy_recommendation():
    """Test strategy recommendation logic."""
    from swim_ai_reflex.backend.services.championship.strategies import (
        ChampionshipStrategy,
        recommend_strategy,
    )

    # Beginner team should get conservative
    rec = recommend_strategy(
        team_size=15,
        relay_strength="average",
        experience_level="beginner",
        meet_importance="regular",
    )
    assert rec.key == ChampionshipStrategy.CONSERVATIVE

    # Championship meet with strong relay team should get balanced approach
    # (because relay_strength=="strong" check comes before championship check)
    rec = recommend_strategy(
        team_size=25,
        relay_strength="strong",
        experience_level="advanced",
        meet_importance="championship",
    )
    assert rec.key == ChampionshipStrategy.BALANCED_APPROACH

    # Championship meet without strong relay gets aggressive
    rec = recommend_strategy(
        team_size=15,
        relay_strength="average",
        experience_level="advanced",
        meet_importance="championship",
    )
    assert rec.key == ChampionshipStrategy.AGGRESSIVE


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
