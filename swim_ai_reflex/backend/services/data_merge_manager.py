"""
Data Merge Manager for AquaForge

Permanent data management with:
- Auto-merge from multiple sources (scraped, local, HDD)
- Freshness tracking with auto-refresh triggers
- Parquet cache for fast loading
- On-demand scraping for missing data

Usage:
    from swim_ai_reflex.backend.services.data_merge_manager import DataMergeManager

    manager = DataMergeManager()
    manager.refresh_all()  # Merge all sources
    manager.get_team("TCS")  # Get with auto-refresh if stale
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURATION
# ============================================================================


@dataclass
class DataSourceConfig:
    """Configuration for a data source."""

    name: str
    path: Path
    priority: int = 10  # Lower = higher priority
    max_age_days: int = 7  # Days before considered stale
    auto_refresh: bool = True
    file_pattern: str = "*.json"


@dataclass
class FreshnessRecord:
    """Track data freshness for a team."""

    team_code: str
    last_updated: datetime
    source: str
    entry_count: int
    is_stale: bool = False


# ============================================================================
# DATA MERGE MANAGER
# ============================================================================


class DataMergeManager:
    """
    Manages permanent merging and caching of swim data.

    Priorities (lower = higher priority):
    1. Championship psych sheet (most curated)
    2. SwimCloud scraped (current season)
    3. Local team data
    4. External HDD archives
    """

    # Base paths
    PROJECT_ROOT = Path(
        "/Users/mpage1/Desktop/AquaForge/AquaForge_v1.0.0-next_2026-01-10"
    )
    DATA_DIR = PROJECT_ROOT / "data"
    CACHE_DIR = DATA_DIR / ".cache"

    # Source configurations
    SOURCES = [
        DataSourceConfig(
            name="championship",
            path=DATA_DIR / "championship_data",
            priority=1,
            max_age_days=30,
        ),
        DataSourceConfig(
            name="vcac",
            path=DATA_DIR / "vcac",
            priority=2,
            max_age_days=14,
        ),
        DataSourceConfig(
            name="scraped",
            path=DATA_DIR / "scraped",
            priority=3,
            max_age_days=7,
        ),
        DataSourceConfig(
            name="swimcloud",
            path=DATA_DIR / "swimcloud",
            priority=4,
            max_age_days=7,
        ),
        DataSourceConfig(
            name="external_hdd",
            path=Path("/Volumes/Miguel/swimdatadump"),
            priority=10,
            max_age_days=365,
            auto_refresh=False,
        ),
    ]

    def __init__(self):
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self._freshness: dict[str, FreshnessRecord] = {}
        self._merged_data: pd.DataFrame | None = None
        self._load_freshness()

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def refresh_all(self, force: bool = False) -> pd.DataFrame:
        """
        Merge all data sources into unified dataset.

        Args:
            force: Force refresh even if cache is fresh

        Returns:
            Merged DataFrame with all entries
        """
        cache_path = self.CACHE_DIR / "merged_data.parquet"

        # Check cache freshness
        if not force and cache_path.exists():
            cache_age = datetime.now() - datetime.fromtimestamp(
                cache_path.stat().st_mtime
            )
            if cache_age < timedelta(hours=6):
                logger.info(
                    f"Loading from cache ({cache_age.total_seconds() // 60:.0f}m old)"
                )
                self._merged_data = pd.read_parquet(cache_path)
                return self._merged_data

        logger.info("Refreshing all data sources...")
        all_entries = []

        for source in sorted(self.SOURCES, key=lambda s: s.priority):
            if not source.path.exists():
                logger.debug(f"Skipping {source.name}: path not found")
                continue

            entries = self._load_source(source)
            if entries:
                for e in entries:
                    e["_source"] = source.name
                    e["_priority"] = source.priority
                all_entries.extend(entries)
                logger.info(f"  Loaded {len(entries)} entries from {source.name}")

        if not all_entries:
            logger.warning("No data loaded from any source!")
            return pd.DataFrame()

        # Create DataFrame and deduplicate
        df = pd.DataFrame(all_entries)
        df = self._deduplicate(df)

        # Save to parquet cache
        df.to_parquet(cache_path, index=False)
        self._merged_data = df

        # Update freshness records
        self._update_freshness(df)

        logger.info(f"Merged {len(df)} unique entries from {len(self.SOURCES)} sources")
        return df

    def get_team(self, team_code: str, auto_refresh: bool = True) -> pd.DataFrame:
        """
        Get data for a specific team.

        Args:
            team_code: Team code (e.g., "SST", "TCS")
            auto_refresh: Trigger refresh if data is stale

        Returns:
            DataFrame with team entries
        """
        # Check freshness
        if auto_refresh and self._is_stale(team_code):
            self.refresh_all()

        if self._merged_data is None:
            self.refresh_all()

        return (
            self._merged_data[self._merged_data["team"] == team_code].copy()
            if self._merged_data is not None
            else pd.DataFrame()
        )

    def get_all_teams(self) -> list[str]:
        """Get list of all available team codes."""
        if self._merged_data is None:
            self.refresh_all()

        if self._merged_data is None or self._merged_data.empty:
            return []

        return sorted(self._merged_data["team"].unique().tolist())

    def get_freshness_report(self) -> dict[str, FreshnessRecord]:
        """Get freshness status for all teams."""
        return self._freshness.copy()

    def mark_needs_refresh(self, team_code: str) -> None:
        """Mark a team as needing data refresh."""
        if team_code in self._freshness:
            self._freshness[team_code].is_stale = True
            self._save_freshness()

    def export_to_parquet(self, output_path: Path) -> None:
        """Export merged data to parquet file."""
        if self._merged_data is None:
            self.refresh_all()

        if self._merged_data is not None:
            self._merged_data.to_parquet(output_path, index=False)
            logger.info(f"Exported {len(self._merged_data)} entries to {output_path}")

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about merged data."""
        if self._merged_data is None:
            self.refresh_all()

        if self._merged_data is None or self._merged_data.empty:
            return {"total_entries": 0, "teams": 0, "events": 0}

        return {
            "total_entries": len(self._merged_data),
            "teams": self._merged_data["team"].nunique(),
            "events": self._merged_data["event"].nunique()
            if "event" in self._merged_data
            else 0,
            "swimmers": self._merged_data["swimmer"].nunique()
            if "swimmer" in self._merged_data
            else 0,
            "sources": self._merged_data["_source"].unique().tolist()
            if "_source" in self._merged_data
            else [],
        }

    # -------------------------------------------------------------------------
    # Private methods
    # -------------------------------------------------------------------------

    def _load_source(self, source: DataSourceConfig) -> list[dict]:
        """Load entries from a data source."""
        entries = []

        try:
            for f in source.path.glob(source.file_pattern):
                try:
                    with open(f) as fp:
                        data = json.load(fp)

                    # Handle different formats
                    if isinstance(data, list):
                        entries.extend(data)
                    elif isinstance(data, dict):
                        if "entries" in data:
                            entries.extend(data["entries"])
                        elif "times" in data:
                            # SwimCloud format
                            for t in data["times"]:
                                t["team"] = data.get("team_code", "")
                                entries.append(t)
                        else:
                            entries.append(data)

                except Exception as e:
                    logger.debug(f"Error reading {f}: {e}")

        except Exception as e:
            logger.debug(f"Error loading source {source.name}: {e}")

        return entries

    def _deduplicate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove duplicate entries, keeping highest priority source."""
        if df.empty:
            return df

        # Define key columns for deduplication
        key_cols = ["swimmer", "event", "team"]
        key_cols = [c for c in key_cols if c in df.columns]

        if not key_cols:
            return df

        # Sort by priority (lower = keep) then drop duplicates
        if "_priority" in df.columns:
            df = df.sort_values("_priority", ascending=True)

        df = df.drop_duplicates(subset=key_cols, keep="first")
        return df.reset_index(drop=True)

    def _is_stale(self, team_code: str) -> bool:
        """Check if team data is stale."""
        if team_code not in self._freshness:
            return True

        record = self._freshness[team_code]
        if record.is_stale:
            return True

        age = datetime.now() - record.last_updated
        return age > timedelta(days=7)

    def _update_freshness(self, df: pd.DataFrame) -> None:
        """Update freshness records from DataFrame."""
        if "team" not in df.columns:
            return

        for team in df["team"].unique():
            if pd.isna(team) or team == "":
                continue  # Skip empty/null team values

            team_data = df[df["team"] == team]
            if team_data.empty:
                continue  # Skip if no data after filter

            source = "merged"
            if "_source" in team_data.columns and len(team_data) > 0:
                source = team_data["_source"].iloc[0]

            self._freshness[str(team)] = FreshnessRecord(
                team_code=str(team),
                last_updated=datetime.now(),
                source=source,
                entry_count=len(team_data),
                is_stale=False,
            )

        self._save_freshness()

    def _load_freshness(self) -> None:
        """Load freshness records from disk."""
        path = self.CACHE_DIR / "freshness.json"
        if path.exists():
            try:
                with open(path) as f:
                    data = json.load(f)
                for team, record in data.items():
                    self._freshness[team] = FreshnessRecord(
                        team_code=team,
                        last_updated=datetime.fromisoformat(record["last_updated"]),
                        source=record["source"],
                        entry_count=record["entry_count"],
                        is_stale=record.get("is_stale", False),
                    )
            except Exception as e:
                logger.debug(f"Could not load freshness: {e}")

    def _save_freshness(self) -> None:
        """Save freshness records to disk."""
        path = self.CACHE_DIR / "freshness.json"
        data = {
            team: {
                "last_updated": record.last_updated.isoformat(),
                "source": record.source,
                "entry_count": record.entry_count,
                "is_stale": record.is_stale,
            }
            for team, record in self._freshness.items()
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)


# ============================================================================
# SINGLETON
# ============================================================================


_manager: DataMergeManager | None = None


def get_merge_manager() -> DataMergeManager:
    """Get singleton merge manager instance."""
    global _manager
    if _manager is None:
        _manager = DataMergeManager()
    return _manager


# ============================================================================
# CLI
# ============================================================================


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Data Merge Manager")
    parser.add_argument(
        "--refresh", action="store_true", help="Force refresh all sources"
    )
    parser.add_argument("--stats", action="store_true", help="Show statistics")
    parser.add_argument("--export", type=str, help="Export to parquet file")
    parser.add_argument("--team", type=str, help="Get data for specific team")
    args = parser.parse_args()

    manager = get_merge_manager()

    if args.refresh:
        df = manager.refresh_all(force=True)
        print(f"Refreshed {len(df)} entries")

    if args.stats:
        stats = manager.get_stats()
        print("\n=== Data Merge Statistics ===")
        for key, value in stats.items():
            print(f"  {key}: {value}")

    if args.export:
        manager.export_to_parquet(Path(args.export))

    if args.team:
        df = manager.get_team(args.team)
        print(f"\n{args.team}: {len(df)} entries")
        if not df.empty and "event" in df.columns:
            print(f"  Events: {df['event'].nunique()}")
            print(
                f"  Swimmers: {df['swimmer'].nunique() if 'swimmer' in df.columns else 'N/A'}"
            )

    if not any([args.refresh, args.stats, args.export, args.team]):
        # Default: show stats
        manager.refresh_all()
        stats = manager.get_stats()
        print("\n=== Data Merge Manager ===")
        print(f"Teams: {manager.get_all_teams()}")
        print(f"Total entries: {stats['total_entries']}")
        print(f"Sources: {stats['sources']}")
