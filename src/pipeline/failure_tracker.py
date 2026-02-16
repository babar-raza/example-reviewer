"""
Failure tracking helper for pipeline orchestrator.
Provides utilities to track failures for analytics.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from ..core.database import Database
from ..core.models import FailureDetail, FailureCategory, FailureResolution

logger = logging.getLogger(__name__)


def track_failure(
    db: Database,
    run_id: str,
    phase: str,
    failure_category: FailureCategory,
    example_id: Optional[str] = None,
    error_category: Optional[str] = None,
    error_message: Optional[str] = None,
    resolution: FailureResolution = FailureResolution.PENDING,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Track a failure for analytics.

    Args:
        db: Database instance
        run_id: Current run ID
        phase: Phase where failure occurred (e.g., 'Phase B', 'Phase C')
        failure_category: Category of failure
        example_id: Optional example ID
        error_category: Specific error type (e.g., 'CS0246', 'FileNotFoundException')
        error_message: Error message text (truncated to 1000 chars)
        resolution: Resolution status
        metadata: Additional context

    Returns:
        failure_id
    """
    # Truncate error message to avoid database bloat
    truncated_error = error_message[:1000] if error_message else None

    failure = FailureDetail(
        run_id=run_id,
        example_id=example_id,
        phase=phase,
        failure_category=failure_category,
        error_category=error_category,
        error_message=truncated_error,
        resolution=resolution,
        metadata=metadata or {},
        timestamp=datetime.now(timezone.utc),
    )

    try:
        failure_id = db.save_failure_detail(failure)
        logger.debug(
            f"Tracked failure: {failure_category.value} in {phase} "
            f"(example: {example_id}, resolution: {resolution.value})"
        )
        return failure_id
    except Exception as e:
        logger.warning(f"Failed to track failure: {e}")
        return ""


