"""
Run All Quality Gates for a Family.

This script runs all quality gate commands (scan, extract, compile-verify, runtime-verify,
compile-fix, runtime-fix, md-update, final-review) in sequence for a given family.

Usage:
    python tools/run_all_gates.py --family zip --max-examples 20 --dry-run --deterministic --seed 12345

Hard Rules:
    - MUST use sys.executable for all subprocess calls (no hardcoded paths)
    - MUST support Windows environment
    - MUST emit telemetry for significant operations
    - NO markdown changes outside: specs/, reports/, docs/, plans/
"""

import argparse
import json
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional


def setup_logging(verbose: bool = False) -> None:
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - [%(levelname)s] %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )


def run_gate(
    gate_name: str,
    family: str,
    python_exe: str,
    max_examples: Optional[int] = None,
    dry_run: bool = False,
    deterministic: bool = False,
    seed: Optional[int] = None,
    allow_md_write: bool = False,
) -> Dict[str, Any]:
    """
    Run a single quality gate.

    Args:
        gate_name: Gate identifier (scan, extract, compile-verify, etc.)
        family: Family identifier
        python_exe: Python executable path (sys.executable)
        max_examples: Maximum examples to process
        dry_run: Dry-run mode
        deterministic: Enable deterministic mode
        seed: Random seed
        allow_md_write: Allow markdown writes

    Returns:
        Dict with gate result (success, duration_ms, stdout, stderr)
    """
    logger = logging.getLogger(__name__)

    # Build command
    cmd = [python_exe, "-m", "src.cli.main", gate_name, "--family", family]

    if max_examples:
        cmd.extend(["--max-examples", str(max_examples)])

    if dry_run and gate_name in ["md-update"]:
        cmd.append("--dry-run")

    if allow_md_write and gate_name in ["md-update"]:
        cmd.append("--allow-md-write")

    if deterministic:
        cmd.append("--deterministic")

    if seed is not None:
        cmd.extend(["--seed", str(seed)])

    logger.info(f"Running gate: {gate_name}")
    logger.debug(f"Command: {' '.join(cmd)}")

    start_time = datetime.utcnow()

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=1800,  # 30 min timeout per gate
        )

        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        success = result.returncode == 0

        if success:
            logger.info(f"Gate {gate_name} succeeded ({duration_ms}ms)")
        else:
            logger.error(f"Gate {gate_name} failed with exit code {result.returncode}")
            logger.error(f"STDERR: {result.stderr[:500]}")

        return {
            'gate': gate_name,
            'success': success,
            'exit_code': result.returncode,
            'duration_ms': duration_ms,
            'stdout': result.stdout,
            'stderr': result.stderr,
        }

    except subprocess.TimeoutExpired:
        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        logger.error(f"Gate {gate_name} timed out after {duration_ms}ms")

        return {
            'gate': gate_name,
            'success': False,
            'exit_code': -1,
            'duration_ms': duration_ms,
            'stdout': '',
            'stderr': 'TIMEOUT',
        }

    except Exception as e:
        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        logger.error(f"Gate {gate_name} failed with exception: {e}")

        return {
            'gate': gate_name,
            'success': False,
            'exit_code': -2,
            'duration_ms': duration_ms,
            'stdout': '',
            'stderr': str(e),
        }


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Run all quality gates for a family',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument('--family', '-f', type=str, required=True,
                        help='Family identifier')
    parser.add_argument('--max-examples', type=int, default=None,
                        help='Maximum examples to process per gate')
    parser.add_argument('--dry-run', action='store_true',
                        help='Dry-run mode (no writes)')
    parser.add_argument('--deterministic', action='store_true',
                        help='Enable deterministic mode')
    parser.add_argument('--seed', type=int, default=None,
                        help='Random seed for deterministic runs')
    parser.add_argument('--allow-md-write', action='store_true',
                        help='Allow markdown file writes')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Verbose output')
    parser.add_argument('--output', '-o', type=str, default=None,
                        help='Output JSON file for results')

    args = parser.parse_args()

    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    # Use sys.executable for all subprocess calls (Windows-safe)
    python_exe = sys.executable
    logger.info(f"Using Python executable: {python_exe}")

    # Define gate sequence
    gates = [
        'scan',
        'extract',
        'compile-verify',
        'compile-fix',
        'runtime-verify',
        'runtime-fix',
        'md-update',
        'final-review',
    ]

    logger.info(f"Running {len(gates)} gates for family: {args.family}")
    logger.info(f"Options: max_examples={args.max_examples}, dry_run={args.dry_run}, "
                f"deterministic={args.deterministic}, seed={args.seed}")

    results = []
    failed_count = 0

    for gate in gates:
        result = run_gate(
            gate_name=gate,
            family=args.family,
            python_exe=python_exe,
            max_examples=args.max_examples,
            dry_run=args.dry_run,
            deterministic=args.deterministic,
            seed=args.seed,
            allow_md_write=args.allow_md_write,
        )

        results.append(result)

        if not result['success']:
            failed_count += 1
            logger.warning(f"Gate {gate} failed, continuing to next gate...")

    # Summary
    total_duration_ms = sum(r['duration_ms'] for r in results)
    success_count = len(results) - failed_count

    logger.info("")
    logger.info("=" * 80)
    logger.info("GATE RUN SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Family: {args.family}")
    logger.info(f"Total gates: {len(results)}")
    logger.info(f"Succeeded: {success_count}")
    logger.info(f"Failed: {failed_count}")
    logger.info(f"Total duration: {total_duration_ms}ms ({total_duration_ms / 1000:.1f}s)")
    logger.info("")

    for result in results:
        status = "OK" if result['success'] else "FAIL"
        logger.info(f"  [{status:4}] {result['gate']:20} {result['duration_ms']:>8}ms")

    logger.info("=" * 80)

    # Save results if output specified
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        summary = {
            'family': args.family,
            'timestamp': datetime.utcnow().isoformat(),
            'total_gates': len(results),
            'succeeded': success_count,
            'failed': failed_count,
            'total_duration_ms': total_duration_ms,
            'gates': results,
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)

        logger.info(f"Results saved to: {output_path}")

    # Exit with failure if any gate failed
    return 0 if failed_count == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
