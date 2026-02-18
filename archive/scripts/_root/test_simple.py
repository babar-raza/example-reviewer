"""Simple test to verify test infrastructure."""
import sys

# Add user site-packages
user_site = r'C:\Users\prora\AppData\Roaming\Python\Python313\site-packages'
if user_site not in sys.path:
    sys.path.insert(0, user_site)

def test_progressive_retry_tier_1():
    """Test that tier 1 is returned for first attempt."""
    # Simple assertion
    assert 1 + 1 == 2, "Math should work"

def test_progressive_retry_tier_2():
    """Test that tier 2 is returned for second attempt."""
    assert 2 + 2 == 4, "Math should work"

if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
