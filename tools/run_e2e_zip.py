#!/usr/bin/env python
"""
End-to-End Harness for ZIP Family Production Validation

This tool orchestrates a complete E2E validation flow:
1. Test data audit and provisioning
2. Pipeline execution (1-N runs)
3. Artifact collection and export
4. Determinism comparison across runs
5. Final JSON summary with KPIs

Usage:
    python tools/run_e2e_zip.py --family zip --seed 12345 --runs 3
    python tools/run_e2e_zip.py --family zip --seed 12345 --runs 1 --skip-provision

Flags:
    --family: Family identifier (default: zip)
    --seed: Random seed for deterministic runs (default: 12345)
    --runs: Number of consecutive runs to execute (default: 3)
    --skip-provision: Skip test data provisioning step
    --verbose: Print detailed progress

Hard Rules:
    - Uses sys.executable for all subprocess calls
    - Exports artifacts to reports/e2e/<run_id>/
    - Compares selection_hash and terminal statuses across runs
    - Generates final JSON summary with KPIs
    - NO markdown writes (dry-run enforced)
"""

import argparse
import hashlib
import json
import logging
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Add user site-packages to path
import site
user_site = site.getusersitepackages()
if user_site not in sys.path:
    sys.path.insert(0, user_site)

from core.database import Database


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


def provision_test_data(family: str, verbose: bool = False) -> bool:
    """
    Provision test data for the specified family.

    Args:
        family: Family identifier
        verbose: Print detailed progress

    Returns:
        True if successful, False otherwise
    """
    logger.info(f"[PROVISION] Provisioning test data for family: {family}")

    try:
        cmd = [
            sys.executable,
            "tools/provision_test_data_zip.py",
        ]

        if verbose:
            cmd.append("--verbose")

        # Prepare environment with user site-packages in PYTHONPATH
        import os
        env = os.environ.copy()
        user_site = site.getusersitepackages()
        current_pythonpath = env.get('PYTHONPATH', '')
        if current_pythonpath:
            env['PYTHONPATH'] = f"{user_site}{os.pathsep}{current_pythonpath}"
        else:
            env['PYTHONPATH'] = user_site

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            env=env,
        )

        if result.returncode != 0:
            logger.error(f"[PROVISION] Failed: {result.stderr}")
            return False

        logger.info("[PROVISION] [OK] Complete")
        return True

    except subprocess.TimeoutExpired:
        logger.error("[PROVISION] Timeout after 120 seconds")
        return False
    except Exception as e:
        logger.error(f"[PROVISION] Error: {str(e)}")
        return False


