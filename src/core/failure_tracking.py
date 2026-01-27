"""
Failure tracking methods to be integrated into Database class.
This module provides methods for saving and querying failure details for analytics.
"""

import json
import sqlite3
from datetime import datetime
from typing import List, Dict, Any, Optional

from .models import FailureDetail, FailureCategory, FailureResolution


# =========================================================================
# FAILURE TRACKING METHODS
# =========================================================================

def save_failure_detail(self, failure: FailureDetail) -> str:
    """
    Save a failure detail record.

    Args:
        failure: FailureDetail instance

    Returns:
        failure_id
    """
    with self.get_connection() as conn:
        conn.execute("""
            INSERT INTO failure_details (
                failure_id, run_id, example_id, phase,
                failure_category, error_category, error_message,
                resolution, metadata, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            failure.failure_id,
            failure.run_id,
            failure.example_id,
            failure.phase,
            failure.failure_category.value,
            failure.error_category,
            failure.error_message,
            failure.resolution.value,
            json.dumps(failure.metadata),
            failure.timestamp.isoformat(),
        ))
    return failure.failure_id


def get_failure_details_by_run(self, run_id: str) -> List[FailureDetail]:
    """
    Get all failure details for a run.

    Args:
        run_id: Pipeline run ID

    Returns:
        List of FailureDetail instances
    """
    with self.get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM failure_details WHERE run_id = ? ORDER BY timestamp",
            (run_id,)
        ).fetchall()

        return [_row_to_failure_detail(row) for row in rows]


def get_failure_breakdown(self, run_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Get failure breakdown by category.

    Args:
        run_id: Optional run ID filter

    Returns:
        Dictionary with failure counts and breakdowns
    """
    with self.get_connection() as conn:
        query = """
            SELECT
                failure_category,
                COUNT(*) as failure_count,
                COUNT(DISTINCT example_id) as affected_examples,
                COUNT(CASE WHEN resolution = 'fixed' THEN 1 END) as fixed_count,
                COUNT(CASE WHEN resolution = 'needs_review' THEN 1 END) as needs_review_count,
                COUNT(CASE WHEN resolution = 'abandoned' THEN 1 END) as abandoned_count
            FROM failure_details
        """
        params = []

        if run_id:
            query += " WHERE run_id = ?"
            params.append(run_id)

        query += " GROUP BY failure_category ORDER BY failure_count DESC"

        rows = conn.execute(query, params).fetchall()

        return {
            'failure_categories': [
                {
                    'category': row['failure_category'],
                    'count': row['failure_count'],
                    'affected_examples': row['affected_examples'],
                    'fixed': row['fixed_count'],
                    'needs_review': row['needs_review_count'],
                    'abandoned': row['abandoned_count'],
                }
                for row in rows
            ],
            'total_failures': sum(row['failure_count'] for row in rows),
        }


def get_top_error_types(self, limit: int = 10, run_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get top error types by occurrence count.

    Args:
        limit: Maximum number of error types to return
        run_id: Optional run ID filter

    Returns:
        List of error type statistics
    """
    with self.get_connection() as conn:
        query = """
            SELECT
                error_category,
                failure_category,
                COUNT(*) as occurrence_count,
                COUNT(DISTINCT example_id) as affected_examples,
                COUNT(CASE WHEN resolution = 'fixed' THEN 1 END) as fixed_count,
                ROUND(100.0 * COUNT(CASE WHEN resolution = 'fixed' THEN 1 END) / COUNT(*), 2) as fix_rate_pct
            FROM failure_details
            WHERE error_category IS NOT NULL
        """
        params = []

        if run_id:
            query += " AND run_id = ?"
            params.append(run_id)

        query += """
            GROUP BY error_category, failure_category
            ORDER BY occurrence_count DESC
            LIMIT ?
        """
        params.append(limit)

        rows = conn.execute(query, params).fetchall()

        return [
            {
                'error_category': row['error_category'],
                'failure_category': row['failure_category'],
                'occurrence_count': row['occurrence_count'],
                'affected_examples': row['affected_examples'],
                'fixed_count': row['fixed_count'],
                'fix_rate_pct': row['fix_rate_pct'],
            }
            for row in rows
        ]


def get_resolution_rates(self, run_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get resolution success rates by phase and category.

    Args:
        run_id: Optional run ID filter

    Returns:
        List of resolution statistics
    """
    with self.get_connection() as conn:
        query = """
            SELECT
                phase,
                failure_category,
                COUNT(*) as total_failures,
                COUNT(CASE WHEN resolution = 'fixed' THEN 1 END) as fixed,
                COUNT(CASE WHEN resolution = 'needs_review' THEN 1 END) as needs_review,
                COUNT(CASE WHEN resolution = 'abandoned' THEN 1 END) as abandoned,
                COUNT(CASE WHEN resolution = 'pending' THEN 1 END) as pending,
                ROUND(100.0 * COUNT(CASE WHEN resolution = 'fixed' THEN 1 END) / COUNT(*), 2) as fix_rate_pct
            FROM failure_details
        """
        params = []

        if run_id:
            query += " WHERE run_id = ?"
            params.append(run_id)

        query += " GROUP BY phase, failure_category ORDER BY phase, total_failures DESC"

        rows = conn.execute(query, params).fetchall()

        return [
            {
                'phase': row['phase'],
                'failure_category': row['failure_category'],
                'total_failures': row['total_failures'],
                'fixed': row['fixed'],
                'needs_review': row['needs_review'],
                'abandoned': row['abandoned'],
                'pending': row['pending'],
                'fix_rate_pct': row['fix_rate_pct'],
            }
            for row in rows
        ]


def update_failure_resolution(self, failure_id: str, resolution: FailureResolution) -> bool:
    """
    Update the resolution status of a failure.

    Args:
        failure_id: Failure identifier
        resolution: New resolution status

    Returns:
        True if updated successfully
    """
    with self.get_connection() as conn:
        conn.execute(
            "UPDATE failure_details SET resolution = ? WHERE failure_id = ?",
            (resolution.value, failure_id)
        )
        return conn.total_changes > 0


def _row_to_failure_detail(row: sqlite3.Row) -> FailureDetail:
    """Convert database row to FailureDetail."""
    return FailureDetail(
        failure_id=row['failure_id'],
        run_id=row['run_id'],
        example_id=row['example_id'],
        phase=row['phase'],
        failure_category=FailureCategory(row['failure_category']),
        error_category=row['error_category'],
        error_message=row['error_message'],
        resolution=FailureResolution(row['resolution']),
        metadata=json.loads(row['metadata']) if row['metadata'] else {},
        timestamp=datetime.fromisoformat(row['timestamp']),
    )
