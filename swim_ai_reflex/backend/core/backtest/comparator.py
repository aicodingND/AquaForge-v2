"""Compare optimizer predictions against actual meet results."""

from __future__ import annotations

from swim_ai_reflex.backend.core.backtest.loader import actual_results_to_scoring_df
from swim_ai_reflex.backend.core.backtest.schemas import (
    ActualMeetResults,
    BacktestReport,
    EventComparison,
    PredictionSnapshot,
    SwimmerComparison,
)
from swim_ai_reflex.backend.core.rules import get_meet_profile
from swim_ai_reflex.backend.core.strategies.aqua_optimizer import (
    FatigueModel,
    ScoringEngine,
    ScoringProfile,
)


def compare_prediction_vs_actual(
    prediction: PredictionSnapshot,
    actual: ActualMeetResults,
    target_team: str = "SST",
) -> BacktestReport:
    """Compare a saved optimizer prediction against actual meet results.

    Uses the same ScoringEngine as the optimizer for unified re-scoring,
    following the pattern established in compare_visaa_2026_gurobi_vs_aqua.py.

    The comparison works by:
    1. Loading actual results into scoring-compatible DataFrames
    2. Scoring the prediction's assignments against the actual opponent field
    3. Comparing per-event and per-swimmer results
    """
    # Build scoring engine from meet profile
    rules = get_meet_profile(actual.meet_profile)
    profile = ScoringProfile.from_rules(rules)
    engine = ScoringEngine(profile, FatigueModel(enabled=False))

    # Convert actual results to optimizer-compatible DataFrames
    actual_seton_df, actual_opp_df = actual_results_to_scoring_df(actual, target_team)

    # Collect all events
    pred_events: set[str] = set()
    for events_list in prediction.assignments.values():
        for e in events_list:
            pred_events.add(e)
    actual_events = {evt.full_event_name for evt in actual.events}
    all_events = sorted(pred_events | actual_events)

    event_comparisons: list[EventComparison] = []
    predicted_total = 0.0
    actual_total = 0.0

    for event_name in all_events:
        is_relay = "Relay" in event_name

        # Predicted entries for this event
        pred_swimmers = [
            s for s, evts in prediction.assignments.items() if event_name in evts
        ]

        # Actual Seton entries for this event
        actual_seton_entries: list[str] = []
        actual_seton_records: list[dict] = []
        if not actual_seton_df.empty:
            mask = actual_seton_df["event"] == event_name
            for _, row in actual_seton_df[mask].iterrows():
                actual_seton_records.append(row.to_dict())
                actual_seton_entries.append(str(row["swimmer"]))

        # Actual opponent entries
        actual_opp_records: list[dict] = []
        if not actual_opp_df.empty:
            mask = actual_opp_df["event"] == event_name
            actual_opp_records = actual_opp_df[mask].to_dict("records")

        # Score actual
        actual_s_pts, _, _ = engine.score_event(
            actual_seton_records,
            actual_opp_records,
            is_relay=is_relay,
            event_name=event_name,
        )
        actual_total += actual_s_pts

        # Score predicted assignments against actual opponent field
        pred_seton_records: list[dict] = []
        if not actual_seton_df.empty:
            for swimmer in pred_swimmers:
                row = actual_seton_df[
                    (actual_seton_df["swimmer"] == swimmer)
                    & (actual_seton_df["event"] == event_name)
                ]
                if not row.empty:
                    pred_seton_records.append(row.iloc[0].to_dict())

        pred_s_pts, _, _ = engine.score_event(
            pred_seton_records,
            actual_opp_records,
            is_relay=is_relay,
            event_name=event_name,
        )
        predicted_total += pred_s_pts

        event_comparisons.append(
            EventComparison(
                event_name=event_name,
                predicted_seton_points=pred_s_pts,
                actual_seton_points=actual_s_pts,
                predicted_seton_entries=pred_swimmers,
                actual_seton_entries=actual_seton_entries,
                delta=actual_s_pts - pred_s_pts,
            )
        )

    # Build swimmer-level comparison
    swimmer_comparisons = _build_swimmer_comparisons(prediction, actual, target_team)

    # Aggregate metrics
    match_count = sum(1 for sc in swimmer_comparisons if sc.status == "MATCH")
    total_swimmers = len(swimmer_comparisons)
    match_rate = match_count / total_swimmers if total_swimmers > 0 else 0.0

    score_delta = actual_total - predicted_total
    accuracy_pct = (
        (100 - abs(score_delta) / actual_total * 100) if actual_total > 0 else 0.0
    )

    return BacktestReport(
        meet_id=actual.meet_id,
        meet_name=actual.meet_name,
        optimizer=prediction.optimizer,
        predicted_seton_total=predicted_total,
        actual_seton_total=actual_total,
        score_delta=score_delta,
        score_accuracy_pct=max(0.0, accuracy_pct),
        event_comparisons=event_comparisons,
        swimmer_comparisons=swimmer_comparisons,
        assignment_match_rate=match_rate,
    )


def _build_swimmer_comparisons(
    prediction: PredictionSnapshot,
    actual: ActualMeetResults,
    target_team: str,
) -> list[SwimmerComparison]:
    """Build per-swimmer comparison across all events."""
    # Collect actual swimmer events and points
    actual_swimmer_events: dict[str, list[str]] = {}
    actual_swimmer_points: dict[str, float] = {}
    for evt in actual.events:
        for r in evt.results:
            if r.team.upper() == target_team.upper() and not r.dq:
                actual_swimmer_events.setdefault(r.swimmer, []).append(
                    evt.full_event_name
                )
                actual_swimmer_points[r.swimmer] = (
                    actual_swimmer_points.get(r.swimmer, 0.0) + r.points
                )

    all_swimmers = sorted(
        set(prediction.assignments.keys()) | set(actual_swimmer_events.keys())
    )

    comparisons: list[SwimmerComparison] = []
    for swimmer in all_swimmers:
        pred_evts = sorted(prediction.assignments.get(swimmer, []))
        actual_evts = sorted(actual_swimmer_events.get(swimmer, []))

        if pred_evts == actual_evts:
            status = "MATCH"
        elif not pred_evts:
            status = "actual_only"
        elif not actual_evts:
            status = "predicted_only"
        else:
            status = "DIFFER"

        comparisons.append(
            SwimmerComparison(
                swimmer=swimmer,
                team=target_team,
                predicted_events=pred_evts,
                actual_events=actual_evts,
                actual_points=actual_swimmer_points.get(swimmer, 0.0),
                status=status,
            )
        )

    return comparisons
