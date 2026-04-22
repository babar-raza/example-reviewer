#!/usr/bin/env python3
"""
Refresh eval baseline data after a production pipeline run.

Wraps ``scripts/evals/generate_baseline.py`` to:
  1. Run baseline generation for one or all families
  2. Print a diff summary of changed accuracy rates
  3. Remind you to commit the updated files

Usage:
    python scripts/skills/eval_update.py --family zip
    python scripts/skills/eval_update.py --all
    python scripts/skills/eval_update.py --all --db-path data/example_reviewer_prod.db
    python scripts/skills/eval_update.py --family pdf --db-path /path/to/prod.db
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_GENERATE_SCRIPT = _REPO_ROOT / "scripts" / "evals" / "generate_baseline.py"
_REPORT_PATH = _REPO_ROOT / "evals" / "family_accuracy_report.json"
_BASELINES_DIR = _REPO_ROOT / ".benchmarks" / "baselines"


def _load_baselines_snapshot() -> dict[str, float]:
    """Load current verification rates from committed baselines."""
    rates: dict[str, float] = {}
    if not _BASELINES_DIR.exists():
        return rates
    for path in _BASELINES_DIR.glob("*_baseline.json"):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            family = data.get("family", path.stem.replace("_baseline", ""))
            rate = data.get("totals", {}).get("verification_rate_pct")
            if rate is not None:
                rates[family] = rate
        except (json.JSONDecodeError, KeyError):
            pass
    return rates


def _run_generate(family: str | None, db_path: str | None) -> int:
    """Run generate_baseline.py. Returns exit code."""
    cmd = [sys.executable, str(_GENERATE_SCRIPT)]
    if family:
        cmd += ["--family", family]
    else:
        cmd.append("--all")
    if db_path:
        cmd += ["--db-path", db_path]

    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(_REPO_ROOT))
    return result.returncode


def _print_diff(before: dict[str, float], after: dict[str, float]) -> None:
    """Print a diff of accuracy rates."""
    all_families = sorted(set(before) | set(after))
    changed: list[tuple[str, float | None, float | None]] = []
    new_families: list[tuple[str, float]] = []
    unchanged: list[str] = []

    for fam in all_families:
        b = before.get(fam)
        a = after.get(fam)
        if b is None and a is not None:
            new_families.append((fam, a))
        elif b is not None and a is not None and abs(b - a) >= 0.05:
            changed.append((fam, b, a))
        elif b is not None and a is not None:
            unchanged.append(fam)

    if not changed and not new_families:
        print("\nNo accuracy rate changes detected.")
    else:
        print("\nAccuracy rate changes:")
        for fam, b, a in changed:
            delta = a - b  # type: ignore[operator]
            arrow = "▲" if delta > 0 else "▼"
            print(f"  {fam:12s}  {b:.1f}% → {a:.1f}%  ({arrow}{abs(delta):.1f}%)")
        for fam, a in new_families:
            print(f"  {fam:12s}  (new)  → {a:.1f}%")

    if unchanged:
        print(f"\nUnchanged ({len(unchanged)}): {', '.join(unchanged)}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Refresh eval baselines and show accuracy rate diff."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--family", metavar="NAME", help="Refresh a single family")
    group.add_argument("--all", action="store_true", help="Refresh all families")
    parser.add_argument(
        "--db-path", metavar="PATH",
        help="Path to production SQLite DB (default: data/example_reviewer_prod.db)"
    )
    args = parser.parse_args()

    if not _GENERATE_SCRIPT.exists():
        print(f"ERROR: {_GENERATE_SCRIPT} not found.")
        return 1

    # Snapshot current rates before update
    before = _load_baselines_snapshot()

    family = args.family if not args.all else None
    rc = _run_generate(family, args.db_path)
    if rc != 0:
        print(f"\nERROR: generate_baseline.py exited with code {rc}")
        return rc

    # Snapshot after update
    after = _load_baselines_snapshot()
    _print_diff(before, after)

    print("\nNext steps:")
    print("  1. Review the diff above")
    print("  2. Update evals/family_accuracy_report.json if rates changed significantly")
    print("  3. Commit updated baseline files:")
    print("       git add .benchmarks/baselines/ evals/")
    print("       git commit -m 'eval: refresh baselines after pipeline change'")
    print("  4. Update README.md Section 9 table if production rates changed")

    return 0


if __name__ == "__main__":
    sys.exit(main())
