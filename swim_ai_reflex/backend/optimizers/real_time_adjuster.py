"""
Real-Time Mid-Meet Adjuster

Recommends lineup adjustments during a meet in response to:
- Scratches (opponent or our own)
- DQs (disqualifications)
- Unexpected results
- Strategic pivots
"""

from typing import List
from pydantic import BaseModel, Field
from datetime import datetime
import pandas as pd

from swim_ai_reflex.backend.core.scoring import EVENT_ORDER


class ScratchEvent(BaseModel):
    """A scratch event during a meet."""
    team: str  # "seton" or "opponent"
    swimmer: str
    original_event: str
    reason: str = "unknown"
    timestamp: datetime = Field(default_factory=datetime.now)


class DQEvent(BaseModel):
    """A disqualification event during a meet."""
    team: str
    swimmer: str
    event: str
    reason: str = "unknown"
    points_lost: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.now)


class AdjustmentRecommendation(BaseModel):
    """Recommended adjustment to lineup."""
    type: str  # "substitute", "re-order", "strategic_scratch", "no_action"
    urgency: str  # "immediate", "next_event", "advisory"
    
    # The recommendation
    action: str
    rationale: str
    
    # Details
    affected_events: List[str] = Field(default_factory=list)
    affected_swimmers: List[str] = Field(default_factory=list)
    
    # Impact
    estimated_point_swing: float = 0.0
    confidence: float = Field(default=0.7, ge=0, le=1)


