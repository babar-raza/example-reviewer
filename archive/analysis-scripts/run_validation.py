#!/usr/bin/env python3
"""Wrapper script to run validation with proper Python path."""
import sys
import site

# Enable user site packages
site.ENABLE_USER_SITE = True
sys.path.insert(0, site.getusersitepackages())

# Now import and run the CLI
from src.cli import main

if __name__ == "__main__":
    main()
