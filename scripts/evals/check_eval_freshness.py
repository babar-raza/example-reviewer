#!/usr/bin/env python3
"""
Check that the eval accuracy report is not stale.

Reads ``report_date`` from ``evals/family_accuracy_report.json`` and fails
(exit code 1) if the report is older than ``--max-age-days`` days.

Also warns if any Production-status family in the report has no
``baseline_file`` reference.

Usage:
    python scripts/evals/check_eval_freshness.py
    python scripts/evals/check_eval_freshness.py --max-age-days 90
    python scripts/evals/check_eval_freshness.py --exit-code   # return 0/1 for scripting
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_REPORT_PATH = _REPO_ROOT / "evals" / "family_accuracy_report.json"
_BASELINES_DIR = _REPO_ROOT / ".benchmarks" / "baselines"


def _load_report() -> dict:
    if not _REPORT_PATH.exists():
        print(f"ERROR: {_REPORT_PATH} not found.")
        print("Run: python scripts/evals/generate_baseline.py --all")
        sys.exit(1)
    with open(_REPORT_PATH, encoding="utf-8") as f:
        return json.load(f)


def check_freshness(max_age_days: int) -> list[str]:
    """Return a list of warning/error messages. Empty list = PASS."""
    report = _load_report()
    issues: list[str] = []

    # Check report_date age
    report_date_str = report.get("report_date")
    if not report_date_str:
        issues.append("ERROR: 'report_date' field missing from family_accuracy_report.json")
    else:
        try:
            report_date = date.fromisoformat(report_date_str)
            age_days = (date.today() - report_date).days
            if age_days > max_age_days:
                issues.append(
                    f"ERROR: eval report is {age_days} days old (max allowed: {max_age_days}). "
                    f"Run: python scripts/evals/generate_baseline.py --all"
                )
            else:
                print(f"  Eval report age: {age_days} days (limit: {max_age_days}) - OK")
        except ValueError:
            issues.append(f"ERROR: 'report_date' is not a valid date: {report_date_str!r}")

    # Check Production families have baseline files
    families = report.get("families", [])
    missing_baselines = []
    for fam in families:
        if fam.get("status") == "production":
            baseline = fam.get("baseline_file")
            if not baseline:
                missing_baselines.append(fam["family"])
            elif not (_REPO_ROOT / baseline).exists():
                missing_baselines.append(f"{fam['family']} (file missing: {baseline})")

    if missing_baselines:
        issues.append(
            f"WARNING: {len(missing_baselines)} Production families have no committed baseline: "
            + ", ".join(missing_baselines)
        )

    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Check eval report freshness.")
    parser.add_argument(
        "--max-age-days", type=int, default=90,
        help="Maximum age in days before the report is considered stale (default: 90)"
    )
    parser.add_argument(
        "--exit-code", action="store_true",
        help="Exit with code 1 if there are any ERROR-level issues"
    )
    args = parser.parse_args()

    print(f"Checking eval freshness: {_REPORT_PATH}")
    issues = check_freshness(args.max_age_days)

    if not issues:
        print("PASS: eval report is fresh and all production baselines are present.")
        return 0

    errors = [i for i in issues if i.startswith("ERROR")]
    warnings = [i for i in issues if i.startswith("WARNING")]

    for w in warnings:
        print(f"  {w}")
    for e in errors:
        print(f"  {e}")

    if errors:
        print(f"\nFAIL: {len(errors)} error(s) found.")
        return 1

    print(f"\nPASS with {len(warnings)} warning(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
