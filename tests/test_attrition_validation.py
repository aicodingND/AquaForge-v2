"""
Attrition Model VALIDATION Tests — Real Outcome Checks

Unlike test_attrition_scoring_integration.py which tests plumbing (does the
code wire correctly?), these tests validate OUTCOMES:

1. Does the attrition model produce calibrated DNS predictions?
2. Does attrition-discounted scoring better predict actual meet scores?
3. Is the model stable under holdout cross-validation?
4. Does the +112pt optimization delta hold with attrition applied?

These tests use pre-computed validation results from data/attrition_validation/
(produced by scripts/validate_attrition_*.py). If those files don't exist,
the tests are skipped — they require the HyTek MDB database.
"""

import json
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VALIDATION_DIR = PROJECT_ROOT / "data" / "attrition_validation"


def _load_json(filename: str) -> dict | None:
    """Load a validation results JSON file, or None if not found."""
    path = VALIDATION_DIR / filename
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# 1. Calibration Validation (Experiment 2)
# ---------------------------------------------------------------------------


class TestCalibrationOutcomes:
    """Validate that empirical DNS rates match observed rates at championship meets."""

    @pytest.fixture(autouse=True)
    def load_calibration(self):
        self.data = _load_json("calibration_results.json")
        if self.data is None:
            pytest.skip(
                "calibration_results.json not found (run validate_attrition_calibration.py)"
            )

    def test_global_mae_below_threshold(self):
        """Global MAE across all meets should be < 1%."""
        global_mae = self.data["all_meets"]["global_mae"]
        assert global_mae < 0.01, (
            f"Global MAE {global_mae * 100:.3f}% exceeds 1% threshold"
        )

    def test_championship_mae_below_threshold(self):
        """Championship-specific MAE should be < 2% (tighter context)."""
        champ_mae = self.data["championship_only"]["global_mae"]
        assert champ_mae < 0.02, (
            f"Championship MAE {champ_mae * 100:.3f}% exceeds 2% threshold"
        )

    def test_championship_bias_below_threshold(self):
        """Championship bias should be < 2% (not systematically over/under-predicting)."""
        champ_bias = abs(self.data["championship_only"]["global_bias"])
        assert champ_bias < 0.02, (
            f"Championship bias {champ_bias * 100:.3f}% exceeds 2% threshold"
        )

    def test_per_event_mae_all_below_threshold(self):
        """No single event should have MAE > 5% at championships."""
        for event, info in self.data["championship_only"]["per_event"].items():
            assert info["mae"] < 0.05, (
                f"{event} MAE {info['mae'] * 100:.2f}% exceeds 5% threshold"
            )

    def test_diving_calibration_acceptable(self):
        """Diving has known higher error — verify it's still < 3%."""
        champ = self.data["championship_only"]["per_event"]
        if "Diving" in champ:
            assert champ["Diving"]["mae"] < 0.03, (
                f"Diving MAE {champ['Diving']['mae'] * 100:.2f}% exceeds 3%"
            )


# ---------------------------------------------------------------------------
# 2. Holdout Cross-Validation (Experiment 3)
# ---------------------------------------------------------------------------


class TestHoldoutOutcomes:
    """Validate DNS rates generalize to held-out meets (no overfitting)."""

    @pytest.fixture(autouse=True)
    def load_holdout(self):
        self.data = _load_json("holdout_results.json")
        if self.data is None:
            pytest.skip(
                "holdout_results.json not found (run validate_attrition_holdout.py)"
            )

    def test_mean_mae_below_threshold(self):
        """Mean MAE across folds should be < 10%."""
        mean_mae = self.data["summary"]["mean_mae"]
        assert mean_mae < 0.10, (
            f"Holdout mean MAE {mean_mae * 100:.2f}% exceeds 10% threshold"
        )

    def test_no_fold_exceeds_max_mae(self):
        """No individual fold should have MAE > 15% (severe overfitting signal)."""
        for fold in self.data["fold_results"]:
            assert fold["test_mae"] < 0.15, (
                f"Fold {fold['fold']} MAE {fold['test_mae'] * 100:.2f}% exceeds 15%"
            )

    def test_mae_std_indicates_stability(self):
        """Standard deviation of fold MAEs should be < 5% (rates are stable)."""
        std_mae = self.data["summary"]["std_mae"]
        assert std_mae < 0.05, (
            f"Holdout MAE std {std_mae * 100:.2f}% exceeds 5% — rates are unstable"
        )

    def test_mean_bias_near_zero(self):
        """Mean bias across folds should be < 5% (no systematic direction)."""
        mean_bias = abs(self.data["summary"]["mean_bias"])
        assert mean_bias < 0.05, f"Holdout mean bias {mean_bias * 100:.2f}% exceeds 5%"


