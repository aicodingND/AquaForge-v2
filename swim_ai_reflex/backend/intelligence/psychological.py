"""
Psychological Performance Profiler

Models swimmer psychological factors:
- Clutch performance under pressure
- Rivalry effects
- Consistency/variance patterns
- Home vs away performance
"""

from typing import List, Dict, Tuple
from pydantic import BaseModel, Field
from collections import defaultdict

from swim_ai_reflex.backend.models.opponent import MeetResult
from swim_ai_reflex.backend.models.meet import MeetImportance


class PsychologicalProfile(BaseModel):
    """Psychological performance profile for a swimmer."""
    swimmer: str
    
    # Core traits (1.0 = average)
    clutch_factor: float = Field(
        default=1.0, ge=0.5, le=1.5,
        description="Performance multiplier in big meets (>1 = performs better)"
    )
    consistency: float = Field(
        default=0.8, ge=0, le=1,
        description="How consistent are their times (1 = very consistent)"
    )
    rivalry_boost: float = Field(
        default=1.0, ge=0.8, le=1.3,
        description="Performance vs specific rivals (>1 = rises to challenge)"
    )
    home_advantage: float = Field(
        default=1.0, ge=0.9, le=1.1,
        description="Home pool advantage (>1 = swims faster at home)"
    )
    
    # Patterns
    strong_opponents: List[str] = Field(
        default_factory=list,
        description="Opponents they perform well against"
    )
    weak_opponents: List[str] = Field(
        default_factory=list,
        description="Opponents they struggle against"
    )
    
    # Recommendations
    best_meet_types: List[str] = Field(
        default_factory=list,
        description="Meet types where they excel"
    )
    avoid_pressure_events: bool = Field(
        default=False,
        description="Flag if swimmer struggles under pressure"
    )
    
    # Data quality
    sample_size: int = 0
    confidence: float = Field(default=0.5, ge=0, le=1)
    
    def get_adjusted_time(
        self,
        base_time: float,
        meet_importance: MeetImportance,
        opponent: str = "",
        is_home: bool = True
    ) -> float:
        """Get time adjusted for psychological factors."""
        adjusted = base_time
        
        # Clutch factor for important meets
        if meet_importance in [MeetImportance.CHAMPIONSHIP, MeetImportance.STATE]:
            # Clutch > 1.0 means FASTER times (lower), so multiply by inverse
            adjusted = adjusted / self.clutch_factor
        
        # Rivalry boost
        if opponent in self.strong_opponents:
            adjusted = adjusted / self.rivalry_boost
        elif opponent in self.weak_opponents:
            adjusted = adjusted * 1.02  # Slight slowdown
        
        # Home advantage
        if is_home:
            adjusted = adjusted / self.home_advantage
        
        return round(adjusted, 2)


