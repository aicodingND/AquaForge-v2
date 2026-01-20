"""
Data Loaders Package

Priority loading order for coach workflow:
    1. MDB (HyTek database backup) - most frictionless
    2. HY3/CL2 (SDIF files) - meet results/entries
    3. CSV (fallback) - already exported

Future Extensions:
    - Direct HyTek API if ever released
    - SwimCloud integration
    - USA Swimming SWIMS database sync
"""

from swim_ai_reflex.core.data.loaders.csv_loader import CSVLoader

__all__ = ["CSVLoader"]
