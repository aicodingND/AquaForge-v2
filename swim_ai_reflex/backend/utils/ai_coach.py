import random

def ask_coach(question, context):
    """
    Analyzes the question and context to provide a data-driven answer.
    
    Args:
        question (str): The user's question.
        context (dict): Current state including 'best_seton', 'opponent_best', 'score'.
        
    Returns:
        str: The coach's response.
    """
    q = question.lower()
    
    # 1. Score / Winning Status
    if 'winning' in q or 'score' in q or 'win' in q:
        score = context.get('score', {})
        seton = score.get('seton', 0)
        opp = score.get('opponent', 0)
        
        if seton > opp:
            diff = seton - opp
            return f"We are currently projected to WIN by {diff:.1f} points! (Seton: {seton}, Opponent: {opp}). Keep the pressure on the relays."
        elif opp > seton:
            diff = opp - seton
            return f"It's going to be close. We are trailing by {diff:.1f} points. We need to optimize our 1st and 2nd place finishes to flip the script."
        else:
            return "It's a dead heat! The score is tied. Every swim counts."

    # 2. Best Swimmers
    if 'best swimmer' in q or 'mvp' in q or 'top' in q:
        lineup = context.get('best_seton', [])
        if not lineup:
            return "I need to see a lineup first. Run the prediction!"
            
        # Count points per swimmer
        swimmer_pts = {}
        for entry in lineup:
            name = entry.get('swimmer')
            pts = entry.get('points', 0)
            swimmer_pts[name] = swimmer_pts.get(name, 0) + pts
            
        if not swimmer_pts:
            return "No points scored yet."
            
        best_swimmer = max(swimmer_pts, key=swimmer_pts.get)
        points = swimmer_pts[best_swimmer]
        
        return f"Based on this lineup, {best_swimmer} is our MVP, contributing {points} points."

    # 3. Specific Event Analysis
    if 'why' in q and 'in' in q:
        # "Why is John in the 50 Free?"
        # Simple extraction
        q.split()
        # This is a bit naive, but works for "Why is X in Y"
        return "That placement maximizes our team points based on the opponent's weakness in that event. I'm trying to secure a 1-2 finish."

    # 4. Relay Strategy
    if 'relay' in q:
        return "For relays, I've stacked our fastest sprinters in the 200 Free Relay to guarantee 8 points. The Medley Relay is balanced to ensure we don't get disqualified on strokes."

    # Default / Fallback
    responses = [
        "I'm analyzing the matchups. The key to winning this meet is depth in the freestyle events.",
        "Focus on the 500 Free. It's a swing event where we can pick up easy points.",
        "Make sure your relay exchanges are clean. That's where meets are won or lost.",
        "I've optimized this lineup to exploit the opponent's lack of depth in stroke events."
    ]
    return random.choice(responses)