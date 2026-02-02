"""
Swimmer Trajectory Predictor

Predicts swimmer time improvements/declines over a season.
Uses historical data to model performance curves.
"""

import math
from datetime import date, timedelta

from pydantic import BaseModel, Field

from swim_ai_reflex.backend.models.swimmer import TimeRecord


class TrajectoryPoint(BaseModel):
    """A point on a swimmer's performance trajectory."""

    date: date
    time: float
    is_predicted: bool = False
    confidence: float = Field(default=0.8, ge=0, le=1)


class SwimmerTrajectory(BaseModel):
    """Performance trajectory for a swimmer in an event."""

    swimmer: str
    event: str

    # Historical data
    data_points: list[TrajectoryPoint] = Field(default_factory=list)

    # Trend analysis
    trend: str = "stable"  # "improving", "stable", "declining"
    improvement_rate: float = Field(
        default=0.0, description="Seconds per month improvement (negative = faster)"
    )

    # Predictions
    predicted_times: list[TrajectoryPoint] = Field(default_factory=list)

    # Plateau detection
    has_plateaued: bool = False
    plateau_start: date | None = None


class TrajectoryPredictor:
    """
    Predicts swimmer time evolution over a season.

    Uses linear regression with age-based adjustment factors
    to estimate future performance.
    """

    # Age-based improvement factors (seconds per month, negative = faster)
    AGE_FACTORS = {
        12: -0.5,  # Young swimmers improve fast
        13: -0.4,
        14: -0.3,
        15: -0.2,
        16: -0.15,
        17: -0.1,
        18: -0.05,  # Seniors plateau
    }

    # Event-specific variance (some events are more stable)
    EVENT_STABILITY = {
        "50 Free": 0.8,  # Very stable
        "100 Free": 0.75,
        "200 Free": 0.7,
        "500 Free": 0.65,  # More variance
        "100 Back": 0.7,
        "100 Breast": 0.7,
        "100 Fly": 0.65,  # Technique-dependent
        "200 IM": 0.6,  # Most variable
    }

    def analyze_trajectory(
        self, swimmer: str, event: str, times: list[TimeRecord], grade: int = 12
    ) -> SwimmerTrajectory:
        """
        Analyze a swimmer's performance trajectory.

        Args:
            swimmer: Swimmer name
            event: Event name
            times: List of historical times
            grade: Current grade (for age adjustment)

        Returns:
            SwimmerTrajectory with trend analysis
        """
        if not times:
            return SwimmerTrajectory(swimmer=swimmer, event=event)

        # Sort by date
        sorted_times = sorted(times, key=lambda t: t.meet_date)

        # Convert to trajectory points
        data_points = [
            TrajectoryPoint(date=t.meet_date, time=t.time) for t in sorted_times
        ]

        # Calculate trend
        trend, rate = self._calculate_trend(sorted_times)

        # Detect plateau
        has_plateau, plateau_date = self._detect_plateau(sorted_times)

        # Generate predictions
        predictions = self._predict_future(sorted_times, grade, months_ahead=3)

        return SwimmerTrajectory(
            swimmer=swimmer,
            event=event,
            data_points=data_points,
            trend=trend,
            improvement_rate=rate,
            predicted_times=predictions,
            has_plateaued=has_plateau,
            plateau_start=plateau_date,
        )

    def _calculate_trend(self, times: list[TimeRecord]) -> tuple[str, float]:
        """Calculate trend using linear regression."""
        if len(times) < 2:
            return "stable", 0.0

        # Simple linear regression
        n = len(times)
        first_date = times[0].meet_date

        x = [(t.meet_date - first_date).days / 30 for t in times]  # Months
        y = [t.time for t in times]

        mean_x = sum(x) / n
        mean_y = sum(y) / n

        numerator = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
        denominator = sum((xi - mean_x) ** 2 for xi in x)

        if denominator == 0:
            return "stable", 0.0

        slope = numerator / denominator  # Seconds per month

        if slope < -0.1:
            return "improving", slope
        elif slope > 0.1:
            return "declining", slope
        else:
            return "stable", slope

    def _detect_plateau(self, times: list[TimeRecord]) -> tuple[bool, date | None]:
        """Detect if swimmer has plateaued."""
        if len(times) < 4:
            return False, None

        # Look at last 4 times
        recent = times[-4:]
        recent_times = [t.time for t in recent]

        # Calculate variance
        mean_time = sum(recent_times) / len(recent_times)
        variance = sum((t - mean_time) ** 2 for t in recent_times) / len(recent_times)
        std_dev = math.sqrt(variance)

        # Low variance + no improvement = plateau
        if std_dev < 0.5 and max(recent_times) - min(recent_times) < 1.0:
            return True, recent[0].meet_date

        return False, None

    def _predict_future(
        self, times: list[TimeRecord], grade: int, months_ahead: int = 3
    ) -> list[TrajectoryPoint]:
        """Predict future times."""
        if not times:
            return []

        # Get current best and trend
        best_time = min(t.time for t in times)
        _, rate = self._calculate_trend(times)

        # Adjust rate by age
        age_factor = self.AGE_FACTORS.get(grade + 6, 0.0)  # Grade to age
        adjusted_rate = rate * 0.5 + age_factor * 0.5  # Blend

        predictions = []
        today = date.today()

        for month in range(1, months_ahead + 1):
            future_date = today + timedelta(days=30 * month)
            predicted_time = best_time + adjusted_rate * month

            # Confidence decreases with distance
            confidence = max(0.3, 0.9 - 0.15 * month)

            predictions.append(
                TrajectoryPoint(
                    date=future_date,
                    time=round(predicted_time, 2),
                    is_predicted=True,
                    confidence=confidence,
                )
            )

        return predictions

    def predict_time(
        self,
        swimmer: str,
        event: str,
        target_date: date,
        historical_times: list[TimeRecord],
        grade: int = 12,
    ) -> tuple[float, float]:
        """
        Predict time at a specific future date.

        Returns:
            (predicted_time, confidence)
        """
        trajectory = self.analyze_trajectory(swimmer, event, historical_times, grade)

        if not trajectory.data_points:
            return 0.0, 0.0

        # Find closest prediction
        for pred in trajectory.predicted_times:
            if pred.date >= target_date:
                return pred.time, pred.confidence

        # If beyond predictions, extrapolate with low confidence
        if trajectory.predicted_times:
            last_pred = trajectory.predicted_times[-1]
            months_beyond = (target_date - last_pred.date).days / 30
            extrapolated = last_pred.time + trajectory.improvement_rate * months_beyond
            return extrapolated, 0.3

        return trajectory.data_points[-1].time, 0.5


# Singleton instance
trajectory_predictor = TrajectoryPredictor()
