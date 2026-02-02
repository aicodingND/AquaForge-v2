from dataclasses import dataclass, field

import pandas as pd


@dataclass
class MeetRules:
    """
    Base configuration for meet scoring rules.
    Includes validation to ensure logical consistency.
    """

    name: str
    individual_points: list[int]
    relay_points: list[int]
    max_individual_events_per_swimmer: int
    max_total_events_per_swimmer: int
    max_entries_per_team_per_event: int
    max_relays_per_team_per_event: int
    max_scorers_per_team_individual: int
    max_scorers_per_team_relay: int
    min_scoring_grade: int = 8

    def __post_init__(self):
        """Validate rules configuration."""
        if not self.individual_points:
            raise ValueError("individual_points list cannot be empty")

        if not self.relay_points:
            raise ValueError("relay_points list cannot be empty")

        if self.max_individual_events_per_swimmer <= 0:
            raise ValueError("max_individual_events_per_swimmer must be positive")

        if self.max_total_events_per_swimmer < self.max_individual_events_per_swimmer:
            raise ValueError(
                "max_total_events_per_swimmer must be >= max_individual_events_per_swimmer"
            )

        if self.max_entries_per_team_per_event <= 0:
            raise ValueError("max_entries_per_team_per_event must be positive")


@dataclass
class VISAADualRules(MeetRules):
    """
    VISAA Dual-Meet Rules (legacy - consider using SetonDualRules instead):
    - Individual: Top 7 places score [8, 6, 5, 4, 3, 2, 1]
    - Relays: Top 3 score [10, 5, 3] (per Coach Koehr)
    - Grades 8-12 are SCORING eligible

    Note: This is kept for backward compatibility. SetonDualRules has updated
    values from Coach Koehr's official documentation.
    """

    name: str = "VISAA Dual Meet"
    individual_points: list[int] = field(default_factory=lambda: [8, 6, 5, 4, 3, 2, 1])
    relay_points: list[int] = field(
        default_factory=lambda: [10, 5, 3]
    )  # Fixed per Coach Koehr
    max_individual_events_per_swimmer: int = 2
    max_total_events_per_swimmer: int = 4
    max_entries_per_team_per_event: int = 4
    max_relays_per_team_per_event: int = 2  # A and B only
    min_scoring_grade: int = 8
    max_scorers_per_team_individual: int = 3
    max_scorers_per_team_relay: int = 2

    # Non-scoring grades (can place but don't earn points) - 7th grade and below
    non_scoring_grades: list[int] = field(default_factory=lambda: [6, 7])

    # Standard Event Order for Fatigue Checking
    event_order: list[str] = field(
        default_factory=lambda: [
            "200 Medley Relay",
            "200 Free",
            "200 IM",
            "50 Free",
            "Diving",
            "100 Fly",
            "100 Free",
            "500 Free",
            "200 Free Relay",
            "100 Back",
            "100 Breast",
            "400 Free Relay",
        ]
    )

    # Individual events only (for filtering)
    individual_events: list[str] = field(
        default_factory=lambda: [
            "200 Free",
            "200 IM",
            "50 Free",
            "100 Fly",
            "100 Free",
            "500 Free",
            "100 Back",
            "100 Breast",
        ]
    )

    def is_scoring_eligible(self, grade: int) -> bool:
        """Check if a swimmer's grade makes them scoring-eligible."""
        if grade is None or pd.isna(grade):
            return True  # Assume eligible if grade unknown
        return grade >= self.min_scoring_grade and grade not in self.non_scoring_grades

    def is_individual_event(self, event_name: str) -> bool:
        """Check if event is an individual event (not relay/diving)."""
        if not event_name:
            return False
        name_lower = event_name.lower()
        return "relay" not in name_lower and "diving" not in name_lower

    def is_back_to_back(self, event1: str, event2: str) -> bool:
        """Check if two events are consecutive in standard order."""
        if not event1 or not event2:
            return False

        # Normalize names for matching
        def normalize(name):
            n = name.lower()
            if "medley" in n:
                return "200 Medley Relay"
            if "diving" in n:
                return "Diving"
            if "fly" in n:
                return "100 Fly"
            if "back" in n:
                return "100 Back"
            if "breast" in n:
                return "100 Breast"
            if "im" in n:
                return "200 IM"
            if "50 free" in n:
                return "50 Free"
            if "100 free" in n:
                return "100 Free"
            if "200 free" in n and "relay" not in n:
                return "200 Free"
            if "500 free" in n:
                return "500 Free"
            if "200 free relay" in n:
                return "200 Free Relay"
            if "400 free relay" in n:
                return "400 Free Relay"
            return ""

        e1 = normalize(event1)
        e2 = normalize(event2)

        if not e1 or not e2:
            return False

        try:
            idx1 = self.event_order.index(e1)
            idx2 = self.event_order.index(e2)
            return abs(idx1 - idx2) == 1
        except ValueError:
            return False


