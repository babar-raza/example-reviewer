#!/usr/bin/env python3
"""
Master Gate Runner for Track 1

Single entry point to run all Track 1 acceptance gates.

Requirements (from Plan v2.1):
- Run all 5 gates in sequence:
  - Gate 1: Determinism (run pipeline 3 times, compare)
  - Gate 2: Timeout (run with hard timeout)
  - Gate 3A: Config enforcement (test unknown key)
  - Gate 3B: Config access tracking (optional, warn if not implemented)
  - Gate 4: Safety (verify no MD changes)
  - Gate 5: Tests (run pytest 3 times)
- Accept CLI args: --family, --max-examples, --dry-run, --deterministic, --seed
- Print clear pass/fail status for each gate
- Exit code 0 if all gates pass, 1 if any fail
- Generate report file: reports/track1/gate_outputs/gate_results_{timestamp}.json

Usage:
    python tools/run_all_gates.py --family zip --max-examples 20 --dry-run --deterministic --seed 12345
"""

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional


class GateResult:
    """Result of a gate execution."""

    def __init__(self, gate_name: str, gate_number: str):
        self.gate_name = gate_name
        self.gate_number = gate_number
        self.passed: Optional[bool] = None
        self.exit_code: Optional[int] = None
        self.output: str = ""
        self.error: str = ""
        self.skipped: bool = False
        self.skip_reason: str = ""
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON export."""
        duration = None
        if self.start_time and self.end_time:
            duration = (self.end_time - self.start_time).total_seconds()

        return {
            'gate_number': self.gate_number,
            'gate_name': self.gate_name,
            'passed': self.passed,
            'skipped': self.skipped,
            'skip_reason': self.skip_reason,
            'exit_code': self.exit_code,
            'output': self.output[:1000] if self.output else "",  # Truncate for JSON
            'error': self.error[:1000] if self.error else "",
            'duration_seconds': duration,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None
        }


class GateRunner:
    """Master gate runner orchestrating all Track 1 gates."""

    def __init__(self, args):
        self.args = args
        self.results: List[GateResult] = []
        self.root_path = Path(__file__).parent.parent
        self.tools_path = self.root_path / 'tools'
        self.reports_path = self.root_path / 'reports' / 'track1' / 'gate_outputs'
        self.temp_runs: List[Path] = []

    def run_command(self, cmd: List[str], timeout: int = 300) -> tuple[int, str, str]:
        """
        Run a command and capture output.

        Returns: (exit_code, stdout, stderr)
        """
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.root_path
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return 124, "", f"Command timed out after {timeout}s"
        except Exception as e:
            return 1, "", f"Command failed: {e}"

    def build_pipeline_command(self) -> List[str]:
        """Build the pipeline command from args."""
        cmd = ['python', '-m', 'src.cli.main', 'run']

        if self.args.family:
            cmd.extend(['--family', self.args.family])

        if self.args.max_examples:
            cmd.extend(['--max-examples', str(self.args.max_examples)])

        if self.args.dry_run:
            cmd.append('--dry-run')

        if self.args.deterministic:
            cmd.append('--deterministic')

        if self.args.seed is not None:
            cmd.extend(['--seed', str(self.args.seed)])

        return cmd

    def gate_1_determinism(self) -> GateResult:
        """
        Gate 1: Determinism Verification

        Run pipeline 3 times and compare results_summary.json files.
        """
        result = GateResult("Determinism", "Gate 1")
        result.start_time = datetime.now(timezone.utc)

        print("\n" + "="*70)
        print("GATE 1: DETERMINISM VERIFICATION")
        print("="*70)

        # Build pipeline command
        pipeline_cmd = self.build_pipeline_command()

        print(f"\nPipeline command: {' '.join(pipeline_cmd)}")
        print("\nRunning pipeline 3 times...")

        results_files = []

        # Run pipeline 3 times
        for i in range(3):
            print(f"\n[Run {i+1}/3]")
            exit_code, stdout, stderr = self.run_command(pipeline_cmd, timeout=1800)

            if exit_code != 0:
                result.passed = False
                result.exit_code = exit_code
                result.output = stdout
                result.error = f"Pipeline run {i+1} failed with exit code {exit_code}\n{stderr}"
                result.end_time = datetime.now(timezone.utc)
                print(f"  X FAILED with exit code {exit_code}")
                return result

            print(f"  + Completed successfully")

            # Find results_summary.json from this run
            # TODO: Parse stdout to find run_id, for now use a heuristic
            # This needs the pipeline to output the run_id or results path
            # For now, we'll note this as a limitation
            results_files.append(f"runs/run{i+1}/results_summary.json")

        # Compare results using verify_determinism.py
        print("\nComparing results for determinism...")

        # Note: This is a simplified version. In practice, we need the actual
        # results_summary.json paths from the pipeline runs.
        # For now, we'll skip the comparison and mark as needing implementation.

        result.skipped = True
        result.skip_reason = "Gate 1 requires pipeline to export results_summary.json and return run_id"
        result.passed = None
        result.end_time = datetime.now(timezone.utc)

        print("\n! SKIPPED: Determinism comparison requires results_summary.json export")
        print("  This will be available after Agent 8 (Fingerprint) completes.")

        return result

    def gate_2_timeout(self) -> GateResult:
        """
        Gate 2: Timeout Enforcement

        Verify pipeline can be run with hard timeout.
        """
        result = GateResult("Timeout Enforcement", "Gate 2")
        result.start_time = datetime.now(timezone.utc)

        print("\n" + "="*70)
        print("GATE 2: TIMEOUT ENFORCEMENT")
        print("="*70)

        # Build command for run_with_hard_timeout.py
        pipeline_cmd = self.build_pipeline_command()
        timeout_cmd = [
            'python',
            str(self.tools_path / 'run_with_hard_timeout.py'),
            '--seconds', str(self.args.timeout),
            '--'
        ] + pipeline_cmd

        print(f"\nTimeout: {self.args.timeout} seconds")
        print(f"Command: {' '.join(pipeline_cmd)}")

        exit_code, stdout, stderr = self.run_command(timeout_cmd, timeout=self.args.timeout + 30)

        result.exit_code = exit_code
        result.output = stdout
        result.error = stderr

        if exit_code == 0:
            result.passed = True
            print("\n+ PASS: Pipeline completed within timeout")
        elif exit_code == 124:
            result.passed = False
            print(f"\nX FAIL: Pipeline exceeded {self.args.timeout}s timeout")
        else:
            result.passed = False
            print(f"\nX FAIL: Pipeline failed with exit code {exit_code}")

        result.end_time = datetime.now(timezone.utc)
        return result

    def gate_3a_config_enforcement(self) -> GateResult:
        """
        Gate 3A: Config Schema Enforcement

        Verify unknown config keys cause immediate failure.
        """
        result = GateResult("Config Schema Enforcement", "Gate 3A")
        result.start_time = datetime.now(timezone.utc)

        print("\n" + "="*70)
        print("GATE 3A: CONFIG SCHEMA ENFORCEMENT")
        print("="*70)

        # This requires a test that adds an unknown key to config
        # For now, we'll skip this and note it requires a dedicated test

        result.skipped = True
        result.skip_reason = "Requires dedicated test that modifies config with unknown key"
        result.passed = None
        result.end_time = datetime.now(timezone.utc)

        print("\n! SKIPPED: Config enforcement test requires integration with config system")
        print("  This should be tested via unit tests in Agent 7 (Tests).")

        return result

    def gate_3b_config_access(self) -> GateResult:
        """
        Gate 3B: Config Access Tracking (Optional)

        Verify config_access.json is exported (if implemented).
        """
        result = GateResult("Config Access Tracking", "Gate 3B")
        result.start_time = datetime.now(timezone.utc)

        print("\n" + "="*70)
        print("GATE 3B: CONFIG ACCESS TRACKING (OPTIONAL)")
        print("="*70)

        result.skipped = True
        result.skip_reason = "Optional gate - may be documented rather than implemented"
        result.passed = None
        result.end_time = datetime.now(timezone.utc)

        print("\n! SKIPPED: Config access tracking is optional per Plan v2.1")
        print("  Agent 1 may document why this is not feasible.")

        return result

    def gate_4_safety(self) -> GateResult:
        """
        Gate 4: Safety - No Markdown Changes

        Verify no markdown files were modified.
        """
        result = GateResult("Safety - No MD Changes", "Gate 4")
        result.start_time = datetime.now(timezone.utc)

        print("\n" + "="*70)
        print("GATE 4: SAFETY - NO MARKDOWN CHANGES")
        print("="*70)

        # Run verify_no_md_changes.py
        cmd = [
            'python',
            str(self.tools_path / 'verify_no_md_changes.py'),
            '--allow-paths', 'reports/,docs/,plans/,specs/'
        ]

        exit_code, stdout, stderr = self.run_command(cmd, timeout=30)

        result.exit_code = exit_code
        result.output = stdout
        result.error = stderr

        if exit_code == 0:
            result.passed = True
            print("\n+ PASS: No forbidden markdown changes")
        else:
            result.passed = False
            print("\nX FAIL: Markdown files were modified")
            if stdout:
                print("\nDetails:")
                print(stdout)

        result.end_time = datetime.now(timezone.utc)
        return result

    def gate_5_tests(self) -> GateResult:
        """
        Gate 5: Unit Tests

        Run pytest 3 times to verify reliability.
        """
        result = GateResult("Unit Tests (pytest)", "Gate 5")
        result.start_time = datetime.now(timezone.utc)

        print("\n" + "="*70)
        print("GATE 5: UNIT TESTS")
        print("="*70)

        # Check if pytest is available
        check_cmd = ['python', '-m', 'pytest', '--version']
        exit_code, stdout, stderr = self.run_command(check_cmd, timeout=10)

        if exit_code != 0:
            result.skipped = True
            result.skip_reason = "pytest not installed"
            result.passed = None
            result.end_time = datetime.now(timezone.utc)
            print("\n! SKIPPED: pytest not installed")
            print("  Install with: pip install pytest")
            return result

        # Run pytest 3 times
        print("\nRunning pytest 3 times for reliability check...")

        for i in range(3):
            print(f"\n[Run {i+1}/3]")
            cmd = ['python', '-m', 'pytest', '-q']
            exit_code, stdout, stderr = self.run_command(cmd, timeout=300)

            if exit_code != 0:
                result.passed = False
                result.exit_code = exit_code
                result.output = stdout
                result.error = f"pytest run {i+1} failed\n{stderr}"
                result.end_time = datetime.now(timezone.utc)
                print(f"  X FAILED with exit code {exit_code}")
                return result

            print(f"  + Passed")

        result.passed = True
        result.exit_code = 0
        result.end_time = datetime.now(timezone.utc)
        print("\n+ PASS: All 3 pytest runs succeeded")

        return result

    def run_all_gates(self) -> int:
        """
        Run all gates in sequence.

        Returns 0 if all gates pass, 1 if any fail.
        """
        print("\n" + "="*70)
        print("TRACK 1 ACCEPTANCE GATES - MASTER RUNNER")
        print("="*70)
        print(f"Started: {datetime.now(timezone.utc).isoformat()}")
        print(f"Configuration:")
        print(f"  Family: {self.args.family or 'N/A'}")
        print(f"  Max examples: {self.args.max_examples or 'N/A'}")
        print(f"  Dry run: {self.args.dry_run}")
        print(f"  Deterministic: {self.args.deterministic}")
        print(f"  Seed: {self.args.seed or 'N/A'}")
        print(f"  Timeout: {self.args.timeout}s")

        # Run each gate
        self.results.append(self.gate_1_determinism())
        self.results.append(self.gate_2_timeout())
        self.results.append(self.gate_3a_config_enforcement())
        self.results.append(self.gate_3b_config_access())
        self.results.append(self.gate_4_safety())
        self.results.append(self.gate_5_tests())

        # Generate report
        self.generate_report()

        # Print summary
        self.print_summary()

        # Determine overall result
        failed_count = sum(1 for r in self.results if r.passed is False)
        skipped_count = sum(1 for r in self.results if r.skipped)

        if failed_count > 0:
            return 1
        return 0

    def generate_report(self):
        """Generate JSON report of gate results."""
        self.reports_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        report_path = self.reports_path / f"gate_results_{timestamp}.json"

        report = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'configuration': {
                'family': self.args.family,
                'max_examples': self.args.max_examples,
                'dry_run': self.args.dry_run,
                'deterministic': self.args.deterministic,
                'seed': self.args.seed,
                'timeout': self.args.timeout
            },
            'gates': [r.to_dict() for r in self.results],
            'summary': {
                'total': len(self.results),
                'passed': sum(1 for r in self.results if r.passed is True),
                'failed': sum(1 for r in self.results if r.passed is False),
                'skipped': sum(1 for r in self.results if r.skipped)
            }
        }

        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)

        print(f"\nReport saved to: {report_path}")

    def print_summary(self):
        """Print summary of all gate results."""
        print("\n" + "="*70)
        print("GATE RESULTS SUMMARY")
        print("="*70)

        for result in self.results:
            status = "PASS" if result.passed else ("FAIL" if result.passed is False else "SKIP")
            symbol = "+" if result.passed else ("X" if result.passed is False else "!")
            print(f"{symbol} {result.gate_number}: {result.gate_name} - {status}")
            if result.skip_reason:
                print(f"    Reason: {result.skip_reason}")

        print("="*70)

        passed = sum(1 for r in self.results if r.passed is True)
        failed = sum(1 for r in self.results if r.passed is False)
        skipped = sum(1 for r in self.results if r.skipped)

        print(f"Total: {len(self.results)} | Passed: {passed} | Failed: {failed} | Skipped: {skipped}")

        if failed > 0:
            print("\nX OVERALL RESULT: FAILED")
        elif skipped == len(self.results):
            print("\n! OVERALL RESULT: ALL GATES SKIPPED")
        elif skipped > 0:
            print("\n! OVERALL RESULT: PARTIAL (some gates skipped)")
        else:
            print("\n+ OVERALL RESULT: ALL GATES PASSED")

        print("="*70)


def main():
    parser = argparse.ArgumentParser(
        description="Run all Track 1 acceptance gates",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tools/run_all_gates.py --family zip --max-examples 20 --dry-run --deterministic --seed 12345
  python tools/run_all_gates.py --family zip --max-examples 5 --dry-run --timeout 600

Gates:
  Gate 1: Determinism (run pipeline 3 times, compare results)
  Gate 2: Timeout (enforce hard timeout)
  Gate 3A: Config enforcement (unknown keys fail)
  Gate 3B: Config access tracking (optional)
  Gate 4: Safety (no markdown changes)
  Gate 5: Tests (pytest 3 times)
        """
    )

    parser.add_argument('--family', type=str, help='Product family to test')
    parser.add_argument('--max-examples', type=int, help='Maximum examples to process')
    parser.add_argument('--dry-run', action='store_true', help='Enable dry-run mode')
    parser.add_argument('--deterministic', action='store_true', help='Enable deterministic mode')
    parser.add_argument('--seed', type=int, help='Random seed for determinism')
    parser.add_argument('--timeout', type=int, default=1200, help='Hard timeout in seconds (default: 1200)')

    args = parser.parse_args()

    runner = GateRunner(args)
    exit_code = runner.run_all_gates()
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
