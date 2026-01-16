"""
CLI for Example Reviewer Pipeline.
Provides command-line interface for all pipeline operations.
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Optional

from ..mcp_tools.tools import ExampleReviewerTools, ToolResult


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for CLI."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )


def print_result(result: ToolResult, json_output: bool = False) -> None:
    """Print tool result to stdout."""
    if json_output:
        print(result.to_json())
    else:
        if result.success:
            print("[OK] Success")
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
                arrow = '  ↓'
            elif avg_drift > prev_avg:
                arrow = '  ↑'
            else:
                arrow = '  →'

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
        description='Example Reviewer Pipeline CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    # Global options
    parser.add_argument('--config-dir', type=str, default='config/families',
                        help='Path to family config directory')
    parser.add_argument('--db-path', type=str, default='data/example_reviewer.db',
                        help='Path to database file')
    parser.add_argument('--workspace-dir', type=str, default='workspace',
                        help='Path to workspace directory')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose output')
    parser.add_argument('--json', action='store_true',
                        help='Output results as JSON')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Scan command
    scan_parser = subparsers.add_parser('scan', help='Scan for markdown files')
    scan_parser.add_argument('--family', '-f', type=str, help='Family identifier')
    scan_parser.add_argument('--directory', '-d', type=str, help='Directory to scan')
    scan_parser.add_argument('--max-files', type=int, help='Maximum files to scan')
    
    # Extract command
    extract_parser = subparsers.add_parser('extract', help='Extract code examples')
    extract_parser.add_argument('--family', '-f', type=str, required=True,
                                help='Family identifier')
    extract_parser.add_argument('--max-files', type=int, help='Maximum files to process')
    
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
    run_parser.add_argument('--family', '-f', type=str, required=True,
                            help='Family identifier')
    run_parser.add_argument('--max-examples', type=int,
                            help='Maximum examples to process')
    run_parser.add_argument('--skip-runtime', action='store_true',
                            help='Skip runtime verification')
    run_parser.add_argument('--skip-llm', action='store_true',
                            help='Skip LLM-based fixing')
    run_parser.add_argument('--dry-run', action='store_true',
                            help="Don't write changes")
    
    # List families command
    list_parser = subparsers.add_parser('list-families',
                                         help='List available families')

    # Backfill command
    backfill_parser = subparsers.add_parser('backfill',
                                             help='Backfill missing context data')
    backfill_parser.add_argument('--family', '-f', type=str, required=True,
                                  help='Family identifier')
    backfill_parser.add_argument('--targets', '-t', type=str, nargs='+',
                                  help='Backfill targets (test_data, api_reference, examples, gist_source_code)')
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

    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    setup_logging(args.verbose)
    
    # Initialize tools
    tools = ExampleReviewerTools(
        config_dir=Path(args.config_dir),
        db_path=Path(args.db_path),
        workspace_dir=Path(args.workspace_dir),
    )
    
    # Execute command
    result = None
    
    if args.command == 'scan':
        result = tools.scan(
            family=args.family,
            directory=args.directory,
            max_files=args.max_files,
        )
    
    elif args.command == 'extract':
        result = tools.extract(
            family=args.family,
            max_files=args.max_files,
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
        )
    
    elif args.command == 'final-review':
        result = tools.final_review(family=args.family)
    
    elif args.command == 'commit':
        result = tools.commit(family=args.family)
    
    elif args.command == 'status':
        result = tools.status(family=args.family)
    
    elif args.command == 'run':
        result = tools.run_pipeline(
            family=args.family,
            max_examples=args.max_examples,
            skip_runtime=args.skip_runtime,
            skip_llm_fixes=args.skip_llm,
            dry_run=args.dry_run,
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

    if result:
        print_result(result, args.json)
        return 0 if result.success else 1

    return 1


if __name__ == '__main__':
    sys.exit(main())
