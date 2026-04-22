#!/usr/bin/env python3
"""
Cross-validate README Section 9 accuracy claims against evals/family_accuracy_report.json.

Parses the family accuracy table from README.md and compares each family's
claimed verification rate against the rate stored in
evals/family_accuracy_report.json.

Exits non-zero if any family's README claim diverges from the JSON by more
than ``--tolerance`` percentage points (default: 1.0).

Writes a machine-readable result to evals/ci_eval_report.json.

Usage:
    python scripts/evals/validate_eval_claims.py
    python scripts/evals/validate_eval_claims.py --tolerance 1.0
    python scripts/evals/validate_eval_claims.py --readme-path README.md
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_README_PATH = _REPO_ROOT / "README.md"
_REPORT_PATH = _REPO_ROOT / "evals" / "family_accuracy_report.json"
_CI_REPORT_PATH = _REPO_ROOT / "evals" / "ci_eval_report.json"

# Regex to match README Section 9 table rows like:
# | ZIP | `config/families/zip.json` | 66 | 61 | Production — 92.4% verified |
_ROW_PATTERN = re.compile(
    r"^\|\s*(?P<family>\w+)\s*\|"       # | ZIP |
    r"[^|]+\|"                           # config_file column
    r"\s*(?P<discovered>\d+)\s*\|"      # discovered
    r"\s*(?P<verified_n>\d+)\s*\|"      # verified count
    r"[^|]*?(?P<rate>[\d.]+)%\s*verified[^|]*\|",  # rate (non-greedy to avoid consuming leading digits)
    re.IGNORECASE,
)


def _parse_readme_claims(readme_path: Path) -> dict[str, float]:
    """Parse README Section 9 table and return {family_lower: rate_pct}."""
    claims: dict[str, float] = {}
    in_section_9 = False

    for line in readme_path.read_text(encoding="utf-8").splitlines():
        if re.match(r"^##\s*9\.", line):
            in_section_9 = True
            continue
        if in_section_9 and re.match(r"^##\s*\d+\.", line):
            break  # left section 9
        if in_section_9:
            m = _ROW_PATTERN.match(line)
            if m:
                family = m.group("family").lower()
                rate = float(m.group("rate"))
                claims[family] = rate

    return claims


def _load_report() -> dict[str, float]:
    """Load evals/family_accuracy_report.json and return {family: rate_pct}."""
    if not _REPORT_PATH.exists():
        print(f"ERROR: {_REPORT_PATH} not found.")
        sys.exit(1)
    with open(_REPORT_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return {
        fam["family"].lower(): fam["verification_rate_pct"]
        for fam in data.get("families", [])
    }


def validate(tolerance: float, readme_path: Path) -> tuple[list[dict], list[dict]]:
    """
    Compare README claims to eval report.

    Returns (passed, failed) lists, each entry is a dict with
    {family, readme_rate, report_rate, delta, status}.
    """
    readme_claims = _parse_readme_claims(readme_path)
    report_data = _load_report()

    passed: list[dict] = []
    failed: list[dict] = []

    for family, readme_rate in sorted(readme_claims.items()):
        if family not in report_data:
            failed.append({
                "family": family,
                "readme_rate": readme_rate,
                "report_rate": None,
                "delta": None,
                "status": "MISSING_IN_REPORT",
            })
            continue

        report_rate = report_data[family]
        delta = abs(readme_rate - report_rate)
        entry = {
            "family": family,
            "readme_rate": readme_rate,
            "report_rate": report_rate,
            "delta": round(delta, 2),
        }
        if delta <= tolerance:
            entry["status"] = "PASS"
            passed.append(entry)
        else:
            entry["status"] = "FAIL"
            failed.append(entry)

    return passed, failed


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate README accuracy claims against evals/family_accuracy_report.json."
    )
    parser.add_argument(
        "--tolerance", type=float, default=1.0,
        help="Maximum allowed divergence in percentage points (default: 1.0)"
    )
    parser.add_argument(
        "--readme-path", default=str(_README_PATH),
        help="Path to README.md (default: repo root README.md)"
    )
    args = parser.parse_args()

    readme_path = Path(args.readme_path)
    if not readme_path.exists():
        print(f"ERROR: README not found at {readme_path}")
        return 1

    print(f"Validating README claims (tolerance: +/-{args.tolerance}%)")
    passed, failed = validate(args.tolerance, readme_path)

    # Write CI report
    ci_report = {
        "schema_version": "1.0",
        "tolerance_pct": args.tolerance,
        "total_checked": len(passed) + len(failed),
        "passed": len(passed),
        "failed": len(failed),
        "results": sorted(passed + failed, key=lambda x: x["family"]),
    }
    _CI_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_CI_REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(ci_report, f, indent=2)

    # Print results
    if passed:
        print(f"\n  PASS ({len(passed)} families):")
        for r in passed:
            print(f"    {r['family']:12s}  README={r['readme_rate']:.1f}%  report={r['report_rate']:.1f}%  d={r['delta']:.1f}%")

    if failed:
        print(f"\n  FAIL ({len(failed)} families):")
        for r in failed:
            if r["status"] == "MISSING_IN_REPORT":
                print(f"    {r['family']:12s}  README={r['readme_rate']:.1f}%  NOT IN REPORT")
            else:
                print(f"    {r['family']:12s}  README={r['readme_rate']:.1f}%  report={r['report_rate']:.1f}%  d={r['delta']:.1f}% > {args.tolerance}%")
        print(f"\nFAIL: {len(failed)} claim(s) diverge beyond tolerance.")
        print(f"Result written to: {_CI_REPORT_PATH}")
        return 1

    print(f"\nPASS: all {len(passed)} README claims match eval report within {args.tolerance}%.")
    print(f"Result written to: {_CI_REPORT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
