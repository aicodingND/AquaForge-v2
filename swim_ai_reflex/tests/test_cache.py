import os

import pandas as pd

from swim_ai_reflex.backend.utils.cache import CACHE_DIR, DataCache


class TestDataCache:
    def setup_method(self):
        # Clear cache before each test
        DataCache.clear_cache()

    def test_get_file_hash(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello world", encoding="utf-8")

        h1 = DataCache.get_file_hash(str(f))

        f2 = tmp_path / "test2.txt"
        f2.write_text("hello world", encoding="utf-8")
        h2 = DataCache.get_file_hash(str(f2))

        assert h1 == h2
        assert len(h1) == 32  # MD5 length

    def test_save_and_load_cache(self, tmp_path):
        df = pd.DataFrame({"col1": [1, 2], "col2": ["a", "b"]})
        file_hash = "test_hash_123"
        filename = "test_file.csv"

        # Save
        success = DataCache.save_to_cache(df, file_hash, filename)
        assert success
        assert DataCache.is_cached(file_hash)

        # Load
        loaded_df, metadata = DataCache.load_from_cache(file_hash)
        assert loaded_df is not None
        assert loaded_df.equals(df)
        assert metadata["original_filename"] == filename

    def test_cache_miss(self):
        loaded_df, _ = DataCache.load_from_cache("non_existent_hash")
        assert loaded_df is None

    def test_clear_cache(self):
        df = pd.DataFrame({"a": [1]})
        DataCache.save_to_cache(df, "h1", "f1")
        assert len(os.listdir(CACHE_DIR)) > 0

        DataCache.clear_cache()
        assert len(os.listdir(CACHE_DIR)) == 0