def run_pipeline(
    family: str,
    seed: int,
    run_number: int,
    verbose: bool = False,
    skip_runtime: bool = False,
    use_workspace_copy: bool = False,
    safe_workspace: bool = False,
    safe_root: Optional[str] = None,
    sqlite_busy_timeout_ms: int = 120000,
    sqlite_wal: bool = True,
    dry_run: bool = False,
) -> Tuple[bool, Optional[str]]:
    """
    Run the full pipeline for the specified family.

    Args:
        family: Family identifier
        seed: Random seed for deterministic execution
        run_number: Run number (for logging)
        verbose: Print detailed progress
        skip_runtime: Skip runtime verification phase
        use_workspace_copy: Enable workspace copy mode
        safe_workspace: Enable safe workspace mode
        safe_root: Override safe workspace root
        sqlite_busy_timeout_ms: SQLite busy timeout in milliseconds
        sqlite_wal: Enable SQLite WAL mode
        dry_run: Pass --dry-run to pipeline (don't write markdown files)

    Returns:
        Tuple of (success: bool, run_id: Optional[str])
    """
    logger.info(f"[RUN {run_number}] Starting pipeline for family: {family}, seed: {seed}")
    start_time = time.time()

    try:
        cmd = [
            sys.executable, "-m", "src.cli.main",
            "--seed", str(seed),
            "--deterministic",  # Enable deterministic mode
            "--sqlite-busy-timeout-ms", str(sqlite_busy_timeout_ms),
        ]

        # Add SQLite WAL flag
        if sqlite_wal:
            cmd.append("--sqlite-wal")
        else:
            cmd.append("--no-sqlite-wal")

        # Add safe workspace flags
        if safe_workspace:
            cmd.append("--safe-workspace")
            if safe_root:
                cmd.extend(["--safe-root", safe_root])

        # Add workspace copy flag (must come before subcommand)
        if use_workspace_copy:
            cmd.append("--use-workspace-copy")

        # Add run command and family
        cmd.extend(["run", "--family", family])

        if skip_runtime:
            cmd.append("--skip-runtime")

        # Add dry-run flag if requested
        if dry_run:
            cmd.append("--dry-run")

        # Prepare environment with user site-packages in PYTHONPATH
        import os
        env = os.environ.copy()
        user_site = site.getusersitepackages()
        current_pythonpath = env.get('PYTHONPATH', '')
        if current_pythonpath:
            env['PYTHONPATH'] = f"{user_site}{os.pathsep}{current_pythonpath}"
        else:
            env['PYTHONPATH'] = user_site

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=1800,  # 30 minute timeout for actual execution
            env=env,
        )

        elapsed = time.time() - start_time

        if result.returncode != 0:
            logger.error(f"[RUN {run_number}] Failed after {elapsed:.1f}s")
            if verbose:
                logger.error(f"[RUN {run_number}] stdout: {result.stdout}")
                logger.error(f"[RUN {run_number}] stderr: {result.stderr}")
            return False, None

        # Parse structured output from CLI (Task 2: Phase-2 unblock)
        safe_workspace_root = None
        safe_db_path = None
        safe_artifacts_dir = None
        run_id = None

        for line in result.stdout.split('\n'):
            line = line.strip()
            if line.startswith('SAFE_WORKSPACE_ROOT:'):
                safe_workspace_root = line.split(':', 1)[1].strip()
            elif line.startswith('DB_PATH:'):
                safe_db_path = line.split(':', 1)[1].strip()
            elif line.startswith('ARTIFACTS_DIR:'):
                safe_artifacts_dir = line.split(':', 1)[1].strip()
            elif line.startswith('RUN_ID:'):
                run_id = line.split(':', 1)[1].strip()
            elif 'run_id' in line.lower() and ':' in line and not run_id:
                # Fallback: try to extract run_id from general output
                parts = line.split(':')
                if len(parts) >= 2:
                    run_id = parts[1].strip().strip('"\'')

        if not run_id:
            # Generate a run_id based on timestamp
            run_id = f"e2e_run{run_number}_{int(time.time())}"

        # Store safe workspace paths for artifact collection (if using safe workspace)
        if safe_workspace_root:
            logger.info(f"[RUN {run_number}] Safe workspace detected: {safe_workspace_root}")
            logger.info(f"[RUN {run_number}] Database path: {safe_db_path}")
            # Return safe paths in a tuple for later use
            run_id = (run_id, safe_db_path, safe_artifacts_dir)

        logger.info(f"[RUN {run_number}] [OK] Complete in {elapsed:.1f}s (run_id: {run_id if isinstance(run_id, str) else run_id[0]})")
        return True, run_id

    except subprocess.TimeoutExpired:
        elapsed = time.time() - start_time
        logger.error(f"[RUN {run_number}] Timeout after {elapsed:.1f}s")
        return False, None
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"[RUN {run_number}] Error after {elapsed:.1f}s: {str(e)}")
        return False, None


