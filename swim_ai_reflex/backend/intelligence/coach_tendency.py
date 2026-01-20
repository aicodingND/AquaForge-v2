"""
Coach Tendency Analyzer

Analyzes historical meet data to discover patterns in opponent coach behavior.
Uses these patterns to predict likely lineup decisions.
"""

from typing import List, Optional, Tuple
from datetime import datetime
import pandas as pd
from collections import defaultdict

from swim_ai_reflex.backend.models.opponent import (
    CoachTendency,
    MeetResult,
)


class CoachTendencyAnalyzer:
    """
    Analyzes opponent coach behavior patterns from historical data.
    
    Designed as a stateless service - can be instantiated fresh or
    used as a singleton.
    """
    
    def analyze_history(
        self,
        past_meets: List[MeetResult],
        team_name: str,
        coach_name: Optional[str] = None
    ) -> CoachTendency:
        """
        Extract patterns from historical lineup data.
        
        Args:
            past_meets: List of historical meet results
            team_name: Opponent team name to analyze
            coach_name: Optional coach name
            
        Returns:
            CoachTendency with discovered patterns
        """
        if not past_meets:
            return CoachTendency(
                coach_name=coach_name or "Unknown",
                team_name=team_name,
                sample_size=0,
                confidence=0.0
            )
        
        # Filter to meets involving this team
        relevant_meets = [m for m in past_meets if m.opponent_team.lower() == team_name.lower()]
        
        if not relevant_meets:
            return CoachTendency(
                coach_name=coach_name or "Unknown",
                team_name=team_name,
                sample_size=0,
                confidence=0.0
            )
        
        # Analyze patterns
        star_placement, favorite_events = self._analyze_star_placement(relevant_meets)
        relay_resting = self._analyze_relay_resting(relevant_meets)
        front_loading = self._analyze_front_loading(relevant_meets)
        predictability = self._analyze_predictability(relevant_meets)
        adaptation = self._analyze_adaptation(relevant_meets)
        exhibition_usage = self._analyze_exhibition_usage(relevant_meets)
        avoided = self._analyze_avoided_events(relevant_meets)
        
        # Calculate confidence based on sample size
        confidence = min(1.0, len(relevant_meets) / 10.0)  # Full confidence at 10+ meets
        
        return CoachTendency(
            coach_name=coach_name or "Unknown",
            team_name=team_name,
            rests_stars_in_relays=relay_resting,
            front_loads_lineup=front_loading,
            predictable_star_placement=predictability,
            adapts_to_opponent=adaptation,
            uses_exhibition_strategically=exhibition_usage,
            favorite_events_for_stars=favorite_events,
            avoided_events=avoided,
            sample_size=len(relevant_meets),
            last_updated=datetime.now(),
            confidence=confidence
        )
    
    def _analyze_star_placement(
        self,
        meets: List[MeetResult]
    ) -> Tuple[float, List[str]]:
        """Analyze where coach places their star swimmers."""
        event_counts = defaultdict(int)
        
        for meet in meets:
            # Find star swimmers (those who scored 1st or 2nd place)
            for entry in meet.opponent_lineup:
                if entry.get('place', 99) <= 2:
                    event_counts[entry.get('event', '')] += 1
        
        # Top 3 events by star placement
        sorted_events = sorted(event_counts.items(), key=lambda x: -x[1])
        favorite_events = [e for e, _ in sorted_events[:3]]
        
        # Probability they put stars in these events
        if meets and favorite_events:
            probability = min(1.0, sorted_events[0][1] / len(meets))
        else:
            probability = 0.5
        
        return probability, favorite_events
    
    def _analyze_relay_resting(self, meets: List[MeetResult]) -> float:
        """Check if coach rests star swimmers in relays."""
        relay_star_count = 0
        relay_total = 0
        
        for meet in meets:
            # Identify stars (1st/2nd in individual events)
            stars = set()
            for entry in meet.opponent_lineup:
                if entry.get('place', 99) <= 2 and 'Relay' not in entry.get('event', ''):
                    stars.add(entry.get('swimmer', ''))
            
            # Check relay participation
            for entry in meet.opponent_lineup:
                if 'Relay' in entry.get('event', ''):
                    relay_total += 1
                    if entry.get('swimmer', '') in stars:
                        relay_star_count += 1
        
        if relay_total == 0:
            return 0.3  # Default
        
        # Higher ratio = stars in relays = NOT resting them
        star_relay_ratio = relay_star_count / relay_total
        return 1.0 - star_relay_ratio  # Invert: high = rests stars
    
    def _analyze_front_loading(self, meets: List[MeetResult]) -> float:
        """Check if coach puts best swimmers in early events."""
        early_wins = 0
        late_wins = 0
        
        early_events = ["200 Medley Relay", "200 Free", "200 IM", "50 Free", "Diving"]
        
        for meet in meets:
            for entry in meet.opponent_lineup:
                if entry.get('place', 99) == 1:
                    if entry.get('event', '') in early_events:
                        early_wins += 1
                    else:
                        late_wins += 1
        
        total = early_wins + late_wins
        if total == 0:
            return 0.5
        
        return early_wins / total
    
    def _analyze_predictability(self, meets: List[MeetResult]) -> float:
        """Check how consistent lineup patterns are across meets."""
        if len(meets) < 2:
            return 0.5
        
        # Compare consecutive meets for consistency
        consistency_scores = []
        
        for i in range(1, len(meets)):
            prev_lineup = {(e.get('swimmer'), e.get('event')) for e in meets[i-1].opponent_lineup}
            curr_lineup = {(e.get('swimmer'), e.get('event')) for e in meets[i].opponent_lineup}
            
            if prev_lineup and curr_lineup:
                overlap = len(prev_lineup & curr_lineup)
                union = len(prev_lineup | curr_lineup)
                consistency_scores.append(overlap / union if union > 0 else 0)
        
        if not consistency_scores:
            return 0.5
        
        return sum(consistency_scores) / len(consistency_scores)
    
    def _analyze_adaptation(self, meets: List[MeetResult]) -> float:
        """Check if lineups change based on opponent strength."""
        # This would require opponent strength data - simplified for now
        # High variance in lineup = adapts to opponent
        if len(meets) < 3:
            return 0.3
        
        # Measure lineup variance
        lineups = []
        for meet in meets:
            lineup_sig = frozenset((e.get('swimmer'), e.get('event')) for e in meet.opponent_lineup)
            lineups.append(lineup_sig)
        
        unique_lineups = len(set(lineups))
        variance_ratio = unique_lineups / len(lineups)
        
        return variance_ratio  # High ratio = high adaptation
    
    def _analyze_exhibition_usage(self, meets: List[MeetResult]) -> float:
        """Check strategic use of exhibition swimmers."""
        strategic_exhibitions = 0
        total_exhibitions = 0
        
        for meet in meets:
            for entry in meet.opponent_lineup:
                if entry.get('was_exhibition', False):
                    total_exhibitions += 1
                    # Strategic = exhibition in close event
                    if entry.get('place', 99) <= 4:
                        strategic_exhibitions += 1
        
        if total_exhibitions == 0:
            return 0.4
        
        return strategic_exhibitions / total_exhibitions
    
    def _analyze_avoided_events(self, meets: List[MeetResult]) -> List[str]:
        """Find events where coach consistently underperforms."""
        event_performance = defaultdict(list)
        
        for meet in meets:
            for entry in meet.opponent_lineup:
                event = entry.get('event', '')
                place = entry.get('place', 99)
                event_performance[event].append(place)
        
        # Events with consistently poor performance (avg place > 4)
        avoided = []
        for event, places in event_performance.items():
            avg_place = sum(places) / len(places)
            if avg_place > 4:
                avoided.append(event)
        
        return avoided
    
    def predict_lineup(
        self,
        coach: CoachTendency,
        opponent_roster: pd.DataFrame,
        our_roster: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """
        Predict opponent's most likely lineup based on tendencies.
        
        Args:
            coach: Analyzed coach tendencies
            opponent_roster: Available opponent swimmers
            our_roster: Optional - our roster for adaptation analysis
            
        Returns:
            Predicted opponent lineup as DataFrame
        """
        if opponent_roster.empty:
            return opponent_roster
        
        # Start with greedy (fastest per event)
        predicted = []
        swimmer_events = defaultdict(int)
        
        events = opponent_roster['event'].unique()
        
        # Prioritize favorite events if predictable
        if coach.predictable_star_placement > 0.6 and coach.favorite_events_for_stars:
            events = sorted(
                events,
                key=lambda e: 0 if e in coach.favorite_events_for_stars else 1
            )
        
        for event in events:
            event_swimmers = opponent_roster[opponent_roster['event'] == event].copy()
            
            if event_swimmers.empty:
                continue
            
            # Sort by time
            event_swimmers = event_swimmers.sort_values('time', ascending=True)
            
            # Apply tendencies
            if 'Relay' in event and coach.rests_stars_in_relays > 0.6:
                # Skip top 2 for relay (resting them)
                event_swimmers = event_swimmers.iloc[2:] if len(event_swimmers) > 2 else event_swimmers
            
            if event in coach.avoided_events:
                # Don't put best swimmers in avoided events
                event_swimmers = event_swimmers.iloc[1:] if len(event_swimmers) > 1 else event_swimmers
            
            # Pick swimmers respecting constraints
            assigned = 0
            for _, row in event_swimmers.iterrows():
                swimmer = row['swimmer']
                if swimmer_events[swimmer] < 4 and assigned < 4:
                    predicted.append(row.to_dict())
                    swimmer_events[swimmer] += 1
                    assigned += 1
        
        return pd.DataFrame(predicted) if predicted else pd.DataFrame(columns=opponent_roster.columns)


# Singleton instance
coach_tendency_analyzer = CoachTendencyAnalyzer()
