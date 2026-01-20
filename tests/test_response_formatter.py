from swim_ai_reflex.backend.utils.response_formatter import format_dual_meet_response


def test_format_dual_meet_response_event_scoring():
    """
    Verify that the response formatter correctly calculates event-specific scores
    instead of carrying over the total meet score.
    """
    # Mock input data
    result_data = {
        "success": True,
        "data": {
            "best_lineup": [
                {
                    "event": "Event 1",
                    "team": "seton",
                    "swimmer": "Swimmer A",
                    "time": "25.00",
                    "event_num": 1,
                },
                {
                    "event": "Event 2",
                    "team": "seton",
                    "swimmer": "Swimmer B",
                    "time": "55.00",
                    "event_num": 2,
                },
            ],
            "opponent_lineup": [
                {"event": "Event 1", "swimmer": "Opponent X", "time": "26.00"},
                {"event": "Event 2", "swimmer": "Opponent Y", "time": "56.00"},
            ],
            # Detailed scoring breakdown
            "details": [
                # Event 1: Seton wins (6 pts), Opponent 2nd (4 pts)
                {
                    "event": "Event 1",
                    "swimmer": "Swimmer A",
                    "team": "Seton",
                    "points": 6.0,
                    "place": 1,
                },
                {
                    "event": "Event 1",
                    "swimmer": "Opponent X",
                    "team": "Opponent",
                    "points": 4.0,
                    "place": 2,
                },
                # Event 2: Seton wins (6 pts), Opponent 2nd (4 pts)
                {
                    "event": "Event 2",
                    "swimmer": "Swimmer B",
                    "team": "Seton",
                    "points": 6.0,
                    "place": 1,
                },
                {
                    "event": "Event 2",
                    "swimmer": "Opponent Y",
                    "team": "Opponent",
                    "points": 4.0,
                    "place": 2,
                },
            ],
            "seton_score": 12.0,  # Total score
            "opponent_score": 8.0,  # Total score
        },
    }

    # Execute formatting
    response = format_dual_meet_response(
        result=result_data,
        seton_score=12.0,
        opponent_score=8.0,
        optimization_time_ms=100.0,
        method="test_method",
    )

    # Assertions
    assert response.success is True
    assert len(response.results) == 2

    # Check Event 1
    event1 = next(r for r in response.results if r.event == "Event 1")
    # The projected score for the EVENT should be 6, not 12
    assert event1.projected_score["seton"] == 6.0
    assert event1.projected_score["opponent"] == 4.0
    assert event1.seton_points == [6.0]

    # Check Event 2
    event2 = next(r for r in response.results if r.event == "Event 2")
    assert event2.projected_score["seton"] == 6.0
    assert event2.projected_score["opponent"] == 4.0

    # Check Total Score
    assert response.seton_score == 12.0


def test_format_dual_meet_name_matching():
    """Test robust name matching logic."""
    result_data = {
        "success": True,
        "data": {
            "best_lineup": [
                {
                    "event": "50 Free",
                    "team": "seton",
                    "swimmer": "John Smith",
                    "time": "22.50",
                },
            ],
            "opponent_lineup": [],
            "details": [
                # Mismatch case/spacing
                {
                    "event": "50 Free",
                    "swimmer": "john smith ",
                    "team": "Seton School",
                    "points": 5.0,
                }
            ],
        },
    }

    response = format_dual_meet_response(
        result=result_data,
        seton_score=5.0,
        opponent_score=0.0,
        optimization_time_ms=10,
        method="test",
    )

    res = response.results[0]
    assert res.seton_points == [5.0]  # Should match despite case/space differences
