from swim_ai_reflex.backend.core.session import session
from swim_ai_reflex.backend.core.analytics import analyze_lineup
from swim_ai_reflex.backend.utils.ai_coach import ask_coach

class AnalyticsService:
    @staticmethod
    def get_analytics(meet_type='dual'):
        """
        Retrieves current results and generates analytics insights.
        """
        lineup, totals = session.get_results()
        
        if lineup is None or lineup.empty:
            return None
            
        scored_dict = lineup.replace({float('nan'): None}).to_dict(orient='records')
        insights = analyze_lineup(scored_dict, meet_type)
        return insights

    @staticmethod
    def ask_coach(question):
        """
        Queries the AI Coach with current context.
        """
        lineup, totals = session.get_results()
        context = {
            'best_seton': lineup.to_dict('records') if lineup is not None else [],
            'score': totals if totals else {}
        }
        return ask_coach(question, context)