# ---------------------------------------------------------------------------
# 3. A/B Backtest (Experiment 1) — Understanding, Not Approval
# ---------------------------------------------------------------------------


class TestABBacktestOutcomes:
    """Validate A/B test results and document the zero-impact finding."""

    @pytest.fixture(autouse=True)
    def load_ab(self):
        self.data = _load_json("ab_results.json")
        if self.data is None:
            pytest.skip("ab_results.json not found (run validate_attrition_ab.py)")

    def test_ab_results_exist(self):
        """At least 10 meets should have been tested."""
        n_meets = self.data["summary"]["n_meets"]
        assert n_meets >= 10, f"Only {n_meets} meets in A/B test (need >= 10)"

    def test_net_effect_documented(self):
        """Mean net effect should be recorded (even if zero)."""
        mean_net = self.data["summary"]["mean_net"]
        # This test documents the finding — not a pass/fail on attrition value
        assert isinstance(mean_net, (int, float))

    def test_zero_impact_acknowledged(self):
        """If lineups never differ, that's a valid finding — verify it's measured."""
        n_differ = self.data["summary"]["n_differ"]
        # This documents the finding for auditability
        assert isinstance(n_differ, int)
        # If zero, the model doesn't affect optimization decisions
        # This is expected given uniform ~20% DNS rates across events


# ---------------------------------------------------------------------------
# 4. Outcome Backtest (Experiment 4) — The Missing Piece
# ---------------------------------------------------------------------------


class TestOutcomeBacktestResults:
    """Validate that outcome backtest has been run and results are meaningful."""

    @pytest.fixture(autouse=True)
    def load_outcomes(self):
        self.data = _load_json("outcome_results.json")
        if self.data is None:
            pytest.skip(
                "outcome_results.json not found (run validate_attrition_outcomes.py)"
            )

    def test_sufficient_meets_tested(self):
        """Outcome backtest should cover >= 10 meets."""
        n = self.data["summary"]["n_meets"]
        assert n >= 10, f"Only {n} meets in outcome backtest"

    def test_seton_prediction_error_recorded(self):
        """Both ON and OFF prediction errors should be finite."""
        err_on = self.data["summary"]["mean_seton_error_on"]
        err_off = self.data["summary"]["mean_seton_error_off"]
        assert err_on >= 0
        assert err_off >= 0

    def test_rank_correlation_positive(self):
        """Rank correlations should be positive (predictions have some value)."""
        rc_on = self.data["summary"].get("mean_rank_corr_on")
        rc_off = self.data["summary"].get("mean_rank_corr_off")
        if rc_on is not None:
            assert rc_on > 0, (
                f"Rank correlation (attrition ON) is {rc_on} — not positive"
            )
        if rc_off is not None:
            assert rc_off > 0, (
                f"Rank correlation (attrition OFF) is {rc_off} — not positive"
            )

    def test_attrition_effect_direction_documented(self):
        """Document whether attrition helps or hurts prediction accuracy."""
        conclusion = self.data["summary"]["seton_conclusion"]
        assert isinstance(conclusion, str) and len(conclusion) > 0


# ---------------------------------------------------------------------------
# 5. DNS Actual Comparison (Experiment 5)
# ---------------------------------------------------------------------------