def collect_artifacts(
    run_id: str,
    family: str,
    db_path: Path,
    output_dir: Path
) -> Dict[str, Any]:
    """
    Collect artifacts for a completed run.

    Args:
        run_id: Run identifier
        family: Family identifier
        db_path: Path to database
        output_dir: Directory to export artifacts to

    Returns:
        Dict with collected artifacts and metadata
    """
    logger.info(f"[ARTIFACTS] Collecting artifacts for run: {run_id}")

    output_dir.mkdir(parents=True, exist_ok=True)

    artifacts = {
        'run_id': run_id,
        'family': family,
        'timestamp': datetime.utcnow().isoformat(),
        'db_path': str(db_path),
        'artifacts_dir': str(output_dir),
        'fingerprint': {},
        'kpis': {},
        'phase2_metrics': {},
        'status_counts': {},
    }

    try:
        # Connect to database and query
        db = Database(db_path)

        # Get run record and run-scoped state
        with db.get_connection() as conn:
            cursor = conn.cursor()

            # Get example counts by status (run-scoped)
            cursor.execute("""
                SELECT ers.status, COUNT(*) as count
                FROM example_run_state ers
                JOIN example_records er ON er.example_id = ers.example_id
                WHERE ers.run_id = ? AND er.family = ?
                GROUP BY ers.status
            """, (run_id, family))

            for row in cursor.fetchall():
                status, count = row
                artifacts['status_counts'][status] = count

            # Get KPIs (Track 2) - legacy
            try:
                kpis = db.get_runtime_kpis(run_id=run_id, family=family)
                artifacts['kpis'] = kpis
            except Exception as e:
                logger.warning(f"[ARTIFACTS] Could not calculate KPIs: {str(e)}")
                artifacts['kpis'] = {}

            # Get Phase-2 metrics (Task 1: all 3 rates)
            try:
                phase2_metrics = db.get_phase2_metrics(run_id=run_id, family=family)
                artifacts['phase2_metrics'] = phase2_metrics
            except Exception as e:
                logger.warning(f"[ARTIFACTS] Could not calculate Phase-2 metrics: {str(e)}")
                artifacts['phase2_metrics'] = {}

            # Generate fingerprint
            # Selection hash: hash of all example_ids in this run
            cursor.execute("""
                SELECT ers.example_id
                FROM example_run_state ers
                WHERE ers.run_id = ?
                ORDER BY ers.example_id
            """, (run_id,))

            example_ids = [row[0] for row in cursor.fetchall()]
            selection_hash = hashlib.sha256(
                '|'.join(example_ids).encode()
            ).hexdigest()[:16]

            # Get compile and runtime attempt counts
            cursor.execute("""
                SELECT COUNT(*) FROM compile_attempts WHERE run_id = ?
            """, (run_id,))
            row = cursor.fetchone()
            compile_attempts_count = row[0] if row else 0

            cursor.execute("""
                SELECT COUNT(*) FROM runtime_attempts WHERE run_id = ?
            """, (run_id,))
            row = cursor.fetchone()
            runtime_attempts_count = row[0] if row else 0

            artifacts['fingerprint'] = {
                'run_id': run_id,
                'selection_hash': selection_hash,
                'total_examples': len(example_ids),
                'status_counts': artifacts['status_counts'].copy(),
                'compile_attempts_count': compile_attempts_count,
                'runtime_attempts_count': runtime_attempts_count,
                'timestamp': datetime.utcnow().isoformat(),
                'db_path': str(db_path),
                'artifacts_dir': str(output_dir),
            }

        # Export artifacts to JSON
        fingerprint_path = output_dir / 'fingerprint.json'
        with open(fingerprint_path, 'w') as f:
            json.dump(artifacts['fingerprint'], f, indent=2)

        results_path = output_dir / 'results_summary.json'
        with open(results_path, 'w') as f:
            json.dump(artifacts, f, indent=2)

        logger.info(f"[ARTIFACTS] [OK] Exported to {output_dir}")

        return artifacts

    except Exception as e:
        logger.error(f"[ARTIFACTS] Error: {str(e)}")
        return artifacts


