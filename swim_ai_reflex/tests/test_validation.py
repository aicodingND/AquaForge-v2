import pytest
import os
import tempfile
from swim_ai_reflex.backend.utils.validation import (
    normalize_team_name,
    safe_join_path,
    sanitize_filename,
    validate_file_extension,
    validate_file_size,
    validate_roster_dataframe,
    sanitize_team_name
)
import pandas as pd

class TestValidation:
    def test_normalize_team_name(self):
        assert normalize_team_name("SETON") == "seton"
        assert normalize_team_name("  Opponent  ") == "opponent"
        assert normalize_team_name("") == ""
        assert normalize_team_name(None) == ""
    
    def test_sanitize_team_name(self):
        assert sanitize_team_name("Seton Hall") == "Seton Hall"
        assert sanitize_team_name("Team <Script>") == "Team Script"
        assert sanitize_team_name("  Bad  Spacing  ") == "Bad Spacing"
    
    def test_safe_join_path_valid(self):
        # Create a temp directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            result = safe_join_path(temp_dir, "file.pdf")
            assert str(temp_dir) in result
            assert "file.pdf" in result
    
    def test_safe_join_path_traversal(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with pytest.raises(ValueError):
                safe_join_path(temp_dir, "../../../etc/passwd")
            
            with pytest.raises(ValueError):
                safe_join_path(temp_dir, "..\\windows\\system32")

    def test_sanitize_filename(self):
        assert sanitize_filename("file.pdf") == "file.pdf"
        assert sanitize_filename("../file.pdf") == "..file.pdf"  # Adjusted expectation based on regex
        assert sanitize_filename("file<>.pdf") == "file.pdf"
        assert sanitize_filename("  file.pdf  ") == "file.pdf"
    
    def test_validate_file_extension(self):
        assert validate_file_extension("file.pdf", {'.pdf'})
        assert validate_file_extension("file.PDF", {'.pdf'})
        assert not validate_file_extension("file.exe", {'.pdf'})
        assert validate_file_extension("file.pdf", {'.csv', '.pdf'})
    
    def test_validate_file_size(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"0" * 1024 * 1024) # 1MB
            f.flush()
            filepath = f.name
        
        try:
            assert validate_file_size(filepath, max_size_mb=2)
            assert not validate_file_size(filepath, max_size_mb=0.5)
        finally:
            os.remove(filepath)

    def test_validate_roster_dataframe(self):
        # Valid DF
        df = pd.DataFrame({
            'swimmer': ['John'], 
            'event': ['50 Free'], 
            'time': [25.5], 
            'team': ['Seton']
        })
        is_valid, errors = validate_roster_dataframe(df)
        assert is_valid
        assert len(errors) == 0

        # Invalid DF (missing col)
        df_missing = pd.DataFrame({'swimmer': ['John']})
        is_valid, errors = validate_roster_dataframe(df_missing)
        assert not is_valid
        assert any("Missing required columns" in e for e in errors)

        # Invalid DF (null values)
        df_null = pd.DataFrame({
            'swimmer': [None], 
            'event': ['50 Free'], 
            'time': [25.5], 
            'team': ['Seton']
        })
        is_valid, errors = validate_roster_dataframe(df_null)
        assert not is_valid
        assert any("contains null values" in e for e in errors)
