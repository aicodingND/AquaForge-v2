"""Tests for backtesting infrastructure: loader, comparator, report generator."""

import json
from pathlib import Path

import pytest

from swim_ai_reflex.backend.core.backtest.comparator import (
    compare_prediction_vs_actual,
)
from swim_ai_reflex.backend.core.backtest.loader import (
    actual_results_to_scoring_df,
    load_actual_results_json,
    load_prediction_snapshot,
    parse_time_to_seconds,
)
from swim_ai_reflex.backend.core.backtest.report_generator import (
    generate_csv_report,
    generate_json_report,
    generate_markdown_report,
)
from swim_ai_reflex.backend.core.backtest.schemas import (
    ActualMeetResults,
    BacktestReport,
    EventResult,
    EventResults,
    PredictionSnapshot,
)


class TestTimeParsing:
    """Test parse_time_to_seconds with various input formats."""

    def test_float_passthrough(self):
        assert parse_time_to_seconds(25.03) == 25.03

    def test_int_passthrough(self):
        assert parse_time_to_seconds(25) == 25.0

    def test_minutes_seconds_format(self):
        assert parse_time_to_seconds("1:56.87") == pytest.approx(116.87)

    def test_seconds_only_string(self):
        assert parse_time_to_seconds("25.03") == 25.03

    def test_none_returns_none(self):
        assert parse_time_to_seconds(None) is None

    def test_empty_string_returns_none(self):
        assert parse_time_to_seconds("") is None

    def test_dq_returns_none(self):
        assert parse_time_to_seconds("DQ") is None

    def test_dns_returns_none(self):
        assert parse_time_to_seconds("DNS") is None

    def test_scr_returns_none(self):
        assert parse_time_to_seconds("SCR") is None

    def test_zero_returns_none(self):
        assert parse_time_to_seconds(0) is None

    def test_negative_returns_none(self):
        assert parse_time_to_seconds(-1.0) is None

    def test_five_minutes_format(self):
        assert parse_time_to_seconds("5:23.45") == pytest.approx(323.45)


class TestLoadActualResults:
    """Test JSON loading and conversion to DataFrames."""

    @pytest.fixture
    def sample_results_path(self, tmp_path: Path) -> Path:
        data = {
            "meet_id": "test_meet",
            "meet_name": "Test Championship",
            "meet_date": "2026-02-12",
            "meet_profile": "visaa_state",
            "source": "unit test",
            "team_scores": {
                "SST": {"boys": 100, "girls": 80, "combined": 180},
                "OAK": {"boys": 90, "girls": 85, "combined": 175},
            },
            "events": [
                {
                    "event_name": "50 Free",
                    "gender": "Boys",
                    "event_type": "individual",
                    "results": [
                        {
                            "place": 1,
                            "swimmer": "Fast Guy",
                            "team": "OAK",
                            "time": 21.5,
                            "points": 20,
                        },
                        {
                            "place": 2,
                            "swimmer": "Our Guy",
                            "team": "SST",
                            "time": 22.0,
                            "points": 17,
                        },
                        {
                            "place": 3,
                            "swimmer": "Slow Guy",
                            "team": "OAK",
                            "time": 23.0,
                            "points": 16,
                        },
                    ],
                },
                {
                    "event_name": "100 Free",
                    "gender": "Girls",
                    "event_type": "individual",
                    "results": [
                        {
                            "place": 1,
                            "swimmer": "Fast Girl",
                            "team": "SST",
                            "time": 55.0,
                            "points": 20,
                        },
                        {
                            "place": 2,
                            "swimmer": "Other Girl",
                            "team": "OAK",
                            "time": 56.0,
                            "points": 17,
                        },
                        {
                            "place": 3,
                            "swimmer": "DQ Girl",
                            "team": "SST",
                            "time": None,
                            "points": 0,
                            "dq": True,
                        },
                    ],
                },
            ],
        }
        path = tmp_path / "actual_results.json"
        with open(path, "w") as f:
            json.dump(data, f)
        return path

    def test_load_json_basic(self, sample_results_path: Path):
        results = load_actual_results_json(sample_results_path)
        assert results.meet_id == "test_meet"
        assert results.meet_profile == "visaa_state"
        assert len(results.events) == 2
        assert results.events[0].full_event_name == "Boys 50 Free"

    def test_load_json_team_scores(self, sample_results_path: Path):
        results = load_actual_results_json(sample_results_path)
        assert results.team_scores["SST"]["combined"] == 180

    def test_load_json_event_results(self, sample_results_path: Path):
        results = load_actual_results_json(sample_results_path)
        boys_50 = results.events[0]
        assert len(boys_50.results) == 3
        assert boys_50.results[0].swimmer == "Fast Guy"
        assert boys_50.results[0].time == 21.5

    def test_conversion_to_scoring_df(self, sample_results_path: Path):
        results = load_actual_results_json(sample_results_path)
        seton_df, opp_df = actual_results_to_scoring_df(results, "SST")

        # SST has 2 scoring entries (DQ excluded)
        assert len(seton_df) == 2
        # Opponents have 3 entries (Fast Guy, Slow Guy, Other Girl)
        assert len(opp_df) == 3

    def test_dq_entries_excluded_from_df(self, sample_results_path: Path):
        results = load_actual_results_json(sample_results_path)
        seton_df, _ = actual_results_to_scoring_df(results, "SST")
        assert "DQ Girl" not in seton_df["swimmer"].values


