"""
Data Scanner - Discovers importable files from directory trees.

Handles the E:\\swimdatadump directory structure:
  Seton School/Seton Swim Coach/
    Season 'XX-'YY/
      N. Meet Name-MonDD,YY/
        Results/*.mdb, *.pdf
    Meet Results/  (older archives)
"""

import hashlib
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

SUPPORTED_EXTENSIONS = {".mdb", ".csv", ".xlsx", ".xls", ".pdf"}

# Skip Hy-Tek system databases (not meet data)
SYSTEM_DB_PATTERNS = {
    "tm5sys",
    "tm6sys",
    "tm7sys",
    "tm8sys",
    "swmm4-sys",
    "swmm7-sys",
    "swmm8-sys",
    "clmm3sys",
    "clmm4sys",
    "report",
    "translation",
    "template",
}


@dataclass
class DiscoveredFile:
    """A file discovered by the scanner with metadata extracted from its path."""

    path: str
    extension: str
    size_bytes: int
    season: str | None = None  # "2025-2026"
    meet_name: str | None = None
    meet_date_str: str | None = None  # "Jan10,26"
    meet_number: int | None = None  # 7 (from "7. Meet Name")
    checksum: str | None = None
    is_system_db: bool = False


@dataclass
class ScanResult:
    """Results of a directory scan."""

    files: list[DiscoveredFile] = field(default_factory=list)
    total_scanned: int = 0
    skipped_system: int = 0
    skipped_unsupported: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def by_season(self) -> dict[str, list[DiscoveredFile]]:
        """Group files by season."""
        grouped: dict[str, list[DiscoveredFile]] = {}
        for f in self.files:
            key = f.season or "unknown"
            grouped.setdefault(key, []).append(f)
        return grouped

    @property
    def by_extension(self) -> dict[str, int]:
        """Count files by extension."""
        counts: dict[str, int] = {}
        for f in self.files:
            counts[f.extension] = counts.get(f.extension, 0) + 1
        return counts


def file_checksum(path: str) -> str:
    """Compute MD5 checksum of a file (for idempotent imports)."""
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def classify_season(path_str: str) -> str | None:
    """
    Extract season from path like "Season '25-'26" -> "2025-2026".
    Also handles "Season '09-'10-Done" and similar.
    """
    m = re.search(r"Season\s+'(\d{2})-'(\d{2})", path_str, re.IGNORECASE)
    if not m:
        return None
    start_yy = int(m.group(1))
    end_yy = int(m.group(2))
    # Convert 2-digit year to 4-digit: 25 -> 2025, 99 -> 1999
    start_yyyy = 2000 + start_yy if start_yy < 50 else 1900 + start_yy
    end_yyyy = 2000 + end_yy if end_yy < 50 else 1900 + end_yy
    return f"{start_yyyy}-{end_yyyy}"


def classify_meet(path_str: str) -> tuple[str | None, str | None, int | None]:
    """
    Extract meet info from folder names like:
      '7. 16th Annual NoVa Catholics-Jan10,26'
      '1. Time Trials-Nov14,25'

    Returns: (meet_name, date_str, meet_number)
    """
    # Pattern: "N. Meet Name-MonDD,YY" or "N. Meet Name-MonDD"
    m = re.search(
        r"(\d+)\.\s+(.+?)-((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\d+(?:,\d{2})?)",
        path_str,
        re.IGNORECASE,
    )
    if m:
        return m.group(2).strip(), m.group(3), int(m.group(1))

    # Simpler pattern without number: "Meet Name-MonDD,YY"
    m = re.search(
        r"([^/\\]+?)-((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\d+,\d{2})",
        path_str,
        re.IGNORECASE,
    )
    if m:
        return m.group(1).strip(), m.group(2), None

    return None, None, None


def is_system_database(filename: str) -> bool:
    """Check if an .mdb file is a Hy-Tek system database (not meet data)."""
    lower = filename.lower().replace(".mdb", "")
    for pattern in SYSTEM_DB_PATTERNS:
        if pattern in lower:
            return True
    return False


def scan_directory(
    root_path: str,
    compute_checksums: bool = False,
    extensions: set[str] | None = None,
) -> ScanResult:
    """
    Recursively scan a directory for importable swim data files.

    Args:
        root_path: Directory to scan
        compute_checksums: Whether to compute file checksums (slower but needed for idempotency)
        extensions: File extensions to include (default: SUPPORTED_EXTENSIONS)

    Returns:
        ScanResult with discovered files and statistics
    """
    result = ScanResult()
    target_extensions = extensions or SUPPORTED_EXTENSIONS

    root = Path(root_path)
    if not root.exists():
        result.errors.append(f"Directory not found: {root_path}")
        return result

    for dirpath, _dirnames, filenames in os.walk(root):
        for filename in filenames:
            result.total_scanned += 1
            filepath = os.path.join(dirpath, filename)
            ext = os.path.splitext(filename)[1].lower()

            if ext not in target_extensions:
                result.skipped_unsupported += 1
                continue

            if ext == ".mdb" and is_system_database(filename):
                result.skipped_system += 1
                continue

            try:
                size = os.path.getsize(filepath)
            except OSError:
                result.errors.append(f"Cannot access: {filepath}")
                continue

            # Extract metadata from path
            season = classify_season(filepath)
            meet_name, meet_date_str, meet_number = classify_meet(filepath)

            checksum = None
            if compute_checksums:
                try:
                    checksum = file_checksum(filepath)
                except OSError as e:
                    result.errors.append(f"Checksum failed for {filepath}: {e}")

            df = DiscoveredFile(
                path=filepath,
                extension=ext,
                size_bytes=size,
                season=season,
                meet_name=meet_name,
                meet_date_str=meet_date_str,
                meet_number=meet_number,
                checksum=checksum,
                is_system_db=(ext == ".mdb" and is_system_database(filename)),
            )
            result.files.append(df)

    # Sort: current season first, then by meet number
    result.files.sort(key=lambda f: (f.season or "0000", f.meet_number or 999, f.path))
    return result
