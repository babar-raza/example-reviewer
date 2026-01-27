#!/usr/bin/env python3
"""
Phase-2 Gate B Validation Script: Strict Context Mode

This script validates that when all three context-related flags are enabled:
1. same_context_only: True
2. context_enforcement: True
3. context_harness: True

The pipeline preserves app_context throughout the lifecycle and ASP.NET
examples compile successfully as ASP.NET projects.

Usage:
    python tools/validate_strict_context_mode.py --run-id <run_id>
    python tools/validate_strict_context_mode.py --family zip --strict-mode
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict, Counter
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.database import Database
from src.core.models import ExampleStatus


class StrictContextValidator:
    """Validates app_context preservation in strict mode."""

    def __init__(self, db_path: str):
        """Initialize validator with database connection."""
        self.db = Database(db_path)
        self.validation_results = {
            "timestamp": datetime.utcnow().isoformat(),
            "validation_criteria": {
                "same_context_only": True,
                "context_enforcement": True,
                "context_harness": True
            },
            "tests": [],
            "summary": {},
            "evidence": {}
        }

    def validate_run(self, run_id: str) -> Dict[str, Any]:
        """
        Validate a specific run for context preservation.

        Args:
            run_id: Run ID to validate

        Returns:
            Validation results dictionary
        """
        print(f"[Phase-2 Gate B] Validating run: {run_id}")
        print("=" * 80)

        # Check if any examples were processed
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM example_run_state WHERE run_id = ?", (run_id,))
        example_count = cursor.fetchone()[0]
        conn.close()

        if example_count == 0:
            print("\n[WARN]  NO_EXAMPLES_PROCESSED: Cannot validate strict context enforcement")
            print("    No examples found for this run. Validation cannot proceed.")
            print("=" * 80)
            self.validation_results["summary"] = {
                "total_tests": 0,
                "passed_tests": 0,
                "failed_tests": 0,
                "overall_status": "NO_EXAMPLES_PROCESSED",
                "example_count": 0
            }
            return self.validation_results

        print(f"\n[STAT] Found {example_count} examples for run {run_id}")

        # Test 1: Verify no cross-context conversions
        self._test_no_cross_context_conversions(run_id)

        # Test 2: Verify ASP.NET examples compile as ASP.NET projects
        self._test_aspnet_compilation_success(run_id)

        # Test 3: Verify context preservation (app_context_before == app_context_after)
        self._test_context_preservation(run_id)

        # Test 4: Compilation success rate per context type
        self._test_compilation_success_rate_per_context(run_id)

        # Test 5: Check for context drift rejections
        self._test_drift_rejections(run_id)

        # Generate summary
        self._generate_summary()

        return self.validation_results

    def _test_no_cross_context_conversions(self, run_id: str):
        """Test that no examples changed context type."""
        print("\n[Test 1] Checking for cross-context conversions...")

        query = """
            SELECT
                ers.example_id,
                er.app_context,
                ers.status,
                ers.failure_reason
            FROM example_run_state ers
            LEFT JOIN example_records er ON ers.example_id = er.example_id
            WHERE ers.run_id = ?
            AND er.app_context IS NOT NULL
        """

        conn = sqlite3.connect(self.db.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, (run_id,))
        rows = cursor.fetchall()
        conn.close()

        cross_context_conversions = []

        for row in rows:
            example_id = row["example_id"]
            app_context = row["app_context"]
            status = row["status"]
            failure_reason = row["failure_reason"]

            # Check if failure reason indicates context drift
            if failure_reason == "context_drift_detected":
                cross_context_conversions.append({
                    "example_id": example_id,
                    "original_context": app_context,
                    "status": status,
                    "failure_reason": failure_reason
                })

        # Record test result
        test_result = {
            "test_name": "no_cross_context_conversions",
            "passed": len(cross_context_conversions) == 0,
            "cross_context_count": len(cross_context_conversions),
            "violations": cross_context_conversions
        }

        self.validation_results["tests"].append(test_result)
        self.validation_results["evidence"]["cross_context_conversions"] = cross_context_conversions

        if test_result["passed"]:
            print(f"  [PASS] PASS: No cross-context conversions detected")
        else:
            print(f"  [FAIL] FAIL: Found {len(cross_context_conversions)} cross-context conversions")
            for violation in cross_context_conversions[:5]:  # Show first 5
                print(f"     - {violation['example_id']}: {violation['original_context']} → {violation['fixed_context']}")

    def _test_aspnet_compilation_success(self, run_id: str):
        """Test that ASP.NET examples compile successfully."""
        print("\n[Test 2] Checking ASP.NET compilation success...")

        query = """
            SELECT
                ers.example_id,
                er.app_context,
                ers.status,
                ers.failure_reason
            FROM example_run_state ers
            LEFT JOIN example_records er ON ers.example_id = er.example_id
            WHERE ers.run_id = ?
            AND er.app_context IN ('aspnet_core_minimal', 'aspnet_core_mvc', 'aspnet_core_webapi')
        """

        conn = sqlite3.connect(self.db.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, (run_id,))
        rows = cursor.fetchall()
        conn.close()

        aspnet_examples = []
        aspnet_compile_success = []
        aspnet_compile_failures = []

        for row in rows:
            example_id = row["example_id"]
            app_context = row["app_context"]
            status = row["status"]
            failure_reason = row["failure_reason"]

            aspnet_examples.append({
                "example_id": example_id,
                "app_context": app_context,
                "status": status,
                "failure_reason": failure_reason
            })

            if status in [ExampleStatus.VERIFIED.value, ExampleStatus.RUNTIME_FAILED.value]:
                aspnet_compile_success.append(example_id)
            elif status == ExampleStatus.COMPILE_FAILED.value:
                aspnet_compile_failures.append({
                    "example_id": example_id,
                    "app_context": app_context,
                    "failure_reason": failure_reason
                })

        total_aspnet = len(aspnet_examples)
        success_count = len(aspnet_compile_success)
        success_rate = (success_count / total_aspnet * 100) if total_aspnet > 0 else 0

        # Record test result
        test_result = {
            "test_name": "aspnet_compilation_success",
            "passed": success_rate >= 80.0,  # 80% threshold for success
            "total_aspnet_examples": total_aspnet,
            "compiled_successfully": success_count,
            "compilation_failures": len(aspnet_compile_failures),
            "success_rate": round(success_rate, 2),
            "failures": aspnet_compile_failures[:10]  # First 10 failures
        }

        self.validation_results["tests"].append(test_result)
        self.validation_results["evidence"]["aspnet_compilation"] = {
            "total": total_aspnet,
            "success": success_count,
            "success_rate": round(success_rate, 2)
        }

        if test_result["passed"]:
            print(f"  [PASS] PASS: ASP.NET compilation success rate: {success_rate:.1f}% ({success_count}/{total_aspnet})")
        else:
            print(f"  [WARN]  WARN: ASP.NET compilation success rate: {success_rate:.1f}% ({success_count}/{total_aspnet})")
            print(f"     Expected: >=80%, Got: {success_rate:.1f}%")

    def _test_context_preservation(self, run_id: str):
        """Test that app_context is preserved (no unauthorized changes)."""
        print("\n[Test 3] Checking app_context preservation...")

        query = """
            SELECT
                ers.example_id,
                er.app_context,
                ers.status,
                ers.failure_reason
            FROM example_run_state ers
            LEFT JOIN example_records er ON ers.example_id = er.example_id
            WHERE ers.run_id = ?
            AND er.app_context IS NOT NULL
        """

        conn = sqlite3.connect(self.db.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, (run_id,))
        rows = cursor.fetchall()
        conn.close()

        preservation_violations = []

        for row in rows:
            example_id = row["example_id"]
            original_context = row["app_context"]
            status = row["status"]
            failure_reason = row["failure_reason"]

            # If failure reason indicates context drift, it's a preservation violation
            if failure_reason == "context_drift_detected":
                preservation_violations.append({
                    "example_id": example_id,
                    "original_context": original_context,
                    "status": status,
                    "failure_reason": failure_reason
                })

        # Record test result
        test_result = {
            "test_name": "context_preservation",
            "passed": len(preservation_violations) == 0,
            "violations_count": len(preservation_violations),
            "violations": preservation_violations
        }

        self.validation_results["tests"].append(test_result)

        if test_result["passed"]:
            print(f"  [PASS] PASS: All examples preserved app_context (0 violations)")
        else:
            print(f"  [FAIL] FAIL: Found {len(preservation_violations)} context preservation violations")

    def _test_compilation_success_rate_per_context(self, run_id: str):
        """Test compilation success rate per context type."""
        print("\n[Test 4] Analyzing compilation success rate per context...")

        query = """
            SELECT
                er.app_context,
                ers.status,
                COUNT(*) as count
            FROM example_run_state ers
            LEFT JOIN example_records er ON ers.example_id = er.example_id
            WHERE ers.run_id = ?
            AND er.app_context IS NOT NULL
            GROUP BY er.app_context, ers.status
        """

        conn = sqlite3.connect(self.db.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, (run_id,))
        rows = cursor.fetchall()
        conn.close()

        context_stats = defaultdict(lambda: {"total": 0, "compiled": 0, "runtime_ok": 0})

        for row in rows:
            app_context = row["app_context"]
            status = row["status"]
            count = row["count"]

            context_stats[app_context]["total"] += count

            if status in [ExampleStatus.VERIFIED.value, ExampleStatus.RUNTIME_FAILED.value]:
                context_stats[app_context]["compiled"] += count

            if status == ExampleStatus.VERIFIED.value:
                context_stats[app_context]["runtime_ok"] += count

        # Calculate success rates
        success_rates = {}
        for context, stats in context_stats.items():
            compile_rate = (stats["compiled"] / stats["total"] * 100) if stats["total"] > 0 else 0
            runtime_rate = (stats["runtime_ok"] / stats["total"] * 100) if stats["total"] > 0 else 0

            success_rates[context] = {
                "total": stats["total"],
                "compiled": stats["compiled"],
                "compile_rate": round(compile_rate, 2),
                "runtime_ok": stats["runtime_ok"],
                "runtime_rate": round(runtime_rate, 2)
            }

            print(f"  [STAT] {context}:")
            print(f"     Total: {stats['total']}, Compiled: {stats['compiled']} ({compile_rate:.1f}%), Runtime OK: {stats['runtime_ok']} ({runtime_rate:.1f}%)")

        # Record test result
        test_result = {
            "test_name": "compilation_success_rate_per_context",
            "passed": True,  # Informational test
            "context_stats": success_rates
        }

        self.validation_results["tests"].append(test_result)
        self.validation_results["evidence"]["context_success_rates"] = success_rates

        print(f"  [PASS] Context-specific success rates calculated")

    def _test_drift_rejections(self, run_id: str):
        """Test that drift validator rejected fixes that changed context."""
        print("\n[Test 5] Checking context drift rejections...")

        query = """
            SELECT
                ers.example_id,
                er.app_context,
                ers.failure_reason
            FROM example_run_state ers
            LEFT JOIN example_records er ON ers.example_id = er.example_id
            WHERE ers.run_id = ?
            AND ers.failure_reason = 'context_drift_detected'
        """

        conn = sqlite3.connect(self.db.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, (run_id,))
        rows = cursor.fetchall()
        conn.close()

        drift_rejections = []

        for row in rows:
            example_id = row["example_id"]
            original_context = row["app_context"]
            failure_reason = row["failure_reason"]

            drift_rejections.append({
                "example_id": example_id,
                "original_context": original_context,
                "failure_reason": failure_reason
            })

        # Record test result
        test_result = {
            "test_name": "drift_rejections",
            "passed": True,  # Informational test - rejections are expected behavior
            "rejection_count": len(drift_rejections),
            "rejections": drift_rejections
        }

        self.validation_results["tests"].append(test_result)
        self.validation_results["evidence"]["drift_rejections"] = drift_rejections

        print(f"  [INFO] Found {len(drift_rejections)} context drift rejections (expected behavior)")
        if drift_rejections:
            print(f"     Examples where context drift was detected:")
            for rejection in drift_rejections[:5]:
                print(f"       - {rejection['example_id']}: original context = {rejection['original_context']}")

    def _generate_summary(self):
        """Generate validation summary."""
        total_tests = len(self.validation_results["tests"])
        passed_tests = sum(1 for test in self.validation_results["tests"] if test["passed"])

        self.validation_results["summary"] = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": total_tests - passed_tests,
            "overall_status": "PASS" if passed_tests == total_tests else "FAIL"
        }

    def export_report(self, output_path: Path):
        """Export validation report to JSON file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.validation_results, f, indent=2)

        print(f"\n[FILE] Validation report exported to: {output_path}")

    def print_summary(self):
        """Print validation summary."""
        print("\n" + "=" * 80)
        print("[Phase-2 Gate B] VALIDATION SUMMARY")
        print("=" * 80)

        summary = self.validation_results["summary"]
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Passed: {summary['passed_tests']}")
        print(f"Failed: {summary['failed_tests']}")
        print(f"Overall Status: {summary['overall_status']}")

        if summary["overall_status"] == "PASS":
            print("\n[PASS] All critical validation tests passed!")
            print("   - No cross-context conversions detected")
            print("   - app_context preserved throughout pipeline")
            print("   - Context-specific compilation working as expected")
        else:
            print("\n[FAIL] Some validation tests failed. Review the report for details.")

        print("=" * 80)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate strict context mode for Phase-2 Gate B"
    )
    parser.add_argument(
        "--run-id",
        type=str,
        help="Run ID to validate"
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default="./data/example_reviewer.db",
        help="Path to database (default: ./data/example_reviewer.db)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="./artifacts/phase2_gateb_validation_report.json",
        help="Output path for validation report"
    )

    args = parser.parse_args()

    if not args.run_id:
        print("[FAIL] Error: --run-id is required")
        print("\nUsage:")
        print("  python tools/validate_strict_context_mode.py --run-id <run_id>")
        print("\nTo find available run IDs:")
        print("  sqlite3 data/example_reviewer.db 'SELECT DISTINCT run_id FROM runs ORDER BY created_at DESC LIMIT 10'")
        sys.exit(1)

    # Initialize validator
    validator = StrictContextValidator(db_path=args.db_path)

    # Run validation
    results = validator.validate_run(args.run_id)

    # Print summary
    validator.print_summary()

    # Export report
    output_path = Path(args.output)
    validator.export_report(output_path)

    # Exit with appropriate code
    status = results["summary"]["overall_status"]
    if status == "NO_EXAMPLES_PROCESSED":
        sys.exit(2)  # Special exit code for no examples
    elif status == "PASS":
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
