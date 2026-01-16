"""
Top-level CLI package for cleaner invocation.

This package provides a convenient entry point for the Example Reviewer Pipeline CLI.

Usage:
    python -m cli [command] [options]

Example:
    python -m cli run --family zip
    python -m cli discover --family pdf --max-files 10
    python -m cli status --family zip

For backward compatibility, the old invocation pattern still works:
    python -m src.cli.main [command] [options]
"""
from src.cli.main import main

__all__ = ['main']
