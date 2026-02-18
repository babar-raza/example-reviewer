"""Run Track 2 unit tests (skip slow timeout tests)."""
import sys

# Add user site-packages
user_site = r'C:\Users\prora\AppData\Roaming\Python\Python313\site-packages'
if user_site not in sys.path:
    sys.path.insert(0, user_site)

if __name__ == "__main__":
    import pytest

    args = [
        "tests/test_track2_progressive_retry.py",
        "tests/test_track2_validation_routing.py",
        "tests/test_track2_timeout_manager.py::TestTimeoutManagerCrossPlatform",
        "tests/test_track2_timeout_manager.py::TestTimeoutManagerTelemetry",
        "tests/test_track2_timeout_manager.py::TestTimeoutManagerResourceCleanup",
        "tests/test_track2_timeout_manager.py::TestTimeoutManagerEdgeCases",
        "-v",
        "--tb=short",
    ]

    exit_code = pytest.main(args)
    print(f"\n{'='*70}")
    print(f"Track 2 Unit Tests (Fast) Exit Code: {exit_code}")
    print(f"{'='*70}\n")
    sys.exit(exit_code)
