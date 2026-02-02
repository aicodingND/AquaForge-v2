class SessionState:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SessionState, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        # In-Memory Storage
        self.seton_std = None
        self.opp_std = None
        self.lineup = None
        self.totals = None
        self.optimizer_candidate_seton = None
        self.last_result = None

    def clear(self):
        """Resets the in-memory state."""
        self._initialize()

    def set_rosters(self, seton_df, opp_df):
        self.seton_std = seton_df
        self.opp_std = opp_df

    def get_rosters(self):
        return self.seton_std, self.opp_std

    def set_results(self, lineup, totals):
        self.lineup = lineup
        self.totals = totals

    def get_results(self):
        return self.lineup, self.totals

    def set_candidate(self, candidate_df):
        self.optimizer_candidate_seton = candidate_df

    def get_candidate(self):
        return self.optimizer_candidate_seton


# Global instance
session = SessionState()