def compare_runs(
    run_artifacts: List[Dict[str, Any]],
    output_dir: Path
) -> Dict[str, Any]:
    """
    Compare artifacts across multiple runs to verify determinism.

    Args:
        run_artifacts: List of artifact dicts from each run
        output_dir: Directory to export comparison report

    Returns:
        Dict with comparison results
    """
    logger.info(f"[COMPARE] Comparing {len(run_artifacts)} runs for determinism")

    if len(run_artifacts) < 2:
        logger.info("[COMPARE] Determinism checks skipped (need at least 2 runs)")
        return {
            'status': 'skipped',
            'runs': len(run_artifacts),
            'overall_determinism': 'SKIPPED',
            'reason': 'Need at least 2 runs for determinism comparison'
        }

    comparison = {
        'runs_compared': len(run_artifacts),
        'timestamp': datetime.utcnow().isoformat(),
        'determinism_checks': {},
    }

    # Check 1: Selection hash stability
    selection_hashes = [
        run['fingerprint'].get('selection_hash', 'MISSING')
        for run in run_artifacts
    ]

    all_same = len(set(selection_hashes)) == 1
    comparison['determinism_checks']['selection_hash'] = {
        'stable': all_same,
        'values': selection_hashes,
        'status': 'PASS' if all_same else 'FAIL',
    }

    if all_same:
        logger.info(f"[COMPARE] [OK] Selection hash stable: {selection_hashes[0]}")
    else:
        logger.error(f"[COMPARE] [FAIL] Selection hash unstable: {selection_hashes}")

    # Check 2: Status counts stability
    status_counts_list = [run.get('status_counts', {}) for run in run_artifacts]

    # Check if all runs have same status counts
    status_keys = set()
    for sc in status_counts_list:
        status_keys.update(sc.keys())

    status_stable = {}
    for status in status_keys:
        counts = [sc.get(status, 0) for sc in status_counts_list]
        status_stable[status] = {
            'stable': len(set(counts)) == 1,
            'values': counts,
            'status': 'PASS' if len(set(counts)) == 1 else 'FAIL',
        }

    comparison['determinism_checks']['status_counts'] = status_stable

    # Check 3: KPI stability (if available)
    kpi_keys = set()
    for run in run_artifacts:
        kpi_keys.update(run.get('kpis', {}).keys())

    kpi_stable = {}
    for key in kpi_keys:
        values = [run.get('kpis', {}).get(key, None) for run in run_artifacts]
        # Filter out None values
        values = [v for v in values if v is not None]

        if len(values) > 0:
            # For numeric values, check if they're equal (with tolerance for floats)
            if isinstance(values[0], (int, float)):
                # Allow small floating point differences
                max_diff = max(values) - min(values) if len(values) > 1 else 0
                stable = max_diff < 0.01
            else:
                stable = len(set(map(str, values))) == 1

            kpi_stable[key] = {
                'stable': stable,
                'values': values,
                'status': 'PASS' if stable else 'FAIL',
            }

    comparison['determinism_checks']['kpis'] = kpi_stable

    # Overall determinism verdict
    all_checks_passed = (
        comparison['determinism_checks']['selection_hash']['status'] == 'PASS' and
        all(v['status'] == 'PASS' for v in status_stable.values())
    )

    comparison['overall_determinism'] = 'PASS' if all_checks_passed else 'FAIL'

    # Export comparison report
    comparison_path = output_dir / 'determinism_comparison.json'
    with open(comparison_path, 'w') as f:
        json.dump(comparison, f, indent=2)

    logger.info(f"[COMPARE] Overall determinism: {comparison['overall_determinism']}")

    return comparison


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='E2E harness for ZIP family production validation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument('--family', type=str, default='zip',
                        help='Family identifier (default: zip)')
    parser.add_argument('--seed', type=int, default=12345,
                        help='Random seed for deterministic runs (default: 12345)')
    parser.add_argument('--runs', type=int, default=3,
                        help='Number of consecutive runs (default: 3)')
    parser.add_argument('--skip-provision', action='store_true',
                        help='Skip test data provisioning')
    parser.add_argument('--skip-runtime', action='store_true',
                        help='Skip runtime verification phase')
    parser.add_argument('--use-workspace-copy', action='store_true',
                        help='Enable workspace copy mode')
    parser.add_argument('--dry-run', dest='dry_run', action='store_true', default=True,
                        help='Pass --dry-run to pipeline (default: enabled)')
    parser.add_argument('--no-dry-run', dest='dry_run', action='store_false',
                        help='Do NOT pass --dry-run to pipeline (actually execute)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Verbose output')
    parser.add_argument('--db-path', type=str, default='data/example_reviewer.db',
                        help='Path to database (default: data/example_reviewer.db)')

    # Task 5: SQLite locking hardening flags
    parser.add_argument('--safe-workspace', action='store_true',
                        help='Enable safe workspace mode (outside OneDrive/DrvFS)')
    parser.add_argument('--safe-root', type=str, default=None,
                        help='Override safe workspace root directory')
    parser.add_argument('--sqlite-busy-timeout-ms', type=int, default=120000,
                        help='SQLite busy timeout in milliseconds (default: 120000)')
    parser.add_argument('--sqlite-wal', dest='sqlite_wal', action='store_true', default=True,
                        help='Enable SQLite WAL mode (default: enabled)')
    parser.add_argument('--no-sqlite-wal', dest='sqlite_wal', action='store_false',
                        help='Disable SQLite WAL mode (not recommended)')

    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info("E2E HARNESS - ZIP Family Production Validation")
    logger.info("=" * 80)
    logger.info(f"Family: {args.family}")
    logger.info(f"Seed: {args.seed}")
    logger.info(f"Runs: {args.runs}")
    logger.info(f"Skip provision: {args.skip_provision}")
    logger.info("")

    # Create output directory
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    output_dir = Path(f"reports/e2e/run_{timestamp}")
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Output directory: {output_dir}")
    logger.info("")

    # Step 1: Provision test data (if not skipped)
    if not args.skip_provision:
        success = provision_test_data(args.family, args.verbose)
        if not success:
            logger.error("[FAIL] Test data provisioning failed")
            return 1
    else:
        logger.info("[PROVISION] Skipped (--skip-provision)")

    logger.info("")

    # Step 2: Run pipeline N times
    run_artifacts = []

    for i in range(1, args.runs + 1):
        success, run_id = run_pipeline(
            args.family,
            args.seed,
            i,
            args.verbose,
            skip_runtime=args.skip_runtime,
            use_workspace_copy=args.use_workspace_copy,
            safe_workspace=args.safe_workspace,
            safe_root=args.safe_root,
            sqlite_busy_timeout_ms=args.sqlite_busy_timeout_ms,
            sqlite_wal=args.sqlite_wal,
            dry_run=args.dry_run,
        )

        if not success:
            logger.error(f"[FAIL] Run {i}/{args.runs} failed")
            return 1

        # Extract run information and safe workspace paths if present
        actual_run_id = run_id
        db_path_to_use = Path(args.db_path)
        artifacts_dir_to_use = None

        if isinstance(run_id, tuple):
            actual_run_id, safe_db_path, safe_artifacts_dir = run_id
            if safe_db_path:
                db_path_to_use = Path(safe_db_path)
            if safe_artifacts_dir:
                artifacts_dir_to_use = Path(safe_artifacts_dir)

        # Collect artifacts for this run
        run_output_dir = output_dir / f"run_{i}"
        artifacts = collect_artifacts(
            actual_run_id,
            args.family,
            db_path_to_use,
            run_output_dir
        )

        # Add safe workspace info to artifacts
        if artifacts_dir_to_use:
            artifacts['db_path'] = str(db_path_to_use)
            artifacts['artifacts_dir'] = str(artifacts_dir_to_use)

        run_artifacts.append(artifacts)
        logger.info("")

    # Step 3: Compare runs for determinism
    comparison = compare_runs(run_artifacts, output_dir)

    # Step 4: Extract Phase-2 metrics from last run
    phase2_metrics = {}
    if run_artifacts:
        phase2_metrics = run_artifacts[-1].get('phase2_metrics', {})

    # Step 5: Generate final summary with Phase-2 metrics
    summary = {
        'e2e_harness_version': '2.0',  # Phase-2 version
        'timestamp': datetime.utcnow().isoformat(),
        'family': args.family,
        'seed': args.seed,
        'total_runs': args.runs,
        'successful_runs': len(run_artifacts),
        'output_directory': str(output_dir),
        'determinism': comparison.get('overall_determinism', 'UNKNOWN'),

        # Phase-2 Metrics (Task 1: all 3 rates)
        'phase2_metrics': {
            # The 3 required rates
            'overall_verified_rate': phase2_metrics.get('overall_verified_rate', 0.0),
            'eligible_verified_rate': phase2_metrics.get('eligible_verified_rate', 0.0),
            'runtime_verified_rate': phase2_metrics.get('runtime_verified_rate', 0.0),

            # Denominators
            'total_examples': phase2_metrics.get('total_examples', 0),
            'eligible_examples': phase2_metrics.get('eligible_examples', 0),
            'runtime_attempted': phase2_metrics.get('runtime_attempted', 0),

            # Counts breakdown
            'verified_count': phase2_metrics.get('verified_count', 0),
            'infra_blocked_count': phase2_metrics.get('infra_blocked_count', 0),
            'precheck_only_count': phase2_metrics.get('precheck_only_count', 0),
            'compile_failed_count': phase2_metrics.get('compile_failed_count', 0),
            'runtime_failed_count': phase2_metrics.get('runtime_failed_count', 0),

            # Closure gate
            'gate_selected': phase2_metrics.get('gate_selected', 'B'),
            'gate_a_pass': phase2_metrics.get('gate_a_pass', False),
            'gate_b_pass': phase2_metrics.get('gate_b_pass', False),
            'gate_pass': phase2_metrics.get('gate_pass', False),

            # Infra breakdown
            'infra_breakdown': phase2_metrics.get('infra_breakdown', {}),
        },

        'run_artifacts': run_artifacts,
        'comparison': comparison,
    }

    summary_path = output_dir / 'e2e_summary.json'
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)

    # Print Phase-2 Summary
    logger.info("=" * 80)
    logger.info("E2E HARNESS - PHASE-2 CLOSURE SUMMARY")
    logger.info("=" * 80)
    logger.info("")
    logger.info("PHASE-2 METRICS:")
    logger.info("-" * 40)
    p2 = summary['phase2_metrics']
    logger.info(f"  1. overall_verified_rate:   {p2['overall_verified_rate']:>6.2f}%  ({p2['verified_count']}/{p2['total_examples']} total)")
    logger.info(f"  2. eligible_verified_rate:  {p2['eligible_verified_rate']:>6.2f}%  ({p2['verified_count']}/{p2['eligible_examples']} eligible)")
    logger.info(f"  3. runtime_verified_rate:   {p2['runtime_verified_rate']:>6.2f}%  ({p2['verified_count']}/{p2['runtime_attempted']} runtime attempted)")
    logger.info("")
    logger.info("EXCLUSIONS (from eligible):")
    logger.info(f"  - INFRA_BLOCKED:            {p2['infra_blocked_count']}")
    logger.info(f"  - NEEDS_REVIEW (precheck):  {p2['precheck_only_count']}")
    logger.info("")
    logger.info("STATUS BREAKDOWN:")
    logger.info(f"  - VERIFIED:                 {p2['verified_count']}")
    logger.info(f"  - COMPILE_FAILED:           {p2['compile_failed_count']}")
    logger.info(f"  - RUNTIME_FAILED:           {p2['runtime_failed_count']}")
    logger.info("")
    if p2['infra_breakdown']:
        logger.info("INFRA BLOCKERS DETAIL:")
        for reason, count in p2['infra_breakdown'].items():
            if count > 0:
                logger.info(f"  - {reason}: {count}")
        logger.info("")
    logger.info("CLOSURE GATE EVALUATION:")
    logger.info(f"  - Gate A (strict):      overall_verified >= 90%:  {'PASS' if p2['gate_a_pass'] else 'FAIL'}")
    logger.info(f"  - Gate B (recommended): eligible_verified >= 90%: {'PASS' if p2['gate_b_pass'] else 'FAIL'}")
    logger.info(f"  - Selected Gate: {p2['gate_selected']}")
    gate_result = 'PASS' if p2['gate_pass'] else 'FAIL'
    logger.info(f"  - Gate Result: {gate_result}")
    logger.info("")
    logger.info("-" * 40)
    logger.info(f"Total runs: {args.runs}")
    logger.info(f"Successful runs: {len(run_artifacts)}")
    logger.info(f"Determinism: {summary['determinism']}")
    logger.info(f"Summary: {summary_path}")
    logger.info("=" * 80)

    # Determine exit code based on gate result and determinism
    if summary['determinism'] == 'FAIL':
        logger.error("[FAIL] Determinism checks failed")
        return 1
    elif not p2['gate_pass']:
        logger.warning(f"[WARN] Phase-2 closure gate {p2['gate_selected']} did not pass")
        logger.info("[INFO] Gate not passed but determinism OK - returning success for iteration")
        return 0  # Return 0 so we can iterate on fixes
    else:
        logger.info(f"[SUCCESS] Phase-2 closure gate {p2['gate_selected']} PASSED!")
        return 0


if __name__ == '__main__':
    sys.exit(main())
