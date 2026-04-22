#!/usr/bin/env python3
"""
Detect risky file changes on the current branch that lack accompanying test changes.

Runs ``git diff --name-only origin/main...HEAD`` and checks each changed file
against the risky-category path list defined in CONTRIBUTING.md.

If risky files are changed without any test file changes in the same diff,
emits a warning.

Modes:
  --warn-only  (default) Emit warnings and exit 0 (non-blocking CI)
  --strict     Emit warnings and exit 1 if any risky-without-test found

Usage:
    python scripts/validation/check_risky_diff.py
    python scripts/validation/check_risky_diff.py --warn-only
    python scripts/validation/check_risky_diff.py --strict
    python scripts/validation/check_risky_diff.py --base-branch develop
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]

# Paths that are intrinsically high-risk: changes here can silently affect
# pipeline accuracy, safety, or fallback behaviour.
_RISKY_PATTERNS: list[tuple[str, str]] = [
    # (path prefix or substring, human category label)
    ("src/pipeline/orchestrator.py",            "Pipeline phase logic"),
    ("src/core/path_guard.py",                  "Safety gate"),
    ("src/core/provenance_guard.py",             "Safety gate"),
    ("src/services/llm_service.py",             "LLM routing/fallback"),
    ("src/services/circuit_breaker.py",         "LLM routing/fallback"),
    ("src/services/ollama_manager.py",           "LLM routing/fallback"),
    ("src/core/config.py",                      "Config schema"),
    ("config/global.json",                      "Config schema"),
    ("config/families",                         "Family configuration"),
]

_TEST_INDICATORS = ("tests/", "test_")


def _get_changed_files(base_branch: str) -> list[str]:
    """Return list of changed files vs. base_branch using git diff."""
    try:
        result = subprocess.check_output(
            ["git", "diff", "--name-only", f"origin/{base_branch}...HEAD"],
            cwd=str(_REPO_ROOT),
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return [f.strip() for f in result.splitlines() if f.strip()]
    except subprocess.CalledProcessError:
        # Fallback: compare against local main
        try:
            result = subprocess.check_output(
                ["git", "diff", "--name-only", f"{base_branch}...HEAD"],
                cwd=str(_REPO_ROOT),
                stderr=subprocess.DEVNULL,
                text=True,
            )
            return [f.strip() for f in result.splitlines() if f.strip()]
        except subprocess.CalledProcessError:
            return []


def _classify_risky(files: list[str]) -> list[tuple[str, str]]:
    """Return list of (file, category) for risky files."""
    risky = []
    for f in files:
        for pattern, category in _RISKY_PATTERNS:
            if pattern in f:
                risky.append((f, category))
                break
    return risky


def _has_test_changes(files: list[str]) -> bool:
    """Return True if any changed file is a test file."""
    return any(
        any(indicator in f for indicator in _TEST_INDICATORS)
        for f in files
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Warn when risky files are changed without test file changes."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--warn-only", action="store_true", default=True,
        help="Emit warnings and exit 0 (default, non-blocking CI)"
    )
    mode.add_argument(
        "--strict", action="store_true",
        help="Emit warnings and exit 1 if risky-without-test found"
    )
    parser.add_argument(
        "--base-branch", default="main",
        help="Base branch to diff against (default: main)"
    )
    args = parser.parse_args()
    strict = args.strict

    changed = _get_changed_files(args.base_branch)
    if not changed:
        print("check_risky_diff: no changed files detected (or git not available). SKIP.")
        return 0

    risky = _classify_risky(changed)
    has_tests = _has_test_changes(changed)

    if not risky:
        print(f"check_risky_diff: {len(changed)} changed file(s), none in risky categories. OK.")
        return 0

    # Print summary
    print(f"check_risky_diff: {len(changed)} changed file(s), {len(risky)} in risky categories:")
    for f, cat in risky:
        print(f"  [{cat}] {f}")

    if has_tests:
        print(f"  Test file(s) also changed — risky diff accompanied by tests. OK.")
        return 0

    # Risky files changed without tests
    msg = (
        f"\n  WARNING: {len(risky)} risky file(s) changed with no test file changes.\n"
        f"  Per CONTRIBUTING.md, risky changes should include a targeted test.\n"
        f"  Risky categories: {', '.join(sorted(set(c for _, c in risky)))}\n"
        f"  See: CONTRIBUTING.md#risky-change-categories"
    )
    print(msg)

    if strict:
        print("\nFAIL: --strict mode. Add tests or use --warn-only to proceed.")
        return 1

    print("\nWARN: --warn-only mode. Exiting 0. Fix before enforcing --strict.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
