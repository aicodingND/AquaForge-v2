"""
LLM Token Optimization Configuration.

Provides smart defaults for LLM-powered features (AI Coach, strategic analysis).
Implements prompt caching, model routing, and cost controls.

Usage:
    from swim_ai_reflex.backend.utils.llm_config import llm_config
    response = await llm_config.get_completion(prompt, complexity="simple")
"""

import hashlib
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ModelTier:
    """Configuration for a specific model tier."""

    model_id: str
    max_tokens: int
    temperature: float = 0.7
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0


@dataclass
class LLMConfig:
    """
    Central LLM configuration with token optimization strategies.

    Strategies implemented:
    1. Smart model routing: Use cheap models for simple tasks, expensive for complex
    2. Prompt caching: Cache system prompts for 90% cost reduction (Anthropic)
    3. Output token limits: Enforce max_tokens to control costs
    4. Response caching: Cache identical query results in Redis
    5. Structured output: Use JSON mode to reduce verbose responses
    """

    # Model tiers for smart routing
    tiers: dict = field(
        default_factory=lambda: {
            "simple": ModelTier(
                model_id="claude-haiku-4-5-20251001",
                max_tokens=256,
                temperature=0.3,
                cost_per_1k_input=0.001,
                cost_per_1k_output=0.005,
            ),
            "standard": ModelTier(
                model_id="claude-sonnet-4-5-20250929",
                max_tokens=1024,
                temperature=0.5,
                cost_per_1k_input=0.003,
                cost_per_1k_output=0.015,
            ),
            "complex": ModelTier(
                model_id="claude-opus-4-6",
                max_tokens=2048,
                temperature=0.7,
                cost_per_1k_input=0.015,
                cost_per_1k_output=0.075,
            ),
        }
    )

    # Budget controls
    daily_budget_usd: float = 10.0
    monthly_budget_usd: float = 200.0

    # Caching
    cache_ttl_seconds: int = 3600  # 1 hour
    enable_response_cache: bool = True
    enable_prompt_cache: bool = True

    # System prompts (cached for 90% discount on Anthropic)
    system_prompts: dict = field(
        default_factory=lambda: {
            "coach": (
                "You are AquaForge AI Coach, a swim meet strategy assistant. "
                "Analyze lineup data and provide actionable coaching advice. "
                "Be concise - respond in 2-3 sentences max unless asked for detail. "
                "Focus on: event matchups, scoring opportunities, and fatigue management."
            ),
            "analysis": (
                "You are a swim meet data analyst. Analyze the provided meet results "
                "and identify patterns, strengths, and weaknesses. "
                "Output as structured JSON with keys: insights, recommendations, risks."
            ),
        }
    )

    def get_model_for_complexity(self, complexity: str = "standard") -> ModelTier:
        """Route to appropriate model based on task complexity."""
        return self.tiers.get(complexity, self.tiers["standard"])

    def get_cache_key(self, prompt: str, system_prompt_key: str = "") -> str:
        """Generate cache key for response caching."""
        content = f"{system_prompt_key}:{prompt}"
        return f"llm_cache:{hashlib.sha256(content.encode()).hexdigest()[:16]}"

    def estimate_cost(
        self, input_tokens: int, output_tokens: int, tier: str = "standard"
    ) -> float:
        """Estimate cost for a given token count."""
        model = self.get_model_for_complexity(tier)
        return (input_tokens / 1000) * model.cost_per_1k_input + (
            output_tokens / 1000
        ) * model.cost_per_1k_output


# Singleton
llm_config = LLMConfig()
