"""Wrapper to run Track 2 tests with proper Python path."""
import sys
import os

# Add user site-packages to path
user_site = r'C:\Users\prora\AppData\Roaming\Python\Python313\site-packages'
if user_site not in sys.path:
    sys.path.insert(0, user_site)

# Now import and run pytest
import pytest

if __name__ == "__main__":
    # Run Track 2 tests
    args = [
        "tests/test_track2_progressive_retry.py",
        "tests/test_track2_timeout_manager.py",
        "tests/test_track2_validation_routing.py",
        "-v",
        "--tb=short",
    ]

    sys.exit(pytest.main(args))
