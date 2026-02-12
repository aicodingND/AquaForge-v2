"""
LLM-Powered Strategy Advisor for Swim Meet Optimization

Uses GPT-4/Claude to analyze matchups and suggest tactical decisions.

Features:
- Lineup strategy recommendations
- Opponent weakness analysis
- Event-specific tactics
- Championship meet planning
- Natural language explanations
"""

import json
import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Try to import OpenAI (graceful degradation)
try:
    from openai import OpenAI

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI not available. Install with: pip install openai")


@dataclass
class StrategyRecommendation:
    """AI-generated strategy recommendation"""

    recommendation: str
    confidence: float  # 0-1
    rationale: str
    key_insights: list[str]
    tactical_adjustments: list[str]
    risk_level: str  # 'low', 'medium', 'high'


class LLMStrategyAdvisor:
    """
    AI-powered strategy advisor using large language models.

    Analyzes swim meet scenarios and provides strategic recommendations
    for lineup optimization, event selection, and tactical decisions.
    """

    def __init__(self, api_key: str | None = None, model: str = "gpt-4-turbo-preview"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.available = False

        if OPENAI_AVAILABLE and self.api_key:
            try:
                self.client = OpenAI(api_key=self.api_key)
                self.available = True
                logger.info(f"LLM Strategy Advisor initialized with {model}")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
        else:
            logger.warning("LLM Advisor not available (missing API key or library)")

    def analyze_lineup_strategy(
        self,
        seton_roster: list[dict],
        opponent_roster: list[dict],
        meet_context: dict | None = None,
    ) -> StrategyRecommendation:
        """Analyze lineup matchup and provide strategic recommendations."""
        if not self.available:
            return self._fallback_strategy(seton_roster, opponent_roster)

        try:
            context = self._prepare_context(seton_roster, opponent_roster, meet_context)
            prompt = self._create_strategy_prompt(context)

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=1500,
            )

            content = response.choices[0].message.content
            recommendation = self._parse_llm_response(content)

            logger.info("LLM strategy recommendation generated")
            return recommendation

        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")
            return self._fallback_strategy(seton_roster, opponent_roster)

    def explain_lineup_decision(
        self, swimmer_name: str, event: str, decision: str, reasoning: str
    ) -> str:
        """Generate natural language explanation for a lineup decision."""
        if not self.available:
            return f"{swimmer_name} {decision} for {event}. Reasoning: {reasoning}"

        try:
            prompt = f"""
            Explain this lineup decision in simple terms for a coach:

            Swimmer: {swimmer_name}
            Event: {event}
            Decision: {decision}
            Technical Reasoning: {reasoning}

            Provide a clear, concise explanation that a coach or parent would understand.
            Focus on the strategic benefit.
            """

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a swim coaching AI assistant. Explain lineup decisions clearly and strategically.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.5,
                max_tokens=200,
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"Explanation generation failed: {e}")
            return f"{swimmer_name} {decision} for {event}. {reasoning}"

    def _get_system_prompt(self) -> str:
        """System prompt defining the AI's role"""
        return """You are an expert swimming coach and strategist with deep knowledge of:
        - Dual meet scoring rules (6-3-2-1 for top 4 finishers)
        - Event strategy and swimmer specializations
        - Fatigue management and event spacing
        - Championship meet tactics and qualifying standards
        - Game theory in competitive swimming

        Provide strategic recommendations that maximize team scoring while managing
        swimmer workload and performance quality. Consider both short-term results
        and long-term swimmer development.

        Respond in JSON format with:
        {
            "recommendation": "Main strategic recommendation",
            "confidence": 0.85,
            "rationale": "Detailed explanation",
            "key_insights": ["Insight 1", "Insight 2"],
            "tactical_adjustments": ["Adjustment 1", "Adjustment 2"],
            "risk_level": "medium"
        }
        """

    def _create_strategy_prompt(self, context: dict) -> str:
        """Create prompt for strategy analysis"""
        return f"""
        Analyze this swim meet matchup and provide strategic recommendations:

        **Seton Swimmers:**
        {json.dumps(context["seton_summary"], indent=2)}

        **Opponent Swimmers:**
        {json.dumps(context["opponent_summary"], indent=2)}

        **Meet Context:**
        {json.dumps(context.get("meet_context", {}), indent=2)}

        **Key Questions:**
        1. What are the opponent's main weaknesses we can exploit?
        2. Which events should we prioritize for maximum scoring?
        3. Are there any risky but high-reward strategies worth considering?
        4. How should we manage our top swimmers to avoid over-racing?
        5. What's the optimal balance between individual times and team scoring?

        Provide your strategic analysis in the specified JSON format.
        """

    def _prepare_context(
        self,
        seton_roster: list[dict],
        opponent_roster: list[dict],
        meet_context: dict | None,
    ) -> dict:
        """Prepare analysis context from roster data"""
        seton_summary = {
            "total_swimmers": len(seton_roster),
            "events": self._group_by_event(seton_roster),
            "top_performers": self._get_top_performers(seton_roster, n=5),
        }

        opponent_summary = {
            "total_swimmers": len(opponent_roster),
            "events": self._group_by_event(opponent_roster),
            "top_performers": self._get_top_performers(opponent_roster, n=5),
        }

        return {
            "seton_summary": seton_summary,
            "opponent_summary": opponent_summary,
            "meet_context": meet_context or {"type": "dual_meet"},
        }

    def _group_by_event(self, roster: list[dict]) -> dict:
        """Group swimmers by event"""
        events: dict[str, list[dict]] = {}
        for swimmer in roster:
            event = swimmer.get("event", "Unknown")
            if event not in events:
                events[event] = []
            events[event].append(
                {
                    "name": swimmer.get("name", "Unknown"),
                    "time": swimmer.get("time", 999.99),
                }
            )
        return events

    def _get_top_performers(self, roster: list[dict], n: int = 5) -> list[dict]:
        """Get top N performers from roster"""
        sorted_roster = sorted(roster, key=lambda x: x.get("time", 999.99))
        return [
            {
                "name": s.get("name", "Unknown"),
                "event": s.get("event", "Unknown"),
                "time": s.get("time", 999.99),
            }
            for s in sorted_roster[:n]
        ]

    def _parse_llm_response(self, content: str) -> StrategyRecommendation:
        """Parse LLM JSON response"""
        try:
            start = content.find("{")
            end = content.rfind("}") + 1
            json_str = content[start:end]
            data = json.loads(json_str)

            return StrategyRecommendation(
                recommendation=data.get("recommendation", ""),
                confidence=data.get("confidence", 0.7),
                rationale=data.get("rationale", ""),
                key_insights=data.get("key_insights", []),
                tactical_adjustments=data.get("tactical_adjustments", []),
                risk_level=data.get("risk_level", "medium"),
            )
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return StrategyRecommendation(
                recommendation="Unable to parse AI recommendation",
                confidence=0.5,
                rationale=content,
                key_insights=[],
                tactical_adjustments=[],
                risk_level="unknown",
            )

    def _fallback_strategy(
        self, seton_roster: list[dict], opponent_roster: list[dict]
    ) -> StrategyRecommendation:
        """Rule-based fallback when LLM unavailable"""
        return StrategyRecommendation(
            recommendation="Focus on events where Seton has the strongest swimmers relative to the opponent",
            confidence=0.6,
            rationale="LLM advisor not available. Using rule-based strategy.",
            key_insights=[
                f"Seton has {len(seton_roster)} swimmers available",
                f"Opponent has {len(opponent_roster)} swimmers",
                "Optimize for maximum point differential",
            ],
            tactical_adjustments=[
                "Assign best swimmers to their strongest events",
                "Consider fatigue when assigning multiple events",
                "Exploit opponent weaknesses where identified",
            ],
            risk_level="low",
        )
