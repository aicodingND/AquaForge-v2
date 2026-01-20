"""
Quick validation test for newly added team name normalization utilities.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from swim_ai_reflex.backend.utils.helpers import normalize_team_name, sanitize_team_name


def test_normalize_team_name():
    """Test team name normalization."""
    assert normalize_team_name("  SETON  ") == "seton"
    assert normalize_team_name("Trinity Christian") == "trinity christian"
    assert normalize_team_name("OPPONENT") == "opponent"
    assert normalize_team_name("") == ""
    assert normalize_team_name(None) == ""
    print("✅ normalize_team_name tests passed!")


def test_sanitize_team_name():
    """Test team name sanitization."""
    # XSS prevention
    result = sanitize_team_name("Seton<script>alert('XSS')</script>")
    assert "<" not in result
    assert ">" not in result
    
    # Valid characters preserved
    assert sanitize_team_name("Trinity-Christian ABC 123") == "Trinity-Christian ABC 123"
    
    # Length limiting
    long_name = "A" * 100
    result = sanitize_team_name(long_name)
    assert len(result) <= 50
    
    # Empty/None handling
    assert sanitize_team_name("") == ""
    assert sanitize_team_name(None) == ""
    
    print("✅ sanitize_team_name tests passed!")


if __name__ == "__main__":
    test_normalize_team_name()
    test_sanitize_team_name()
    print("\n✅ All team name utility tests passed!")