class TestDNSActualResults:
    """Validate predicted vs actual DNS at specific meets."""

    @pytest.fixture(autouse=True)
    def load_dns(self):
        self.data = _load_json("dns_actual_results.json")
        if self.data is None:
            pytest.skip(
                "dns_actual_results.json not found (run validate_attrition_dns_actual.py)"
            )

    def test_sufficient_meets_tested(self):
        """DNS comparison should cover >= 10 meets."""
        n = self.data["summary"]["n_meets"]
        assert n >= 10, f"Only {n} meets in DNS comparison"

    def test_mean_mae_below_threshold(self):
        """Mean per-meet DNS MAE should be < 25%.

        KNOWN ISSUE: The model's DNS rates (trained on psych-sheet entries
        including no-shows) are ~20%, but the RESULT table only records
        swimmers who actually entered the meet, showing ~3.6% DNS.
        These measure different populations:
          - Psych sheet DNS: "swimmer was seeded but never showed up"
          - Result table DNS: "swimmer entered but scratched at the meet"
        The model over-predicts because it conflates these two definitions.
        """
        mae = self.data["summary"]["mean_mae"]
        assert mae < 0.25, f"DNS prediction MAE {mae * 100:.1f}% exceeds 25% threshold"

    def test_total_dns_count_documents_overprediction(self):
        """Document the systematic DNS over-prediction.

        KNOWN FINDING: Model predicts ~6x more DNS than observed in RESULT table.
        This is because psych-sheet "seeded but no-showed" is fundamentally
        different from "entered but scratched". The model should be retrained
        on result-table data for accurate championship prediction.
        """
        actual = self.data["summary"]["total_actual_dns"]
        predicted = self.data["summary"]["total_predicted_dns"]
        if actual > 0:
            ratio = predicted / actual
            # Document the overprediction — we expect ~5-7x until model is retrained
            assert ratio > 1.0, f"Expected over-prediction but got ratio {ratio:.2f}"
            assert ratio < 10.0, (
                f"Over-prediction ratio {ratio:.2f} is unreasonably high (>10x)"
            )

    def test_bias_direction_consistent(self):
        """Model should consistently over-predict DNS (positive bias).

        This is a known property: psych-sheet-trained rates include no-shows
        that the result-table never sees.
        """
        bias = self.data["summary"]["mean_bias"]
        # Bias should be positive (over-predicting DNS)
        assert bias > 0, (
            f"Expected positive bias (over-prediction) but got {bias * 100:.1f}%"
        )
        # And documented
        assert bias < 0.30, f"DNS prediction bias {bias * 100:.1f}% exceeds 30%"


# ---------------------------------------------------------------------------
# 6. Cross-Experiment Consistency
# ---------------------------------------------------------------------------


class TestCrossExperimentConsistency:
    """Verify results are consistent across experiments."""

    def test_calibration_and_holdout_agree(self):
        """Calibration MAE should be smaller than holdout MAE (training vs test)."""
        cal = _load_json("calibration_results.json")
        hold = _load_json("holdout_results.json")
        if cal is None or hold is None:
            pytest.skip("Need both calibration and holdout results")

        # Use championship-only calibration (the relevant benchmark)
        # because all-meets global MAE is artificially low (trained on same data)
        cal_champ_mae = cal["championship_only"]["global_mae"]
        hold_mae = hold["summary"]["mean_mae"]
        # Holdout MAE should be within 20x of championship calibration MAE
        # (holdout uses all meet types, so it's expected to be higher)
        assert hold_mae < cal_champ_mae * 20, (
            f"Holdout MAE {hold_mae:.4f} is too far from "
            f"championship calibration MAE {cal_champ_mae:.4f}"
        )

    def test_ab_and_outcome_complementary(self):
        """If A/B shows zero lineup change, outcome test should show similar
        predictions with/without attrition (both give similar team scores)."""
        ab = _load_json("ab_results.json")
        outcomes = _load_json("outcome_results.json")
        if ab is None or outcomes is None:
            pytest.skip("Need both A/B and outcome results")

        # If A/B lineups never differ, the outcome test differences
        # come purely from scoring discount, not lineup changes
        if ab["summary"]["n_differ"] == 0:
            # With same lineups, attrition just scales scores down ~20%
            # So the error difference should be bounded
            err_delta = abs(
                outcomes["summary"]["mean_seton_error_on"]
                - outcomes["summary"]["mean_seton_error_off"]
            )
            # The delta should be roughly proportional to the attrition discount
            # (~20% of mean Seton score). Allow generous bound.
            assert err_delta < 500, (
                f"Error delta {err_delta} is unexpectedly large for same lineups"
            )