@dataclass
class VISAAChampRules(MeetRules):
    """
    VISAA Championship Rules (Consolation Finals scoring).
    Note: This uses consolation scoring. For championship finals, use VISAAStateRules.
    """

    name: str = "VISAA Championship (Consolation)"
    individual_points: list[int] = field(
        default_factory=lambda: [20, 17, 16, 15, 14, 13, 12, 11, 9, 7, 6, 5, 4, 3, 2, 1]
    )
    # Relays usually double individual in championship
    relay_points: list[int] = field(
        default_factory=lambda: [
            40,
            34,
            32,
            30,
            28,
            26,
            24,
            22,
            18,
            14,
            12,
            10,
            8,
            6,
            4,
            2,
        ]
    )
    max_individual_events_per_swimmer: int = 2
    max_total_events_per_swimmer: int = 4
    max_entries_per_team_per_event: int = 999
    max_relays_per_team_per_event: int = 2
    min_scoring_grade: int = 8
    max_scorers_per_team_individual: int = 16
    max_scorers_per_team_relay: int = 16


@dataclass
class SetonDualRules(MeetRules):
    """
    Seton Dual Meet Rules (from Coach Koehr's official documentation).
    Source: setonswimming.org/so-how-is-a-high-school-meet-scored-anyway/

    - Individual: Top 7 score [8, 6, 5, 4, 3, 2, 1]
    - Relay: Top 3 score [10, 5, 3]
    - 4 varsity entries per individual event
    - 2 relay entries per event (A and B)
    - Grades 7 and below = exhibition (non-scoring)
    """

    name: str = "Seton Dual Meet"
    individual_points: list[int] = field(default_factory=lambda: [8, 6, 5, 4, 3, 2, 1])
    relay_points: list[int] = field(default_factory=lambda: [10, 5, 3])
    max_individual_events_per_swimmer: int = 2
    max_total_events_per_swimmer: int = 4  # 2 indiv + 2 relay OR 1 indiv + 3 relay
    max_entries_per_team_per_event: int = 4  # varsity entries
    max_relays_per_team_per_event: int = 2  # A and B relays
    min_scoring_grade: int = 8  # 7th grade = exhibition
    max_scorers_per_team_individual: int = 4
    max_scorers_per_team_relay: int = 2

    # Non-scoring grades
    non_scoring_grades: list[int] = field(default_factory=lambda: [6, 7])

    # Standard Event Order
    event_order: list[str] = field(
        default_factory=lambda: [
            "200 Medley Relay",
            "200 Free",
            "200 IM",
            "50 Free",
            "Diving",
            "100 Fly",
            "100 Free",
            "500 Free",
            "200 Free Relay",
            "100 Back",
            "100 Breast",
            "400 Free Relay",
        ]
    )


@dataclass
class VCACChampRules(MeetRules):
    """
    VCAC Conference Championship Rules (12-Place Scoring).
    Authority: setonswimming.org, VCAC official rules, Seton Parents' Handbook 2024-25
    Last Validated: 2026-02-02

    Scoring (12 places):
    - Individual/Diving: 16-13-12-11-10-9-7-5-4-3-2-1
    - Relay: 32-26-24-22-20-18-14-10-8-6-4-2 (exactly 2× individual)

    Entry Constraints (NFHS Rule 3-2-1):
    - Max 2 individual events per swimmer (diving counts as 1)
    - Max 4 total events per swimmer
    - Max 3 relays per swimmer (200 Medley, 200 Free, 400 Free)
    - Only top 4 swimmers per team per event can score
    - Only A and B relays can score
    - 11-Dive championship format for diving

    Exhibition Rules:
    - NO exhibition swims at championship meets
    - Only Varsity swimmers participate (all entered swimmers score)
    - 7th graders swim at JV Invitational instead
    """

    name: str = "VCAC Championship"
    # 12-place individual scoring (same for diving)
    individual_points: list[int] = field(
        default_factory=lambda: [16, 13, 12, 11, 10, 9, 7, 5, 4, 3, 2, 1]
    )
    # 12-place relay scoring (2× individual at each placement)
    relay_points: list[int] = field(
        default_factory=lambda: [32, 26, 24, 22, 20, 18, 14, 10, 8, 6, 4, 2]
    )
    max_individual_events_per_swimmer: int = 2
    max_total_events_per_swimmer: int = 4  # 2 individual + up to 3 relays, max 4 total
    max_entries_per_team_per_event: int = 999  # unlimited entries
    max_relays_per_team_per_event: int = 2  # A and B both score
    min_scoring_grade: int = 8  # 7th graders not eligible per VISAA
    max_scorers_per_team_individual: int = 4  # Only top 4 per team score
    max_scorers_per_team_relay: int = 2

    # VCAC-specific rules
    diving_counts_as_individual: bool = True
    max_relays: int = 3  # only 3 relay events exist
    no_exhibition: bool = True  # Championship: all entered swimmers score

    def is_valid_entry(
        self, swim_individual: int, is_diver: bool, relay_count: int
    ) -> bool:
        """
        Check if swimmer entry is valid per VCAC rules.

        Rules:
        - Max 2 individual swim events
        - Diving counts as 1 individual
        - Max 3 relays
        - Max 4 total events
        """
        if swim_individual > 2:
            return False
        if relay_count > 3:
            return False

        individual_used = swim_individual + (1 if is_diver else 0)
        total_events = individual_used + relay_count

        return individual_used <= 2 and total_events <= 4


