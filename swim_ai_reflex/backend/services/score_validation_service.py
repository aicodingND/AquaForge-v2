"""
Score Validation Service - Detects abnormal scoring patterns and provides actionable feedback.
"""

import pandas as pd

from swim_ai_reflex.backend.core.scoring import EVENT_ORDER
from swim_ai_reflex.backend.services.base_service import BaseService


class ScoreValidationService(BaseService):
    """
    Validates meet scoring results and detects anomalies.
    """

    # Realistic score ranges for dual meets
    NORMAL_DUAL_MEET_RANGE = (40, 150)  # Typical dual meet scores
    WARNING_THRESHOLD = 800  # Scores above this trigger warnings
    ERROR_THRESHOLD = 1500  # Scores above this trigger errors

    # Expected entries per event
    TYPICAL_ENTRIES_PER_EVENT = (1, 6)  # Min 1, max 6 per team per event
    MAX_EVENTS_PER_SWIMMER = 2  # NFHS rule

    def validate_scores(
        self, totals: dict[str, float], scored_df: pd.DataFrame, roster_df: pd.DataFrame
    ) -> dict[str, any]:
        """
        Validate scoring results and detect anomalies.

        Args:
            totals: Score totals dict {'seton': X, 'opponent': Y}
            scored_df: Scored DataFrame with places and points
            roster_df: Original roster DataFrame

        Returns:
            Validation result with status, warnings, and recommendations
        """
        issues = []
        warnings = []
        recommendations = []

        seton_score = totals.get("seton", 0)
        opponent_score = totals.get("opponent", 0)

        # Check 1: Score magnitude
        if seton_score > self.ERROR_THRESHOLD or opponent_score > self.ERROR_THRESHOLD:
            issues.append(
                {
                    "type": "ABNORMAL_SCORE",
                    "severity": "ERROR",
                    "message": f"Scores are abnormally high (Seton: {seton_score:.0f}, Opponent: {opponent_score:.0f})",
                    "expected": f"{self.NORMAL_DUAL_MEET_RANGE[0]}-{self.NORMAL_DUAL_MEET_RANGE[1]} points per team",
                    "actual": f"{seton_score:.0f} / {opponent_score:.0f}",
                }
            )
            recommendations.append("Check for duplicate swimmer entries in the data")
            recommendations.append(
                "Verify max_scorers_per_team rule is enforced (should be 3)"
            )

        elif (
            seton_score > self.WARNING_THRESHOLD
            or opponent_score > self.WARNING_THRESHOLD
        ):
            warnings.append(
                {
                    "type": "HIGH_SCORE",
                    "severity": "WARNING",
                    "message": f"Scores are higher than typical (Seton: {seton_score:.0f}, Opponent: {opponent_score:.0f})",
                    "expected": f"{self.NORMAL_DUAL_MEET_RANGE[0]}-{self.NORMAL_DUAL_MEET_RANGE[1]} points per team",
                }
            )

        # Check 2: Duplicate entries
        if not roster_df.empty:
            duplicate_check = self._check_duplicates(roster_df)
            if duplicate_check["has_duplicates"]:
                issues.append(
                    {
                        "type": "DUPLICATE_ENTRIES",
                        "severity": "ERROR",
                        "message": f"Found {duplicate_check['count']} duplicate entries",
                        "details": duplicate_check["examples"],
                    }
                )
                recommendations.append("Remove duplicate entries from source data")
                recommendations.append(
                    'Use deduplication: df.drop_duplicates(subset=["swimmer", "event"])'
                )

        # Check 3: Entries per event
        if (
            not scored_df.empty
            and "event" in scored_df.columns
            and "team" in scored_df.columns
        ):
            entries_check = self._check_entries_per_event(scored_df)
            if entries_check["violations"]:
                warnings.append(
                    {
                        "type": "EXCESSIVE_ENTRIES",
                        "severity": "WARNING",
                        "message": f"{len(entries_check['violations'])} events have excessive entries",
                        "details": entries_check["violations"][:5],  # Show first 5
                    }
                )

        # Note: We removed the "events per swimmer" check because:
        # 1. The optimizer already enforces the 2-event rule correctly
        # 2. The roster_df naturally has many events per swimmer (their full times list)
        # 3. This was causing false positives ("43 swimmers exceed limit")

        # Determine overall status
        status = "VALID"
        if issues:
            status = "INVALID"
        elif warnings:
            status = "WARNING"

        return {
            "status": status,
            "valid": status == "VALID",
            "scores": totals,
            "issues": issues,
            "warnings": warnings,
            "recommendations": list(set(recommendations)),  # Deduplicate
            "summary": self._generate_summary(status, totals, issues, warnings),
        }

    def _check_duplicates(self, df: pd.DataFrame) -> dict[str, any]:
        """Check for duplicate swimmer-event combinations."""
        if df.empty:
            return {"has_duplicates": False, "count": 0, "examples": []}

        # True duplicates: same swimmer in same event multiple times
        duplicates = df[df.duplicated(subset=["swimmer", "event"], keep=False)]

        if duplicates.empty:
            return {"has_duplicates": False, "count": 0, "examples": []}

        examples = []
        for (swimmer, event), group in duplicates.groupby(["swimmer", "event"]):
            if len(group) > 1:
                examples.append(
                    {
                        "swimmer": swimmer,
                        "event": event,
                        "count": len(group),
                        "times": group["time"].tolist()
                        if "time" in group.columns
                        else [],
                    }
                )
                if len(examples) >= 5:  # Limit examples
                    break

        return {"has_duplicates": True, "count": len(duplicates), "examples": examples}

    def _check_entries_per_event(self, df: pd.DataFrame) -> dict[str, any]:
        """Check if any event has too many entries per team."""
        violations = []

        for (event, team), group in df.groupby(["event", "team"]):
            count = len(group)
            if count > self.TYPICAL_ENTRIES_PER_EVENT[1]:
                violations.append(
                    {
                        "event": event,
                        "team": team,
                        "count": count,
                        "expected_max": self.TYPICAL_ENTRIES_PER_EVENT[1],
                    }
                )

        return {"violations": violations}

    def _check_events_per_swimmer(self, df: pd.DataFrame) -> dict[str, any]:
        """Check if any swimmer exceeds 2-event limit."""
        violations = []

        if "swimmer" not in df.columns or "event" not in df.columns:
            return {"violations": []}

        for swimmer, group in df.groupby("swimmer"):
            event_count = group["event"].nunique()
            if event_count > self.MAX_EVENTS_PER_SWIMMER:
                violations.append(
                    {
                        "swimmer": swimmer,
                        "event_count": event_count,
                        "events": group["event"].unique().tolist(),
                        "limit": self.MAX_EVENTS_PER_SWIMMER,
                    }
                )

        return {"violations": violations}

    def _generate_summary(
        self,
        status: str,
        totals: dict[str, float],
        issues: list[dict],
        warnings: list[dict],
    ) -> str:
        """Generate human-readable summary."""
        seton = totals.get("seton", 0)
        opponent = totals.get("opponent", 0)

        if status == "VALID":
            return f"✅ Scores are valid (Seton: {seton:.0f}, Opponent: {opponent:.0f})"
        elif status == "WARNING":
            return f"⚠️ Scores validated with {len(warnings)} warning(s) (Seton: {seton:.0f}, Opponent: {opponent:.0f})"
        else:
            return f"❌ Scores are invalid with {len(issues)} error(s) (Seton: {seton:.0f}, Opponent: {opponent:.0f})"

    def detect_data_issues(self, df: pd.DataFrame) -> dict[str, any]:
        """
        Detect common data issues and suggest fixes.
        Returns structured issues with auto-fix availability.
        """
        issues = []

        if df.empty:
            return {"issues": [], "fixable": False, "fix_count": 0}

        # Issue 1: Duplicate entries (same swimmer + same event)
        duplicates = df[df.duplicated(subset=["swimmer", "event"], keep=False)]
        if not duplicates.empty:
            dup_count = (
                len(duplicates)
                - duplicates.drop_duplicates(subset=["swimmer", "event"]).shape[0]
            )
            issues.append(
                {
                    "type": "DUPLICATES",
                    "severity": "error",
                    "title": "Duplicate Entries Found",
                    "description": f"{dup_count} duplicate swimmer-event combinations detected",
                    "fix_available": True,
                    "fix_action": "Keep fastest time for each swimmer-event pair",
                    "affected_count": dup_count,
                }
            )

        # Issue 2: Missing required columns
        required = ["swimmer", "event", "time", "team"]
        missing = [col for col in required if col not in df.columns]
        if missing:
            issues.append(
                {
                    "type": "MISSING_COLUMNS",
                    "severity": "error",
                    "title": "Missing Required Columns",
                    "description": f"Missing: {', '.join(missing)}",
                    "fix_available": False,
                    "fix_action": "Add missing columns to your data file",
                    "affected_count": len(missing),
                }
            )

        # Issue 3: Invalid times (negative, zero, or unrealistic)
        if "time" in df.columns:
            invalid_times = df[
                (df["time"] <= 0) | (df["time"] > 600)
            ]  # 0 or >10 minutes
            if not invalid_times.empty:
                issues.append(
                    {
                        "type": "INVALID_TIMES",
                        "severity": "warning",
                        "title": "Invalid Times Detected",
                        "description": f"{len(invalid_times)} entries have invalid times (≤0 or >10 min)",
                        "fix_available": True,
                        "fix_action": "Remove entries with invalid times",
                        "affected_count": len(invalid_times),
                    }
                )

        # Issue 4: Empty swimmer names
        if "swimmer" in df.columns:
            empty_names = df[
                df["swimmer"].isna() | (df["swimmer"].astype(str).str.strip() == "")
            ]
            if not empty_names.empty:
                issues.append(
                    {
                        "type": "EMPTY_NAMES",
                        "severity": "error",
                        "title": "Empty Swimmer Names",
                        "description": f"{len(empty_names)} entries have no swimmer name",
                        "fix_available": True,
                        "fix_action": "Remove entries with missing names",
                        "affected_count": len(empty_names),
                    }
                )

        # Issue 5: Unrecognized Events (Data Mismatch)
        if "event" in df.columns:
            # Check for events not in our standard list (ignoring case/spacing differences handled by fix)
            known_events = set(EVENT_ORDER)
            # Basic normalization for check: strip
            df_events = df["event"].astype(str).str.strip()
            unknown_mask = ~df_events.isin(known_events)

            if unknown_mask.any():
                unknown_list = df.loc[unknown_mask, "event"].unique().tolist()
                issues.append(
                    {
                        "type": "UNRECOGNIZED_EVENTS",
                        "severity": "warning",
                        "title": "Unrecognized Event Names",
                        "description": f'{len(unknown_list)} unknown event types found (e.g. "{unknown_list[0]}")',
                        "fix_available": True,
                        "fix_action": 'Standardize event names (e.g. "Freestyle" -> "Free")',
                        "affected_count": unknown_mask.sum(),
                        "details": unknown_list,
                    }
                )

        return {
            "issues": issues,
            "fixable": any(i["fix_available"] for i in issues),
            "fix_count": sum(i["affected_count"] for i in issues if i["fix_available"]),
            "total_issues": len(issues),
        }

    def auto_fix_roster(self, df: pd.DataFrame) -> dict[str, any]:
        """
        Automatically fix common data issues.

        Returns:
            Dict with:
                - fixed_df: Cleaned DataFrame
                - fixes_applied: List of fixes that were applied
                - rows_removed: Count of rows removed
                - rows_before: Original row count
                - rows_after: Final row count
        """
        if df.empty:
            return {
                "fixed_df": df,
                "fixes_applied": [],
                "rows_removed": 0,
                "rows_before": 0,
                "rows_after": 0,
            }

        fixes_applied = []
        rows_before = len(df)
        fixed_df = df.copy()

        # Fix 1: Remove entries with empty swimmer names
        if "swimmer" in fixed_df.columns:
            empty_mask = fixed_df["swimmer"].isna() | (
                fixed_df["swimmer"].astype(str).str.strip() == ""
            )
            if empty_mask.any():
                count = empty_mask.sum()
                fixed_df = fixed_df[~empty_mask]
                fixes_applied.append(
                    {
                        "type": "REMOVED_EMPTY_NAMES",
                        "description": f"Removed {count} entries with empty swimmer names",
                        "count": count,
                    }
                )

        # Fix 2: Remove invalid times
        if "time" in fixed_df.columns:
            invalid_mask = (fixed_df["time"] <= 0) | (fixed_df["time"] > 600)
            if invalid_mask.any():
                count = invalid_mask.sum()
                fixed_df = fixed_df[~invalid_mask]
                fixes_applied.append(
                    {
                        "type": "REMOVED_INVALID_TIMES",
                        "description": f"Removed {count} entries with invalid times",
                        "count": count,
                    }
                )

        # Fix 3: Deduplicate (keep fastest time per swimmer-event)
        if (
            "swimmer" in fixed_df.columns
            and "event" in fixed_df.columns
            and "time" in fixed_df.columns
        ):
            before_dedup = len(fixed_df)
            # Sort by time ascending, then drop duplicates keeping first (fastest)
            fixed_df = fixed_df.sort_values("time", ascending=True)
            fixed_df = fixed_df.drop_duplicates(
                subset=["swimmer", "event"], keep="first"
            )
            duplicates_removed = before_dedup - len(fixed_df)
            if duplicates_removed > 0:
                fixes_applied.append(
                    {
                        "type": "DEDUPLICATED",
                        "description": f"Removed {duplicates_removed} duplicate entries (kept fastest times)",
                        "count": duplicates_removed,
                    }
                )

        if "team" in fixed_df.columns:
            # Normalize Seton variations
            seton_mask = fixed_df["team"].str.lower().str.contains("seton", na=False)
            if seton_mask.any():
                fixed_df.loc[seton_mask, "team"] = "Seton"
                fixes_applied.append(
                    {
                        "type": "NORMALIZED_TEAMS",
                        "description": 'Standardized "Seton" team name variations',
                        "count": seton_mask.sum(),
                    }
                )

        # Fix 5: Normalize Event Names (Data Mismatch Fix)
        if "event" in fixed_df.columns:
            replacements = {
                r"Freestyle": "Free",
                r"Breaststroke": "Breast",
                r"Backstroke": "Back",
                r"Butterfly": "Fly",
                r"Individual Medley": "IM",
                r"I.M.": "IM",
                r"Diving.*": "Diving",
                r" Yard": "",
                r" Meter": "",
            }
            original_events = fixed_df["event"].copy()
            for pattern, replace in replacements.items():
                fixed_df["event"] = fixed_df["event"].str.replace(
                    pattern, replace, regex=True
                )

            # Check changes
            changed_mask = original_events != fixed_df["event"]
            if changed_mask.any():
                fixes_applied.append(
                    {
                        "type": "NORMALIZED_EVENTS",
                        "description": f"Normalized {changed_mask.sum()} event names (e.g. Freestyle -> Free)",
                        "count": changed_mask.sum(),
                    }
                )

        # Fix 6: Clean Swimmer Names
        if "swimmer" in fixed_df.columns:
            original_names = fixed_df["swimmer"].copy()
            fixed_df["swimmer"] = fixed_df["swimmer"].str.strip().str.title()

            changed_mask = original_names != fixed_df["swimmer"]
            if changed_mask.any():
                fixes_applied.append(
                    {
                        "type": "CLEANED_NAMES",
                        "description": f"Cleaned {changed_mask.sum()} swimmer names (whitespace/formatting)",
                        "count": changed_mask.sum(),
                    }
                )

        rows_after = len(fixed_df)

        return {
            "fixed_df": fixed_df,
            "fixes_applied": fixes_applied,
            "rows_removed": rows_before - rows_after,
            "rows_before": rows_before,
            "rows_after": rows_after,
            "success": True,
        }


# Singleton instance
score_validation_service = ScoreValidationService()
