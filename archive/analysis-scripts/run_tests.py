#!/usr/bin/env python
"""Test runner with proper Python path for user-installed packages."""
import sys
from pathlib import Path

# Add user site-packages to path
user_site = Path.home() / "AppData" / "Roaming" / "Python" / f"Python{sys.version_info.major}{sys.version_info.minor}" / "site-packages"
sys.path.insert(0, str(user_site))

# Add src and tests to path
src_dir = Path(__file__).parent / "src"
tests_dir = Path(__file__).parent / "tests"
sys.path.insert(0, str(src_dir))
sys.path.insert(0, str(tests_dir))

# Run pytest
if __name__ == "__main__":
    try:
        import pytest
        sys.exit(pytest.main(sys.argv[1:]))
    except ImportError:
        print("ERROR: pytest not installed")
        print("Install with: pip install --user pytest")
        sys.exit(1)
