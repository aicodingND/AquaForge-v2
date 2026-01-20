import os
import hashlib
import pickle
import pandas as pd
from typing import Optional, Tuple
from swim_ai_reflex.backend.config import get_config

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
        return os.path.join(CACHE_DIR, f"{file_hash}.pkl")

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
                "parsed_at": pd.Timestamp.now(),
                "row_count": len(df)
            }
            
            with open(cache_path, "wb") as f:
                pickle.dump({"data": df, "metadata": metadata}, f)
            return True
        except Exception as e:
            print(f"Failed to cache dataset: {e}")
            return False

    @staticmethod
    def load_from_cache(file_hash: str) -> Tuple[Optional[pd.DataFrame], Optional[dict]]:
        """
        Load a dataset from the cache if it exists.
        Returns (DataFrame, Metadata) or (None, None).
        """
        cache_path = DataCache.get_cache_path(file_hash)
        if not os.path.exists(cache_path):
            return None, None
            
        try:
            with open(cache_path, "rb") as f:
                cached_obj = pickle.load(f)
            
            # Handle potential legacy cache format if any (though this is new)
            if isinstance(cached_obj, dict) and "data" in cached_obj:
                return cached_obj["data"], cached_obj.get("metadata", {})
            return cached_obj, {} # Assume raw dataframe if not dict
            
        except Exception as e:
            print(f"Failed to load cached dataset: {e}")
            return None, None

    @staticmethod
    def clear_cache():
        """Clear all cached datasets."""
        try:
            for f in os.listdir(CACHE_DIR):
                os.remove(os.path.join(CACHE_DIR, f))
        except Exception as e:
            print(f"Error clearing cache: {e}")
