#!/usr/bin/env python3
"""CLI tool for validating family KB files.

Usage:
    # Validate all families found in the default config dir:
    python scripts/validate_kb.py --all

    # Validate a specific family:
    python scripts/validate_kb.py --family words

    # Use a custom config directory:
    python scripts/validate_kb.py --all --config-dir path/to/config/families

Exit codes:
    0  All validated files are valid (or no KB files found)
    1  One or more KB files failed validation
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def _find_kb_families(config_dir: Path) -> list[str]:
    """Return sorted list of family names that have at least one KB file."""
    families: set[str] = set()
    for path in config_dir.glob("*_review_hints.json"):
        name = path.stem.removesuffix("_review_hints")
        families.add(name)
    for path in config_dir.glob("*_behavioral_patterns.json"):
        name = path.stem.removesuffix("_behavioral_patterns")
        families.add(name)
    return sorted(families)


def _validate_family(family: str, config_dir: Path) -> list[str]:
    """Validate both KB file types for *family*.

    Returns a list of error strings (empty == all OK).
    """
    # Import here so the script can be run from repo root without installation.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from src.services.kb import KBLoadError, KnowledgeBaseLoader  # noqa: PLC0415

    errors: list[str] = []

    hints_path = config_dir / f"{family}_review_hints.json"
    if hints_path.exists():
        try:
            hints = KnowledgeBaseLoader.load_review_hints(family, config_dir=config_dir)
            print(f"  [OK] {hints_path.name}  ({len(hints)} hints)")
        except KBLoadError as exc:
            errors.append(f"  [FAIL] {hints_path.name}: {exc}")

    patterns_path = config_dir / f"{family}_behavioral_patterns.json"
    if patterns_path.exists():
        try:
            patterns = KnowledgeBaseLoader.load_behavioral_patterns(family, config_dir=config_dir)
            blocking = sum(1 for p in patterns if p.severity in {"error", "critical"})
            print(
                f"  [OK] {patterns_path.name}  "
                f"({len(patterns)} patterns, {blocking} blocking)"
            )
        except KBLoadError as exc:
            errors.append(f"  [FAIL] {patterns_path.name}: {exc}")

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate family KB files (review hints + behavioral patterns)."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--all",
        action="store_true",
        help="Validate all families that have KB files in config-dir.",
    )
    group.add_argument(
        "--family",
        metavar="FAMILY",
        help="Validate a single family (e.g. 'words').",
    )
    parser.add_argument(
        "--config-dir",
        default="config/families",
        metavar="DIR",
        help="Directory containing family KB files (default: config/families).",
    )
    args = parser.parse_args(argv)

    config_dir = Path(args.config_dir)
    if not config_dir.is_dir():
        print(f"ERROR: config-dir '{config_dir}' does not exist or is not a directory.", file=sys.stderr)
        return 1

    families: list[str]
    if args.all:
        families = _find_kb_families(config_dir)
        if not families:
            print(f"No KB files found in '{config_dir}'. Nothing to validate.")
            return 0
    else:
        families = [args.family]

    all_errors: list[str] = []
    for family in families:
        print(f"Family: {family}")
        errors = _validate_family(family, config_dir)
        all_errors.extend(errors)
        for err in errors:
            print(err, file=sys.stderr)

    if all_errors:
        print(
            f"\nValidation FAILED: {len(all_errors)} error(s) found.",
            file=sys.stderr,
        )
        return 1

    print(f"\nAll KB files valid ({len(families)} family/families checked).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
