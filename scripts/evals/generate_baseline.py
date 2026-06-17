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
    """Generate baseline by querying the production database directly."""
    import sqlite3

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Find the most representative completed run (largest example count)
    run_row = conn.execute(
        """SELECT run_id, examples_processed
           FROM run_records
           WHERE family = ? AND status = 'completed'
           ORDER BY examples_processed DESC, completed_at DESC LIMIT 1""",
        (family,),
    ).fetchone()
    if not run_row:
        conn.close()
        raise ValueError(f"No completed runs for family '{family}' in {db_path}")

    run_id = run_row["run_id"]

    # Count verified/failed from example_run_state joined with example_records
    stats = conn.execute(
        """SELECT
               COUNT(*) AS total,
               SUM(CASE WHEN ers.status IN ('VERIFIED','MD_UPDATED',
                    'FINAL_REVIEW_PASSED','COMMITTED') THEN 1 ELSE 0 END) AS verified,
               SUM(CASE WHEN ers.status LIKE '%FAILED%' THEN 1 ELSE 0 END) AS failed,
               SUM(CASE WHEN ers.status = 'COMPILE_FAILED' THEN 1 ELSE 0 END) AS compile_failed,
               SUM(CASE WHEN ers.status = 'RUNTIME_FAILED' THEN 1 ELSE 0 END) AS runtime_failed
           FROM example_records er
           JOIN example_run_state ers ON er.example_id = ers.example_id
           WHERE er.family = ? AND ers.run_id = ?""",
        (family, run_id),
    ).fetchone()
    conn.close()

    discovered = stats["total"] or 0
    verified = stats["verified"] or 0
    failed = stats["failed"] or 0
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
            "compile_failed": stats["compile_failed"] or 0,
            "runtime_failed": stats["runtime_failed"] or 0,
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


# README Section 9 documented production-run figures (fallback when DB unavailable)
# Source: README.md#9-supported-families (refreshed 2026-06-17 from production DB)
_README_TOTALS: dict[str, dict] = {
    "words":    {"discovered": 94,  "verified": 84},
    "html":     {"discovered": 17,  "verified": 15},
    "zip":      {"discovered": 56,  "verified": 49},
    "psd":      {"discovered": 391, "verified": 336},
    "email":    {"discovered": 19,  "verified": 16},
    "barcode":  {"discovered": 128, "verified": 105},
    "cad":      {"discovered": 9,   "verified": 7},
    "tex":      {"discovered": 45,  "verified": 34},
    "pdf":      {"discovered": 825, "verified": 621},
    "imaging":  {"discovered": 221, "verified": 138},
    "cells":    {"discovered": 192, "verified": 112},
    "page":     {"discovered": 8,   "verified": 1},
    "slides":   {"discovered": 551, "verified": 60},
    "ocr":      {"discovered": 115, "verified": 12},
    "medical":  {"discovered": 88,  "verified": 3},
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
