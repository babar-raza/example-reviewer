"""
Telemetry utilities for Example Reviewer Pipeline.
Provides context managers and helpers for tracking pipeline performance.
"""

import json
import logging
import os
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from .models import TelemetryEvent
from .database import Database

logger = logging.getLogger(__name__)


@contextmanager
def track_phase_timing(
    db: Database,
    run_id: str,
    family: str,
    phase: str,
    metadata: Optional[Dict[str, Any]] = None,
):
    """
    Context manager to track execution time for a pipeline phase.

    Usage:
        with track_phase_timing(db, run_id, family, "compilation"):
            compile_stats = run_compilation_phase(...)

    Args:
        db: Database instance
        run_id: Pipeline run ID
        family: Product family identifier
        phase: Phase name (e.g., "compilation", "runtime", "final_review")
        metadata: Optional metadata to attach to the event

    Yields:
        None

    Notes:
        - Records start/end times automatically
        - Calculates duration in milliseconds
        - Saves telemetry event to database
        - Handles exceptions gracefully (logs but doesn't re-raise)
        - Zero performance impact if database operation fails
    """
    start_time = time.perf_counter()
    start_timestamp = datetime.utcnow()
    success = True
    error_info = None

    try:
        yield
    except Exception as e:
        success = False
        error_info = str(e)
        # Re-raise to let caller handle the exception
        raise
    finally:
        # Calculate duration
        end_time = time.perf_counter()
        duration_ms = int((end_time - start_time) * 1000)

        # Prepare metadata
        event_metadata = metadata or {}
        if error_info:
            event_metadata['error'] = error_info

        # Create telemetry event
        try:
            event = TelemetryEvent(
                run_id=run_id,
                family=family,
                event_type="phase_timing",
                phase=phase,
                duration_ms=duration_ms,
                success=success,
                metadata=event_metadata,
                timestamp=start_timestamp,
            )

            db.save_telemetry_event(event)
            logger.debug(f"Phase '{phase}' completed in {duration_ms}ms (success={success})")

        except Exception as e:
            # Don't fail the pipeline if telemetry fails
            logger.warning(f"Failed to record telemetry for phase '{phase}': {e}")


