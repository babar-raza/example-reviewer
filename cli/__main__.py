"""
Entry point for python -m cli

This module delegates to src.cli.main.main() to provide a cleaner
invocation pattern for the Example Reviewer Pipeline CLI.

Usage:
    python -m cli [command] [options]
"""
from src.cli.main import main

if __name__ == '__main__':
    main()
