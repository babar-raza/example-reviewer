#!/usr/bin/env python
"""Wrapper to run CLI with proper Python path for user-installed packages."""
import sys
from pathlib import Path

# Add user site-packages to path
user_site = Path.home() / "AppData" / "Roaming" / "Python" / f"Python{sys.version_info.major}{sys.version_info.minor}" / "site-packages"
sys.path.insert(0, str(user_site))

# Add src to path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

# Import and run CLI
from cli import main

if __name__ == "__main__":
    main()
