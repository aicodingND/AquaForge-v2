import hashlib
import json
import logging
import os
from io import StringIO

import pandas as pd

from swim_ai_reflex.backend.config import get_config

logger = logging.getLogger(__name__)

# Get configuration
config = get_config()

# Define cache directory
CACHE_DIR = os.path.join(os.getcwd(), ".cache", "datasets")
os.makedirs(CACHE_DIR, exist_ok=True)


class DataCache:
    """
    Manages caching of parsed datasets to prevent re-parsing and ensure persistence.
    """

    @staticmethod
    def get_file_hash(filepath: str) -> str:
        """
        Calculate MD5 hash of a file to uniquely identify its content.
        This allows detecting duplicate files even if filenames differ.
        """
        hash_md5 = hashlib.md5()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    @staticmethod
    def get_cache_path(file_hash: str) -> str:
        """Get the path where the cached dataset would be stored."""
        return os.path.join(CACHE_DIR, f"{file_hash}.json")

    @staticmethod
    def is_cached(file_hash: str) -> bool:
        """Check if a dataset with this hash is already cached."""
        return os.path.exists(DataCache.get_cache_path(file_hash))

    @staticmethod
    def save_to_cache(df: pd.DataFrame, file_hash: str, original_filename: str) -> bool:
        """
        Save a parsed DataFrame to the cache.
        Returns True if successful.
        """
        try:
            cache_path = DataCache.get_cache_path(file_hash)
            metadata = {
                "original_filename": original_filename,
                "parsed_at": pd.Timestamp.now().isoformat(),
                "row_count": len(df),
            }

            cache_obj = {"data": df.to_json(orient="split"), "metadata": metadata}

            with open(cache_path, "w") as f:
                json.dump(cache_obj, f)
            return True
        except Exception as e:
            logger.error(f"Failed to cache dataset: {e}")
            return False

    @staticmethod
    def load_from_cache(
        file_hash: str,
    ) -> tuple[pd.DataFrame | None, dict | None]:
        """
        Load a dataset from the cache if it exists.
        Returns (DataFrame, Metadata) or (None, None).
        """
        cache_path = DataCache.get_cache_path(file_hash)
        if not os.path.exists(cache_path):
            return None, None

        try:
            with open(cache_path) as f:
                cached_obj = json.load(f)

            # Handle potential legacy cache format if any (though this is new)
            if isinstance(cached_obj, dict) and "data" in cached_obj:
                df = pd.read_json(StringIO(cached_obj["data"]), orient="split")
                return df, cached_obj.get("metadata", {})

            logger.warning("Unexpected cache format, returning None")
            return None, None

        except Exception as e:
            logger.error(f"Failed to load cached dataset: {e}")
            return None, None

    @staticmethod
    def clear_cache():
        """Clear all cached datasets."""
        try:
            for f in os.listdir(CACHE_DIR):
                os.remove(os.path.join(CACHE_DIR, f))
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
