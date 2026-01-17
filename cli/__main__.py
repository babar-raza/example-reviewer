"""
Entry point for `python -m cli` invocation.

This delegates to src.cli.main for backward compatibility while
providing the user-facing contract documented in README.md.
"""

import sys
from src.cli.main import main

if __name__ == "__main__":
    sys.exit(main())