def emit_telemetry_event(
    db: Database,
    run_id: str,
    family: str,
    event_type: str,
    phase: Optional[str] = None,
    example_id: Optional[str] = None,
    duration_ms: Optional[int] = None,
    success: bool = True,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Emit a telemetry event to the database.

    Standalone function for per-operation event tracking.
    Non-fatal: logs warnings on failure, never raises.

    Args:
        db: Database instance
        run_id: Pipeline run ID
        family: Product family identifier
        event_type: Type of event (e.g., 'llm_call', 'discovery_complete')
        phase: Pipeline phase
        example_id: Example being processed
        duration_ms: Duration in milliseconds
        success: Whether the operation succeeded
        metadata: Additional key-value metadata

    Returns:
        event_id string, or empty string on failure
    """
    try:
        event = TelemetryEvent(
            run_id=run_id,
            family=family,
            event_type=event_type,
            phase=phase,
            example_id=example_id,
            duration_ms=duration_ms,
            success=success,
            metadata=metadata or {},
            timestamp=datetime.utcnow(),
        )
        db.save_telemetry_event(event)
        logger.debug(f"Emitted telemetry event: {event_type} for {example_id or 'run'}")
        return event.event_id
    except Exception as e:
        logger.warning(f"Failed to emit telemetry event '{event_type}': {e}")
        return ""


def _collect_artifact_refs(
    db: Database,
    family: str,
    run_id: str,
) -> Dict[str, Any]:
    """
    Collect all artifact references for a run.

    Gathers artifact refs from compile_attempts, runtime_attempts, and markdown_edits
    to create an index of all artifacts produced during the run.

    Args:
        db: Database instance
        family: Product family identifier
        run_id: Pipeline run ID

    Returns:
        Dictionary with categorized artifact references
    """
    artifact_index = {
        'run_id': run_id,
        'family': family,
        'compiler_logs': [],
        'runtime_logs': [],
        'llm_requests': [],
        'llm_responses': [],
        'md_diffs': [],
        'code_artifacts': [],
        'total_artifacts': 0,
    }

    try:
        with db.get_connection() as conn:
            # Collect from compile_attempts
            compile_rows = conn.execute("""
                SELECT attempt_id, example_id, compiler_log_ref, input_code_ref,
                       output_code_ref, llm_request_ref, llm_response_ref
                FROM compile_attempts WHERE family = ?
            """, (family,)).fetchall()

            for row in compile_rows:
                if row['compiler_log_ref']:
                    artifact_index['compiler_logs'].append({
                        'attempt_id': row['attempt_id'],
                        'example_id': row['example_id'],
                        'ref': row['compiler_log_ref'],
                    })
                if row['input_code_ref']:
                    artifact_index['code_artifacts'].append({
                        'type': 'input_code',
                        'attempt_id': row['attempt_id'],
                        'ref': row['input_code_ref'],
                    })
                if row['output_code_ref']:
                    artifact_index['code_artifacts'].append({
                        'type': 'output_code',
                        'attempt_id': row['attempt_id'],
                        'ref': row['output_code_ref'],
                    })
                if row['llm_request_ref']:
                    artifact_index['llm_requests'].append({
                        'phase': 'compilation',
                        'attempt_id': row['attempt_id'],
                        'ref': row['llm_request_ref'],
                    })
                if row['llm_response_ref']:
                    artifact_index['llm_responses'].append({
                        'phase': 'compilation',
                        'attempt_id': row['attempt_id'],
                        'ref': row['llm_response_ref'],
                    })

            # Collect from runtime_attempts
            runtime_rows = conn.execute("""
                SELECT attempt_id, example_id, runtime_log_ref,
                       llm_request_ref, llm_response_ref
                FROM runtime_attempts WHERE family = ?
            """, (family,)).fetchall()

            for row in runtime_rows:
                if row['runtime_log_ref']:
                    artifact_index['runtime_logs'].append({
                        'attempt_id': row['attempt_id'],
                        'example_id': row['example_id'],
                        'ref': row['runtime_log_ref'],
                    })
                if row['llm_request_ref']:
                    artifact_index['llm_requests'].append({
                        'phase': 'runtime',
                        'attempt_id': row['attempt_id'],
                        'ref': row['llm_request_ref'],
                    })
                if row['llm_response_ref']:
                    artifact_index['llm_responses'].append({
                        'phase': 'runtime',
                        'attempt_id': row['attempt_id'],
                        'ref': row['llm_response_ref'],
                    })

            # Collect from markdown_edits
            edit_rows = conn.execute("""
                SELECT edit_id, example_id, diff_ref
                FROM markdown_edits WHERE diff_ref IS NOT NULL AND diff_ref != ''
            """).fetchall()

            for row in edit_rows:
                artifact_index['md_diffs'].append({
                    'edit_id': row['edit_id'],
                    'example_id': row['example_id'],
                    'ref': row['diff_ref'],
                })

        # Calculate total
        artifact_index['total_artifacts'] = (
            len(artifact_index['compiler_logs']) +
            len(artifact_index['runtime_logs']) +
            len(artifact_index['llm_requests']) +
            len(artifact_index['llm_responses']) +
            len(artifact_index['md_diffs']) +
            len(artifact_index['code_artifacts'])
        )

    except Exception as e:
        logger.warning(f"Failed to collect artifact refs: {e}")

    return artifact_index


def export_run_telemetry(
    db: Database,
    run_id: str,
    output_dir: str,
) -> Dict[str, str]:
    """
    Export telemetry data for a run to local files.

    Creates JSON files with:
    - run_summary.json: High-level run statistics
    - phase_events.json: Detailed phase timing events
    - artifact_index.json: Index of all artifacts created during the run
    - errors.json: All error events

    Args:
        db: Database instance
        run_id: Pipeline run ID
        output_dir: Directory to write telemetry files

    Returns:
        Dictionary mapping file types to file paths (empty dict on failure)
    """
    exported_files = {}

    try:
        output_root = Path(output_dir)
        if os.name == "nt" and str(output_dir).startswith(("/", "\\")):
            if len(output_root.drive) == 0:
                logger.error(f"Output directory not supported on Windows: {output_dir}")
                return {}
        if not output_root.exists() or not output_root.is_dir():
            logger.error(f"Output directory not available: {output_dir}")
            return {}

        # Create output directory
        run_dir = output_root / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        # Get run record
        with db.get_connection() as conn:
            run_row = conn.execute(
                "SELECT * FROM run_records WHERE run_id = ?",
                (run_id,)
            ).fetchone()

            if not run_row:
                logger.warning(f"Run {run_id} not found in database")
                return {}

        # Gather telemetry data
        phase_timings = db.get_phase_timings(run_id)
        attempt_counts = db.get_attempt_counts(run_id)

        # Calculate total duration from phase timings
        total_duration_ms = sum(p['duration_ms'] for p in phase_timings)

        # Build run summary
        run_summary = {
            'run_id': run_id,
            'family': run_row['family'],
            'status': run_row['status'],
            'started_at': run_row['started_at'],
            'completed_at': run_row['completed_at'],
            'examples_processed': run_row['examples_processed'],
            'examples_successful': run_row['examples_successful'],
            'examples_failed': run_row['examples_failed'],
            'phases_completed': run_row['phases_completed'],
            'total_duration_ms': total_duration_ms,
            'attempt_counts': attempt_counts,
            'phase_summary': {
                p['phase']: {
                    'duration_ms': p['duration_ms'],
                    'success': p['success'],
                }
                for p in phase_timings
            },
        }

        if run_row['error']:
            run_summary['error'] = run_row['error']

        # Export run_summary.json
        summary_path = run_dir / "run_summary.json"
        summary_path.write_text(
            json.dumps(run_summary, indent=2, default=str),
            encoding='utf-8'
        )
        exported_files['run_summary'] = str(summary_path)
        logger.info(f"Exported run summary to {summary_path}")

        # Export phase_events.json
        phase_events_path = run_dir / "phase_events.json"
        phase_events_path.write_text(
            json.dumps(phase_timings, indent=2, default=str),
            encoding='utf-8'
        )
        exported_files['phase_events'] = str(phase_events_path)
        logger.info(f"Exported phase events to {phase_events_path}")

        # Export artifact_index.json
        artifact_index = _collect_artifact_refs(db, run_row['family'], run_id)
        if artifact_index['total_artifacts'] > 0:
            artifact_index_path = run_dir / "artifact_index.json"
            artifact_index_path.write_text(
                json.dumps(artifact_index, indent=2, default=str),
                encoding='utf-8'
            )
            exported_files['artifact_index'] = str(artifact_index_path)
            logger.info(f"Exported artifact index to {artifact_index_path}")

        # Export errors.json if there were failures
        errors = []
        for phase in phase_timings:
            if not phase['success'] and phase['metadata'].get('error'):
                errors.append({
                    'phase': phase['phase'],
                    'timestamp': phase['timestamp'],
                    'error': phase['metadata']['error'],
                })

        if errors:
            errors_path = run_dir / "errors.json"
            errors_path.write_text(
                json.dumps(errors, indent=2, default=str),
                encoding='utf-8'
            )
            exported_files['errors'] = str(errors_path)
            logger.info(f"Exported errors to {errors_path}")

        logger.info(f"Successfully exported telemetry for run {run_id} to {run_dir}")
        return exported_files

    except Exception as e:
        # Don't fail the pipeline if export fails
        logger.error(f"Failed to export telemetry for run {run_id}: {e}")
        return {}


def log_resource_decision(
    db: Database,
    run_id: str,
    family: str,
    resource_decision,
) -> bool:
    """
    Log resource allocation decision to telemetry.

    Records GPU/VRAM detection results and chosen strategy for audit trail.
    Matches the spec telemetry.resource_decisions schema:
    - gpu_detected: boolean
    - vram_total_mb: integer
    - vram_used_mb: integer
    - cpu_mode: boolean
    - chosen_strategy: string
    - limits_applied: object

    Args:
        db: Database instance
        run_id: Pipeline run ID
        family: Product family identifier
        resource_decision: ResourceDecision instance from ResourceDetectionService

    Returns:
        True if logged successfully, False otherwise (never raises)
    """
    try:
        # Convert resource decision to telemetry dict
        decision_data = resource_decision.to_telemetry_dict()

        # Create telemetry event
        event = TelemetryEvent(
            run_id=run_id,
            family=family,
            event_type="resource_decision",
            phase="initialization",
            duration_ms=0,  # Detection is nearly instant
            success=True,
            metadata=decision_data,
            timestamp=datetime.utcnow(),
        )

        db.save_telemetry_event(event)

        logger.info(
            f"Resource decision logged: gpu_detected={decision_data['gpu_detected']}, "
            f"strategy={decision_data['chosen_strategy']}, "
            f"vram_total={decision_data['vram_total_mb']}MB"
        )
        return True

    except Exception as e:
        # Don't fail the pipeline if telemetry fails
        logger.warning(f"Failed to log resource decision: {e}")
        return False


def export_drift_metrics(
    db: Database,
    family: str,
) -> Dict[str, Any]:
    """
    Export drift metrics for a family to telemetry JSON.

    Computes drift statistics from example_records table:
    - avg_drift: Average drift score
    - median_drift: Median drift score
    - max_drift: Maximum drift score
    - p95_drift: 95th percentile drift score
    - drift_distribution: Histogram buckets

    Args:
        db: Database instance
        family: Product family identifier

    Returns:
        Dictionary with drift metrics, or empty metrics if no drift data available

    Example:
        >>> metrics = export_drift_metrics(db, "zip")
        >>> print(metrics['avg_drift'])
        0.18
    """
    try:
        # Check if drift_score column exists (backward compatibility)
        with db.get_connection() as conn:
            cursor = conn.execute("PRAGMA table_info(example_records)")
            columns = [row[1] for row in cursor.fetchall()]

            if 'drift_score' not in columns:
                logger.warning(f"drift_score column not found for family {family}, returning empty metrics")
                return _empty_drift_metrics(family)

        # Query drift scores
        with db.get_connection() as conn:
            cursor = conn.execute("""
                SELECT drift_score, drift_similarity
                FROM example_records
                WHERE family = ? AND drift_score IS NOT NULL
            """, (family,))

            rows = cursor.fetchall()

            if not rows:
                logger.info(f"No drift data found for family {family}")
                return _empty_drift_metrics(family)

        # Extract drift scores
        drift_scores = [row[0] for row in rows]

        logger.info(f"Computing drift metrics for {len(drift_scores)} examples in family {family}")

        # Compute statistics
        stats = _compute_drift_stats(drift_scores)

        # Compute distribution
        distribution = _compute_drift_distribution(drift_scores)

        # Combine results
        result = {
            'family': family,
            'avg_drift': stats['avg_drift'],
            'median_drift': stats['median_drift'],
            'max_drift': stats['max_drift'],
            'p95_drift': stats['p95_drift'],
            'count': stats['count'],
            'drift_distribution': distribution,
        }

        logger.info(
            f"Drift metrics computed for {family}: "
            f"avg={result['avg_drift']:.3f}, "
            f"median={result['median_drift']:.3f}, "
            f"p95={result['p95_drift']:.3f}"
        )

        return result

    except Exception as e:
        logger.error(f"Failed to export drift metrics for {family}: {e}")
        return _empty_drift_metrics(family)


def get_drift_trends(
    db: Database,
    family: str,
    n_runs: int = 10,
) -> Dict[str, Any]:
    """
    Get drift trends over last N pipeline runs.

    Analyzes drift evolution across runs to identify improvement or regression.

    Args:
        db: Database instance
        family: Product family identifier
        n_runs: Number of recent runs to analyze (default: 10)

    Returns:
        Dictionary with run-by-run drift metrics and overall trend

    Example:
        >>> trends = get_drift_trends(db, "zip", n_runs=5)
        >>> print(trends['overall_trend'])
        {'direction': 'down', 'percentage': -25.0}
    """
    try:
        # Get recent runs for this family
        with db.get_connection() as conn:
            cursor = conn.execute("""
                SELECT run_id, started_at, completed_at, status
                FROM run_records
                WHERE family = ?
                ORDER BY started_at DESC
                LIMIT ?
            """, (family, n_runs))

            runs = cursor.fetchall()

            if not runs:
                logger.info(f"No runs found for family {family}")
                return {
                    'family': family,
                    'runs': [],
                    'overall_trend': {'direction': 'stable', 'percentage': 0.0},
                }

        # Check if drift_score column exists
        with db.get_connection() as conn:
            cursor = conn.execute("PRAGMA table_info(example_records)")
            columns = [row[1] for row in cursor.fetchall()]

            if 'drift_score' not in columns:
                logger.warning(f"drift_score column not found, returning empty trends")
                return {
                    'family': family,
                    'runs': [],
                    'overall_trend': {'direction': 'stable', 'percentage': 0.0},
                }

        # For each run, compute drift metrics
        run_metrics = []
        avg_drifts = []

        for idx, run in enumerate(runs):
            run_id = run[0]
            started_at = run[1]
            next_started_at = runs[idx - 1][1] if idx > 0 else None

            # Get examples processed in this run (bounded by run window when possible)
            with db.get_connection() as conn:
                query = """
                    SELECT drift_score
                    FROM example_records
                    WHERE family = ?
                      AND drift_score IS NOT NULL
                      AND updated_at >= ?
                """
                params = [family, started_at]
                if next_started_at:
                    query += " AND updated_at < ?"
                    params.append(next_started_at)

                cursor = conn.execute(query, params)
                drift_scores = [row[0] for row in cursor.fetchall()]

            if drift_scores:
                stats = _compute_drift_stats(drift_scores)
                run_metrics.append({
                    'run_id': run_id,
                    'date': started_at.split('T')[0] if 'T' in started_at else started_at[:10],
                    'avg_drift': stats['avg_drift'],
                    'max_drift': stats['max_drift'],
                    'count': stats['count'],
                })
                avg_drifts.append(stats['avg_drift'])

        # Reverse to show oldest first
        run_metrics.reverse()
        avg_drifts.reverse()

        # Calculate overall trend
        trend = _calculate_trend(avg_drifts)

        logger.info(
            f"Drift trends for {family}: {len(run_metrics)} runs, "
            f"trend={trend['direction']} ({trend['percentage']:.1f}%)"
        )

        return {
            'family': family,
            'runs': run_metrics,
            'overall_trend': trend,
        }

    except Exception as e:
        logger.error(f"Failed to get drift trends for {family}: {e}")
        return {
            'family': family,
            'runs': [],
            'overall_trend': {'direction': 'stable', 'percentage': 0.0},
        }


def _compute_drift_stats(drift_scores: List[float]) -> Dict[str, Any]:
    """
    Compute drift statistics from scores.

    Args:
        drift_scores: List of drift scores (0.0-1.0)

    Returns:
        Dictionary with avg, median, max, p95, and count
    """
    if not drift_scores:
        return {
            'avg_drift': 0.0,
            'median_drift': 0.0,
            'max_drift': 0.0,
            'p95_drift': 0.0,
            'count': 0,
        }

    # Use numpy for statistics
    try:
        import numpy as np

        return {
            'avg_drift': float(np.mean(drift_scores)),
            'median_drift': float(np.median(drift_scores)),
            'max_drift': float(np.max(drift_scores)),
            'p95_drift': float(np.percentile(drift_scores, 95)),
            'count': len(drift_scores),
        }
    except ImportError:
        # Fallback to basic Python if numpy not available
        sorted_scores = sorted(drift_scores)
        n = len(sorted_scores)

        return {
            'avg_drift': sum(drift_scores) / n,
            'median_drift': sorted_scores[n // 2],
            'max_drift': max(drift_scores),
            'p95_drift': sorted_scores[int(n * 0.95)] if n > 1 else sorted_scores[0],
            'count': n,
        }


def _compute_drift_distribution(drift_scores: List[float]) -> Dict[str, int]:
    """
    Compute drift distribution histogram.

    Args:
        drift_scores: List of drift scores (0.0-1.0)

    Returns:
        Dictionary mapping bucket labels to counts
    """
    bins = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 1.0]
    bin_labels = [
        '0.0-0.1', '0.1-0.2', '0.2-0.3', '0.3-0.4',
        '0.4-0.5', '0.5-0.6', '0.6-0.7', '0.7+'
    ]

    try:
        import numpy as np
        counts, _ = np.histogram(drift_scores, bins=bins)
        return {label: int(count) for label, count in zip(bin_labels, counts)}
    except ImportError:
        # Fallback to manual binning
        counts = [0] * len(bin_labels)
        for score in drift_scores:
            for i in range(len(bins) - 1):
                if bins[i] <= score < bins[i + 1]:
                    counts[i] += 1
                    break
            else:
                # Handle edge case: score == 1.0
                if score >= bins[-2]:
                    counts[-1] += 1

        return {label: count for label, count in zip(bin_labels, counts)}


def _calculate_trend(values: List[float]) -> Dict[str, Any]:
    """
    Calculate trend direction and percentage change.

    Args:
        values: List of metric values over time (oldest first)

    Returns:
        Dictionary with direction ('up', 'down', 'stable') and percentage
    """
    if len(values) < 2:
        return {'direction': 'stable', 'percentage': 0.0}

    first_val = values[0]
    last_val = values[-1]

    if first_val == 0:
        return {'direction': 'stable', 'percentage': 0.0}

    percentage = ((last_val - first_val) / first_val) * 100

    # Consider < 5% change as stable
    if abs(percentage) < 5:
        direction = 'stable'
    elif percentage > 0:
        direction = 'up'
    else:
        direction = 'down'

    return {'direction': direction, 'percentage': percentage}


def _empty_drift_metrics(family: str) -> Dict[str, Any]:
    """
    Return empty drift metrics structure.

    Args:
        family: Product family identifier

    Returns:
        Dictionary with zero values
    """
    return {
        'family': family,
        'avg_drift': 0.0,
        'median_drift': 0.0,
        'max_drift': 0.0,
        'p95_drift': 0.0,
        'count': 0,
        'drift_distribution': {
            '0.0-0.1': 0,
            '0.1-0.2': 0,
            '0.2-0.3': 0,
            '0.3-0.4': 0,
            '0.4-0.5': 0,
            '0.5-0.6': 0,
            '0.6-0.7': 0,
            '0.7+': 0,
        },
    }