class TestLoadPredictionSnapshot:
    """Test prediction snapshot loading."""

    @pytest.fixture
    def sample_prediction_path(self, tmp_path: Path) -> Path:
        data = {
            "meet_id": "test_meet",
            "optimizer": "aqua",
            "meet_profile": "visaa_state",
            "timestamp": "2026-02-10T14:30:00",
            "solve_time_ms": 1500.0,
            "quality_mode": "balanced",
            "assignments": {
                "Our Guy": ["Boys 50 Free", "Boys 100 Free"],
                "Fast Girl": ["Girls 100 Free"],
            },
            "predicted_scores": {"seton": 180.0, "opponent": 1500.0},
            "event_breakdown": {},
        }
        path = tmp_path / "prediction.json"
        with open(path, "w") as f:
            json.dump(data, f)
        return path

    def test_load_prediction(self, sample_prediction_path: Path):
        pred = load_prediction_snapshot(sample_prediction_path)
        assert pred.meet_id == "test_meet"
        assert pred.optimizer == "aqua"
        assert "Our Guy" in pred.assignments
        assert len(pred.assignments["Our Guy"]) == 2


class TestComparator:
    """Test the comparison engine."""

    def _make_actual(self) -> ActualMeetResults:
        return ActualMeetResults(
            meet_id="test",
            meet_name="Test Meet",
            meet_date="2026-01-01",
            meet_profile="visaa_dual",
            events=[
                EventResults(
                    event_name="50 Free",
                    gender="Boys",
                    event_type="individual",
                    results=[
                        EventResult(
                            place=1,
                            swimmer="Swimmer A",
                            team="SST",
                            time=22.0,
                            points=8,
                        ),
                        EventResult(
                            place=2, swimmer="Opp 1", team="OPP", time=23.0, points=6
                        ),
                        EventResult(
                            place=3,
                            swimmer="Swimmer B",
                            team="SST",
                            time=24.0,
                            points=5,
                        ),
                        EventResult(
                            place=4, swimmer="Opp 2", team="OPP", time=25.0, points=4
                        ),
                    ],
                ),
            ],
        )

    def _make_prediction(self) -> PredictionSnapshot:
        return PredictionSnapshot(
            meet_id="test",
            optimizer="aqua",
            meet_profile="visaa_dual",
            assignments={
                "Swimmer A": ["Boys 50 Free"],
                "Swimmer B": ["Boys 50 Free"],
            },
            predicted_scores={"seton": 13.0},
        )

    def test_comparison_produces_report(self):
        actual = self._make_actual()
        prediction = self._make_prediction()
        report = compare_prediction_vs_actual(prediction, actual)

        assert isinstance(report, BacktestReport)
        assert report.meet_id == "test"
        assert report.optimizer == "aqua"
        assert report.actual_seton_total > 0

    def test_swimmer_comparison_match(self):
        actual = self._make_actual()
        prediction = self._make_prediction()
        report = compare_prediction_vs_actual(prediction, actual)

        # Both swimmers were predicted for Boys 50 Free and actually swam it
        matches = [sc for sc in report.swimmer_comparisons if sc.status == "MATCH"]
        assert len(matches) >= 1

    def test_event_comparison(self):
        actual = self._make_actual()
        prediction = self._make_prediction()
        report = compare_prediction_vs_actual(prediction, actual)

        assert len(report.event_comparisons) >= 1
        ec = report.event_comparisons[0]
        assert ec.event_name == "Boys 50 Free"
        assert ec.actual_seton_points > 0


class TestReportGenerator:
    """Test report generation in various formats."""

    @pytest.fixture
    def sample_report(self) -> BacktestReport:
        from swim_ai_reflex.backend.core.backtest.schemas import (
            EventComparison,
            SwimmerComparison,
        )

        return BacktestReport(
            meet_id="test",
            meet_name="Test Championship",
            optimizer="aqua",
            predicted_seton_total=150.0,
            actual_seton_total=145.0,
            score_delta=-5.0,
            score_accuracy_pct=96.6,
            event_comparisons=[
                EventComparison(
                    event_name="Boys 50 Free",
                    predicted_seton_points=20.0,
                    actual_seton_points=17.0,
                    predicted_seton_entries=["Swimmer A"],
                    actual_seton_entries=["Swimmer A"],
                    delta=-3.0,
                ),
            ],
            swimmer_comparisons=[
                SwimmerComparison(
                    swimmer="Swimmer A",
                    team="SST",
                    predicted_events=["Boys 50 Free"],
                    actual_events=["Boys 50 Free"],
                    actual_points=17.0,
                    status="MATCH",
                ),
            ],
            assignment_match_rate=1.0,
        )

    def test_markdown_report(self, sample_report: BacktestReport, tmp_path: Path):
        path = generate_markdown_report(sample_report, tmp_path / "report.md")
        assert path.exists()
        content = path.read_text()
        assert "Test Championship" in content
        assert "Predicted SST Total" in content
        assert "Boys 50 Free" in content

    def test_json_report(self, sample_report: BacktestReport, tmp_path: Path):
        path = generate_json_report(sample_report, tmp_path / "report.json")
        assert path.exists()
        with open(path) as f:
            data = json.load(f)
        assert data["meet_id"] == "test"
        assert data["predicted_seton_total"] == 150.0
        assert len(data["event_comparisons"]) == 1

    def test_csv_report(self, sample_report: BacktestReport, tmp_path: Path):
        event_path, swimmer_path = generate_csv_report(sample_report, tmp_path)
        assert event_path.exists()
        assert swimmer_path.exists()
        # Check event CSV has content
        event_content = event_path.read_text()
        assert "Boys 50 Free" in event_content
        assert "event_name" in event_content  # header
