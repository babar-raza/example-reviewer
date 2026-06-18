# src/cli/ - Command-Line Interface

Pipeline CLI built with `argparse`. Run via `python -m src.cli.main`.

## Commands

- `run` - Execute the full VFV pipeline for a family
- `discover` - Discover code examples from markdown content
- `compile` - Compile discovered examples
- `verify` - Run compiled examples and verify output
- `status` - Show pipeline status for a family/run
- `list-families` - List configured families
- `commit` - Commit verified changes to markdown files

## Files

- `main.py` - CLI argument parsing and command dispatch
- `__init__.py` - Package marker