class PsychologicalProfiler:
    """
    Analyzes swimmer performance patterns to build psychological profiles.
    """
    
    def build_profile(
        self,
        swimmer: str,
        meet_results: List[MeetResult],
        swimmer_times: List[dict]  # List of {meet_id, event, time, place}
    ) -> PsychologicalProfile:
        """
        Build psychological profile from historical data.
        
        Args:
            swimmer: Swimmer name
            meet_results: All meet results for context
            swimmer_times: This swimmer's times across meets
            
        Returns:
            PsychologicalProfile with discovered patterns
        """
        if not swimmer_times:
            return PsychologicalProfile(swimmer=swimmer, sample_size=0, confidence=0.0)
        
        # Build meet type lookup
        meet_lookup = {m.meet_id: m for m in meet_results}
        
        # Analyze performance patterns
        clutch = self._analyze_clutch(swimmer_times, meet_lookup)
        consistency = self._analyze_consistency(swimmer_times)
        rivalry = self._analyze_rivalry(swimmer_times, meet_results)
        home_adv = self._analyze_home_advantage(swimmer_times, meet_lookup)
        
        # Identify strong/weak opponents
        strong, weak = self._identify_opponent_patterns(swimmer_times, meet_lookup)
        
        # Confidence based on sample size
        confidence = min(1.0, len(swimmer_times) / 20.0)
        
        return PsychologicalProfile(
            swimmer=swimmer,
            clutch_factor=clutch,
            consistency=consistency,
            rivalry_boost=rivalry,
            home_advantage=home_adv,
            strong_opponents=strong,
            weak_opponents=weak,
            best_meet_types=self._identify_best_meet_types(swimmer_times, meet_lookup),
            avoid_pressure_events=(clutch < 0.95),
            sample_size=len(swimmer_times),
            confidence=confidence
        )
    
    def _analyze_clutch(
        self,
        times: List[dict],
        meet_lookup: Dict[str, MeetResult]
    ) -> float:
        """Analyze clutch performance (big meet vs regular)."""
        regular_times = []
        big_meet_times = []
        
        for t in times:
            meet = meet_lookup.get(t.get('meet_id'))
            if meet is None:
                continue
            
            # Categorize by meet importance
            if hasattr(meet, 'importance'):
                # We don't have importance on MeetResult, estimate from type
                if meet.meet_type in ['championship', 'state']:
                    big_meet_times.append(t['time'])
                else:
                    regular_times.append(t['time'])
            else:
                regular_times.append(t['time'])
        
        if not big_meet_times or not regular_times:
            return 1.0  # Not enough data
        
        avg_big = sum(big_meet_times) / len(big_meet_times)
        avg_regular = sum(regular_times) / len(regular_times)
        
        # Clutch factor: how much faster in big meets
        # < 1.0 = slower in big meets (bad)
        # > 1.0 = faster in big meets (clutch!)
        if avg_regular == 0:
            return 1.0
        
        clutch = avg_regular / avg_big
        return max(0.8, min(1.2, clutch))
    
    def _analyze_consistency(self, times: List[dict]) -> float:
        """Analyze time consistency (low variance = consistent)."""
        if len(times) < 3:
            return 0.8  # Default
        
        # Group by event
        event_times = defaultdict(list)
        for t in times:
            event_times[t.get('event', 'unknown')].append(t['time'])
        
        # Calculate coefficient of variation for each event
        cvs = []
        for event, event_ts in event_times.items():
            if len(event_ts) >= 3:
                mean = sum(event_ts) / len(event_ts)
                variance = sum((t - mean) ** 2 for t in event_ts) / len(event_ts)
                std_dev = variance ** 0.5
                cv = std_dev / mean if mean > 0 else 0
                cvs.append(cv)
        
        if not cvs:
            return 0.8
        
        avg_cv = sum(cvs) / len(cvs)
        
        # Convert CV to consistency score (lower CV = higher consistency)
        # CV of 0.02 (2%) = consistency of 0.95
        # CV of 0.05 (5%) = consistency of 0.75
        consistency = max(0.5, min(1.0, 1.0 - avg_cv * 5))
        return consistency
    
    def _analyze_rivalry(
        self,
        times: List[dict],
        meet_results: List[MeetResult]
    ) -> float:
        """Analyze performance against specific rivals."""
        # Simplified: check win rate when head-to-head is close
        close_wins = 0
        close_losses = 0
        
        for t in times:
            place = t.get('place', 99)
            # Close race = 1st-3rd place
            if place <= 3:
                close_wins += 1
            elif place <= 5:
                close_losses += 1
        
        total = close_wins + close_losses
        if total < 3:
            return 1.0
        
        win_rate = close_wins / total
        # Convert to rivalry boost (50% = 1.0)
        return 0.9 + win_rate * 0.2
    
    def _analyze_home_advantage(
        self,
        times: List[dict],
        meet_lookup: Dict[str, MeetResult]
    ) -> float:
        """Analyze home vs away performance."""
        home_times = []
        away_times = []
        
        for t in times:
            meet = meet_lookup.get(t.get('meet_id'))
            if meet is None:
                continue
            
            if hasattr(meet, 'location') and 'seton' in meet.location.lower():
                home_times.append(t['time'])
            else:
                away_times.append(t['time'])
        
        if not home_times or not away_times:
            return 1.0
        
        avg_home = sum(home_times) / len(home_times)
        avg_away = sum(away_times) / len(away_times)
        
        if avg_away == 0:
            return 1.0
        
        return max(0.95, min(1.05, avg_away / avg_home))
    
    def _identify_opponent_patterns(
        self,
        times: List[dict],
        meet_lookup: Dict[str, MeetResult]
    ) -> Tuple[List[str], List[str]]:
        """Identify opponents where swimmer excels or struggles."""
        opponent_performance = defaultdict(list)
        
        for t in times:
            meet = meet_lookup.get(t.get('meet_id'))
            if meet is None:
                continue
            
            opponent = meet.opponent_team
            place = t.get('place', 99)
            opponent_performance[opponent].append(place)
        
        strong = []
        weak = []
        
        for opponent, places in opponent_performance.items():
            avg_place = sum(places) / len(places)
            if avg_place <= 2:
                strong.append(opponent)
            elif avg_place >= 5:
                weak.append(opponent)
        
        return strong, weak
    
    def _identify_best_meet_types(
        self,
        times: List[dict],
        meet_lookup: Dict[str, MeetResult]
    ) -> List[str]:
        """Identify meet types where swimmer excels."""
        type_places = defaultdict(list)
        
        for t in times:
            meet = meet_lookup.get(t.get('meet_id'))
            if meet is None:
                continue
            
            meet_type = getattr(meet, 'meet_type', 'regular')
            type_places[meet_type].append(t.get('place', 99))
        
        best = []
        for mtype, places in type_places.items():
            if places and sum(places) / len(places) <= 2.5:
                best.append(mtype)
        
        return best


# Singleton instance
psychological_profiler = PsychologicalProfiler()
