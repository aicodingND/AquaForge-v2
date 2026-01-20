"""
Strategy Analysis Service - Generates intuitive summaries, decision explanations, and alternatives.
Designed for coaches who need actionable insights, not technical jargon.
"""
from typing import Dict, List, Any
import pandas as pd
from swim_ai_reflex.backend.services.base_service import BaseService


class StrategyAnalysisService(BaseService):
    """
    Generates comprehensive strategy analysis after optimization.
    """
    
    # Point values for VISAA dual meet
    POINT_VALUES = {1: 8, 2: 6, 3: 5, 4: 4, 5: 3, 6: 2, 7: 1}
    
    def analyze(
        self,
        lineup_df: pd.DataFrame,
        opponent_df: pd.DataFrame,
        totals: Dict[str, float],
        seton_roster: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Generate complete strategy analysis.
        
        Returns:
            Dict with:
                - summary: High-level narrative
                - key_matchups: Critical head-to-head races
                - decisions: Per-swimmer explanations
                - alternatives: 2-3 what-if scenarios
        """
        if lineup_df.empty:
            return self._empty_analysis()
        
        # Filter to Seton only for analysis
        seton_mask = lineup_df['team'].str.lower() == 'seton'
        seton_lineup = lineup_df[seton_mask].copy()
        opponent_lineup = lineup_df[~seton_mask].copy()
        
        return {
            "summary": self._generate_summary(totals, seton_lineup, opponent_lineup),
            "key_matchups": self._find_key_matchups(lineup_df),
            "decisions": self._explain_all_decisions(seton_lineup, opponent_lineup, seton_roster),
            "alternatives": self._generate_alternatives(seton_lineup, opponent_lineup, seton_roster, totals)
        }
    
    def _empty_analysis(self) -> Dict[str, Any]:
        return {
            "summary": "No lineup data available for analysis.",
            "key_matchups": [],
            "decisions": [],
            "alternatives": []
        }
    
    def _generate_summary(
        self, 
        totals: Dict[str, float], 
        seton_lineup: pd.DataFrame,
        opponent_lineup: pd.DataFrame
    ) -> str:
        """Generate a coach-friendly narrative summary."""
        seton_score = totals.get('seton', 0)
        opponent_score = totals.get('opponent', 0)
        margin = seton_score - opponent_score
        
        # Win/Loss/Tie determination
        if margin > 0:
            outcome = f"**Seton wins {seton_score:.0f}-{opponent_score:.0f}** (+{margin:.0f} margin)"
        elif margin < 0:
            outcome = f"**Seton loses {seton_score:.0f}-{opponent_score:.0f}** ({margin:.0f} margin)"
        else:
            outcome = f"**Tie game {seton_score:.0f}-{opponent_score:.0f}**"
        
        # Identify strengths
        strengths = []
        weaknesses = []
        
        events = seton_lineup['event'].unique() if not seton_lineup.empty else []
        for event in events:
            seton_in_event = seton_lineup[seton_lineup['event'] == event]
            opp_in_event = opponent_lineup[opponent_lineup['event'] == event]
            
            seton_pts = seton_in_event['points'].sum() if 'points' in seton_in_event.columns else 0
            opp_pts = opp_in_event['points'].sum() if 'points' in opp_in_event.columns else 0
            
            if seton_pts - opp_pts >= 6:
                strengths.append(event)
            elif opp_pts - seton_pts >= 6:
                weaknesses.append(event)
        
        str_text = f"Strong in: {', '.join(strengths[:3])}" if strengths else "No dominant events"
        weak_text = f"Vulnerable in: {', '.join(weaknesses[:3])}" if weaknesses else "No critical weaknesses"
        
        return f"{outcome}\n\n{str_text}\n{weak_text}"
    
    def _find_key_matchups(self, lineup_df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Find races decided by <1 second (critical matchups)."""
        key_matchups = []
        
        for event in lineup_df['event'].unique():
            event_df = lineup_df[lineup_df['event'] == event].copy()
            if len(event_df) < 2:
                continue
            
            # Sort by time
            event_df = event_df.sort_values('time')
            
            # Check gaps between consecutive times
            times = event_df['time'].tolist()
            swimmers = event_df['swimmer'].tolist()
            teams = event_df['team'].tolist()
            
            for i in range(len(times) - 1):
                gap = times[i+1] - times[i]
                if 0 < gap < 1.0 and teams[i] != teams[i+1]:
                    key_matchups.append({
                        "event": event,
                        "swimmer1": swimmers[i],
                        "team1": teams[i],
                        "time1": times[i],
                        "swimmer2": swimmers[i+1],
                        "team2": teams[i+1],
                        "time2": times[i+1],
                        "gap": gap,
                        "description": f"{swimmers[i]} beats {swimmers[i+1]} by {gap:.2f}s in {event}"
                    })
        
        return sorted(key_matchups, key=lambda x: x['gap'])[:5]
    
    def _explain_all_decisions(
        self, 
        seton_lineup: pd.DataFrame, 
        opponent_lineup: pd.DataFrame,
        full_roster: pd.DataFrame
    ) -> List[Dict[str, Any]]:
        """Explain why each Seton swimmer is in their assigned events with role-based logic."""
        decisions = []
        
        if seton_lineup.empty:
            return decisions
        
        swimmers = seton_lineup['swimmer'].unique()
        
        for swimmer in swimmers:
            swimmer_events = seton_lineup[seton_lineup['swimmer'] == swimmer]
            events_list = swimmer_events['event'].tolist()
            
            # Get all events this swimmer COULD have done
            if not full_roster.empty and 'swimmer' in full_roster.columns:
                all_options = full_roster[full_roster['swimmer'] == swimmer]['event'].unique().tolist()
            else:
                all_options = events_list
            
            dropped = [e for e in all_options if e not in events_list and "Relay" not in e]
            
            explanation_parts = []
            
            for _, row in swimmer_events.iterrows():
                event = row['event']
                points = row.get('points', 0)
                place = row.get('place', 99)
                
                # Check opponent in this event
                opp_in_event = opponent_lineup[opponent_lineup['event'] == event]
                opp_best_place = opp_in_event['place'].min() if not opp_in_event.empty else 99
                
                # Determine Role
                role = "participant"
                reason = ""
                
                if points >= 5: # 1st or 2nd (6 or 4 pts)
                    role = "🚀 Point Maximizer"
                    if not opp_in_event.empty and place < opp_best_place:
                         reason = f"Beats top opponent (Place {opp_best_place})"
                    else:
                         reason = "Dominant swim"
                elif points > 0: # 3rd, 4th, 5th
                    role = "🧱 Depth Scoring"
                    reason = "Captures clear points"
                elif points == 0 and place < opp_best_place:
                    # Non-scoring but beat an opponent? (e.g. 3rd Seton swimmer finishing ahead of opp)
                    role = "🛡️ Blocker"
                    reason = f"Displaces opponent from Place {place}"
                elif points == 0:
                    role = "⚪ Support"
                    reason = "Fills lane"
                
                part = f"{role} in {event}: {place} place ({points:.0f} pts)"
                if reason:
                    part += f" - {reason}"
                explanation_parts.append(part)
            
            explanation = "\n".join(explanation_parts)
            
            if dropped:
                explanation += f"\n\n⤵️ Dropped: {', '.join(dropped[:2])} (Lower strategic value)"
            
            decisions.append({
                "swimmer": swimmer,
                "events": events_list,
                "explanation": explanation,
                "total_points": swimmer_events['points'].sum() if 'points' in swimmer_events.columns else 0
            })
        
        # Sort by total contribution
        return sorted(decisions, key=lambda x: x['total_points'], reverse=True)

    def generate_exportable_report(self, summary: str, decisions: List[Dict], alternatives: List[Dict], suggestions: List[Dict] = []) -> str:
        """Generate a formatted text report for export."""
        report = []
        report.append("="*50)
        report.append("  AQUAFORGE STRATEGIC ANALYSIS REPORT")
        report.append("="*50)
        report.append("\n[MEET SUMMARY]")
        report.append(summary)
        
        if suggestions:
            report.append("\n" + "="*50)
            report.append("[STRATEGIC SUGGESTIONS & OPPORTUNITIES]")
            report.append("="*50)
            for sug in suggestions:
                report.append(f"\n💡 {sug['swimmer']}: {sug['suggested_change']}")
                report.append(f"   Potential Gain: +{sug['potential_gain']} pts")
                report.append(f"   Reason: {sug['reason']}")
        
        report.append("\n" + "="*50)
        report.append("[SWIMMER ASSIGNMENTS & RATIONALE]")
        report.append("="*50)
        
        for dec in decisions:
            report.append(f"\n👤 {dec['swimmer']} (Total Pts: {dec['total_points']:.0f})")
            report.append(f"   Events: {', '.join(dec['events'])}")
            report.append("   Strategy:\n   " + dec['explanation'].replace('\n', '\n   '))
            
        report.append("\n" + "="*50)
        report.append("[ALTERNATIVE STRATEGIES]")
        report.append("="*50)
        
        for alt in alternatives:
            report.append(f"\n🔄 {alt['name']} ({alt['projected_score']})")
            report.append(f"   {alt['description']}")
            report.append(f"   RISK: {alt.get('risk', 'Unknown')}")
            report.append(f"   IMPLICATION: {alt.get('implication', '')}")
            
        return "\n".join(report)
    
    def _generate_alternatives(
        self,
        seton_lineup: pd.DataFrame,
        opponent_lineup: pd.DataFrame,
        full_roster: pd.DataFrame,
        original_totals: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """Generate 2-3 alternative scenarios with plusses and drawbacks."""
        alternatives = []
        original_margin = original_totals.get('seton', 0) - original_totals.get('opponent', 0)
        
        # Alternative 1: "Conservative" - Minimize risk by avoiding close matchups
        alternatives.append({
            "name": "Conservative Strategy",
            "description": "Focus on guaranteed 1st-3rd places, avoid risky 4th-5th matchups",
            "projected_score": f"~{original_totals.get('seton', 0) - 5:.0f}-{original_totals.get('opponent', 0) + 5:.0f}",
            "plusses": [
                "Reliable results even if opponent swims fast",
                "Less stress on race day",
                "Good for inexperienced swimmers"
            ],
            "drawbacks": [
                "Leaves points on the table",
                "May lose close meets you could have won"
            ],
            "implication": "Lower ceiling but safer floor. Good if opponent has surprise fast times.",
            "risk": "Low"
        })
        
        # Alternative 2: "Aggressive" - Stack best swimmers in highest-value events
        alternatives.append({
            "name": "Aggressive Strategy", 
            "description": "Stack your fastest swimmers in 200IM, 100Fly, 500Free for maximum points",
            "projected_score": f"~{original_totals.get('seton', 0) + 8:.0f}-{original_totals.get('opponent', 0) - 8:.0f}",
            "plusses": [
                "Maximum possible point total",
                "Psychological advantage over opponent",
                "Best for must-win situations"
            ],
            "drawbacks": [
                "High fatigue risk for key swimmers",
                "Vulnerable if anyone has a bad race"
            ],
            "implication": "Higher risk, higher reward. Best when you need a decisive win.",
            "risk": "High"
        })
        
        # Alternative 3: "Rest Key Athletes" - Save energy for future meets
        if original_margin > 15:
            alternatives.append({
                "name": "Rest Key Athletes",
                "description": "Move your top 2-3 swimmers to relays only, rest for championship",
                "projected_score": f"~{original_totals.get('seton', 0) - 12:.0f}-{original_totals.get('opponent', 0):.0f}",
                "plusses": [
                    f"Still win by ~{original_margin - 12:.0f} points",
                    "Fresh legs for States/Regionals",
                    "Gives JV swimmers meet experience"
                ],
                "drawbacks": [
                    "Smaller margin of victory",
                    "Risk if opponent has hidden fast times"
                ],
                "implication": "Strategic rest for championship season.",
                "risk": "Medium"
            })
        else:
            alternatives.append({
                "name": "Max Individual Points",
                "description": "Every swimmer swims exactly 2 individual events for maximum total entries",
                "projected_score": f"~{original_totals.get('seton', 0) + 3:.0f}-{original_totals.get('opponent', 0) - 3:.0f}",
                "plusses": [
                    "More entries = more scoring chances",
                    "Spreads load across team",
                    "Best for close dual meets"
                ],
                "drawbacks": [
                    "Some swimmers may swim weaker events",
                    "Higher total team fatigue"
                ],
                "implication": "Maximize scoring opportunities in close meets.",
                "risk": "Medium"
            })
        
        return alternatives
    
    def generate_event_suggestions(
        self,
        seton_roster: pd.DataFrame,
        opponent_df: pd.DataFrame,
        current_lineup: pd.DataFrame
    ) -> List[Dict[str, Any]]:
        """
        Generate strategic event suggestions for swimmers.
        Highlights potential improvements based on scoring vs opponent.
        
        Returns list of suggestions like:
        {
            "swimmer": "John Doe",
            "current_events": ["100 Free", "50 Free"],
            "suggested_change": "Move from 100 Free to 200 IM",
            "reason": "Would place 2nd instead of 3rd (+1 pt)",
            "potential_gain": 1,
            "priority": "medium"
        }
        """
        suggestions = []
        
        if seton_roster.empty or opponent_df.empty:
            return suggestions
        
        # Get Seton swimmers from current lineup
        seton_mask = current_lineup['team'].str.lower().str.contains('seton', na=False)
        seton_in_lineup = current_lineup[seton_mask].copy() if 'team' in current_lineup.columns else current_lineup.copy()
        
        # For each Seton swimmer, analyze their event options
        seton_swimmers = seton_roster['swimmer'].unique() if 'swimmer' in seton_roster.columns else []
        
        for swimmer in seton_swimmers:
            # Get all events this swimmer has times for
            swimmer_times = seton_roster[seton_roster['swimmer'] == swimmer]
            if len(swimmer_times) <= 2:
                continue  # Already optimal or limited options
            
            # Get their current lineup events
            current = seton_in_lineup[seton_in_lineup['swimmer'] == swimmer] if 'swimmer' in seton_in_lineup.columns else pd.DataFrame()
            current_events = current['event'].tolist() if not current.empty and 'event' in current.columns else []
            
            # Calculate expected points for each possible event
            event_scores = []
            for _, row in swimmer_times.iterrows():
                event = row['event']
                time = row['time']
                
                # Skip relays
                if 'relay' in str(event).lower():
                    continue
                
                # Get opponent times for this event
                opp_in_event = opponent_df[opponent_df['event'] == event] if 'event' in opponent_df.columns else pd.DataFrame()
                opp_times = sorted(opp_in_event['time'].tolist()) if not opp_in_event.empty and 'time' in opp_in_event.columns else []
                
                # Calculate place
                place = 1
                for opp_time in opp_times:
                    if time > opp_time:
                        place += 1
                
                # Get points (assume max 6 scoring places)
                points = self.POINT_VALUES.get(place, 0) if place <= 6 else 0
                
                event_scores.append({
                    'event': event,
                    'time': time,
                    'place': place,
                    'points': points,
                    'in_lineup': event in current_events
                })
            
            # Sort by points descending
            event_scores.sort(key=lambda x: x['points'], reverse=True)
            
            # Check if there's a better event not in lineup
            if len(event_scores) >= 3:
                top_2 = event_scores[:2]
                current_in_lineup = [e for e in event_scores if e['in_lineup']]
                
                # Find potential improvement
                for top_event in top_2:
                    if not top_event['in_lineup']:
                        # There's a better event not selected
                        # Find worst current event
                        if current_in_lineup:
                            worst_current = min(current_in_lineup, key=lambda x: x['points'])
                            gain = top_event['points'] - worst_current['points']
                            
                            if gain > 0:
                                priority = "high" if gain >= 2 else "medium" if gain >= 1 else "low"
                                suggestions.append({
                                    "swimmer": swimmer,
                                    "current_events": current_events,
                                    "suggested_change": f"Switch {worst_current['event']} → {top_event['event']}",
                                    "reason": f"Would place {top_event['place']} vs {worst_current['place']} (+{gain} pts)",
                                    "potential_gain": gain,
                                    "priority": priority
                                })
                                break  # One suggestion per swimmer
        
        # Sort by potential gain
        suggestions.sort(key=lambda x: x['potential_gain'], reverse=True)
        return suggestions[:10]  # Top 10 suggestions


# Singleton
strategy_analysis_service = StrategyAnalysisService()