class RealTimeAdjuster:
    """
    Makes real-time recommendations during a meet.
    
    Key scenarios:
    1. Opponent scratches a strong swimmer → opportunity to adjust
    2. Our swimmer scratches → need replacement
    3. DQ happens → recalculate remaining events
    4. Unexpected blowout → adjust strategy for remaining events
    """
    
    def handle_opponent_scratch(
        self,
        scratch: ScratchEvent,
        current_lineup: pd.DataFrame,
        remaining_events: List[str],
        available_swimmers: pd.DataFrame
    ) -> AdjustmentRecommendation:
        """
        Recommend adjustments when opponent scratches a swimmer.
        
        Args:
            scratch: The scratch event details
            current_lineup: Our current lineup
            remaining_events: Events that haven't happened yet
            available_swimmers: Swimmers who could still be reassigned
            
        Returns:
            Recommendation for how to respond
        """
        event = scratch.original_event
        
        # If event already happened, nothing to do
        if event not in remaining_events:
            return AdjustmentRecommendation(
                type="no_action",
                urgency="advisory",
                action="No action needed",
                rationale=f"Event {event} has already occurred",
                confidence=1.0
            )
        
        # Analyze impact
        our_entries_in_event = current_lineup[current_lineup['event'] == event]
        
        if our_entries_in_event.empty:
            return AdjustmentRecommendation(
                type="advisory",
                urgency="advisory",
                action=f"Opponent scratched {scratch.swimmer} from {event}",
                rationale="We have no entries in this event - no adjustment needed",
                affected_events=[event],
                confidence=0.9
            )
        
        # Opportunity: Their scratch improves our placement
        return AdjustmentRecommendation(
            type="advisory",
            urgency="next_event",
            action=f"Opponent scratched {scratch.swimmer} from {event} - our swimmers move up",
            rationale=(
                f"Our entries in {event} will each place one position higher. "
                f"Consider if we can sacrifice elsewhere to strengthen another close event."
            ),
            affected_events=[event],
            affected_swimmers=our_entries_in_event['swimmer'].tolist(),
            estimated_point_swing=2.0,  # Approximate gain
            confidence=0.8
        )
    
    def handle_our_scratch(
        self,
        scratch: ScratchEvent,
        current_lineup: pd.DataFrame,
        remaining_events: List[str],
        available_swimmers: pd.DataFrame
    ) -> AdjustmentRecommendation:
        """
        Recommend replacement when our swimmer scratches.
        """
        event = scratch.original_event
        
        if event not in remaining_events:
            return AdjustmentRecommendation(
                type="no_action",
                urgency="advisory",
                action="No action needed",
                rationale=f"Event {event} has already occurred",
                confidence=1.0
            )
        
        # Find replacement candidates
        candidates = available_swimmers[available_swimmers['event'] == event].copy()
        
        # Filter out already-assigned swimmers
        assigned_swimmers = set(current_lineup['swimmer'].unique())
        candidates = candidates[~candidates['swimmer'].isin(assigned_swimmers)]
        
        if candidates.empty:
            return AdjustmentRecommendation(
                type="no_action",
                urgency="immediate",
                action=f"No replacement available for {scratch.swimmer} in {event}",
                rationale="All eligible swimmers are already assigned to other events",
                affected_events=[event],
                affected_swimmers=[scratch.swimmer],
                estimated_point_swing=-4.0,  # Lost points estimate
                confidence=0.9
            )
        
        # Best replacement
        candidates = candidates.sort_values('time', ascending=True)
        best_replacement = candidates.iloc[0]
        
        return AdjustmentRecommendation(
            type="substitute",
            urgency="immediate",
            action=f"Replace {scratch.swimmer} with {best_replacement['swimmer']} in {event}",
            rationale=(
                f"{best_replacement['swimmer']} has time {best_replacement['time']:.2f} "
                f"and is available for {event}"
            ),
            affected_events=[event],
            affected_swimmers=[scratch.swimmer, best_replacement['swimmer']],
            estimated_point_swing=0.0,  # Neutral if good replacement
            confidence=0.85
        )
    
    def handle_dq(
        self,
        dq: DQEvent,
        current_lineup: pd.DataFrame,
        remaining_events: List[str],
        current_score: dict  # {"seton": X, "opponent": Y}
    ) -> AdjustmentRecommendation:
        """
        Recommend adjustments after a DQ.
        """
        event = dq.event
        margin = current_score.get('seton', 0) - current_score.get('opponent', 0)
        
        if dq.team == "seton":
            # Our swimmer DQ'd - points lost
            return AdjustmentRecommendation(
                type="strategic_scratch",
                urgency="advisory",
                action=f"DQ in {event} - reassess remaining events",
                rationale=(
                    f"Lost approximately {dq.points_lost:.0f} points. "
                    f"Current margin: {margin:+.0f}. "
                    f"May need to strengthen remaining events."
                ),
                affected_events=[event] + remaining_events[:2],
                affected_swimmers=[dq.swimmer],
                estimated_point_swing=-dq.points_lost,
                confidence=0.7
            )
        else:
            # Opponent DQ'd - we gain
            return AdjustmentRecommendation(
                type="advisory",
                urgency="advisory",
                action=f"Opponent DQ in {event} - our swimmers moved up",
                rationale=(
                    f"Gained approximately {dq.points_lost:.0f} points. "
                    f"Current margin: {margin:+.0f}."
                ),
                affected_events=[event],
                estimated_point_swing=dq.points_lost,
                confidence=0.9
            )
    
    def calculate_remaining_events(
        self,
        current_event_index: int
    ) -> List[str]:
        """Get list of events remaining in the meet."""
        if current_event_index >= len(EVENT_ORDER):
            return []
        return EVENT_ORDER[current_event_index + 1:]
    
    def assess_meet_status(
        self,
        current_score: dict,
        remaining_events: List[str],
        our_lineup: pd.DataFrame,
        opponent_lineup: pd.DataFrame
    ) -> dict:
        """
        Assess current meet status and projected outcome.
        """
        margin = current_score.get('seton', 0) - current_score.get('opponent', 0)
        events_left = len(remaining_events)
        max_points_remaining = events_left * 16  # Approximate
        
        status = {
            "current_margin": margin,
            "events_remaining": events_left,
            "max_points_remaining": max_points_remaining,
            "projected_outcome": "unknown",
            "recommendations": []
        }
        
        if margin > max_points_remaining:
            status["projected_outcome"] = "locked_win"
            status["recommendations"].append("Victory secured - consider resting swimmers")
        elif margin < -max_points_remaining:
            status["projected_outcome"] = "locked_loss"
            status["recommendations"].append("Focus on individual event wins and records")
        elif margin > 20:
            status["projected_outcome"] = "likely_win"
            status["recommendations"].append("Maintain intensity but manage fatigue")
        elif margin < -20:
            status["projected_outcome"] = "likely_loss"
            status["recommendations"].append("Go aggressive in remaining events")
        else:
            status["projected_outcome"] = "competitive"
            status["recommendations"].append("Every event matters - full effort")
        
        return status


# Singleton instance
real_time_adjuster = RealTimeAdjuster()
