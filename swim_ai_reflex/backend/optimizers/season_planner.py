"""
Season Planner

Multi-meet optimization across an entire season.
Balances winning meets with developing swimmers and peaking for championships.
"""

from typing import List, Dict, Optional
from collections import defaultdict
import pandas as pd

from swim_ai_reflex.backend.models.meet import (
    Season,
    ScheduledMeet,
    SeasonGoals,
    SeasonPlan,
    MeetImportance,
)


class SeasonPlanner:
    """
    Optimize swimmer usage across an entire season.
    
    Key considerations:
    - Rest stars before championship meets
    - Develop JV in less important meets
    - Build momentum with early wins
    - Strategic load management
    """
    
    def plan_season(
        self,
        season: Season,
        roster: pd.DataFrame,
        goals: SeasonGoals
    ) -> SeasonPlan:
        """
        Create a season-level strategy.
        
        Args:
            season: Season with scheduled meets
            roster: Full team roster
            goals: Season objectives
            
        Returns:
            SeasonPlan with meet-by-meet recommendations
        """
        if not season.meets:
            return SeasonPlan(
                season=season.season_name,
                meet_strategies=[],
                swimmer_load={},
                rest_recommendations=["No meets scheduled"],
                jv_development_opportunities=[]
            )
        
        # Analyze roster
        stars = self._identify_stars(roster)
        jv_swimmers = self._identify_jv(roster)
        
        # Calculate load and create recommendations
        meet_strategies = []
        swimmer_events = defaultdict(list)
        rest_recs = []
        jv_opportunities = []
        
        # Sort meets by date
        sorted_meets = sorted(season.meets, key=lambda m: m.date)
        
        # Championship index (if exists)
        championship_idx = None
        if season.championship_meet:
            for i, m in enumerate(sorted_meets):
                if m.meet_id == season.championship_meet.meet_id:
                    championship_idx = i
                    break
        
        for i, meet in enumerate(sorted_meets):
            strategy = self._plan_single_meet(
                meet=meet,
                meet_index=i,
                championship_index=championship_idx,
                total_meets=len(sorted_meets),
                stars=stars,
                jv_swimmers=jv_swimmers,
                roster=roster,
                goals=goals,
                swimmer_events=swimmer_events
            )
            meet_strategies.append(strategy)
            
            # Update swimmer load tracking
            for swimmer in strategy.get('recommended_rest', []):
                rest_recs.append(f"Rest {swimmer} for {meet.opponent} ({meet.date})")
            
            for swimmer in strategy.get('jv_opportunities', []):
                jv_opportunities.append(f"{swimmer} can swim {meet.opponent} ({meet.date})")
        
        # Calculate projected outcomes
        projected_wins, projected_losses = self._project_outcomes(meet_strategies)
        
        # Championship readiness
        readiness = self._calculate_championship_readiness(
            season, stars, goals, swimmer_events
        )
        
        return SeasonPlan(
            season=season.season_name,
            meet_strategies=meet_strategies,
            swimmer_load=dict(swimmer_events),
            rest_recommendations=rest_recs[:10],  # Top 10
            jv_development_opportunities=jv_opportunities[:10],
            projected_wins=projected_wins,
            projected_losses=projected_losses,
            championship_readiness=readiness
        )
    
    def _identify_stars(self, roster: pd.DataFrame, top_n: int = 5) -> List[str]:
        """Identify the top N star swimmers."""
        if roster.empty:
            return []
        
        # Score swimmers by their best times (lower = better)
        swimmer_scores = {}
        
        for swimmer in roster['swimmer'].unique():
            swimmer_data = roster[roster['swimmer'] == swimmer]
            # Use their best time percentile across events
            avg_time = swimmer_data['time'].mean()
            swimmer_scores[swimmer] = avg_time
        
        # Sort by score (lower is better)
        sorted_swimmers = sorted(swimmer_scores.items(), key=lambda x: x[1])
        return [s for s, _ in sorted_swimmers[:top_n]]
    
    def _identify_jv(self, roster: pd.DataFrame) -> List[str]:
        """Identify JV swimmers (grade < 10 or slower times)."""
        if roster.empty or 'grade' not in roster.columns:
            return []
        
        jv = roster[roster['grade'] < 10]['swimmer'].unique().tolist()
        return jv
    
    def _plan_single_meet(
        self,
        meet: ScheduledMeet,
        meet_index: int,
        championship_index: Optional[int],
        total_meets: int,
        stars: List[str],
        jv_swimmers: List[str],
        roster: pd.DataFrame,
        goals: SeasonGoals,
        swimmer_events: Dict
    ) -> dict:
        """Create strategy for a single meet."""
        strategy = {
            'meet_id': meet.meet_id,
            'date': str(meet.date),
            'opponent': meet.opponent,
            'importance': meet.importance.value,
            'strategy_type': 'standard',
            'recommended_rest': [],
            'jv_opportunities': [],
            'focus_events': [],
            'projected_outcome': 'unknown'
        }
        
        # Championship proximity check
        if championship_index is not None and goals.rest_stars_before_championship:
            days_to_champ = (championship_index - meet_index)
            
            # If this is the meet right before championship
            if days_to_champ == 1:
                strategy['strategy_type'] = 'rest_stars'
                strategy['recommended_rest'] = stars[:3]  # Rest top 3
                strategy['notes'] = "Rest stars for upcoming championship"
        
        # JV development in regular meets
        if (meet.importance == MeetImportance.REGULAR and 
            goals.develop_jv_in_regular_meets and
            jv_swimmers):
            strategy['jv_opportunities'] = jv_swimmers[:3]
        
        # Championship meets - all hands on deck
        if meet.importance == MeetImportance.CHAMPIONSHIP:
            strategy['strategy_type'] = 'full_strength'
            strategy['focus_events'] = goals.priority_events
            strategy['notes'] = "Championship meet - maximize every event"
        
        # Project outcome based on historical margin
        if meet.historical_margin > 10:
            strategy['projected_outcome'] = 'likely_win'
        elif meet.historical_margin < -10:
            strategy['projected_outcome'] = 'likely_loss'
        else:
            strategy['projected_outcome'] = 'competitive'
        
        return strategy
    
    def _project_outcomes(self, strategies: List[dict]) -> tuple:
        """Project season wins/losses based on meet strategies."""
        wins = 0
        losses = 0
        
        for s in strategies:
            if s.get('projected_outcome') == 'likely_win':
                wins += 1
            elif s.get('projected_outcome') == 'likely_loss':
                losses += 1
            else:
                # 50/50 for competitive
                wins += 0.5
                losses += 0.5
        
        return int(wins), int(losses)
    
    def _calculate_championship_readiness(
        self,
        season: Season,
        stars: List[str],
        goals: SeasonGoals,
        swimmer_events: Dict
    ) -> float:
        """Calculate how ready the team is for championship."""
        if not season.championship_meet:
            return 0.5  # Unknown without championship
        
        readiness = 0.7  # Base readiness
        
        # Boost for upcoming championship
        days = season.days_until_championship
        if days is not None:
            if 7 <= days <= 14:
                readiness += 0.15  # Ideal taper period
            elif days < 7:
                readiness += 0.1  # Close but OK
        
        # Check if stars are well-rested (not overused)
        for star in stars[:3]:
            events = swimmer_events.get(star, [])
            if len(events) > 30:  # Over 30 events in season
                readiness -= 0.05  # Slight concern about fatigue
        
        return min(1.0, max(0.0, readiness))
    
    def get_next_meet_recommendation(
        self,
        season: Season,
        roster: pd.DataFrame
    ) -> dict:
        """Get recommendation for the next upcoming meet."""
        next_meet = season.next_meet
        if not next_meet:
            return {"message": "No upcoming meets"}
        
        stars = self._identify_stars(roster)
        self._identify_jv(roster)
        
        rec = {
            "meet": next_meet.opponent,
            "date": str(next_meet.date),
            "importance": next_meet.importance.value,
            "days_until": next_meet.days_until,
            "recommendations": []
        }
        
        # Add recommendations based on importance
        if next_meet.importance == MeetImportance.CHAMPIONSHIP:
            rec["recommendations"].append("Use full varsity strength")
            rec["recommendations"].append("Focus on all priority events")
        elif next_meet.importance == MeetImportance.REGULAR:
            rec["recommendations"].append(f"Consider resting {stars[0] if stars else 'top swimmer'}")
            rec["recommendations"].append("Good opportunity for JV development")
        
        return rec


# Singleton instance
season_planner = SeasonPlanner()