def track_compile_failure(
    db: Database,
    run_id: str,
    example_id: str,
    errors: list,
    resolution: FailureResolution = FailureResolution.PENDING,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Track a compilation failure.

    Args:
        db: Database instance
        run_id: Current run ID
        example_id: Example that failed
        errors: List of error messages
        resolution: Resolution status
        metadata: Additional context

    Returns:
        failure_id
    """
    # Extract error category from first error (e.g., CS0246)
    error_category = None
    if errors:
        import re
        match = re.search(r'(CS\d{4})', errors[0])
        if match:
            error_category = match.group(1)

    error_message = '\n'.join(errors[:3]) if errors else "Unknown compile error"

    return track_failure(
        db=db,
        run_id=run_id,
        phase="Phase B",
        failure_category=FailureCategory.COMPILE_ERROR,
        example_id=example_id,
        error_category=error_category,
        error_message=error_message,
        resolution=resolution,
        metadata=metadata,
    )


def track_runtime_failure(
    db: Database,
    run_id: str,
    example_id: str,
    exception_type: Optional[str],
    exception_message: Optional[str],
    exit_code: int,
    resolution: FailureResolution = FailureResolution.PENDING,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Track a runtime failure.

    Args:
        db: Database instance
        run_id: Current run ID
        example_id: Example that failed
        exception_type: Exception type
        exception_message: Exception message
        exit_code: Exit code
        resolution: Resolution status
        metadata: Additional context

    Returns:
        failure_id
    """
    error_message = exception_message or f"Runtime error (exit code: {exit_code})"

    return track_failure(
        db=db,
        run_id=run_id,
        phase="Phase C",
        failure_category=FailureCategory.RUNTIME_ERROR,
        example_id=example_id,
        error_category=exception_type,
        error_message=error_message,
        resolution=resolution,
        metadata=metadata or {'exit_code': exit_code},
    )


def track_drift_exceeded(
    db: Database,
    run_id: str,
    example_id: str,
    phase: str,
    drift_score: float,
    threshold: float,
    resolution: FailureResolution = FailureResolution.ABANDONED,
) -> str:
    """
    Track a drift threshold exceeded failure.

    Args:
        db: Database instance
        run_id: Current run ID
        example_id: Example that exceeded drift
        phase: Phase where drift was detected
        drift_score: Actual drift score
        threshold: Configured threshold
        resolution: Resolution status

    Returns:
        failure_id
    """
    return track_failure(
        db=db,
        run_id=run_id,
        phase=phase,
        failure_category=FailureCategory.DRIFT_EXCEEDED,
        example_id=example_id,
        error_category="drift_threshold_exceeded",
        error_message=f"Drift score {drift_score:.3f} exceeds threshold {threshold:.3f}",
        resolution=resolution,
        metadata={'drift_score': drift_score, 'threshold': threshold},
    )


def track_timeout(
    db: Database,
    run_id: str,
    phase: str,
    timeout_seconds: int,
    example_id: Optional[str] = None,
    context: Optional[str] = None,
    resolution: FailureResolution = FailureResolution.ABANDONED,
) -> str:
    """
    Track a timeout failure.

    Args:
        db: Database instance
        run_id: Current run ID
        phase: Phase where timeout occurred
        timeout_seconds: Timeout limit
        example_id: Optional example ID
        context: Optional context (e.g., 'LLM request', 'compilation')
        resolution: Resolution status

    Returns:
        failure_id
    """
    error_message = f"Timeout after {timeout_seconds}s"
    if context:
        error_message += f": {context}"

    return track_failure(
        db=db,
        run_id=run_id,
        phase=phase,
        failure_category=FailureCategory.TIMEOUT,
        example_id=example_id,
        error_category="timeout",
        error_message=error_message,
        resolution=resolution,
        metadata={'timeout_seconds': timeout_seconds, 'context': context},
    )


def track_review_failure(
    db: Database,
    run_id: str,
    example_id: str,
    issues_count: int,
    resolution: FailureResolution = FailureResolution.NEEDS_REVIEW,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Track a final review failure.

    Args:
        db: Database instance
        run_id: Current run ID
        example_id: Example that failed review
        issues_count: Number of issues found
        resolution: Resolution status
        metadata: Additional context

    Returns:
        failure_id
    """
    return track_failure(
        db=db,
        run_id=run_id,
        phase="Phase E",
        failure_category=FailureCategory.REVIEW_FAILED,
        example_id=example_id,
        error_category="review_issues",
        error_message=f"Final review found {issues_count} issue(s)",
        resolution=resolution,
        metadata=metadata or {'issues_count': issues_count},
    )


def track_llm_response_rejected(
    db: Database,
    run_id: str,
    phase: str,
    example_id: str,
    reason: str,
    resolution: FailureResolution = FailureResolution.ABANDONED,
) -> str:
    """
    Track an LLM response rejection.

    Args:
        db: Database instance
        run_id: Current run ID
        phase: Phase where rejection occurred
        example_id: Example ID
        reason: Rejection reason
        resolution: Resolution status

    Returns:
        failure_id
    """
    return track_failure(
        db=db,
        run_id=run_id,
        phase=phase,
        failure_category=FailureCategory.LLM_RESPONSE_REJECTED,
        example_id=example_id,
        error_category="llm_response_rejected",
        error_message=reason,
        resolution=resolution,
    )


def track_api_context_missing(
    db: Database,
    run_id: str,
    phase: str,
    example_id: str,
    missing_namespaces: list,
    resolution: FailureResolution = FailureResolution.PENDING,
) -> str:
    """
    Track missing API context.

    Args:
        db: Database instance
        run_id: Current run ID
        phase: Phase where context was missing
        example_id: Example ID
        missing_namespaces: List of missing namespaces
        resolution: Resolution status

    Returns:
        failure_id
    """
    return track_failure(
        db=db,
        run_id=run_id,
        phase=phase,
        failure_category=FailureCategory.API_CONTEXT_MISSING,
        example_id=example_id,
        error_category="missing_api_context",
        error_message=f"Missing API context for: {', '.join(missing_namespaces[:5])}",
        resolution=resolution,
        metadata={'missing_namespaces': missing_namespaces},
    )


def track_infra_missing_test_data(
    db: Database,
    run_id: str,
    example_id: str,
    missing_files: list,
    resolution: FailureResolution = FailureResolution.PENDING,
) -> str:
    """
    Track infrastructure failure due to missing test data files.

    Args:
        db: Database instance
        run_id: Current run ID
        example_id: Example ID that is blocked
        missing_files: List of missing test data files
        resolution: Resolution status

    Returns:
        failure_id
    """
    return track_failure(
        db=db,
        run_id=run_id,
        phase="Phase C (Pre-Runtime)",
        failure_category=FailureCategory.INFRA_MISSING_TEST_DATA,
        example_id=example_id,
        error_category="missing_test_data",
        error_message=f"Missing test data files: {', '.join(missing_files[:5])}",
        resolution=resolution,
        metadata={'missing_files': missing_files, 'missing_count': len(missing_files)},
    )


def track_infra_blocked_rar(
    db: Database,
    run_id: str,
    example_id: str,
    reason: str = "RAR fixtures not available",
    resolution: FailureResolution = FailureResolution.ABANDONED,
) -> str:
    """
    Track infrastructure blocker for RAR fixtures.

    Args:
        db: Database instance
        run_id: Current run ID
        example_id: Example ID that is blocked
        reason: Specific reason
        resolution: Resolution status

    Returns:
        failure_id
    """
    return track_failure(
        db=db,
        run_id=run_id,
        phase="Phase C (Pre-Runtime)",
        failure_category=FailureCategory.INFRA_BLOCKED_RAR_FIXTURE,
        example_id=example_id,
        error_category="missing_rar_fixture",
        error_message=reason,
        resolution=resolution,
        metadata={'infra_type': 'rar_fixture'},
    )


def track_infra_blocked_7z(
    db: Database,
    run_id: str,
    example_id: str,
    reason: str = "7z fixtures not compatible",
    resolution: FailureResolution = FailureResolution.ABANDONED,
) -> str:
    """
    Track infrastructure blocker for 7z fixtures.

    Args:
        db: Database instance
        run_id: Current run ID
        example_id: Example ID that is blocked
        reason: Specific reason
        resolution: Resolution status

    Returns:
        failure_id
    """
    return track_failure(
        db=db,
        run_id=run_id,
        phase="Phase C (Pre-Runtime)",
        failure_category=FailureCategory.INFRA_BLOCKED_7Z_FIXTURE,
        example_id=example_id,
        error_category="missing_7z_fixture",
        error_message=reason,
        resolution=resolution,
        metadata={'infra_type': '7z_fixture'},
    )


def track_precheck_failure(
    db: Database,
    run_id: str,
    example_id: str,
    reason: str,
    resolution: FailureResolution = FailureResolution.ABANDONED,
) -> str:
    """
    Track pre-check failure (empty/incomplete code, no C# block, etc.).

    Args:
        db: Database instance
        run_id: Current run ID
        example_id: Example ID that failed pre-check
        reason: Pre-check failure reason
        resolution: Resolution status

    Returns:
        failure_id
    """
    return track_failure(
        db=db,
        run_id=run_id,
        phase="Phase A (Pre-Compilation)",
        failure_category=FailureCategory.PRECHECK_ONLY,
        example_id=example_id,
        error_category="precheck_failure",
        error_message=reason,
        resolution=resolution,
        metadata={'precheck_reason': reason},
    )
