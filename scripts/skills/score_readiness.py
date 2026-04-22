#!/usr/bin/env python3
"""
On-demand quarterly review readiness audit for Example Reviewer.

Checks six dimensions of reviewer-readiness and produces a markdown report at
``reports/score_readiness_<YYYY-MM-DD>.md``.

Dimensions checked:
  1. Eval freshness     — report_date in family_accuracy_report.json vs. max-age threshold
  2. Benchmark complete — production families with committed baseline files
  3. Fallback tests     — dedicated fallback test files exist
  4. Docs-to-code       — README accuracy claims match eval report (via validate_eval_claims)
  5. CI evidence        — .gitlab-ci.yml exists and has required stage/job names
  6. CODEOWNERS         — critical paths covered in CODEOWNERS

Usage:
    python scripts/skills/score_readiness.py
    python scripts/skills/score_readiness.py --output-dir reports
    python scripts/skills/score_readiness.py --max-age-days 60
    python scripts/skills/score_readiness.py --ci          # exit 1 on any FAIL
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------------------
# Dimension 1: Eval freshness
# ---------------------------------------------------------------------------
_REPORT_PATH = _REPO_ROOT / "evals" / "family_accuracy_report.json"


def _check_eval_freshness(max_age_days: int) -> tuple[str, str]:
    """Return (status, detail)."""
    if not _REPORT_PATH.exists():
        return "FAIL", f"`evals/family_accuracy_report.json` does not exist. Run: `python scripts/evals/generate_baseline.py --all`"
    with open(_REPORT_PATH, encoding="utf-8") as f:
        report = json.load(f)
    report_date_str = report.get("report_date")
    if not report_date_str:
        return "FAIL", "`report_date` field missing from family_accuracy_report.json"
    try:
        report_date = date.fromisoformat(report_date_str)
        age_days = (date.today() - report_date).days
        if age_days > max_age_days:
            return "FAIL", f"Report is {age_days} days old (limit: {max_age_days}). Run `generate_baseline.py --all`."
        return "PASS", f"Report date: {report_date_str} ({age_days} days old, limit: {max_age_days})"
    except ValueError:
        return "FAIL", f"`report_date` is not a valid ISO date: {report_date_str!r}"


# ---------------------------------------------------------------------------
# Dimension 2: Benchmark completeness
# ---------------------------------------------------------------------------
_BASELINES_DIR = _REPO_ROOT / ".benchmarks" / "baselines"


def _check_benchmark_completeness() -> tuple[str, str]:
    """Return (status, detail)."""
    if not _REPORT_PATH.exists():
        return "FAIL", "`evals/family_accuracy_report.json` missing — cannot check baselines"
    with open(_REPORT_PATH, encoding="utf-8") as f:
        report = json.load(f)
    families = report.get("families", [])
    production = [f for f in families if f.get("status") == "production"]
    missing: list[str] = []
    present: list[str] = []
    for fam in production:
        baseline = fam.get("baseline_file")
        if not baseline or not (_REPO_ROOT / baseline).exists():
            missing.append(fam["family"])
        else:
            present.append(fam["family"])

    total = len(production)
    if not missing:
        return "PASS", f"All {total} production families have committed baselines"
    if len(present) >= total * 0.75:
        return "PARTIAL", (
            f"{len(present)}/{total} production families have baselines. "
            f"Missing: {', '.join(missing)}"
        )
    return "FAIL", (
        f"Only {len(present)}/{total} production families have baselines. "
        f"Missing: {', '.join(missing)}. Run `generate_baseline.py --all`."
    )


# ---------------------------------------------------------------------------
# Dimension 3: Fallback test files
# ---------------------------------------------------------------------------
_FALLBACK_TEST_FILES: list[tuple[str, str]] = [
    ("tests/test_circuit_breaker_scenarios.py", "Circuit breaker state machine tests"),
    ("tests/test_degraded_mode.py", "Degraded mode routing tests"),
    ("tests/test_kb_error_handling.py", "KB error handling tests"),
]


def _check_fallback_tests() -> tuple[str, str]:
    """Return (status, detail)."""
    missing = []
    present = []
    for rel_path, label in _FALLBACK_TEST_FILES:
        if (_REPO_ROOT / rel_path).exists():
            present.append(label)
        else:
            missing.append(f"`{rel_path}` ({label})")
    if not missing:
        return "PASS", f"All {len(present)} fallback test files exist"
    return "FAIL", "Missing fallback test files:\n" + "\n".join(f"  - {m}" for m in missing)


# ---------------------------------------------------------------------------
# Dimension 4: Docs-to-code alignment (README claims vs. eval report)
# ---------------------------------------------------------------------------
_CI_EVAL_REPORT = _REPO_ROOT / "evals" / "ci_eval_report.json"


def _check_docs_to_code() -> tuple[str, str]:
    """Return (status, detail). Runs validate_eval_claims inline."""
    # Try to run the validate script as a subprocess for cleanliness
    validate_script = _REPO_ROOT / "scripts" / "evals" / "validate_eval_claims.py"
    if not validate_script.exists():
        return "FAIL", "`scripts/evals/validate_eval_claims.py` does not exist"

    try:
        result = subprocess.run(
            [sys.executable, str(validate_script)],
            capture_output=True,
            text=True,
            cwd=str(_REPO_ROOT),
        )
        if result.returncode == 0:
            # Parse ci_eval_report.json for counts
            if _CI_EVAL_REPORT.exists():
                with open(_CI_EVAL_REPORT, encoding="utf-8") as f:
                    ci_report = json.load(f)
                total = ci_report.get("total_checked", "?")
                passed = ci_report.get("passed", "?")
                return "PASS", f"All {passed}/{total} README accuracy claims match eval report"
            return "PASS", "validate_eval_claims.py exited 0"
        # Failed — try to parse the CI report for failure details
        if _CI_EVAL_REPORT.exists():
            with open(_CI_EVAL_REPORT, encoding="utf-8") as f:
                ci_report = json.load(f)
            failed_fams = [
                r["family"]
                for r in ci_report.get("results", [])
                if r.get("status") != "PASS"
            ]
            return "FAIL", (
                f"{ci_report.get('failed', '?')} claim(s) diverge from eval report: "
                + ", ".join(failed_fams)
            )
        return "FAIL", "validate_eval_claims.py exited non-zero. Run it directly for details."
    except Exception as exc:
        return "FAIL", f"Could not run validate_eval_claims.py: {exc}"


# ---------------------------------------------------------------------------
# Dimension 5: CI evidence (.gitlab-ci.yml with required jobs/stages)
# ---------------------------------------------------------------------------
_GITLAB_CI_PATH = _REPO_ROOT / ".gitlab-ci.yml"
_REQUIRED_CI_PATTERNS: list[tuple[str, str]] = [
    ("stages:", "stages block"),
    ("unit-tests:", "unit-tests job"),
    ("--cov", "coverage flag"),
    ("fallback-tests:", "fallback-tests job"),
    ("eval-baseline-check:", "eval-baseline-check job"),
    ("coverage.xml", "Cobertura coverage artifact"),
]


def _check_ci_evidence() -> tuple[str, str]:
    """Return (status, detail)."""
    if not _GITLAB_CI_PATH.exists():
        return "FAIL", "`.gitlab-ci.yml` does not exist. Create it to enable GitLab-native CI."
    content = _GITLAB_CI_PATH.read_text(encoding="utf-8")
    missing = [label for pattern, label in _REQUIRED_CI_PATTERNS if pattern not in content]
    if not missing:
        return "PASS", f"`.gitlab-ci.yml` contains all {len(_REQUIRED_CI_PATTERNS)} required elements"
    return "PARTIAL", "Missing CI elements: " + ", ".join(missing)


# ---------------------------------------------------------------------------
# Dimension 6: CODEOWNERS coverage
# ---------------------------------------------------------------------------
_CODEOWNERS_PATH = _REPO_ROOT / "CODEOWNERS"
_REQUIRED_CODEOWNERS_PATHS: list[tuple[str, str]] = [
    ("evals/", "evals/ directory"),
    (".benchmarks/", ".benchmarks/ directory"),
    ("src/pipeline/orchestrator.py", "orchestrator"),
    ("src/core/path_guard.py", "path_guard safety gate"),
    ("src/services/kb/", "KB subsystem source"),
]


def _check_codeowners() -> tuple[str, str]:
    """Return (status, detail)."""
    if not _CODEOWNERS_PATH.exists():
        return "FAIL", "`CODEOWNERS` file does not exist"
    content = _CODEOWNERS_PATH.read_text(encoding="utf-8")
    missing = [label for pattern, label in _REQUIRED_CODEOWNERS_PATHS if pattern not in content]
    if not missing:
        return "PASS", f"CODEOWNERS covers all {len(_REQUIRED_CODEOWNERS_PATHS)} required paths"
    return "FAIL", "CODEOWNERS missing coverage for: " + ", ".join(missing)


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------
_STATUS_EMOJI = {"PASS": "✅", "PARTIAL": "⚠️", "FAIL": "❌"}
_STATUS_ASCII = {"PASS": "[PASS]", "PARTIAL": "[PARTIAL]", "FAIL": "[FAIL]"}


def _render_report(
    results: list[tuple[str, str, str]],
    report_date: str,
    pass_count: int,
    fail_count: int,
    partial_count: int,
) -> str:
    lines = [
        f"# Score Readiness Report — {report_date}",
        "",
        "Generated by `scripts/skills/score_readiness.py`.",
        "",
        "## Summary",
        "",
        f"| Result | Count |",
        f"|--------|-------|",
        f"| ✅ PASS    | {pass_count} |",
        f"| ⚠️  PARTIAL | {partial_count} |",
        f"| ❌ FAIL    | {fail_count} |",
        "",
    ]

    overall = "PASS" if fail_count == 0 and partial_count == 0 else (
        "PARTIAL" if fail_count == 0 else "FAIL"
    )
    lines.append(f"**Overall: {_STATUS_EMOJI.get(overall, '')} {overall}**")
    lines.append("")

    lines.append("## Dimensions")
    lines.append("")

    for dim_name, status, detail in results:
        emoji = _STATUS_EMOJI.get(status, "?")
        lines.append(f"### {emoji} {dim_name}: {status}")
        lines.append("")
        lines.append(detail)
        lines.append("")

    lines.append("## Next Steps")
    lines.append("")
    if fail_count == 0 and partial_count == 0:
        lines.append("All dimensions PASS. Repository is ready for quarterly review.")
    else:
        lines.append("Address the following before the quarterly review snapshot:")
        lines.append("")
        for dim_name, status, detail in results:
            if status in ("FAIL", "PARTIAL"):
                lines.append(f"- **{dim_name}** ({status}): {detail.splitlines()[0]}")
        lines.append("")
        lines.append("Re-run this script after addressing each item:")
        lines.append("```")
        lines.append("python scripts/skills/score_readiness.py")
        lines.append("```")

    lines.append("")
    lines.append("---")
    lines.append(f"*Report generated: {report_date}*")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Quarterly review readiness audit for Example Reviewer."
    )
    parser.add_argument(
        "--output-dir", default="reports",
        help="Directory to write the readiness report into (default: reports/)"
    )
    parser.add_argument(
        "--max-age-days", type=int, default=90,
        help="Maximum eval report age in days before flagging stale (default: 90)"
    )
    parser.add_argument(
        "--ci", action="store_true",
        help="Exit 1 if any dimension is FAIL (for CI integration)"
    )
    args = parser.parse_args()

    today = date.today().isoformat()
    print(f"Score Readiness Audit - {today}")
    print("=" * 50)

    checks: list[tuple[str, callable]] = [
        ("Eval Freshness",         lambda: _check_eval_freshness(args.max_age_days)),
        ("Benchmark Completeness", _check_benchmark_completeness),
        ("Fallback Test Coverage", _check_fallback_tests),
        ("Docs-to-Code Alignment", _check_docs_to_code),
        ("CI Evidence",            _check_ci_evidence),
        ("CODEOWNERS Coverage",    _check_codeowners),
    ]

    results: list[tuple[str, str, str]] = []
    pass_count = partial_count = fail_count = 0

    for dim_name, fn in checks:
        status, detail = fn()
        results.append((dim_name, status, detail))
        tag = _STATUS_ASCII.get(status, "?")
        print(f"  {tag} {dim_name}")
        if status == "PASS":
            pass_count += 1
        elif status == "PARTIAL":
            partial_count += 1
            print(f"     {detail.splitlines()[0]}")
        else:
            fail_count += 1
            print(f"     {detail.splitlines()[0]}")

    print()
    overall = "PASS" if fail_count == 0 and partial_count == 0 else (
        "PARTIAL" if fail_count == 0 else "FAIL"
    )
    print(f"Overall: {overall} ({pass_count} pass, {partial_count} partial, {fail_count} fail)")

    # Write markdown report
    output_dir = _REPO_ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / f"score_readiness_{today}.md"
    report_content = _render_report(results, today, pass_count, fail_count, partial_count)
    report_path.write_text(report_content, encoding="utf-8")
    print(f"\nReport written to: {report_path.relative_to(_REPO_ROOT)}")

    if args.ci and fail_count > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
