"""
Advanced Analytics Service

Provides deeper insights into team performance, trends, and optimization quality.
"""

import logging
from typing import Any

import numpy as np
import pandas as pd

from swim_ai_reflex.backend.core.rules import MeetRules
from swim_ai_reflex.backend.utils.helpers import normalize_team_name

logger = logging.getLogger(__name__)


class AdvancedAnalyticsService:
    """Advanced analytics for swim team optimization"""

    def calculate_lineup_efficiency(
        self, lineup: list[dict], max_possible_score: float
    ) -> dict:
        """
        Calculate how efficiently the lineup maximizes points.

        Returns efficiency metrics and improvement opportunities.
        """
        actual_score = sum(r.get("points", 0) for r in lineup)
        efficiency = (
            (actual_score / max_possible_score) * 100 if max_possible_score > 0 else 0
        )

        return {
            "efficiency_pct": efficiency,
            "points_earned": actual_score,
            "points_possible": max_possible_score,
            "points_left": max_possible_score - actual_score,
            "grade": self._get_efficiency_grade(efficiency),
        }

    def _get_efficiency_grade(self, efficiency: float) -> str:
        """Convert efficiency to letter grade"""
        if efficiency >= 95:
            return "A+"
        elif efficiency >= 90:
            return "A"
        elif efficiency >= 85:
            return "B+"
        elif efficiency >= 80:
            return "B"
        elif efficiency >= 75:
            return "C+"
        elif efficiency >= 70:
            return "C"
        else:
            return "D"

    def analyze_event_depth(self, roster: list[dict]) -> dict[str, list[dict]]:
        """
        Analyze team depth for each event.

        Returns number of competitive swimmers per event.
        """
        events: dict[str, list[dict]] = {}

        for swimmer in roster:
            event = swimmer.get("event", "Unknown")
            if event not in events:
                events[event] = []
            events[event].append(
                {"name": swimmer.get("name"), "time": swimmer.get("time"), "rank": None}
            )

        # Rank swimmers within each event
        for event, swimmers in events.items():
            sorted_swimmers = sorted(swimmers, key=lambda x: x["time"])
            for i, swimmer in enumerate(sorted_swimmers):
                swimmer["rank"] = i + 1
            events[event] = sorted_swimmers

        return events

    def predict_score_range(
        self, predicted_score: float, confidence: float = 0.85
    ) -> tuple[float, float]:
        """
        Predict score range based on uncertainty.

        Returns (low, high) score estimates.
        """
        std_dev = (1 - confidence) * predicted_score * 0.15

        low = max(0, predicted_score - (1.96 * std_dev))
        high = predicted_score + (1.96 * std_dev)

        return (round(low, 1), round(high, 1))

    def calculate_win_probability(
        self,
        seton_score: float,
        opponent_score: float,
        seton_variance: float = 5.0,
        opponent_variance: float = 5.0,
    ) -> float:
        """
        Calculate probability of winning based on predicted scores.

        Uses normal distribution assumptions.
        """
        score_diff = seton_score - opponent_score
        combined_std = np.sqrt(seton_variance**2 + opponent_variance**2)

        if combined_std > 0:
            z_score = score_diff / combined_std
            win_prob = 0.5 * (1 + np.tanh(z_score * 0.7))
        else:
            win_prob = 0.5 if score_diff == 0 else (1.0 if score_diff > 0 else 0.0)

        return round(win_prob, 3)

    def identify_improvement_opportunities(
        self, lineup: list[dict], roster: list[dict]
    ) -> list[dict]:
        """
        Identify potential lineup improvements.

        Returns list of suggested changes with expected point gains.
        """
        opportunities = []

        event_swimmers: dict[str, list[dict]] = {}
        for swimmer in roster:
            event = swimmer.get("event", "Unknown")
            if event not in event_swimmers:
                event_swimmers[event] = []
            event_swimmers[event].append(swimmer)

        for assignment in lineup:
            event = assignment.get("event")
            current_swimmer = assignment.get("swimmer")
            current_time = assignment.get("time", 999.99)

            if event in event_swimmers:
                for swimmer in event_swimmers[event]:
                    if swimmer.get("name") != current_swimmer:
                        swimmer_time = swimmer.get("time", 999.99)
                        if swimmer_time < current_time:
                            time_improvement = current_time - swimmer_time
                            opportunities.append(
                                {
                                    "event": event,
                                    "current_swimmer": current_swimmer,
                                    "suggested_swimmer": swimmer.get("name"),
                                    "time_improvement": round(time_improvement, 2),
                                    "priority": "high"
                                    if time_improvement > 2.0
                                    else "medium",
                                }
                            )

        opportunities.sort(key=lambda x: x["time_improvement"], reverse=True)

        return opportunities[:10]

    def calculate_fatigue_risk(self, swimmer_events: list[str]) -> dict:
        """
        Calculate fatigue risk for a swimmer based on event assignments.

        Returns risk assessment and recommendations.
        """
        num_events = len(swimmer_events)

        if num_events <= 2:
            risk_level = "low"
            fatigue_score = 0.2
        elif num_events == 3:
            risk_level = "medium"
            fatigue_score = 0.5
        elif num_events == 4:
            risk_level = "high"
            fatigue_score = 0.75
        else:
            risk_level = "critical"
            fatigue_score = 0.95

        return {
            "num_events": num_events,
            "risk_level": risk_level,
            "fatigue_score": fatigue_score,
            "recommended_max": 3,
            "recommendation": self._get_fatigue_recommendation(num_events),
        }

    def _get_fatigue_recommendation(self, num_events: int) -> str:
        """Get fatigue management recommendation"""
        if num_events <= 2:
            return "Optimal event load. Swimmer can perform at peak capacity."
        elif num_events == 3:
            return "Acceptable load. Monitor performance in later events."
        elif num_events == 4:
            return (
                "High load. Consider rest between events and focus on priority events."
            )
        else:
            return "Critical overload. Strongly recommend reducing event count."

    def generate_performance_report(
        self, lineup: list[dict], seton_score: float, opponent_score: float
    ) -> dict:
        """Generate comprehensive performance report"""

        total_swims = len(lineup)
        avg_points_per_swim = seton_score / total_swims if total_swims > 0 else 0

        point_distribution: dict[float, int] = {}
        for assignment in lineup:
            points = assignment.get("points", 0)
            if points not in point_distribution:
                point_distribution[points] = 0
            point_distribution[points] += 1

        return {
            "total_swims": total_swims,
            "total_points": seton_score,
            "opponent_points": opponent_score,
            "point_margin": seton_score - opponent_score,
            "avg_points_per_swim": round(avg_points_per_swim, 2),
            "win_probability": self.calculate_win_probability(
                seton_score, opponent_score
            ),
            "point_distribution": point_distribution,
            "efficiency_grade": self._get_efficiency_grade(
                (seton_score / (seton_score + opponent_score)) * 100
                if opponent_score > 0
                else 100
            ),
        }

    # ------------------------------------------------------------------
    # Point-swing analysis
    # ------------------------------------------------------------------

    def point_swing_analysis(
        self,
        scored_df: pd.DataFrame,
        totals: dict[str, float],
        rules: MeetRules | None = None,
    ) -> list[dict[str, Any]]:
        """
        For each event, analyse:
        1. Current point split (Seton vs opponent)
        2. How close opposing swimmers are (time gap to next place)
        3. Point swing potential
        4. Risk: if the opponent closes the gap
        5. Human-readable recommendation text

        Returns a list of dicts sorted by *swing_potential* (highest first).
        """
        if scored_df is None or scored_df.empty:
            return []

        df = scored_df.copy()
        df["team_norm"] = df["team"].apply(normalize_team_name)

        results: list[dict[str, Any]] = []

        for event_name, event_df in df.groupby("event"):
            is_relay = (
                event_df["is_relay"].any() if "is_relay" in event_df.columns else False
            )
            if is_relay:
                continue

            event_sorted = event_df.sort_values("time", ascending=True).reset_index(
                drop=True
            )

            seton_points_total = float(
                event_sorted.loc[event_sorted["team_norm"] == "seton", "points"].sum()
            )
            opp_points_total = float(
                event_sorted.loc[event_sorted["team_norm"] != "seton", "points"].sum()
            )
            point_differential = round(seton_points_total - opp_points_total, 2)

            swimmers_detail: list[dict[str, Any]] = []
            event_swing_potential: float = 0.0
            closest_gap: float = 999.0
            best_recommendation: str = ""
            best_swing: float = 0.0

            if rules is not None:
                points_map = list(rules.individual_points)
            else:
                points_map = [8, 6, 5, 4, 3, 2, 1]

            for idx, row in event_sorted.iterrows():
                place = int(row.get("place", 0))
                current_pts = float(row.get("points", 0.0))
                time_val = float(row["time"])
                swimmer_name = row["swimmer"]
                is_seton = row["team_norm"] == "seton"

                gap_to_next: float = 0.0
                points_if_improved: float = current_pts

                if place > 1 and is_seton:
                    ahead_rows = event_sorted[event_sorted["place"] == place - 1]
                    if not ahead_rows.empty:
                        ahead_time = float(ahead_rows.iloc[0]["time"])
                        gap_to_next = round(time_val - ahead_time, 2)

                        new_place = place - 1
                        points_if_improved = float(
                            points_map[new_place - 1]
                            if new_place <= len(points_map)
                            else 0.0
                        )
                        swing = points_if_improved - current_pts
                        if swing > 0:
                            event_swing_potential += swing

                        if 0 < gap_to_next < closest_gap:
                            closest_gap = gap_to_next

                        if swing > best_swing:
                            best_swing = swing
                            ahead_name = ahead_rows.iloc[0]["swimmer"]
                            best_recommendation = (
                                f"{swimmer_name} is {gap_to_next}s behind "
                                f"{ahead_name} for place {new_place}. "
                                f"Dropping {gap_to_next}s gains {swing:.0f} points."
                            )

                swimmers_detail.append(
                    {
                        "name": swimmer_name,
                        "team": row["team"],
                        "time": time_val,
                        "place": place,
                        "points": current_pts,
                        "gap_to_next": gap_to_next if is_seton else 0.0,
                        "points_if_improved": points_if_improved
                        if is_seton
                        else current_pts,
                    }
                )

            risk_gap = 999.0
            for idx, row in event_sorted.iterrows():
                if row["team_norm"] == "seton":
                    place = int(row.get("place", 0))
                    seton_time = float(row["time"])
                    behind_rows = event_sorted[event_sorted["place"] == place + 1]
                    if (
                        not behind_rows.empty
                        and behind_rows.iloc[0]["team_norm"] != "seton"
                    ):
                        opp_time = float(behind_rows.iloc[0]["time"])
                        gap = round(opp_time - seton_time, 2)
                        if 0 < gap < risk_gap:
                            risk_gap = gap

            if risk_gap < 0.5:
                risk_level = "high"
            elif risk_gap < 1.5:
                risk_level = "medium"
            else:
                risk_level = "low"

            if closest_gap >= 999.0:
                closest_gap = 0.0

            results.append(
                {
                    "event": event_name,
                    "seton_points": seton_points_total,
                    "opponent_points": opp_points_total,
                    "point_differential": point_differential,
                    "swing_potential": round(event_swing_potential, 2),
                    "risk_level": risk_level,
                    "closest_gap_seconds": closest_gap,
                    "recommendation": best_recommendation,
                    "swimmers": swimmers_detail,
                }
            )

        results.sort(key=lambda e: e["swing_potential"], reverse=True)
        return results

    def generate_coaching_summary(
        self,
        swing_analysis: list[dict[str, Any]],
        totals: dict[str, float],
    ) -> dict[str, Any]:
        """Generate a high-level coaching summary from swing analysis."""
        seton_score = totals.get("seton", 0.0)
        opp_score = totals.get("opponent", 0.0)
        margin = round(seton_score - opp_score, 2)

        if margin > 0:
            score_status = "winning"
        elif margin < 0:
            score_status = "losing"
        else:
            score_status = "tied"

        top_opportunities = [
            {
                "event": e["event"],
                "swing_potential": e["swing_potential"],
                "recommendation": e["recommendation"],
            }
            for e in swing_analysis[:3]
            if e["swing_potential"] > 0
        ]

        risk_events = [
            {
                "event": e["event"],
                "risk_level": e["risk_level"],
                "closest_gap_seconds": e["closest_gap_seconds"],
            }
            for e in swing_analysis
            if e["risk_level"] in ("high", "medium")
        ]

        total_swing = round(sum(e["swing_potential"] for e in swing_analysis), 2)

        focus_recommendations: list[str] = []
        for opp in top_opportunities:
            if opp["recommendation"]:
                focus_recommendations.append(opp["recommendation"])

        if not focus_recommendations and swing_analysis:
            focus_recommendations.append(
                "Maintain current lineup -- limited swing opportunities."
            )

        return {
            "score_status": score_status,
            "margin": margin,
            "top_opportunities": top_opportunities,
            "risk_events": risk_events,
            "total_swing_potential": total_swing,
            "focus_recommendations": focus_recommendations,
        }
