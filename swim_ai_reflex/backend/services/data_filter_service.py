"""
Data Filter Service - Pre-optimization filtering for meet-specific constraints.

Applies filters like:
- Gender (Girls only, Boys only, Both)
- Event Type (Individual only, with/without Relay, with/without Diving)
- Grade Range (e.g., 7-12 for all, 8-12 for scoring only)
"""

import pandas as pd

from swim_ai_reflex.backend.core.rules import VISAADualRules
from swim_ai_reflex.backend.services.base_service import BaseService


class DataFilterService(BaseService):
    """
    Pre-filters roster data before optimization based on meet configuration.
    """

    def filter_for_dual_meet(
        self,
        df: pd.DataFrame,
        gender: str = "F",  # 'F' = Girls only, 'M' = Boys only, 'B' = Both
        include_individual: bool = True,
        include_relay: bool = False,
        include_diving: bool = False,
        grades: list[int] | None = None,
        rules: VISAADualRules = None,
    ) -> pd.DataFrame:
        """
        Apply all filters for a dual meet optimization.

        Args:
            df: Raw roster DataFrame
            gender: 'F' for girls, 'M' for boys, 'B' for both
            include_individual: Include individual events
            include_relay: Include relay events
            include_diving: Include diving
            grades: List of grades to include (default: 7-12)
            rules: Meet rules for event classification

        Returns:
            Filtered DataFrame ready for optimization
        """
        if df.empty:
            return df

        if rules is None:
            rules = VISAADualRules()

        if grades is None:
            grades = [6, 7, 8, 9, 10, 11, 12]  # Include 6th grade as non-scoring

        filtered = df.copy()
        original_count = len(filtered)

        # --- EVENT NORMALIZATION & MAPPING ---
        # 0. Normalize event names to standard set (remove Age Group, Gender, map 400->500)
        if "event" in filtered.columns:

            def normalize_event(raw_event: str) -> str | None:
                if not raw_event:
                    return None
                raw = str(raw_event).lower()

                # Check for Diving
                if "dive" in raw or "diving" in raw:
                    return "Diving"

                # Check for Relays
                if "relay" in raw:
                    if "200" in raw and "medley" in raw:
                        return "200 Medley Relay"
                    if "200" in raw and "free" in raw:
                        return "200 Free Relay"
                    if "400" in raw and "free" in raw:
                        return "400 Free Relay"
                    return None  # specific filtering later

                # Individual Events Mapping
                if "back" in raw:
                    if "100" in raw:
                        return "100 Yard Backstroke"
                    # Exclude 50 Back (JV)
                    return None

                if "breast" in raw:
                    if "100" in raw:
                        return "100 Yard Breaststroke"
                    # Exclude 50 Breast (JV)
                    return None

                if "fly" in raw:
                    if "100" in raw:
                        return "100 Yard Butterfly"
                    # Exclude 50 Fly (JV)
                    return None

                if "im" in raw:
                    if "200" in raw:
                        return "200 Yard IM"
                    # Exclude 100 IM (JV)
                    return None

                if "free" in raw:
                    if "50" in raw and "150" not in raw and "500" not in raw:
                        return "50 Yard Freestyle"
                    if "100" in raw:
                        return "100 Yard Freestyle"
                    if "200" in raw:
                        return "200 Yard Freestyle"
                    if "500" in raw:
                        return "500 Yard Freestyle"
                    if "400" in raw:
                        return "500 Yard Freestyle"  # Map 400 to 500
                    return None

                return None

            filtered["original_event"] = filtered["event"]
            filtered["event"] = filtered["event"].apply(normalize_event)

            # Remove unmapped events (JV events, etc.)
            pre_map_count = len(filtered)
            filtered = filtered[filtered["event"].notna()]
            self._log_filter(
                "Event Normalization",
                "Standard 8 + Relays",
                pre_map_count,
                len(filtered),
            )

        # 1. Gender filter
        if gender in ["F", "M"] and "gender" in filtered.columns:
            filtered = filtered[filtered["gender"] == gender]
            self._log_filter("Gender", gender, original_count, len(filtered))

        # 2. Event type filter
        if "event" in filtered.columns:

            def event_filter(event_name: str) -> bool:
                if not event_name:
                    return False
                name_lower = str(event_name).lower()

                is_relay = "relay" in name_lower
                is_diving = "diving" in name_lower
                is_individual = not is_relay and not is_diving

                if is_relay and not include_relay:
                    return False
                if is_diving and not include_diving:
                    return False
                if is_individual and not include_individual:
                    return False

                return True

            pre_count = len(filtered)
            filtered = filtered[filtered["event"].apply(event_filter)]
            self._log_filter(
                "Event Type",
                f"Ind={include_individual}, Relay={include_relay}, Dive={include_diving}",
                pre_count,
                len(filtered),
            )

        # 3. Grade filter
        if "grade" in filtered.columns and grades:
            pre_count = len(filtered)
            # Ensure grade is int
            filtered["grade"] = pd.to_numeric(filtered["grade"], errors="coerce")
            filtered = filtered.dropna(subset=["grade"])
            filtered = filtered[filtered["grade"].isin(grades)]
            self._log_filter("Grade", str(grades), pre_count, len(filtered))

        # 4. Mark scoring eligibility
        if "grade" in filtered.columns:
            filtered["scoring_eligible"] = filtered["grade"].apply(
                lambda g: rules.is_scoring_eligible(g) if pd.notna(g) else True
            )
        else:
            filtered["scoring_eligible"] = True

        # Summary
        scoring_swimmers = (
            filtered[filtered["scoring_eligible"]]["swimmer"].nunique()
            if "swimmer" in filtered.columns
            else 0
        )
        non_scoring_swimmers = (
            filtered[~filtered["scoring_eligible"]]["swimmer"].nunique()
            if "swimmer" in filtered.columns
            else 0
        )

        print(f"\n{'=' * 50}")
        print("DATA FILTER SUMMARY")
        print(f"{'=' * 50}")
        print(f"Original entries: {original_count}")
        print(f"Filtered entries: {len(filtered)}")
        print(
            f"Unique swimmers: {filtered['swimmer'].nunique() if 'swimmer' in filtered.columns else 'N/A'}"
        )
        print(f"  - Scoring eligible (8-12): {scoring_swimmers}")
        print(f"  - Non-scoring (7th grade and below): {non_scoring_swimmers}")
        print(
            f"Events: {filtered['event'].nunique() if 'event' in filtered.columns else 'N/A'}"
        )
        print(f"{'=' * 50}\n")

        return filtered

    def _log_filter(self, filter_name: str, filter_value: str, before: int, after: int):
        """Log a filter application."""
        removed = before - after
        print(f"  [{filter_name}] {filter_value}: {before} → {after} (-{removed})")

    def get_individual_events(self, df: pd.DataFrame) -> list[str]:
        """Get list of individual events in the data."""
        if df.empty or "event" not in df.columns:
            return []

        events = df["event"].unique().tolist()
        return [
            e
            for e in events
            if "relay" not in str(e).lower() and "diving" not in str(e).lower()
        ]

    def validate_for_dual_meet(
        self, seton_df: pd.DataFrame, opponent_df: pd.DataFrame
    ) -> dict:
        """
        Validate that both rosters are ready for dual meet optimization.

        Returns:
            Dict with 'valid' bool and 'issues' list
        """
        issues = []

        # Check event counts
        seton_events = self.get_individual_events(seton_df)
        opponent_events = self.get_individual_events(opponent_df)

        if len(seton_events) != 8:
            issues.append(f"Seton has {len(seton_events)} events, expected 8")
        if len(opponent_events) != 8:
            issues.append(f"Opponent has {len(opponent_events)} events, expected 8")

        # Check swimmer counts per event
        for event in seton_events:
            count = len(seton_df[seton_df["event"] == event]["swimmer"].unique())
            if count < 4:
                issues.append(f"Seton has only {count} swimmers for {event} (need 4)")

        return {"valid": len(issues) == 0, "issues": issues}


# Singleton instance
data_filter_service = DataFilterService()
