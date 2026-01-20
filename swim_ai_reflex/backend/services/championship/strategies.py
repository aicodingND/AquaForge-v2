"""
Championship Optimization Strategies Guide

This module provides comprehensive strategies for championship meet optimization,
with clear explanations, examples, and use cases for coaches.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List


class ChampionshipStrategy(Enum):
    """Available championship optimization strategies."""

    MAXIMIZE_INDIVIDUAL = "maximize_individual"
    BALANCED_APPROACH = "balanced_approach"
    RELAY_FOCUSED = "relay_focused"
    CONSERVATIVE = "conservative"
    AGGRESSIVE = "aggressive"


@dataclass
class StrategyInfo:
    """Information about a championship strategy."""

    name: str
    key: ChampionshipStrategy
    description: str
    when_to_use: str
    example_scenario: str
    pros: List[str]
    cons: List[str]
    recommended_for: List[str]


# ============================================================================
# STRATEGY DEFINITIONS
# ============================================================================

MAXIMIZE_INDIVIDUAL = StrategyInfo(
    name="Maximize Individual Events",
    key=ChampionshipStrategy.MAXIMIZE_INDIVIDUAL,
    description="""
    Optimizes swimmer assignments to maximize points from individual events only.
    This is the DEFAULT strategy and focuses on getting the most points from 
    individual swims (50 Free, 100 Fly, 200 IM, etc.).
    
    Relays and diving are NOT optimized - they use seed times for projection.
    """,
    when_to_use="""
    Use this strategy when:
    - You want to focus on individual event scoring
    - Your relay teams are already set
    - You have strong individual swimmers
    - You want to see maximum potential from individual events
    """,
    example_scenario="""
    **Scenario**: VCAC Championship with 6 teams
    
    Your team has:
    - 3 strong freestylers who could swim 50/100 Free
    - 2 IMers who could do 100 Back/Breast/Fly or 200 IM
    - Limited relay depth
    
    **Strategy**: Maximize Individual Events
    - Assigns swimmers to their best individual events
    - Considers back-to-back constraints
    - Accounts for 400 Free Relay swimmers (they lose 1 individual slot)
    - Result: "191 points from individual events"
    
    **What it means**: If your swimmers perform at seed times, you'll score
    191 points from individual events. Add relay/diving points separately.
    """,
    pros=[
        "Clear focus on individual scoring",
        "Respects swimmer strengths and seed times",
        "Accounts for back-to-back event constraints",
        "Handles 400 Free Relay penalty automatically",
        "Fast optimization (< 2 seconds)",
    ],
    cons=[
        "Does NOT optimize relay lineups",
        "Does NOT optimize diving assignments",
        "Assumes relays swim at seed times",
        "May not account for strategic relay decisions",
    ],
    recommended_for=[
        "Teams with established relay lineups",
        "Coaches who want to focus on individual assignments",
        "First-time championship planning",
        "Quick 'what-if' scenario testing",
    ],
)

BALANCED_APPROACH = StrategyInfo(
    name="Balanced Approach",
    key=ChampionshipStrategy.BALANCED_APPROACH,
    description="""
    Balances individual event optimization with relay considerations.
    This strategy considers both individual points AND relay potential when
    making assignments.
    
    **Coming Soon** - This strategy is under development.
    """,
    when_to_use="""
    Use this strategy when:
    - You have flexibility in both individual and relay assignments
    - You want to consider relay trade-offs
    - You have swimmers who could excel in either role
    """,
    example_scenario="""
    **Scenario**: Your best 50 Freestyler is also your best relay lead-off
    
    **Question**: Should they swim 50 Free individually, or save energy for relays?
    
    **Balanced Approach**: Considers both options and chooses the one that
    maximizes TOTAL meet points (individual + relay combined).
    """,
    pros=[
        "Considers relay impact on individual assignments",
        "May find non-obvious optimal lineups",
        "Accounts for swimmer fatigue across events",
    ],
    cons=[
        "More complex optimization (slower)",
        "Requires accurate relay split predictions",
        "May suggest counterintuitive assignments",
    ],
    recommended_for=[
        "Experienced coaches comfortable with complex strategies",
        "Teams with deep rosters and flexibility",
        "Championship meets where every point matters",
    ],
)

RELAY_FOCUSED = StrategyInfo(
    name="Relay-Focused Strategy",
    key=ChampionshipStrategy.RELAY_FOCUSED,
    description="""
    Prioritizes relay performance over individual events.
    This strategy optimizes relay lineups FIRST, then assigns remaining
    swimmers to individual events.
    
    **Coming Soon** - This strategy is under development.
    """,
    when_to_use="""
    Use this strategy when:
    - Your relay teams are your strength
    - You want to ensure optimal relay lineups
    - Individual depth is limited but relay depth is strong
    """,
    example_scenario="""
    **Scenario**: Close championship race, relays could be the difference
    
    Your team:
    - Has 6-8 strong relay swimmers
    - Limited individual event depth
    - Relays could score 40-50 points
    
    **Relay-Focused Strategy**:
    1. Optimizes all 3 relay lineups first
    2. Assigns remaining individual slots to maximize points
    3. Ensures relay swimmers are fresh for their relay events
    """,
    pros=[
        "Ensures optimal relay lineups",
        "Accounts for relay swimmer fatigue",
        "Good for teams with relay strength",
    ],
    cons=[
        "May sacrifice individual event points",
        "Requires accurate relay split data",
        "More complex to understand",
    ],
    recommended_for=[
        "Teams with strong relay programs",
        "Meets where relays are worth significant points",
        "Teams competing for top 3 finish",
    ],
)

CONSERVATIVE = StrategyInfo(
    name="Conservative Strategy",
    key=ChampionshipStrategy.CONSERVATIVE,
    description="""
    Minimizes risk by using proven assignments and avoiding back-to-back events.
    This strategy prioritizes reliability over maximum points.
    
    **Coming Soon** - This strategy is under development.
    """,
    when_to_use="""
    Use this strategy when:
    - You want to avoid risky back-to-back assignments
    - Swimmer fatigue is a concern
    - You prefer proven, reliable lineups
    """,
    example_scenario="""
    **Scenario**: Championship meet with young/inexperienced team
    
    **Conservative Strategy**:
    - Avoids all back-to-back events (even if allowed)
    - Uses swimmers in their primary events only
    - Builds in rest time between events
    - Result: Lower projected points but higher reliability
    """,
    pros=[
        "Minimizes fatigue risk",
        "More reliable performance predictions",
        "Easier for swimmers to execute",
        "Good for inexperienced teams",
    ],
    cons=[
        "May leave points on the table",
        "Doesn't maximize potential",
        "May not be competitive in close meets",
    ],
    recommended_for=[
        "Young or inexperienced teams",
        "Teams prioritizing swimmer development",
        "Meets where finishing position isn't critical",
    ],
)

AGGRESSIVE = StrategyInfo(
    name="Aggressive Strategy",
    key=ChampionshipStrategy.AGGRESSIVE,
    description="""
    Maximizes points by using all available options, including back-to-back
    events and strategic risk-taking.
    
    **Coming Soon** - This strategy is under development.
    """,
    when_to_use="""
    Use this strategy when:
    - You're competing for a championship
    - Every point matters
    - Your swimmers can handle back-to-back events
    - You're willing to take calculated risks
    """,
    example_scenario="""
    **Scenario**: Close race for 1st place, need maximum points
    
    **Aggressive Strategy**:
    - Uses back-to-back events where beneficial
    - Assigns swimmers to 4 individual events (maximum allowed)
    - Optimizes relay lineups for maximum speed
    - May suggest unconventional assignments
    - Result: Maximum projected points, higher fatigue risk
    """,
    pros=[
        "Maximizes point potential",
        "Uses all available options",
        "Good for championship races",
        "May find creative solutions",
    ],
    cons=[
        "Higher fatigue risk",
        "More complex for swimmers",
        "Requires experienced team",
        "May backfire if swimmers underperform",
    ],
    recommended_for=[
        "Experienced, competitive teams",
        "Championship meets",
        "Teams competing for top finish",
        "Swimmers who can handle pressure",
    ],
)


# ============================================================================
# STRATEGY REGISTRY
# ============================================================================

ALL_STRATEGIES: Dict[ChampionshipStrategy, StrategyInfo] = {
    ChampionshipStrategy.MAXIMIZE_INDIVIDUAL: MAXIMIZE_INDIVIDUAL,
    ChampionshipStrategy.BALANCED_APPROACH: BALANCED_APPROACH,
    ChampionshipStrategy.RELAY_FOCUSED: RELAY_FOCUSED,
    ChampionshipStrategy.CONSERVATIVE: CONSERVATIVE,
    ChampionshipStrategy.AGGRESSIVE: AGGRESSIVE,
}


def get_strategy_info(strategy: ChampionshipStrategy) -> StrategyInfo:
    """Get detailed information about a strategy."""
    return ALL_STRATEGIES[strategy]


def get_available_strategies() -> List[StrategyInfo]:
    """Get list of all available strategies."""
    return list(ALL_STRATEGIES.values())


def get_implemented_strategies() -> List[StrategyInfo]:
    """Get list of currently implemented strategies."""
    return [MAXIMIZE_INDIVIDUAL]  # Only this one is implemented


def get_coming_soon_strategies() -> List[StrategyInfo]:
    """Get list of strategies under development."""
    return [
        BALANCED_APPROACH,
        RELAY_FOCUSED,
        CONSERVATIVE,
        AGGRESSIVE,
    ]


# ============================================================================
# STRATEGY SELECTION HELPER
# ============================================================================


def recommend_strategy(
    team_size: int,
    relay_strength: str,  # "weak", "average", "strong"
    experience_level: str,  # "beginner", "intermediate", "advanced"
    meet_importance: str,  # "practice", "regular", "championship"
) -> StrategyInfo:
    """
    Recommend a strategy based on team characteristics.

    Args:
        team_size: Number of swimmers on team
        relay_strength: Team's relay capability
        experience_level: Team's experience level
        meet_importance: Importance of the meet

    Returns:
        Recommended StrategyInfo
    """
    # For now, always recommend MAXIMIZE_INDIVIDUAL since it's the only implemented one
    # In the future, this will have more sophisticated logic

    if experience_level == "beginner" or meet_importance == "practice":
        return CONSERVATIVE
    elif relay_strength == "strong" and team_size >= 20:
        return BALANCED_APPROACH
    elif meet_importance == "championship":
        return AGGRESSIVE
    else:
        return MAXIMIZE_INDIVIDUAL


# ============================================================================
# EXPORT FOR API
# ============================================================================


def get_strategies_for_api() -> List[Dict[str, Any]]:
    """
    Get strategy information formatted for API response.

    Returns:
        List of strategy dictionaries suitable for JSON serialization
    """
    strategies = []

    for strategy_info in get_available_strategies():
        is_implemented = strategy_info in get_implemented_strategies()

        strategies.append(
            {
                "key": strategy_info.key.value,
                "name": strategy_info.name,
                "description": strategy_info.description.strip(),
                "when_to_use": strategy_info.when_to_use.strip(),
                "example_scenario": strategy_info.example_scenario.strip(),
                "pros": strategy_info.pros,
                "cons": strategy_info.cons,
                "recommended_for": strategy_info.recommended_for,
                "is_implemented": is_implemented,
                "status": "available" if is_implemented else "coming_soon",
            }
        )

    return strategies
