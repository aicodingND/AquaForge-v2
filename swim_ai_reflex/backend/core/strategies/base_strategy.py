from abc import ABC, abstractmethod
import pandas as pd
from typing import Dict, Any, Tuple, List

class BaseOptimizerStrategy(ABC):
    """
    Abstract base class for lineup optimization strategies.
    All optimizers must implement the optimize method.
    """
    
    @abstractmethod
    def optimize(
        self,
        seton_roster: pd.DataFrame,
        opponent_roster: pd.DataFrame,
        scoring_fn: Any,
        rules: Any,
        **kwargs
    ) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, float], List[Dict[str, Any]]]:
        """
        Run the optimization.
        
        Args:
            seton_roster: DataFrame of Seton swimmers and eligible events
            opponent_roster: DataFrame of opponent swimmers and events
            scoring_fn: Function to score the meet
            rules: MeetRules object containing constraints
            **kwargs: Additional strategy-specific parameters
            
        Returns:
            Tuple containing:
            1. Best Seton lineup (DataFrame)
            2. Scored meet DataFrame (Result)
            3. Totals dictionary {'seton': float, 'opponent': float}
            4. History list (for progress tracking)
        """
        pass
