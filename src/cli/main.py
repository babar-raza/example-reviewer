"""
CLI for Example Reviewer Pipeline.
Provides command-line interface for all pipeline operations.
"""

import argparse
import json
import logging
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

# Fix Windows cp1252 encoding issues with Unicode in log messages
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from ..mcp_tools.tools import ExampleReviewerTools, ToolResult


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for CLI.

    Uses JSON-structured logging when available, falls back to plain text.
    """
    level = logging.DEBUG if verbose else logging.INFO
    try:
        from ..core.logging_config import setup_structured_logging
        setup_structured_logging(level=level)
    except Exception:
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler(sys.stdout)]
        )


def is_risky_path(path: Path) -> Tuple[bool, str]:
    """
    Check if a path is in a risky location for SQLite (OneDrive or DrvFS).

    Args:
        path: Path to check

    Returns:
        Tuple of (is_risky, reason)
    """
    path_str = str(path.resolve())

    # Check for OneDrive
    if 'OneDrive' in path_str or 'onedrive' in path_str.lower():
        return True, "OneDrive"

    # Check for WSL DrvFS (/mnt/c, /mnt/d, etc.)
    if platform.system() == 'Linux' and path_str.startswith('/mnt/'):
        return True, "WSL DrvFS"

    return False, ""


def resolve_safe_workspace(safe_root: Optional[str] = None) -> Path:
    """
    Resolve safe workspace directory outside OneDrive/DrvFS.

    Args:
        safe_root: Optional override for safe root directory

    Returns:
        Path to safe workspace root
    """
    if safe_root:
        return Path(safe_root).resolve()

    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')

    if platform.system() == 'Windows':
        # Windows: Use %LOCALAPPDATA%\ExampleReviewer\workspaces\<timestamp>
        local_appdata = os.environ.get('LOCALAPPDATA')
        if not local_appdata:
            # Fallback to %USERPROFILE%\AppData\Local
            user_profile = os.environ.get('USERPROFILE', str(Path.home()))
            local_appdata = str(Path(user_profile) / 'AppData' / 'Local')

        return Path(local_appdata) / 'ExampleReviewer' / 'workspaces' / timestamp
    else:
        # Linux/WSL: Use ~/.cache/example_reviewer/workspaces/<timestamp>
        cache_dir = os.environ.get('XDG_CACHE_HOME')
        if not cache_dir:
            cache_dir = str(Path.home() / '.cache')

        return Path(cache_dir) / 'example_reviewer' / 'workspaces' / timestamp


def setup_safe_workspace(safe_root: Path, verbose: bool = False) -> Tuple[Path, Path, Path]:
    """
    Set up safe workspace directory structure.

    Creates:
    - <safe_root>/db/
    - <safe_root>/artifacts/
    - <safe_root>/workspace/

    Args:
        safe_root: Safe workspace root directory
        verbose: Enable verbose output

    Returns:
        Tuple of (db_dir, artifacts_dir, workspace_dir)
    """
    db_dir = safe_root / 'db'
    artifacts_dir = safe_root / 'artifacts'
    workspace_dir = safe_root / 'workspace'

    # Create directories
    db_dir.mkdir(parents=True, exist_ok=True)
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    workspace_dir.mkdir(parents=True, exist_ok=True)

    if verbose:
        print(f"[Safe Workspace] Created directory structure at: {safe_root}")
        print(f"  - DB directory: {db_dir}")
        print(f"  - Artifacts directory: {artifacts_dir}")
        print(f"  - Workspace directory: {workspace_dir}")

    return db_dir, artifacts_dir, workspace_dir


def check_and_warn_risky_paths(db_path: Path, workspace_dir: Path, verbose: bool = False) -> None:
    """
    Check if paths are in risky locations and print warnings.

    Args:
        db_path: Database file path
        workspace_dir: Workspace directory path
        verbose: Enable verbose output
    """
    # Check DB path
    db_risky, db_reason = is_risky_path(db_path)
    workspace_risky, workspace_reason = is_risky_path(workspace_dir)

    if db_risky or workspace_risky:
        print("\n" + "=" * 80)
        print("WARNING: SQLite Locking Risk Detected")
        print("=" * 80)

        if db_risky:
            print(f"\nDatabase path is on {db_reason}:")
            print(f"  {db_path}")

        if workspace_risky:
            print(f"\nWorkspace directory is on {workspace_reason}:")
            print(f"  {workspace_dir}")

        print("\nSQLite on OneDrive/DrvFS can cause database locking and deadlocks.")
        print("This may result in 'database is locked' errors during pipeline execution.")
        print("\nRECOMMENDATION: Use --safe-workspace flag to avoid these issues.")
        print("  Example: python -m src.cli.main run --family zip --safe-workspace")
        print("=" * 80)
        print()


def print_result(result: ToolResult, json_output: bool = False) -> None:
    """Print tool result to stdout."""
    if json_output:
        print(result.to_json())
    else:
        if result.success:
            print("[OK] Success")
            # Print run_id in machine-parseable format if present
            if result.data and 'run_id' in result.data:
                print(f"RUN_ID: {result.data['run_id']}")
            if result.data:
                for key, value in result.data.items():
                    if isinstance(value, (dict, list)):
                        print(f"  {key}:")
                        if isinstance(value, list):
                            for item in value[:10]:
                                print(f"    - {item}")
                            if len(value) > 10:
                                print(f"    ... and {len(value) - 10} more")
                        else:
                            for k, v in value.items():
                                print(f"    {k}: {v}")
                    else:
                        print(f"  {key}: {value}")
        else:
            print(f"[FAIL] Failed: {result.error}")


def clean_vector_db(args) -> ToolResult:
    """
    Clean high-drift examples from vector DB.

    NEW (ID-05): CLI command to remove drifted examples that may cause contagion.
    """
    from ..core.database import Database
    from ..services.vector_db_service import VectorDBService
    from ..core.config import ConfigurationManager

    try:
        # Initialize database and config
        db = Database(Path(args.db_path))
        config_manager = ConfigurationManager(Path(args.config_dir))
        global_config = config_manager.load_global_config()

        # Initialize vector DB service
        vector_db = VectorDBService(
            persist_directory=global_config.vector_db.persist_directory,
            embedding_model=global_config.vector_db.embedding_model,
            enabled=global_config.vector_db.enabled,
        )

        if not vector_db.is_available():
            return ToolResult(
                success=False,
                error="Vector DB not available (disabled or missing dependencies)"
            )

        # Clean high-drift examples
        removed = vector_db.clean_high_drift(
            family=args.family,
            max_drift=args.max_drift
        )

        return ToolResult(
            success=True,
            data={
                'family': args.family,
                'max_drift': args.max_drift,
                'removed_count': removed,
                'message': f"Removed {removed} high-drift examples from vector DB"
            }
        )

    except Exception as e:
        return ToolResult(
            success=False,
            error=f"Failed to clean vector DB: {str(e)}"
        )


def visualize_drift(args) -> ToolResult:
    """
    Visualize drift distribution for a family.

    NEW (ID-06): CLI command to show drift metrics and distribution.
    """
    from ..core.database import Database
    from ..core.telemetry import export_drift_metrics

    try:
        # Initialize database
        db = Database(Path(args.db_path))

        # Get drift metrics
        metrics = export_drift_metrics(db, args.family)

        if args.format == 'json':
            # JSON output
            return ToolResult(
                success=True,
                data=metrics
            )
        else:
            # ASCII output
            output = _render_drift_visualization(metrics)
            print(output)

            return ToolResult(
                success=True,
                data=metrics
            )

    except Exception as e:
        return ToolResult(
            success=False,
            error=f"Failed to visualize drift: {str(e)}"
        )


def show_drift_trends(args) -> ToolResult:
    """
    Show drift trends over recent runs.

    NEW (ID-06): CLI command to analyze drift evolution.
    """
    from ..core.database import Database
    from ..core.telemetry import get_drift_trends

    try:
        # Initialize database
        db = Database(Path(args.db_path))

        # Get trends
        trends = get_drift_trends(db, args.family, args.last_n_runs)

        # Render output
        output = _render_drift_trends(trends, args.last_n_runs)
        print(output)

        return ToolResult(
            success=True,
            data=trends
        )

    except Exception as e:
        return ToolResult(
            success=False,
            error=f"Failed to get drift trends: {str(e)}"
        )


def review_queue(args) -> ToolResult:
    """
    List examples requiring human review.

    NEW (Track 2: D.4): CLI command to show NEEDS_REVIEW queue.
    """
    from ..core.database import Database

    try:
        # Initialize database
        db = Database(Path(args.db_path))

        # Get NEEDS_REVIEW examples
        examples = db.get_needs_review_examples(
            family=args.family,
            limit=args.limit
        )

        if not examples:
            print("\nNo examples in review queue.")
            if args.family:
                print(f"Family: {args.family}")
            return ToolResult(
                success=True,
                data={'count': 0, 'examples': []}
            )

        # Render output
        output = _render_review_queue(examples, args.show_code)
        print(output)

        return ToolResult(
            success=True,
            data={
                'count': len(examples),
                'examples': [
                    {
                        'example_id': ex.example_id,
                        'file_path': ex.file_path,
                        'status': ex.status.value,
                        'escalation_reason': ex.escalation_reason,
                        'failure_reason': ex.failure_reason,
                    }
                    for ex in examples
                ]
            }
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return ToolResult(
            success=False,
            error=f"Failed to get review queue: {str(e)}"
        )


def _render_drift_visualization(metrics: dict) -> str:
    """
    Render ASCII visualization of drift distribution.

    Args:
        metrics: Drift metrics dictionary

    Returns:
        ASCII art string
    """
    lines = []
    lines.append(f"Drift Distribution (family: {metrics['family']})")
    lines.append("=" * len(lines[0]))
    lines.append("")

    # Render histogram
    distribution = metrics.get('drift_distribution', {})
    if distribution:
        # Find max count for scaling
        max_count = max(distribution.values()) if distribution.values() else 1
        bar_width = 50

        for label in ['0.0-0.1', '0.1-0.2', '0.2-0.3', '0.3-0.4',
                      '0.4-0.5', '0.5-0.6', '0.6-0.7', '0.7+']:
            count = distribution.get(label, 0)
            if max_count > 0:
                bar_len = int((count / max_count) * bar_width)
            else:
                bar_len = 0
            bar = '█' * bar_len
            lines.append(f"{label:10} {bar} ({count})")

    lines.append("")

    # Render summary statistics
    lines.append(f"Avg drift: {metrics.get('avg_drift', 0.0):.2f}")
    lines.append(f"Median drift: {metrics.get('median_drift', 0.0):.2f}")
    lines.append(f"P95 drift: {metrics.get('p95_drift', 0.0):.2f}")
    lines.append(f"Max drift: {metrics.get('max_drift', 0.0):.2f}")
    lines.append(f"Total examples: {metrics.get('count', 0)}")

    return '\n'.join(lines)


def _render_review_queue(examples: list, show_code: bool = False) -> str:
    """
    Render review queue as formatted text.

    Args:
        examples: List of ExampleRecord instances
        show_code: Whether to include code snippets

    Returns:
        Formatted string
    """
    lines = []
    lines.append("\n" + "=" * 80)
    lines.append(f"REVIEW QUEUE - {len(examples)} Example(s) Requiring Human Review")
    lines.append("=" * 80)
    lines.append("")

    for idx, example in enumerate(examples, 1):
        lines.append(f"[{idx}] {example.file_path}")
        lines.append(f"    Example ID: {example.example_id[:16]}...")
        lines.append(f"    Status: {example.status.value}")

        if example.escalation_reason:
            lines.append(f"    Escalation Reason: {example.escalation_reason}")

        if example.failure_reason:
            lines.append(f"    Failure Reason: {example.failure_reason}")

        if example.location:
            lines.append(f"    Location: Block {example.location.block_index}, Lines {example.location.start_line}-{example.location.end_line}")

        if show_code and example.current_code:
            lines.append("    Code Preview:")
            code_lines = example.current_code.split('\n')[:10]
            for code_line in code_lines:
                lines.append(f"      {code_line}")
            if len(example.current_code.split('\n')) > 10:
                lines.append("      ...")

        lines.append("")

    lines.append("=" * 80)
    lines.append(f"Total: {len(examples)} example(s)")
    lines.append("")

    return '\n'.join(lines)


def telemetry_verify(args) -> ToolResult:
    """
    Verify telemetry API can read run data without "database is locked" errors.

    Telemetry investigation command: Retries on database locked errors with exponential backoff.
    """
    import time
    import httpx

    run_id = args.run_id
    telemetry_url = args.telemetry_url.rstrip('/')
    max_retries = args.max_retries
    retry_delay = args.retry_delay

    print(f"\n[Telemetry Verify] Verifying run {run_id}")
    print(f"  Telemetry API: {telemetry_url}")
    print(f"  Max retries: {max_retries}")
    print(f"  Initial retry delay: {retry_delay}s")
    print("=" * 80)

    # Build API endpoint URL
    api_url = f"{telemetry_url}/api/v1/runs/{run_id}"

    attempt = 0
    current_delay = retry_delay
    last_error = None

    while attempt <= max_retries:
        try:
            print(f"\n[Attempt {attempt + 1}/{max_retries + 1}] Fetching {api_url}")

            with httpx.Client(timeout=30.0) as client:
                response = client.get(api_url)

                if response.status_code == 200:
                    data = response.json()
                    print(f"\n[SUCCESS] Retrieved run data successfully")
                    print(f"  Status code: {response.status_code}")
                    print(f"  Response size: {len(response.text)} bytes")
                    print(f"  Run ID: {data.get('run_id', 'N/A')}")
                    print(f"  Status: {data.get('status', 'N/A')}")
                    print(f"  Product: {data.get('product', 'N/A')}")

                    if 'db_path' in data:
                        print(f"  DB Path: {data['db_path']}")

                    print("=" * 80)

                    return ToolResult(
                        success=True,
                        data={
                            'run_id': run_id,
                            'api_url': api_url,
                            'attempts': attempt + 1,
                            'response': data,
                        }
                    )
                elif response.status_code == 404:
                    print(f"[ERROR] Run not found: {run_id}")
                    return ToolResult(
                        success=False,
                        error=f"Run {run_id} not found in telemetry API (404)"
                    )
                else:
                    error_text = response.text[:500]
                    print(f"[ERROR] HTTP {response.status_code}: {error_text}")

                    # Check if error message indicates database lock
                    if 'database is locked' in error_text.lower():
                        last_error = f"database is locked (HTTP {response.status_code})"
                        print(f"  Database locked, retrying in {current_delay:.1f}s...")
                        time.sleep(current_delay)
                        current_delay *= 2  # Exponential backoff
                        attempt += 1
                        continue
                    else:
                        return ToolResult(
                            success=False,
                            error=f"HTTP {response.status_code}: {error_text}"
                        )

        except httpx.TimeoutException:
            last_error = "Request timeout"
            print(f"[ERROR] Request timeout, retrying in {current_delay:.1f}s...")
            time.sleep(current_delay)
            current_delay *= 2
            attempt += 1
            continue

        except httpx.ConnectError as e:
            last_error = f"Connection error: {str(e)}"
            print(f"[ERROR] {last_error}")
            return ToolResult(
                success=False,
                error=f"Cannot connect to telemetry API at {telemetry_url}: {str(e)}"
            )

        except Exception as e:
            last_error = str(e)
            print(f"[ERROR] Unexpected error: {last_error}")
            print(f"  Retrying in {current_delay:.1f}s...")
            time.sleep(current_delay)
            current_delay *= 2
            attempt += 1
            continue

    # Max retries exceeded
    print(f"\n[FAIL] Failed after {max_retries + 1} attempts")
    print(f"  Last error: {last_error}")
    print("=" * 80)

    return ToolResult(
        success=False,
        error=f"Failed after {max_retries + 1} attempts. Last error: {last_error}"
    )


def _render_drift_trends(trends: dict, n_runs: int) -> str:
    """
    Render ASCII visualization of drift trends.

    Args:
        trends: Drift trends dictionary
        n_runs: Number of runs requested

    Returns:
        ASCII art string
    """
    lines = []
    lines.append(f"Drift Trends (family: {trends['family']}, last {n_runs} runs)")
    lines.append("=" * len(lines[0]))
    lines.append("")

    runs = trends.get('runs', [])
    if not runs:
        lines.append("No runs found with drift data.")
        return '\n'.join(lines)

    # Render run-by-run data
    for i, run in enumerate(runs):
        run_num = i + 1
        date = run.get('date', 'unknown')
        avg_drift = run.get('avg_drift', 0.0)
        max_drift = run.get('max_drift', 0.0)

        # Determine trend arrow
        arrow = ''
        if i > 0:
            prev_avg = runs[i - 1].get('avg_drift', 0.0)
            if avg_drift < prev_avg:
                arrow = '  v'
            elif avg_drift > prev_avg:
                arrow = '  ^'
            else:
                arrow = '  ='

        lines.append(f"Run {run_num} ({date}): Avg {avg_drift:.2f}, Max {max_drift:.2f}{arrow}")

    lines.append("")

    # Render overall trend
    overall = trends.get('overall_trend', {})
    direction = overall.get('direction', 'stable')
    percentage = overall.get('percentage', 0.0)

    if direction == 'down':
        trend_text = f"{abs(percentage):.0f}% reduction in avg drift"
    elif direction == 'up':
        trend_text = f"{abs(percentage):.0f}% increase in avg drift"
    else:
        trend_text = "stable (no significant change)"

    lines.append(f"Overall trend: {trend_text}")

    return '\n'.join(lines)


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog='cli',
        description='Example Reviewer Pipeline CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    # Global options
    parser.add_argument('--config-dir', type=str, default='config/families',
                        help='Path to family config directory')
    parser.add_argument('--db-path', type=str, default='data/example_reviewer.db',
                        help='Path to database file')
    parser.add_argument('--prod-db-path', type=str, default=None,
                        help='Path to production database (enables dual-database mode)')
    parser.add_argument('--workspace-dir', type=str, default='workspace',
                        help='Path to workspace directory')
    parser.add_argument('--artifacts-dir', type=str, default='artifacts',
                        help='Path to artifacts directory')
    parser.add_argument('--use-workspace-copy', '--workspace-copy', action='store_true',
                        help='Enable workspace copy mode (required for tests/fixtures/content/ writes)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose output')
    parser.add_argument('--json', action='store_true',
                        help='Output results as JSON')
    parser.add_argument('--deterministic', action='store_true',
                        help='Enable deterministic mode (sets temp=0, seed if missing, deterministic_mode=true)')
    parser.add_argument('--seed', type=int, default=None,
                        help='Set explicit random seed for reproducibility')

    # Safe workspace mode (Task 1A: SQLite locking hardening)
    parser.add_argument('--safe-workspace', action='store_true',
                        help='Use safe workspace outside OneDrive/DrvFS to prevent SQLite locking issues')
    parser.add_argument('--safe-root', type=str, default=None,
                        help='Override safe workspace root directory (default: ~/.cache/example_reviewer on Linux, %%LOCALAPPDATA%%\\ExampleReviewer on Windows)')

    # SQLite configuration (Task 2A: SQLite locking hardening)
    parser.add_argument('--sqlite-busy-timeout-ms', type=int, default=120000,
                        help='SQLite busy timeout in milliseconds (default: 120000)')
    parser.add_argument('--sqlite-wal', dest='sqlite_wal', action='store_true', default=True,
                        help='Enable SQLite WAL mode (default: enabled)')
    parser.add_argument('--no-sqlite-wal', dest='sqlite_wal', action='store_false',
                        help='Disable SQLite WAL mode (not recommended)')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Scan command
    scan_parser = subparsers.add_parser('scan', help='Scan for markdown files')
    scan_parser.add_argument('--family', '-f', type=str, help='Family identifier')
    scan_parser.add_argument('--directory', '-d', type=str, help='Directory to scan')
    scan_parser.add_argument('--max-files', type=int, help='Maximum files to scan')
    scan_parser.add_argument('--content-roots', nargs='+', metavar='PATH',
                             help='Override content_roots from family config (space-separated paths)')

    # Extract command
    extract_parser = subparsers.add_parser('extract', help='Extract code examples')
    extract_parser.add_argument('--family', '-f', type=str, required=True,
                                help='Family identifier')
    extract_parser.add_argument('--max-files', type=int, help='Maximum files to process')
    extract_parser.add_argument('--content-roots', nargs='+', metavar='PATH',
                                help='Override content_roots from family config (space-separated paths)')
    
    # Compile verify command
    compile_verify_parser = subparsers.add_parser('compile-verify',
                                                   help='Compile and verify examples')
    compile_verify_parser.add_argument('--family', '-f', type=str, required=True,
                                        help='Family identifier')
    compile_verify_parser.add_argument('--max-examples', type=int,
                                        help='Maximum examples to verify')
    
    # Compile fix command
    compile_fix_parser = subparsers.add_parser('compile-fix',
                                                help='Fix compilation errors with LLM')
    compile_fix_parser.add_argument('--family', '-f', type=str, required=True,
                                     help='Family identifier')
    compile_fix_parser.add_argument('--max-examples', type=int,
                                     help='Maximum examples to fix')
    
    # Runtime verify command
    runtime_verify_parser = subparsers.add_parser('runtime-verify',
                                                   help='Execute and verify runtime')
    runtime_verify_parser.add_argument('--family', '-f', type=str, required=True,
                                        help='Family identifier')
    runtime_verify_parser.add_argument('--max-examples', type=int,
                                        help='Maximum examples to verify')

    # Runtime fix command
    runtime_fix_parser = subparsers.add_parser('runtime-fix',
                                                help='Fix runtime errors with LLM')
    runtime_fix_parser.add_argument('--family', '-f', type=str, required=True,
                                     help='Family identifier')
    runtime_fix_parser.add_argument('--max-examples', type=int,
                                     help='Maximum examples to fix')

    # Markdown update command
    md_update_parser = subparsers.add_parser('md-update',
                                              help='Update markdown files')
    md_update_parser.add_argument('--family', '-f', type=str, required=True,
                                   help='Family identifier')
    md_update_parser.add_argument('--dry-run', action='store_true',
                                   help="Don't write changes")
    md_update_parser.add_argument('--allow-md-write', action='store_true',
                                   help='REQUIRED to write .md files (safety guard)')
    md_update_parser.add_argument('--audit-prose', action='store_true',
                                   help='Audit and correct adjacent prose for changed code blocks when LLM review is available')
    
    # Final review command
    final_review_parser = subparsers.add_parser('final-review',
                                                 help='Run final LLM review')
    final_review_parser.add_argument('--family', '-f', type=str, required=True,
                                      help='Family identifier')
    
    # Commit command
    commit_parser = subparsers.add_parser('commit', help='Commit changes to git')
    commit_parser.add_argument('--family', '-f', type=str, required=True,
                               help='Family identifier')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Get pipeline status')
    status_parser.add_argument('--family', '-f', type=str, help='Family identifier')
    
    # Run pipeline command
    run_parser = subparsers.add_parser('run', help='Run full pipeline')
    run_parser.add_argument('--family', '-f', type=str, required=False,
                            help='Family identifier (required unless --from-queue is set)')
    run_parser.add_argument('--from-queue', action='store_true',
                            help='Poll next work item from work_queue table instead of requiring --family')
    run_parser.add_argument('--max-examples', type=int,
                            help='Maximum examples to process')
    run_parser.add_argument('--skip-runtime', action='store_true',
                            help='Skip runtime verification')
    run_parser.add_argument('--skip-llm', '--skip-llm-fixes', dest='skip_llm', action='store_true',
                            help='Skip LLM-based fixing (compile-fix, runtime-fix, final-review phases)')
    run_parser.add_argument('--skip-llm-runtime-fixes', action='store_true',
                            help='Skip LLM fixes for runtime errors only (keeps compile-fix active)')

    # Strategy control flags (for experiments)
    run_parser.add_argument('--enable-transformers', action='store_true',
                            help='Enable enhanced code transformers (E2)')
    run_parser.add_argument('--enable-retrieval', action='store_true',
                            help='Enable vector DB retrieval (E3)')
    run_parser.add_argument('--enable-semantic-microfixes', action='store_true',
                            help='Enable semantic micro-fixes (E4)')
    run_parser.add_argument('--enable-substitution', action='store_true',
                            help='Enable example substitution')
    run_parser.add_argument('--enable-all-deterministic', action='store_true',
                            help='Enable ALL deterministic strategies (overrides individual flags)')
    run_parser.add_argument('--enable-learned-patterns', action='store_true',
                            help='Enable learned pattern fixes from auto-learn (E4.5)')

    run_parser.add_argument('--dry-run', action='store_true',
                            help="Don't write changes")
    run_parser.add_argument('--allow-md-write', action='store_true',
                            help='REQUIRED to write .md files (safety guard)')
    run_parser.add_argument('--commit', action='store_true',
                            help='Commit verified changes to git (overrides config)')
    run_parser.add_argument('--content-roots', nargs='+', metavar='PATH',
                            help='Override content_roots from family config (space-separated paths)')
    run_parser.add_argument('--section', metavar='NAME',
                            help='Run on a single named section from content_pattern (e.g. kb, blog, docs). '
                                 'Selects the matching content_root automatically.')
    run_parser.add_argument('--safe-workspace', action='store_true',
                            help='Use safe workspace outside OneDrive/DrvFS (same as top-level flag)')
    run_parser.add_argument('--files', nargs='+', metavar='PATH',
                            help='Run on specific .md files (space-separated paths). '
                                 'Bypasses content_roots discovery. Paths resolved to absolute.')
    run_parser.add_argument('--audit-prose', action='store_true',
                            help='Audit prose adjacent to updated code blocks when LLM review is available')

    validate_articles_parser = subparsers.add_parser('validate-articles',
                                                     help='Validate markdown article structure and optional prose/code alignment')
    validate_articles_parser.add_argument('--family', '-f', type=str, required=True,
                                          help='Family identifier')
    validate_articles_parser.add_argument('--files', nargs='+', metavar='PATH',
                                          help='Specific markdown files to validate. Paths resolved to absolute.')
    validate_articles_parser.add_argument('--content-roots', nargs='+', metavar='PATH',
                                          help='Override content_roots from family config (space-separated paths)')
    validate_articles_parser.add_argument('--audit-prose', action='store_true',
                                          help='Audit prose against adjacent code when LLM review is available')
    validate_articles_parser.add_argument('--format', choices=['text', 'json'], default='text',
                                          help='Output format (default: text)')

    # List families command
    list_parser = subparsers.add_parser('list-families',
                                         help='List available families')

    # Backfill command
    backfill_parser = subparsers.add_parser('backfill',
                                             help='Backfill missing context data')
    backfill_parser.add_argument('--family', '-f', type=str, required=True,
                                  help='Family identifier')
    backfill_parser.add_argument('--targets', '-t', type=str, nargs='+',
                                  help='Backfill targets (test_data, api_catalog, examples, examples_files, gist_source_code)')
    backfill_parser.add_argument('--force', action='store_true',
                                  help='Force re-download even if data exists')

    # Clean vector DB command (ID-05)
    clean_vector_db_parser = subparsers.add_parser('clean-vector-db',
                                                     help='Clean high-drift examples from vector DB')
    clean_vector_db_parser.add_argument('--family', '-f', type=str, required=True,
                                         help='Family identifier')
    clean_vector_db_parser.add_argument('--max-drift', type=float, default=0.3,
                                         help='Maximum drift score to keep (default: 0.3)')

    # Visualize drift command (ID-06)
    visualize_drift_parser = subparsers.add_parser('visualize-drift',
                                                     help='Visualize drift distribution for a family')
    visualize_drift_parser.add_argument('--family', '-f', type=str, required=True,
                                         help='Family identifier')
    visualize_drift_parser.add_argument('--format', type=str, default='ascii',
                                         choices=['ascii', 'json'],
                                         help='Output format (default: ascii)')

    # Drift trends command (ID-06)
    drift_trends_parser = subparsers.add_parser('drift-trends',
                                                  help='Show drift trends over recent runs')
    drift_trends_parser.add_argument('--family', '-f', type=str, required=True,
                                      help='Family identifier')
    drift_trends_parser.add_argument('--last-n-runs', type=int, default=10,
                                      help='Number of recent runs to analyze (default: 10)')

    # Review queue command (Track 2: D.4)
    review_queue_parser = subparsers.add_parser('review-queue',
                                                 help='List examples requiring human review')
    review_queue_parser.add_argument('--family', '-f', type=str,
                                      help='Family identifier (optional)')
    review_queue_parser.add_argument('--limit', type=int, default=50,
                                      help='Maximum items to show (default: 50)')
    review_queue_parser.add_argument('--show-code', action='store_true',
                                      help='Show code snippets for each item')

    # Telemetry verify command (Telemetry investigation)
    telemetry_verify_parser = subparsers.add_parser('telemetry-verify',
                                                      help='Verify telemetry API can read run data')
    telemetry_verify_parser.add_argument('--run-id', type=str, required=True,
                                          help='Run ID to verify')
    telemetry_verify_parser.add_argument('--telemetry-url', type=str,
                                          default='http://localhost:8765',
                                          help='Telemetry API base URL (default: http://localhost:8765)')
    telemetry_verify_parser.add_argument('--max-retries', type=int, default=10,
                                          help='Maximum retry attempts on "database is locked" (default: 10)')
    telemetry_verify_parser.add_argument('--retry-delay', type=float, default=1.0,
                                          help='Initial retry delay in seconds (default: 1.0)')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    setup_logging(args.verbose)

    # Task 1B: Handle safe workspace mode
    # --safe-workspace is accepted both as a top-level flag and on the run subcommand
    db_path = Path(args.db_path)
    workspace_dir = Path(args.workspace_dir)
    artifacts_dir = Path(args.artifacts_dir)

    if args.safe_workspace:
        # Resolve safe workspace directory
        safe_root = resolve_safe_workspace(args.safe_root)

        # Set up safe workspace structure
        db_dir, safe_artifacts_dir, safe_workspace_dir = setup_safe_workspace(
            safe_root, verbose=args.verbose
        )

        # Override paths
        db_path = db_dir / 'example_reviewer.db'
        artifacts_dir = safe_artifacts_dir
        workspace_dir = safe_workspace_dir

        # Print safe workspace info
        print("\n" + "=" * 80)
        print("SAFE WORKSPACE MODE ENABLED")
        print("=" * 80)
        print(f"\nSafe workspace root: {safe_root}")
        print(f"Database path: {db_path}")
        print(f"Artifacts directory: {artifacts_dir}")
        print(f"Workspace directory: {workspace_dir}")
        print("=" * 80)
        print()

        # Print structured output for harness parsing (Task 2: Phase-2 unblock)
        print(f"SAFE_WORKSPACE_ROOT: {safe_root}")
        print(f"DB_PATH: {db_path}")
        print(f"ARTIFACTS_DIR: {artifacts_dir}")
        print(f"WORKSPACE_DIR: {workspace_dir}")
        print()
    else:
        # Task 1C: Warn about risky paths when not using safe workspace
        check_and_warn_risky_paths(db_path, workspace_dir, verbose=args.verbose)

    # Build CLI overrides for config hash computation
    cli_overrides = {}
    if args.deterministic or args.seed is not None:
        cli_overrides['llm'] = {}

        if args.deterministic:
            cli_overrides['llm']['temperature'] = 0.0
            cli_overrides['llm']['deterministic_mode'] = True
            # Set default seed if not explicitly provided
            if args.seed is None:
                cli_overrides['llm']['seed'] = 42  # Default seed for deterministic mode
            else:
                cli_overrides['llm']['seed'] = args.seed
        elif args.seed is not None:
            # Seed provided without --deterministic
            cli_overrides['llm']['seed'] = args.seed

    # Initialize tools with CLI overrides
    prod_db_path = Path(args.prod_db_path) if args.prod_db_path else None
    tools = ExampleReviewerTools(
        config_dir=Path(args.config_dir),
        db_path=db_path,
        prod_db_path=prod_db_path,
        workspace_dir=workspace_dir,
        cli_overrides=cli_overrides,
        use_workspace_copy=getattr(args, 'use_workspace_copy', False),
        sqlite_config={
            'busy_timeout_ms': args.sqlite_busy_timeout_ms,
            'wal_enabled': args.sqlite_wal,
        },
    )
    
    # Execute command
    result = None
    
    if args.command == 'scan':
        result = tools.scan(
            family=args.family,
            directory=args.directory,
            max_files=args.max_files,
            content_roots=getattr(args, 'content_roots', None),
        )

    elif args.command == 'extract':
        result = tools.extract(
            family=args.family,
            max_files=args.max_files,
            content_roots=getattr(args, 'content_roots', None),
        )
    
    elif args.command == 'compile-verify':
        result = tools.compile_verify(
            family=args.family,
            max_examples=args.max_examples,
        )
    
    elif args.command == 'compile-fix':
        result = tools.compile_fix(
            family=args.family,
            max_examples=args.max_examples,
        )
    
    elif args.command == 'runtime-verify':
        result = tools.runtime_verify(
            family=args.family,
            max_examples=args.max_examples,
        )

    elif args.command == 'runtime-fix':
        result = tools.runtime_fix(
            family=args.family,
            max_examples=args.max_examples,
        )

    elif args.command == 'md-update':
        result = tools.md_update(
            family=args.family,
            dry_run=args.dry_run,
            allow_md_write=getattr(args, 'allow_md_write', False),
            audit_prose=getattr(args, 'audit_prose', False),
        )
    
    elif args.command == 'final-review':
        result = tools.final_review(family=args.family)
    
    elif args.command == 'commit':
        result = tools.commit(family=args.family)
    
    elif args.command == 'status':
        result = tools.status(family=args.family)
    
    elif args.command == 'run':
        # Resolve family: from --from-queue or from --family
        _queue_id: Optional[str] = None
        if getattr(args, 'from_queue', False):
            from ..core.database import Database as _Database  # type: ignore[import]
            _db = _Database(db_path)
            _work = _db.poll_next_work()
            if _work is None:
                print("Queue is empty. Nothing to run.")
                sys.exit(0)
            args.family = _work['family']
            _queue_id = _work['queue_id']
            print(f"[--from-queue] Claimed work item {_queue_id}: family={args.family} "
                  f"priority={_work['priority']} trigger={_work['trigger_source']}")
            if _work.get('max_examples'):
                args.max_examples = _work['max_examples']
            if _work.get('skip_llm'):
                args.skip_llm = True
        elif not args.family:
            print("error: --family / -f is required (or use --from-queue to pull from work_queue)")
            sys.exit(1)

        # Determine strategy configuration
        # Default: all strategies ENABLED (matching orchestrator's intent)
        # Individual flags are opt-in overrides; --enable-all-deterministic is a no-op (already default)
        has_any_flag = any([
            getattr(args, 'enable_transformers', False),
            getattr(args, 'enable_retrieval', False),
            getattr(args, 'enable_semantic_microfixes', False),
            getattr(args, 'enable_substitution', False),
            getattr(args, 'enable_learned_patterns', False),
        ])
        enable_all = getattr(args, 'enable_all_deterministic', False)
        # If no individual flags set, enable all by default
        default_enabled = not has_any_flag or enable_all
        strategy_config = {
            'enable_transformers': default_enabled or getattr(args, 'enable_transformers', False),
            'enable_retrieval': default_enabled or getattr(args, 'enable_retrieval', False),
            'enable_semantic_microfixes': default_enabled or getattr(args, 'enable_semantic_microfixes', False),
            'enable_substitution': default_enabled or getattr(args, 'enable_substitution', False),
            'enable_learned_patterns': default_enabled or getattr(args, 'enable_learned_patterns', False),
        }

        # Resolve --section into a positional content_roots list
        content_roots = getattr(args, 'content_roots', None)
        section = getattr(args, 'section', None)
        if section and not content_roots:
            # Load family config to look up the section's position and root
            try:
                family_cfg = tools.orchestrator.config_manager.load_family_config(args.family)
                if family_cfg.content_pattern and section in family_cfg.content_pattern:
                    pattern_keys = list(family_cfg.content_pattern.keys())
                    section_idx = pattern_keys.index(section)
                    if section_idx < len(family_cfg.content_roots):
                        # Build positional list: empty strings for preceding roots, real path at index
                        import os as _os
                        positional = []
                        for i, root in enumerate(family_cfg.content_roots):
                            if i == section_idx:
                                positional.append(_os.path.expandvars(root))
                            else:
                                positional.append('/nonexistent-section-skip')
                        content_roots = positional
                        print(f"[--section {section}] Using content root: {_os.path.expandvars(family_cfg.content_roots[section_idx])}")
                    else:
                        print(f"[--section {section}] WARNING: section index {section_idx} out of range for content_roots")
                else:
                    available = list(family_cfg.content_pattern.keys()) if family_cfg.content_pattern else []
                    print(f"[--section {section}] WARNING: section not found. Available: {available}")
            except Exception as e:
                print(f"[--section] WARNING: could not resolve section: {e}")

        # Resolve --files into absolute paths
        file_list = getattr(args, 'files', None)
        if file_list:
            import os as _os
            file_list = [_os.path.abspath(f) for f in file_list]
            missing = [f for f in file_list if not _os.path.exists(f)]
            if missing:
                print(f"[--files] WARNING: {len(missing)} file(s) not found: {missing}")

        result = tools.run_pipeline(
            family=args.family,
            max_examples=args.max_examples,
            skip_runtime=args.skip_runtime,
            skip_llm_fixes=args.skip_llm,
            skip_llm_runtime_fixes=getattr(args, 'skip_llm_runtime_fixes', False),
            dry_run=args.dry_run,
            allow_md_write=getattr(args, 'allow_md_write', False),
            allow_commit=getattr(args, 'commit', False),
            strategy_config=strategy_config,
            content_roots=content_roots,
            file_list=file_list,
            audit_prose=getattr(args, 'audit_prose', False),
        )

        if _queue_id is not None:
            _run_id = result.data.get('run_id') if result.data else None
            _db.complete_work(
                queue_id=_queue_id,
                run_id=_run_id,
                success=result.success,
                error=result.error if not result.success else None,
            )
            status_str = "completed" if result.success else "failed"
            print(f"[--from-queue] Work item {_queue_id} marked {status_str}")

    elif args.command == 'validate-articles':
        import os as _os
        # file_list: explicit files from --files flag (highest priority)
        file_list = getattr(args, 'files', None)
        # roots_override: content roots to pass to the tool layer (None = use family config)
        roots_override = getattr(args, 'content_roots', None)

        if file_list:
            # Resolve to absolute paths and deduplicate; keep as explicit file_list.
            file_list = list(dict.fromkeys(_os.path.abspath(f) for f in file_list))
            missing = [f for f in file_list if not _os.path.exists(f)]
            if missing:
                print(f"[--files] WARNING: {len(missing)} file(s) not found: {missing}")
            roots_override = None  # file_list takes precedence; ignore root override
        elif roots_override:
            # --content-roots given but no --files: collect ALL .md files from every
            # supplied root so the validator sees them together for cross-root duplicate
            # detection.  Non-existent roots are skipped with a warning.
            candidate_roots = [_os.path.expandvars(r) for r in roots_override]
            all_files_found: List[str] = []
            for root_dir in candidate_roots:
                if not _os.path.exists(root_dir):
                    print(f"[validate-articles] WARNING: Content root not found, skipping: {root_dir}")
                    continue
                all_files_found.extend(str(p) for p in Path(root_dir).rglob("*.md"))
            if all_files_found:
                # Deduplicate (same file reachable via multiple roots) and resolve.
                file_list = list(dict.fromkeys(str(Path(f).resolve()) for f in all_files_found))
                print(f"[validate-articles] Collected {len(file_list)} file(s) from {len(candidate_roots)} root(s)")
                roots_override = None  # already expanded into file_list; tool needs no override
            else:
                # All roots missing or empty — pass an empty roots list so the tool
                # reports 0 files checked rather than falling back to family config roots.
                print("[validate-articles] WARNING: No files found in any content root — reporting 0 files checked")
                file_list = None
                roots_override = []  # empty list signals: skip family config roots too
        # When neither --files nor --content-roots is given, roots_override stays None
        # and the tool uses family config content_roots via _find_markdown_files (which
        # already iterates all roots, skips missing ones, and deduplicates).

        if getattr(args, 'format', 'text') == 'json':
            args.json = True

        result = tools.validate_articles(
            family=args.family,
            file_list=file_list,
            content_roots=roots_override,
            audit_prose=getattr(args, 'audit_prose', False),
        )
    
    elif args.command == 'list-families':
        families = tools.orchestrator.config_manager.list_families()
        result = ToolResult(
            success=True,
            data={'families': families}
        )

    elif args.command == 'backfill':
        result = tools.backfill(
            family=args.family,
            targets=args.targets,
            force=args.force,
        )

    elif args.command == 'clean-vector-db':
        result = clean_vector_db(args)

    elif args.command == 'visualize-drift':
        result = visualize_drift(args)

    elif args.command == 'drift-trends':
        result = show_drift_trends(args)

    elif args.command == 'review-queue':
        result = review_queue(args)

    elif args.command == 'telemetry-verify':
        result = telemetry_verify(args)

    if result:
        print_result(result, args.json)
        return 0 if result.success else 1

    return 1


if __name__ == '__main__':
    sys.exit(main())
