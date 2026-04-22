#!/usr/bin/env python3
"""
Generate family accuracy baseline JSON files from the production database.

Reads run results from the SQLite database using the existing ResultsSummary
and Database infrastructure, and writes structured JSON to
.benchmarks/baselines/{family}_baseline.json.

Usage:
    python scripts/evals/generate_baseline.py --family zip
    python scripts/evals/generate_baseline.py --all
    python scripts/evals/generate_baseline.py --all --db-path data/prod.db

Output schema (.benchmarks/baselines/{family}_baseline.json):
    schema_version      str     "1.0"
    family              str     Family slug (e.g. "zip")
    generated_at        str     ISO-8601 UTC timestamp
    source              str     "production_db" or "readme_documented"
    pipeline_version    str     Short git SHA of the generating commit
    totals:
        discovered          int     Total examples in family config
        verified            int     VERIFIED status count
        failed              int     Final failed count
        compile_failed      int     COMPILE_FAILED count (if available)
        runtime_failed      int     RUNTIME_FAILED count (if available)
        verification_rate_pct float  verified / discovered * 100
    run_id              str|null  Most recent run ID used
    notes               str     Human notes about this baseline
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Allow running from repo root without installing the package
_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

_BASELINES_DIR = _REPO_ROOT / ".benchmarks" / "baselines"
_CONFIG_DIR = _REPO_ROOT / "config" / "families"
_SCHEMA_VERSION = "1.0"


def _get_pipeline_version() -> str:
    """Return short git SHA, or 'unknown' if git is unavailable."""
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(_REPO_ROOT),
            stderr=subprocess.DEVNULL,
        ).decode().strip()
    except Exception:
        return "unknown"


def _list_families() -> list[str]:
    """Return all family slugs from config/families/ (exclude KB files)."""
    families = []
    for path in sorted(_CONFIG_DIR.glob("*.json")):
        name = path.stem
        if name.endswith("_behavioral_patterns") or name.endswith("_review_hints"):
            continue
        families.append(name)
    return families


def _generate_baseline_from_db(
    family: str,
    db_path: str,
    pipeline_version: str,
) -> dict:
    """Generate baseline by querying the production database."""
    from src.core.database import Database
    from src.core.results_summary import ResultsSummary

    db = Database(db_path)
    # Get the most recent run for this family
    runs = db.get_runs_by_family(family) if hasattr(db, "get_runs_by_family") else []
    if not runs:
        raise ValueError(f"No runs found for family '{family}' in {db_path}")

    # Use the most recent run
    latest_run = runs[-1] if isinstance(runs, list) else runs
    run_id = getattr(latest_run, "run_id", str(latest_run))

    summary = ResultsSummary.from_run(db, run_id)
    stats = db.get_run_stats_from_db(family, run_id)

    discovered = stats.get("total_processed", summary.examples_processed)
    verified = stats.get("verified", summary.examples_verified)
    failed = stats.get("failed", summary.examples_failed)
    rate = round(verified / discovered * 100, 1) if discovered > 0 else 0.0

    return {
        "schema_version": _SCHEMA_VERSION,
        "family": family,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "production_db",
        "pipeline_version": pipeline_version,
        "totals": {
            "discovered": discovered,
            "verified": verified,
            "failed": failed,
            "compile_failed": stats.get("compile_failed", None),
            "runtime_failed": stats.get("runtime_failed", None),
            "verification_rate_pct": rate,
        },
        "run_id": run_id,
        "notes": f"Generated from production DB run {run_id}",
    }


def _generate_baseline_documented(
    family: str,
    pipeline_version: str,
    totals: dict,
) -> dict:
    """
    Create a baseline from documented production-run figures (README data).

    Used when the production DB is not available in the current environment.
    The figures originate from the same production runs that populated the README
    Section 9 table; they are grounded data, not estimates.
    """
    discovered = totals["discovered"]
    verified = totals["verified"]
    rate = round(verified / discovered * 100, 1) if discovered > 0 else 0.0
    return {
        "schema_version": _SCHEMA_VERSION,
        "family": family,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "readme_documented_production_run",
        "pipeline_version": pipeline_version,
        "totals": {
            "discovered": discovered,
            "verified": verified,
            "failed": discovered - verified,
            "compile_failed": None,
            "runtime_failed": None,
            "verification_rate_pct": rate,
        },
        "run_id": None,
        "notes": (
            "Figures sourced from README Section 9 production-run data. "
            "Re-run with --db-path to refresh from the production database."
        ),
    }


# README Section 9 documented production-run figures
# Source: README.md#9-supported-families (as of 2026-04-20)
_README_TOTALS: dict[str, dict] = {
    "zip":      {"discovered": 66,  "verified": 61},
    "psd":      {"discovered": 391, "verified": 347},
    "html":     {"discovered": 16,  "verified": 14},
    "email":    {"discovered": 20,  "verified": 17},
    "words":    {"discovered": 147, "verified": 123},
    "pdf":      {"discovered": 825, "verified": 684},
    "tex":      {"discovered": 45,  "verified": 37},
    "barcode":  {"discovered": 201, "verified": 161},
    "cad":      {"discovered": 10,  "verified": 8},
    "imaging":  {"discovered": 217, "verified": 138},
    "cells":    {"discovered": 196, "verified": 121},
    "slides":   {"discovered": 551, "verified": 223},
    "ocr":      {"discovered": 115, "verified": 41},
    "medical":  {"discovered": 88,  "verified": 6},
    "page":     {"discovered": 8,   "verified": 0},
    "tasks":    {"discovered": 6,   "verified": 0},
    "smoke":    {"discovered": 0,   "verified": 0},
}


def generate_one(family: str, db_path: str | None, pipeline_version: str) -> Path:
    """Generate and write a single family baseline. Returns the output path."""
    output_path = _BASELINES_DIR / f"{family}_baseline.json"
    _BASELINES_DIR.mkdir(parents=True, exist_ok=True)

    if db_path and Path(db_path).exists():
        try:
            data = _generate_baseline_from_db(family, db_path, pipeline_version)
            print(f"  [{family}] Generated from DB: {data['totals']['verification_rate_pct']}% verified")
        except Exception as e:
            print(f"  [{family}] DB query failed ({e}); falling back to documented figures")
            totals = _README_TOTALS.get(family, {"discovered": 0, "verified": 0})
            data = _generate_baseline_documented(family, pipeline_version, totals)
    else:
        totals = _README_TOTALS.get(family, {"discovered": 0, "verified": 0})
        data = _generate_baseline_documented(family, pipeline_version, totals)
        rate = data["totals"]["verification_rate_pct"]
        print(f"  [{family}] Using documented figures: {rate}% verified")

    output_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate .benchmarks/baselines/<family>_baseline.json files."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--family", help="Single family slug (e.g. zip, pdf, words)")
    group.add_argument("--all", action="store_true", help="Generate baselines for all families")
    parser.add_argument(
        "--db-path",
        default=str(_REPO_ROOT / "data" / "example_reviewer_prod.db"),
        help="Path to the production SQLite database (default: data/example_reviewer_prod.db)",
    )
    args = parser.parse_args()

    pipeline_version = _get_pipeline_version()
    print(f"Pipeline version: {pipeline_version}")
    print(f"Output dir: {_BASELINES_DIR}")

    if args.all:
        families = _list_families()
        print(f"Generating baselines for {len(families)} families: {', '.join(families)}")
        for family in families:
            generate_one(family, args.db_path, pipeline_version)
    else:
        generate_one(args.family, args.db_path, pipeline_version)

    print("\nDone. Commit the updated .benchmarks/baselines/ files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
