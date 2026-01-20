"""
Dual Meet Services Package

Services specific to dual meet (2-team head-to-head) optimization:
- Scoring service
- Nash equilibrium optimizer
- Gurobi optimizer
"""

from swim_ai_reflex.backend.services.dual_meet.scoring import DualMeetScoringService

__all__ = [
    "DualMeetScoringService",
]
