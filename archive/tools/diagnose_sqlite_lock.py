"""
SQLite Lock Diagnostic Tool.

Task 4: Add lock diagnostics so future failures are actionable.

This tool helps diagnose SQLite locking issues by:
- Detecting risky filesystem locations (OneDrive, DrvFS)
- Checking SQLite PRAGMA settings
- Running stress tests with detailed error reporting
- Providing actionable recommendations
"""

import argparse
import os
import platform
import sqlite3
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Tuple, List, Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.database import Database


def detect_filesystem_risk(path: Path) -> Tuple[str, str, List[str]]:
    """
    Detect if path is on a risky filesystem for SQLite.

    Args:
        path: Path to check

    Returns:
        Tuple of (risk_level, reason, recommendations)
    """
    path_str = str(path.resolve())
    recommendations = []

    # Check for OneDrive
    if 'OneDrive' in path_str or 'onedrive' in path_str.lower():
        return (
            "HIGH",
            "OneDrive",
            [
                "OneDrive syncing can cause SQLite database corruption and locking",
                "Use --safe-workspace flag to move DB outside OneDrive",
                "Or disable OneDrive syncing for this directory",
            ]
        )

    # Check for WSL DrvFS
    if platform.system() == 'Linux' and path_str.startswith('/mnt/'):
        return (
            "HIGH",
            "WSL DrvFS (/mnt/* paths)",
            [
                "WSL DrvFS has known issues with file locking and SQLite",
                "Use --safe-workspace flag to use native Linux filesystem",
                "Or move repository to native WSL filesystem (e.g., ~/projects/)",
            ]
        )

    # Check for network drives
    if platform.system() == 'Windows':
        if path_str.startswith('\\\\') or (len(path_str) > 1 and path_str[1] == ':'):
            drive_letter = path_str[0]
            try:
                import subprocess
                result = subprocess.run(
                    ['net', 'use', f'{drive_letter}:'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if 'Remote name' in result.stdout or 'Network' in result.stdout:
                    return (
                        "HIGH",
                        "Network Drive",
                        [
                            "Network drives can cause SQLite locking issues",
                            "Use --safe-workspace to move DB to local disk",
                        ]
                    )
            except Exception:
                pass

    return "LOW", "Local filesystem", []


def check_db_pragmas(db_path: Path, verbose: bool = False) -> Dict[str, Any]:
    """
    Check SQLite PRAGMA settings for a database.

    Args:
        db_path: Path to database file
        verbose: Enable verbose output

    Returns:
        Dictionary of pragma values
    """
    if not db_path.exists():
        return {"error": "Database file does not exist"}

    try:
        conn = sqlite3.connect(str(db_path), timeout=5.0)
        pragmas = {}

        # Query all relevant pragmas
        pragmas['journal_mode'] = conn.execute("PRAGMA journal_mode").fetchone()[0]
        pragmas['synchronous'] = conn.execute("PRAGMA synchronous").fetchone()[0]
        pragmas['temp_store'] = conn.execute("PRAGMA temp_store").fetchone()[0]
        pragmas['busy_timeout'] = conn.execute("PRAGMA busy_timeout").fetchone()[0]
        pragmas['foreign_keys'] = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        pragmas['page_size'] = conn.execute("PRAGMA page_size").fetchone()[0]
        pragmas['cache_size'] = conn.execute("PRAGMA cache_size").fetchone()[0]

        # Get WAL checkpoint info if in WAL mode
        if pragmas['journal_mode'].lower() == 'wal':
            try:
                wal_checkpoint = conn.execute("PRAGMA wal_checkpoint(PASSIVE)").fetchone()
                pragmas['wal_checkpoint'] = wal_checkpoint
            except Exception as e:
                pragmas['wal_checkpoint_error'] = str(e)

        conn.close()
        return pragmas

    except Exception as e:
        return {"error": str(e)}


def run_write_stress_test(
    db_path: Path,
    num_threads: int = 8,
    writes_per_thread: int = 50,
    verbose: bool = False
) -> Dict[str, Any]:
    """
    Run a write stress test to detect locking issues.

    Args:
        db_path: Path to database file
        num_threads: Number of concurrent threads
        writes_per_thread: Number of writes per thread
        verbose: Enable verbose output

    Returns:
        Test results dictionary
    """
    results = {
        'num_threads': num_threads,
        'writes_per_thread': writes_per_thread,
        'total_writes': num_threads * writes_per_thread,
        'errors': [],
        'success': False,
        'duration_seconds': 0.0,
    }

    try:
        # Initialize database
        db = Database(db_path=db_path, busy_timeout_ms=120000, wal_enabled=True)
        db.initialize_schema()

        # Create test run
        run_id = db.create_run(family="stress_test", current_phase="stress_test")

        # Thread worker
        def write_worker(thread_id: int, errors: list):
            """Write examples from a thread."""
            from src.core.models import ExampleRecord, ExampleStatus, SourceType, Location

            for i in range(writes_per_thread):
                try:
                    example = ExampleRecord(
                        family="stress_test",
                        file_path=f"stress_test_t{thread_id}_i{i}.md",
                        original_code=f"// Thread {thread_id}, Write {i}",
                        source_type=SourceType.INLINE,
                        language="csharp",
                        location=Location(block_index=0, start_line=1, end_line=2, anchor=""),
                        status=ExampleStatus.DISCOVERED,
                    )
                    db.save_example(example, run_id=run_id)

                    if verbose and i % 10 == 0:
                        print(f"  [Thread {thread_id}] Completed {i}/{writes_per_thread} writes")

                except sqlite3.OperationalError as e:
                    if 'locked' in str(e).lower():
                        errors.append({
                            'thread_id': thread_id,
                            'write_index': i,
                            'error_type': 'database_locked',
                            'error_message': str(e),
                            'timestamp': datetime.utcnow().isoformat(),
                        })
                    else:
                        errors.append({
                            'thread_id': thread_id,
                            'write_index': i,
                            'error_type': 'operational_error',
                            'error_message': str(e),
                            'timestamp': datetime.utcnow().isoformat(),
                        })
                except Exception as e:
                    errors.append({
                        'thread_id': thread_id,
                        'write_index': i,
                        'error_type': type(e).__name__,
                        'error_message': str(e),
                        'timestamp': datetime.utcnow().isoformat(),
                    })

        # Run stress test
        errors = []
        threads = []
        start_time = time.time()

        for thread_id in range(num_threads):
            thread = threading.Thread(target=write_worker, args=(thread_id, errors))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        end_time = time.time()
        results['duration_seconds'] = end_time - start_time

        # Verify writes
        with db.get_connection() as conn:
            actual_count = conn.execute(
                "SELECT COUNT(*) FROM example_records WHERE family = ?",
                ("stress_test",)
            ).fetchone()[0]

        results['actual_writes'] = actual_count
        results['errors'] = errors
        results['success'] = len(errors) == 0 and actual_count == results['total_writes']

    except Exception as e:
        results['fatal_error'] = str(e)
        results['success'] = False

    return results


def print_report(
    db_path: Path,
    fs_risk: Tuple[str, str, List[str]],
    pragmas: Dict[str, Any],
    stress_results: Dict[str, Any],
    output_file: Path = None
) -> None:
    """Print diagnostic report."""
    lines = []

    lines.append("=" * 80)
    lines.append("SQLite Lock Diagnostic Report")
    lines.append("=" * 80)
    lines.append(f"Generated: {datetime.utcnow().isoformat()}")
    lines.append(f"Database: {db_path}")
    lines.append("")

    # Filesystem Risk
    lines.append("-" * 80)
    lines.append("Filesystem Risk Assessment")
    lines.append("-" * 80)
    risk_level, reason, recommendations = fs_risk
    lines.append(f"Risk Level: {risk_level}")
    lines.append(f"Reason: {reason}")
    if recommendations:
        lines.append("\nRecommendations:")
        for rec in recommendations:
            lines.append(f"  - {rec}")
    lines.append("")

    # PRAGMA Settings
    lines.append("-" * 80)
    lines.append("SQLite PRAGMA Settings")
    lines.append("-" * 80)
    if 'error' in pragmas:
        lines.append(f"ERROR: {pragmas['error']}")
    else:
        for key, value in pragmas.items():
            if key != 'wal_checkpoint' and not key.endswith('_error'):
                lines.append(f"  {key}: {value}")
        if 'wal_checkpoint' in pragmas:
            lines.append(f"  wal_checkpoint: {pragmas['wal_checkpoint']}")
        if 'wal_checkpoint_error' in pragmas:
            lines.append(f"  wal_checkpoint_error: {pragmas['wal_checkpoint_error']}")
    lines.append("")

    # Stress Test Results
    lines.append("-" * 80)
    lines.append("Write Stress Test Results")
    lines.append("-" * 80)
    lines.append(f"Threads: {stress_results.get('num_threads', 'N/A')}")
    lines.append(f"Writes per thread: {stress_results.get('writes_per_thread', 'N/A')}")
    lines.append(f"Total expected writes: {stress_results.get('total_writes', 'N/A')}")
    lines.append(f"Actual writes: {stress_results.get('actual_writes', 'N/A')}")
    lines.append(f"Duration: {stress_results.get('duration_seconds', 0):.2f} seconds")
    lines.append(f"Success: {'YES' if stress_results.get('success') else 'NO'}")

    if stress_results.get('errors'):
        lines.append(f"\nErrors detected: {len(stress_results['errors'])}")
        lines.append("\nError details:")
        for i, error in enumerate(stress_results['errors'][:10], 1):  # Show first 10
            lines.append(f"  [{i}] Thread {error['thread_id']}, Write {error['write_index']}")
            lines.append(f"      Type: {error['error_type']}")
            lines.append(f"      Message: {error['error_message']}")
            lines.append(f"      Time: {error['timestamp']}")
        if len(stress_results['errors']) > 10:
            lines.append(f"\n  ... and {len(stress_results['errors']) - 10} more errors")
    elif 'fatal_error' in stress_results:
        lines.append(f"\nFATAL ERROR: {stress_results['fatal_error']}")
    else:
        lines.append("\nNo errors detected!")

    lines.append("")
    lines.append("=" * 80)

    # Print to console
    report = "\n".join(lines)
    print(report)

    # Write to file if specified
    if output_file:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(report)
        print(f"\nReport saved to: {output_file}")


def main():
    """Main diagnostic entry point."""
    parser = argparse.ArgumentParser(
        description="Diagnose SQLite locking issues",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        '--db-path',
        type=str,
        default='data/example_reviewer.db',
        help='Path to database file (default: data/example_reviewer.db)',
    )
    parser.add_argument(
        '--stress-test',
        action='store_true',
        help='Run write stress test',
    )
    parser.add_argument(
        '--threads',
        type=int,
        default=8,
        help='Number of threads for stress test (default: 8)',
    )
    parser.add_argument(
        '--writes',
        type=int,
        default=50,
        help='Writes per thread for stress test (default: 50)',
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Output file path (default: reports/phase2_zip/<timestamp>/sqlite_diagnose.txt)',
    )
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Enable verbose output',
    )

    args = parser.parse_args()

    db_path = Path(args.db_path)

    # Detect filesystem risk
    print("Analyzing filesystem...")
    fs_risk = detect_filesystem_risk(db_path)

    # Check pragmas
    print("Checking SQLite PRAGMA settings...")
    pragmas = check_db_pragmas(db_path, verbose=args.verbose)

    # Run stress test if requested
    stress_results = {'skipped': True}
    if args.stress_test:
        print(f"\nRunning stress test ({args.threads} threads x {args.writes} writes)...")
        stress_results = run_write_stress_test(
            db_path=db_path,
            num_threads=args.threads,
            writes_per_thread=args.writes,
            verbose=args.verbose,
        )
        print("Stress test complete.")

    # Determine output file
    output_file = None
    if args.output:
        output_file = Path(args.output)
    elif args.stress_test:
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        output_file = Path(f"reports/phase2_zip/{timestamp}/sqlite_diagnose.txt")

    # Print report
    print("\n")
    print_report(db_path, fs_risk, pragmas, stress_results, output_file)

    # Exit with appropriate code
    if args.stress_test and not stress_results.get('success'):
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
