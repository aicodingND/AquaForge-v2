"""
Test Championship Scoring End-to-End

Verifies that a 6-team championship meet returns proper standings.
"""

import pytest


def _gurobi_available():
    try:
        import gurobipy as gp

        gp.Model("test")
        return True
    except Exception:
        return False


@pytest.mark.skipif(not _gurobi_available(), reason="Gurobi license unavailable")
def test_championship_6_teams_returns_standings():
    """Test that championship mode with 6 teams returns all team standings."""
    from swim_ai_reflex.backend.core.strategies.championship_strategy import (
        ChampionshipGurobiStrategy,
    )
    from swim_ai_reflex.backend.services.championship.projection import (
        PointProjectionService,
    )
    from swim_ai_reflex.backend.services.championship_formatter import (
        build_championship_entries,
        format_championship_response,
    )

    # Create test data for 6 teams
    test_data = [
        # SST
        {
            "swimmer": "John Smith",
            "team": "SST",
            "event": "Boys 50 Free",
            "time": 22.5,
            "gender": "M",
            "grade": 12,
        },
        {
            "swimmer": "Jane Doe",
            "team": "SST",
            "event": "Girls 50 Free",
            "time": 25.0,
            "gender": "F",
            "grade": 11,
        },
        # TCS
        {
            "swimmer": "Bob Wilson",
            "team": "TCS",
            "event": "Boys 50 Free",
            "time": 23.0,
            "gender": "M",
            "grade": 12,
        },
        {
            "swimmer": "Alice Brown",
            "team": "TCS",
            "event": "Girls 50 Free",
            "time": 25.5,
            "gender": "F",
            "grade": 11,
        },
        # ICS
        {
            "swimmer": "Mike Davis",
            "team": "ICS",
            "event": "Boys 50 Free",
            "time": 23.5,
            "gender": "M",
            "grade": 12,
        },
        {
            "swimmer": "Sarah Miller",
            "team": "ICS",
            "event": "Girls 50 Free",
            "time": 26.0,
            "gender": "F",
            "grade": 11,
        },
        # OAK
        {
            "swimmer": "Tom Garcia",
            "team": "OAK",
            "event": "Boys 50 Free",
            "time": 24.0,
            "gender": "M",
            "grade": 12,
        },
        {
            "swimmer": "Emma Martinez",
            "team": "OAK",
            "event": "Girls 50 Free",
            "time": 26.5,
            "gender": "F",
            "grade": 11,
        },
        # FCS
        {
            "swimmer": "Chris Lee",
            "team": "FCS",
            "event": "Boys 50 Free",
            "time": 24.5,
            "gender": "M",
            "grade": 12,
        },
        {
            "swimmer": "Olivia Taylor",
            "team": "FCS",
            "event": "Girls 50 Free",
            "time": 27.0,
            "gender": "F",
            "grade": 11,
        },
        # DJO
        {
            "swimmer": "Ryan Anderson",
            "team": "DJO",
            "event": "Boys 50 Free",
            "time": 25.0,
            "gender": "M",
            "grade": 12,
        },
        {
            "swimmer": "Sophia Thomas",
            "team": "DJO",
            "event": "Girls 50 Free",
            "time": 27.5,
            "gender": "F",
            "grade": 11,
        },
    ]

    # Build championship entries
    def time_converter(t):
        return float(t) if isinstance(t, (int, float)) else 999.0

    entries = build_championship_entries(test_data, time_converter)

    # Run optimization
    strategy = ChampionshipGurobiStrategy(meet_profile="vcac_championship")
    champ_result = strategy.optimize_entries(
        all_entries=entries,
        target_team="SST",
        time_limit=10,
    )

    # Run projection for all teams
    projection_service = PointProjectionService(meet_profile="vcac_championship")
    projection_result = projection_service.project_standings(
        entries=test_data,
        target_team="SST",
        meet_name="Test VCAC Championship",
    )

    standings_dict = projection_result.to_dict()

    # Format response
    response = format_championship_response(
        champ_result=champ_result,
        entries=entries,
        optimization_time_ms=100.0,
        standings_projection=standings_dict,
    )

    # Assertions
    assert response.success is True
    assert response.seton_score > 0, "Seton should have a score"
    assert response.opponent_score == 0, "No opponent in championship mode"

    # CRITICAL: Check that championship_standings is populated
    assert response.championship_standings is not None, (
        "Championship standings should be present"
    )
    assert len(response.championship_standings) == 6, (
        f"Should have 6 teams, got {len(response.championship_standings)}"
    )

    # Verify all teams are present
    team_codes = {standing["team"] for standing in response.championship_standings}
    expected_teams = {
        "Seton",
        "Trinity",
        "Immanuel Christian",
        "Oakcrest",
        "Fredericksburg Christian",
        "Bishop O'Connell",
    }
    assert team_codes == expected_teams, (
        f"Team mismatch: {team_codes} vs {expected_teams}"
    )

    # Verify standings have ranks and points
    for standing in response.championship_standings:
        assert "rank" in standing
        assert "team" in standing
        assert "points" in standing
        assert standing["points"] > 0, f"Team {standing['team']} should have points"

    # Verify SST is ranked
    sst_standing = next(
        (s for s in response.championship_standings if "Seton" in s["team"]), None
    )
    assert sst_standing is not None, "SST should be in standings"
    assert sst_standing["rank"] >= 1, "SST should have a valid rank"

    print("✅ Championship standings test passed!")
    print(f"   Optimized score: {response.seton_score}")
    print(f"   Teams in standings: {len(response.championship_standings)}")
    for s in response.championship_standings:
        print(f"     {s['rank']}. {s['team']}: {s['points']} points")


if __name__ == "__main__":
    test_championship_6_teams_returns_standings()
