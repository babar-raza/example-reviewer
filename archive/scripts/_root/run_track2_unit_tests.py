"""Run Track 2 unit tests (progressive retry, timeout, validation)."""
import sys
import os

# Add user site-packages
user_site = r'C:\Users\prora\AppData\Roaming\Python\Python313\site-packages'
if user_site not in sys.path:
    sys.path.insert(0, user_site)

if __name__ == "__main__":
    import pytest

    args = [
        "tests/test_track2_progressive_retry.py",
        "tests/test_track2_timeout_manager.py",
        "tests/test_track2_validation_routing.py",
        "-v",
        "--tb=short",
        "-x",  # Stop on first failure
    ]

    exit_code = pytest.main(args)
    print(f"\n{'='*70}")
    print(f"Track 2 Unit Tests Exit Code: {exit_code}")
    print(f"{'='*70}\n")
    sys.exit(exit_code)