@dataclass
class VISAAStateRules(MeetRules):
    """
    VISAA State Championship Rules (16-Place Scoring).
    Authority: visaa.org official rules
    Last Validated: 2026-01-21

    Format: Prelims → Championship Finals (1-8) + Consolation Finals (9-16)

    Unified 16-Place Scoring:
    - Individual/Diving: 20-17-16-15-14-13-12-11-9-7-6-5-4-3-2-1
    - Relay: 40-34-32-30-28-26-24-22-18-14-12-10-8-6-4-2 (exactly 2× individual)

    CRITICAL EDGE CASES:
    - Consolation finals swimmers can NEVER outscore Championship finals swimmers
    - Bonus event swimmers are NOT eligible to score points
    - If 5+ swimmers from one team qualify, coach must designate 4 scorers
    - B Relays may be entered as exhibition (no scoring)
    - NO exhibition swims allowed otherwise
    """

    name: str = "VISAA State Championship"
    # 16-place individual scoring (same for diving)
    individual_points: list[int] = field(
        default_factory=lambda: [
            20,
            17,
            16,
            15,
            14,
            13,
            12,
            11,  # Championship Finals (1-8)
            9,
            7,
            6,
            5,
            4,
            3,
            2,
            1,  # Consolation Finals (9-16)
        ]
    )
    # 16-place relay scoring (2× individual at each placement)
    relay_points: list[int] = field(
        default_factory=lambda: [
            40,
            34,
            32,
            30,
            28,
            26,
            24,
            22,  # Championship Finals (1-8)
            18,
            14,
            12,
            10,
            8,
            6,
            4,
            2,  # Consolation Finals (9-16)
        ]
    )
    max_individual_events_per_swimmer: int = 2
    max_total_events_per_swimmer: int = 4
    max_entries_per_team_per_event: int = 999  # Unlimited entries, but only 4 score
    max_relays_per_team_per_event: int = 2
    min_scoring_grade: int = 8
    max_scorers_per_team_individual: int = 4  # Only top 4 per team score
    max_scorers_per_team_relay: int = 2

    # VISAA State-specific rules
    has_prelims_finals: bool = True
    no_exhibition: bool = True
    bonus_swimmers_score: bool = False  # Bonus event swimmers cannot score


# =============================================================================
# MEET PROFILE REGISTRY
# =============================================================================

MEET_PROFILES = {
    # Dual Meets
    "seton_dual": SetonDualRules,
    "visaa_dual": VISAADualRules,
    # Championships
    "vcac_championship": VCACChampRules,
    "visaa_state": VISAAStateRules,
    "visaa_championship": VISAAChampRules,  # Legacy/consolation
}


def get_meet_profile(profile_name: str) -> MeetRules:
    """
    Get a meet profile by name.

    Available profiles:
    - seton_dual: Seton Dual Meet (Coach Koehr rules)
    - visaa_dual: VISAA Dual Meet (legacy)
    - vcac_championship: VCAC Conference Championship
    - visaa_state: VISAA State Championship
    """
    if profile_name not in MEET_PROFILES:
        available = list(MEET_PROFILES.keys())
        raise ValueError(f"Unknown profile '{profile_name}'. Available: {available}")
    return MEET_PROFILES[profile_name]()


def list_meet_profiles() -> list[dict]:
    """List all available meet profiles with descriptions."""
    profiles = []
    for name, cls in MEET_PROFILES.items():
        instance = cls()
        profiles.append(
            {
                "id": name,
                "name": instance.name,
                "individual_first": instance.individual_points[0]
                if instance.individual_points
                else 0,
                "relay_first": instance.relay_points[0] if instance.relay_points else 0,
            }
        )
    return profiles


# Legacy function for backwards compatibility
def get_rules(meet_type: str) -> MeetRules:
    """Legacy function - use get_meet_profile() instead."""
    if meet_type and meet_type.lower() == "champ":
        return VISAAChampRules()
    if meet_type and meet_type.lower() == "vcac":
        return VCACChampRules()
    if meet_type and meet_type.lower() == "state":
        return VISAAStateRules()
    return SetonDualRules()  # Default to Seton rules
