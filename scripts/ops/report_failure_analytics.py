"""
Failure Analytics Reporting Tool for Example Reviewer Pipeline.

This tool provides comprehensive analytics on pipeline failures:
1. Failure Breakdown by Category - Count and percentage distribution
2. Top Error Types - Top 10 error categories with fix rates
3. NEEDS_REVIEW Stats - Examples requiring human review, grouped by reason
4. Timeout Counts - Timeout failures by phase
5. Drift Distribution - Score distribution across configurable buckets

Supports filtering by:
- run_id: Specific pipeline run
- family: Product family (zip, pdf, words, etc.)
- phase: Specific pipeline phase

Output formats:
- JSON: Structured for programmatic use
- TEXT: Human-readable tables with ASCII visualization

Usage:
    python tools/report_failure_analytics.py --format json --run-id abc123
    python tools/report_failure_analytics.py --family zip --format text
    python tools/report_failure_analytics.py --format text  # All data

Hard Rules:
    - Uses sys.executable for subprocess calls if needed
    - Both JSON and text output must work
    - All queries must complete in <5 seconds
    - No hardcoded database paths
    - Comprehensive docstrings for self-documentation
"""

import argparse
import json
import logging
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


class FailureCategory(str, Enum):
    """Valid failure categories from schema."""
    TIMEOUT = "timeout"
    DRIFT_EXCEEDED = "drift_exceeded"
    API_CONTEXT_MISSING = "api_context_missing"
    LLM_RESPONSE_REJECTED = "llm_response_rejected"
    ESCALATED_TO_REVIEW = "escalated_to_review"
    COMPILE_ERROR = "compile_error"
    RUNTIME_ERROR = "runtime_error"
    REVIEW_FAILED = "review_failed"
    OTHER = "other"


class DriftBucket(str, Enum):
    """Drift score buckets for distribution analysis."""
    VERY_LOW = "[0.00-0.02]"
    LOW = "[0.02-0.05]"
    MEDIUM = "[0.05-0.10]"
    HIGH = "[0.10+]"


@dataclass
class FailureBreakdownRow:
    """Single row in failure breakdown analysis."""
    category: str
    count: int
    percentage: float
    affected_examples: int
    affected_runs: int
    fixed: int
    needs_review: int
    abandoned: int
    pending: int


@dataclass
class TopErrorRow:
    """Single row in top error types analysis."""
    error_category: str
    failure_category: str
    count: int
    percentage: float
    fix_rate: float
    affected_examples: int


@dataclass
class NeedsReviewRow:
    """Single row in NEEDS_REVIEW analysis."""
    escalation_reason: str
    count: int
    percentage: float


@dataclass
class TimeoutRow:
    """Single row in timeout distribution analysis."""
    phase: str
    count: int
    percentage: float


@dataclass
class DriftBucketRow:
    """Single row in drift distribution analysis."""
    bucket: str
    count: int
    percentage: float


@dataclass
class StatusBreakdownRow:
    """Single row in status breakdown analysis."""
    status: str
    count: int
    percentage: float
    top_escalation_reasons: List[str] = field(default_factory=list)


@dataclass
class AnalyticsReport:
    """Complete analytics report."""
    timestamp: str
    data_scope: Dict[str, Any]
    failure_breakdown: List[FailureBreakdownRow] = field(default_factory=list)
    status_breakdown: List[StatusBreakdownRow] = field(default_factory=list)
    top_errors: List[TopErrorRow] = field(default_factory=list)
    needs_review: List[NeedsReviewRow] = field(default_factory=list)
    timeouts: List[TimeoutRow] = field(default_factory=list)
    drift_distribution: List[DriftBucketRow] = field(default_factory=list)
    query_times_ms: Dict[str, float] = field(default_factory=dict)


class FailureAnalyticsDB:
    """
    Database interface for failure analytics.

    Provides specialized queries for:
    - Failure breakdown by category
    - Top error types with fix rates
    - NEEDS_REVIEW escalations
    - Timeout distribution by phase
    - Drift score distribution
    """

    def __init__(self, db_path: str):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database

        Raises:
            FileNotFoundError: If database does not exist
            sqlite3.DatabaseError: If database is corrupted
        """
        db_file = Path(db_path)
        if not db_file.exists():
            raise FileNotFoundError(f"Database not found: {db_path}")

        self.db_path = db_path
        self.connection = None
        self._connect()
        logger.info(f"Connected to database: {db_path}")

    def _connect(self) -> None:
        """Establish database connection with WAL mode."""
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row
        # Enable WAL mode for concurrent access
        self.connection.execute("PRAGMA journal_mode=WAL")

    def close(self) -> None:
        """Close database connection."""
        if self.connection:
            self.connection.close()
            logger.debug("Database connection closed")

    def _build_where_clause(
        self,
        run_id: Optional[str] = None,
        family: Optional[str] = None,
        phase: Optional[str] = None
    ) -> Tuple[str, List[Any]]:
        """
        Build WHERE clause for filtering.

        Args:
            run_id: Filter by run_id
            family: Filter by family (requires JOIN with run_records)
            phase: Filter by phase

        Returns:
            Tuple of (where_clause_string, params_list)
        """
        conditions = []
        params = []

        if run_id:
            conditions.append("failure_details.run_id = ?")
            params.append(run_id)

        if phase:
            conditions.append("failure_details.phase = ?")
            params.append(phase)

        # Family filtering requires JOIN with run_records
        # This will be handled in individual queries

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        return where_clause, params

    def get_failure_breakdown(
        self,
        run_id: Optional[str] = None,
        family: Optional[str] = None,
        phase: Optional[str] = None
    ) -> List[FailureBreakdownRow]:
        """
        Query failure breakdown by category.

        Groups failures by failure_category and provides:
        - Count of failures
        - Percentage of total
        - Number of affected examples and runs
        - Resolution breakdown (fixed, needs_review, abandoned, pending)

        Args:
            run_id: Optional filter by run_id
            family: Optional filter by family
            phase: Optional filter by phase

        Returns:
            List of FailureBreakdownRow with breakdown data
        """
        logger.debug(f"Querying failure breakdown: run_id={run_id}, family={family}, phase={phase}")

        # Build base query
        query = """
        SELECT
            failure_category,
            COUNT(*) as count,
            COUNT(DISTINCT example_id) as affected_examples,
            COUNT(DISTINCT run_id) as affected_runs,
            COUNT(CASE WHEN resolution = 'fixed' THEN 1 END) as fixed,
            COUNT(CASE WHEN resolution = 'needs_review' THEN 1 END) as needs_review,
            COUNT(CASE WHEN resolution = 'abandoned' THEN 1 END) as abandoned,
            COUNT(CASE WHEN resolution = 'pending' THEN 1 END) as pending
        FROM failure_details
        """

        params = []
        conditions = []

        if run_id:
            conditions.append("run_id = ?")
            params.append(run_id)

        if phase:
            conditions.append("phase = ?")
            params.append(phase)

        # Family filtering requires JOIN
        if family:
            query = """
            SELECT
                failure_details.failure_category,
                COUNT(*) as count,
                COUNT(DISTINCT failure_details.example_id) as affected_examples,
                COUNT(DISTINCT failure_details.run_id) as affected_runs,
                COUNT(CASE WHEN failure_details.resolution = 'fixed' THEN 1 END) as fixed,
                COUNT(CASE WHEN failure_details.resolution = 'needs_review' THEN 1 END) as needs_review,
                COUNT(CASE WHEN failure_details.resolution = 'abandoned' THEN 1 END) as abandoned,
                COUNT(CASE WHEN failure_details.resolution = 'pending' THEN 1 END) as pending
            FROM failure_details
            JOIN run_records ON failure_details.run_id = run_records.run_id
            WHERE run_records.family = ?
            """
            params = [family]
            if run_id:
                query += " AND failure_details.run_id = ?"
                params.append(run_id)
            if phase:
                query += " AND failure_details.phase = ?"
                params.append(phase)
            query += " GROUP BY failure_details.failure_category ORDER BY count DESC"
        else:
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            query += " GROUP BY failure_category ORDER BY count DESC"

        cursor = self.connection.execute(query, params)
        rows = cursor.fetchall()

        # Calculate total for percentage
        total = sum(row['count'] for row in rows) if rows else 1

        result = []
        for row in rows:
            count = row['count']
            result.append(FailureBreakdownRow(
                category=row[0],  # failure_category
                count=count,
                percentage=round(100.0 * count / total, 2),
                affected_examples=row['affected_examples'],
                affected_runs=row['affected_runs'],
                fixed=row['fixed'],
                needs_review=row['needs_review'],
                abandoned=row['abandoned'],
                pending=row['pending']
            ))

        logger.debug(f"Found {len(result)} failure categories")
        return result

    def get_top_errors(
        self,
        run_id: Optional[str] = None,
        family: Optional[str] = None,
        phase: Optional[str] = None,
        limit: int = 10
    ) -> List[TopErrorRow]:
        """
        Query top error types by occurrence count.

        Provides top N error categories with:
        - Occurrence count
        - Fix rate percentage
        - Number of affected examples
        - Associated failure category

        Args:
            run_id: Optional filter by run_id
            family: Optional filter by family
            phase: Optional filter by phase
            limit: Maximum number of results (default: 10)

        Returns:
            List of TopErrorRow for top N error types
        """
        logger.debug(f"Querying top {limit} errors: run_id={run_id}, family={family}, phase={phase}")

        query = """
        SELECT
            error_category,
            failure_category,
            COUNT(*) as count,
            COUNT(DISTINCT example_id) as affected_examples,
            COUNT(CASE WHEN resolution = 'fixed' THEN 1 END) as fixed,
            ROUND(100.0 * COUNT(CASE WHEN resolution = 'fixed' THEN 1 END) / COUNT(*), 2) as fix_rate
        FROM failure_details
        WHERE error_category IS NOT NULL
        """

        params = []

        if run_id:
            query += " AND run_id = ?"
            params.append(run_id)

        if phase:
            query += " AND phase = ?"
            params.append(phase)

        # Family filtering
        if family:
            query = """
            SELECT
                failure_details.error_category,
                failure_details.failure_category,
                COUNT(*) as count,
                COUNT(DISTINCT failure_details.example_id) as affected_examples,
                COUNT(CASE WHEN failure_details.resolution = 'fixed' THEN 1 END) as fixed,
                ROUND(100.0 * COUNT(CASE WHEN failure_details.resolution = 'fixed' THEN 1 END) / COUNT(*), 2) as fix_rate
            FROM failure_details
            JOIN run_records ON failure_details.run_id = run_records.run_id
            WHERE run_records.family = ? AND failure_details.error_category IS NOT NULL
            """
            params = [family]
            if run_id:
                query += " AND failure_details.run_id = ?"
                params.append(run_id)
            if phase:
                query += " AND failure_details.phase = ?"
                params.append(phase)

        query += f" GROUP BY error_category ORDER BY count DESC LIMIT {limit}"

        cursor = self.connection.execute(query, params)
        rows = cursor.fetchall()

        # Calculate total for percentage
        total = sum(row['count'] for row in rows) if rows else 1

        result = []
        for row in rows:
            count = row['count']
            result.append(TopErrorRow(
                error_category=row['error_category'] or "unknown",
                failure_category=row['failure_category'],
                count=count,
                percentage=round(100.0 * count / total, 2),
                fix_rate=row['fix_rate'],
                affected_examples=row['affected_examples']
            ))

        logger.debug(f"Found {len(result)} top error types")
        return result

    def get_needs_review_stats(
        self,
        run_id: Optional[str] = None,
        family: Optional[str] = None,
        phase: Optional[str] = None
    ) -> List[NeedsReviewRow]:
        """
        Query examples with NEEDS_REVIEW status.

        Groups examples by escalation_reason and provides:
        - Count of escalations
        - Percentage of total escalations

        Args:
            run_id: Optional filter by run_id
            family: Optional filter by family
            phase: Optional filter by phase

        Returns:
            List of NeedsReviewRow with escalation breakdown
        """
        logger.debug(f"Querying NEEDS_REVIEW stats: run_id={run_id}, family={family}, phase={phase}")

        # Task 5: Use run-scoped state (escalation_reason is in example_run_state)
        query = """
        SELECT
            ers.escalation_reason,
            COUNT(*) as count
        FROM example_run_state ers
        JOIN example_records er ON er.example_id = ers.example_id
        WHERE ers.status = 'NEEDS_REVIEW'
        """

        params = []

        if run_id:
            query += " AND ers.run_id = ?"
            params.append(run_id)

        if family:
            query += " AND er.family = ?"
            params.append(family)

        query += " GROUP BY ers.escalation_reason ORDER BY count DESC"

        cursor = self.connection.execute(query, params)
        rows = cursor.fetchall()

        # Calculate total
        total = sum(row['count'] for row in rows) if rows else 1

        result = []
        for row in rows:
            count = row['count']
            reason = row['escalation_reason'] or "unknown"
            result.append(NeedsReviewRow(
                escalation_reason=reason,
                count=count,
                percentage=round(100.0 * count / total, 2)
            ))

        logger.debug(f"Found {len(result)} escalation reasons")
        return result

    def get_timeout_counts(
        self,
        run_id: Optional[str] = None,
        family: Optional[str] = None
    ) -> List[TimeoutRow]:
        """
        Query timeout failures grouped by phase.

        Provides timeout count per phase with:
        - Count of timeouts
        - Percentage of total timeouts

        Args:
            run_id: Optional filter by run_id
            family: Optional filter by family

        Returns:
            List of TimeoutRow with timeout distribution by phase
        """
        logger.debug(f"Querying timeout counts: run_id={run_id}, family={family}")

        query = """
        SELECT
            phase,
            COUNT(*) as count
        FROM failure_details
        WHERE failure_category = 'timeout'
        """

        params = []

        if run_id:
            query += " AND run_id = ?"
            params.append(run_id)

        # Family filtering
        if family:
            query = """
            SELECT
                failure_details.phase,
                COUNT(*) as count
            FROM failure_details
            JOIN run_records ON failure_details.run_id = run_records.run_id
            WHERE failure_details.failure_category = 'timeout' AND run_records.family = ?
            """
            params = [family]
            if run_id:
                query += " AND failure_details.run_id = ?"
                params.append(run_id)

        query += " GROUP BY phase ORDER BY count DESC"

        cursor = self.connection.execute(query, params)
        rows = cursor.fetchall()

        # Calculate total
        total = sum(row['count'] for row in rows) if rows else 1

        result = []
        for row in rows:
            count = row['count']
            result.append(TimeoutRow(
                phase=row['phase'],
                count=count,
                percentage=round(100.0 * count / total, 2)
            ))

        logger.debug(f"Found {len(result)} phases with timeouts")
        return result

    def get_drift_distribution(
        self,
        run_id: Optional[str] = None,
        family: Optional[str] = None,
        phase: Optional[str] = None
    ) -> List[DriftBucketRow]:
        """
        Query drift score distribution.

        Extracts drift_score from metadata JSON and creates buckets:
        - [0.00-0.02]: Very low drift
        - [0.02-0.05]: Low drift
        - [0.05-0.10]: Medium drift
        - [0.10+]: High drift

        Only considers records with drift_exceeded failure category.

        Args:
            run_id: Optional filter by run_id
            family: Optional filter by family
            phase: Optional filter by phase

        Returns:
            List of DriftBucketRow with drift distribution
        """
        logger.debug(f"Querying drift distribution: run_id={run_id}, family={family}, phase={phase}")

        # Query all drift_exceeded failures with metadata
        query = """
        SELECT metadata
        FROM failure_details
        WHERE failure_category = 'drift_exceeded'
        """

        params = []

        if run_id:
            query += " AND run_id = ?"
            params.append(run_id)

        if phase:
            query += " AND phase = ?"
            params.append(phase)

        # Family filtering
        if family:
            query = """
            SELECT failure_details.metadata
            FROM failure_details
            JOIN run_records ON failure_details.run_id = run_records.run_id
            WHERE failure_details.failure_category = 'drift_exceeded' AND run_records.family = ?
            """
            params = [family]
            if run_id:
                query += " AND failure_details.run_id = ?"
                params.append(run_id)
            if phase:
                query += " AND failure_details.phase = ?"
                params.append(phase)

        cursor = self.connection.execute(query, params)
        rows = cursor.fetchall()

        # Extract drift scores from metadata
        buckets = {
            DriftBucket.VERY_LOW: 0,
            DriftBucket.LOW: 0,
            DriftBucket.MEDIUM: 0,
            DriftBucket.HIGH: 0,
        }

        for row in rows:
            try:
                metadata = json.loads(row[0]) if row[0] else {}
                drift_score = metadata.get('drift_score', 0)

                if isinstance(drift_score, (int, float)):
                    if drift_score < 0.02:
                        buckets[DriftBucket.VERY_LOW] += 1
                    elif drift_score < 0.05:
                        buckets[DriftBucket.LOW] += 1
                    elif drift_score < 0.10:
                        buckets[DriftBucket.MEDIUM] += 1
                    else:
                        buckets[DriftBucket.HIGH] += 1
            except (json.JSONDecodeError, TypeError, KeyError):
                # Skip malformed metadata
                pass

        # Calculate total
        total = sum(buckets.values()) if any(buckets.values()) else 1

        result = []
        for bucket, count in buckets.items():
            result.append(DriftBucketRow(
                bucket=bucket.value,
                count=count,
                percentage=round(100.0 * count / total, 2) if total > 0 else 0.0
            ))

        logger.debug(f"Drift distribution: {buckets}")
        return result

    def get_status_breakdown(
        self,
        run_id: Optional[str] = None,
        family: Optional[str] = None,
    ) -> List[StatusBreakdownRow]:
        """
        Query example status breakdown (COMPILE_FAILED, RUNTIME_FAILED, NEEDS_REVIEW, INFRA_BLOCKED, etc.).

        Groups examples by status from example_run_state and provides:
        - Count of examples in each status
        - Percentage of total examples
        - Top escalation reasons for failed statuses

        Args:
            run_id: Optional filter by run_id
            family: Optional filter by family

        Returns:
            List of StatusBreakdownRow with status distribution
        """
        logger.debug(f"Querying status breakdown: run_id={run_id}, family={family}")

        # Query status counts
        query = """
        SELECT
            ers.status,
            COUNT(*) as count,
            GROUP_CONCAT(DISTINCT ers.escalation_reason) as escalation_reasons
        FROM example_run_state ers
        JOIN example_records er ON er.example_id = ers.example_id
        WHERE 1=1
        """

        params = []

        if run_id:
            query += " AND ers.run_id = ?"
            params.append(run_id)

        if family:
            query += " AND er.family = ?"
            params.append(family)

        query += " GROUP BY ers.status ORDER BY count DESC"

        cursor = self.connection.execute(query, params)
        rows = cursor.fetchall()

        # Calculate total
        total = sum(row['count'] for row in rows) if rows else 1

        result = []
        for row in rows:
            count = row['count']
            escalation_reasons = []
            if row['escalation_reasons']:
                # Parse concatenated reasons and get top 3
                reasons = [r.strip() for r in row['escalation_reasons'].split(',') if r.strip()]
                escalation_reasons = reasons[:3]

            result.append(StatusBreakdownRow(
                status=row['status'],
                count=count,
                percentage=round(100.0 * count / total, 2),
                top_escalation_reasons=escalation_reasons
            ))

        logger.debug(f"Found {len(result)} statuses")
        return result


class AnalyticsFormatter:
    """
    Format analytics reports for output.

    Supports:
    - JSON output: Structured data for programmatic use
    - TEXT output: Human-readable tables with ASCII visualization
    """

    @staticmethod
    def to_json(report: AnalyticsReport) -> str:
        """
        Convert report to JSON format.

        Args:
            report: AnalyticsReport object

        Returns:
            JSON string with proper indentation
        """
        # Convert dataclasses to dicts
        data = {
            'timestamp': report.timestamp,
            'data_scope': report.data_scope,
            'failure_breakdown': [asdict(row) for row in report.failure_breakdown],
            'status_breakdown': [asdict(row) for row in report.status_breakdown],
            'top_errors': [asdict(row) for row in report.top_errors],
            'needs_review': [asdict(row) for row in report.needs_review],
            'timeouts': [asdict(row) for row in report.timeouts],
            'drift_distribution': [asdict(row) for row in report.drift_distribution],
            'query_times_ms': report.query_times_ms,
        }
        return json.dumps(data, indent=2)

    @staticmethod
    def to_text(report: AnalyticsReport) -> str:
        """
        Convert report to human-readable text format with ASCII tables.

        Uses box-drawing characters and bar charts (█) for visualization.

        Args:
            report: AnalyticsReport object

        Returns:
            Formatted text report
        """
        lines = []

        # Header
        lines.append("=" * 80)
        lines.append("FAILURE ANALYTICS REPORT")
        lines.append("=" * 80)
        lines.append(f"Generated: {report.timestamp}")
        lines.append("")

        # Data scope
        lines.append("DATA SCOPE")
        lines.append("-" * 80)
        for key, value in report.data_scope.items():
            if value:
                lines.append(f"  {key}: {value}")
        lines.append("")

        # Failure Breakdown
        if report.failure_breakdown:
            lines.append("1. FAILURE BREAKDOWN BY CATEGORY")
            lines.append("-" * 80)
            lines.append(f"{'Category':<30} {'Count':>8} {'%':>6} {'Examples':>10} {'Runs':>8}")
            lines.append("-" * 80)
            for row in report.failure_breakdown:
                bar = "█" * int(row.percentage / 5)  # 5% per block
                lines.append(
                    f"{row.category:<30} {row.count:>8} {row.percentage:>5.1f}% {row.affected_examples:>10} {row.affected_runs:>8}"
                )
            lines.append("")

        # Status Breakdown
        if report.status_breakdown:
            lines.append("2. STATUS BREAKDOWN (ALL EXAMPLES)")
            lines.append("-" * 80)
            lines.append(f"{'Status':<30} {'Count':>8} {'%':>6} {'Top Reasons':<30}")
            lines.append("-" * 80)
            for row in report.status_breakdown:
                reasons = ', '.join(row.top_escalation_reasons[:2]) if row.top_escalation_reasons else ''
                lines.append(
                    f"{row.status:<30} {row.count:>8} {row.percentage:>5.1f}% {reasons:<30}"
                )
            lines.append("")

        # Top Errors
        if report.top_errors:
            lines.append("3. TOP ERROR TYPES (Fix Rate Analysis)")
            lines.append("-" * 80)
            lines.append(f"{'Error Category':<30} {'Count':>8} {'Fix Rate':>10} {'Examples':>10}")
            lines.append("-" * 80)
            for row in report.top_errors:
                fix_bar = "█" * int(row.fix_rate / 10)  # 10% per block
                lines.append(
                    f"{row.error_category:<30} {row.count:>8} {row.fix_rate:>9.1f}% {row.affected_examples:>10}"
                )
            lines.append("")

        # NEEDS_REVIEW
        if report.needs_review:
            lines.append("4. NEEDS_REVIEW ESCALATIONS")
            lines.append("-" * 80)
            lines.append(f"{'Escalation Reason':<40} {'Count':>8} {'%':>6}")
            lines.append("-" * 80)
            for row in report.needs_review:
                lines.append(
                    f"{row.escalation_reason:<40} {row.count:>8} {row.percentage:>5.1f}%"
                )
            lines.append("")

        # Timeouts
        if report.timeouts:
            lines.append("5. TIMEOUT DISTRIBUTION BY PHASE")
            lines.append("-" * 80)
            lines.append(f"{'Phase':<30} {'Count':>8} {'%':>6}")
            lines.append("-" * 80)
            for row in report.timeouts:
                bar = "█" * int(row.percentage / 5)
                lines.append(
                    f"{row.phase:<30} {row.count:>8} {row.percentage:>5.1f}% {bar}"
                )
            lines.append("")

        # Drift Distribution
        if report.drift_distribution:
            lines.append("6. DRIFT SCORE DISTRIBUTION")
            lines.append("-" * 80)
            lines.append(f"{'Bucket':<20} {'Count':>8} {'%':>6} {'Distribution':<30}")
            lines.append("-" * 80)
            for row in report.drift_distribution:
                bar = "█" * int(row.percentage / 5)
                lines.append(
                    f"{row.bucket:<20} {row.count:>8} {row.percentage:>5.1f}% {bar}"
                )
            lines.append("")

        # Query Performance
        if report.query_times_ms:
            lines.append("QUERY PERFORMANCE")
            lines.append("-" * 80)
            total_ms = sum(report.query_times_ms.values())
            for query_name, duration_ms in sorted(report.query_times_ms.items()):
                lines.append(f"  {query_name:<40} {duration_ms:>8.2f} ms")
            lines.append("-" * 80)
            lines.append(f"  {'TOTAL':<40} {total_ms:>8.2f} ms")
            lines.append("")

        lines.append("=" * 80)

        return "\n".join(lines)


def get_database_path() -> str:
    """
    Locate database file.

    Searches for example_reviewer.db in:
    1. ./data/ (current directory)
    2. ../data/ (parent directory)
    3. Project root /data/

    Returns:
        Path to database file

    Raises:
        FileNotFoundError: If database cannot be found
    """
    candidates = [
        Path("data/example_reviewer.db"),
        Path("../data/example_reviewer.db"),
        Path(__file__).parent.parent / "data" / "example_reviewer.db",
    ]

    for candidate in candidates:
        if candidate.exists():
            return str(candidate.resolve())

    raise FileNotFoundError(
        f"Could not find example_reviewer.db. Searched: {[str(c) for c in candidates]}"
    )


def run_analytics(
    format_type: str = "text",
    run_id: Optional[str] = None,
    family: Optional[str] = None,
    phase: Optional[str] = None,
    db_path: Optional[str] = None,
) -> str:
    """
    Run full analytics suite and return formatted report.

    Executes all 5 analytics queries:
    1. Failure breakdown by category
    2. Top error types with fix rates
    3. NEEDS_REVIEW escalations
    4. Timeout distribution
    5. Drift distribution

    Args:
        format_type: Output format ('json' or 'text')
        run_id: Optional filter by run_id
        family: Optional filter by family
        phase: Optional filter by phase
        db_path: Optional database path (auto-detected if not provided)

    Returns:
        Formatted report string

    Raises:
        FileNotFoundError: If database not found
        sqlite3.DatabaseError: If database query fails
    """
    import time

    if db_path is None:
        db_path = get_database_path()

    db = FailureAnalyticsDB(db_path)

    try:
        # Create report
        report = AnalyticsReport(
            timestamp=datetime.utcnow().isoformat(),
            data_scope={
                'run_id': run_id,
                'family': family,
                'phase': phase,
                'database': db_path,
            }
        )

        # Execute analytics queries with timing
        start = time.time()
        report.failure_breakdown = db.get_failure_breakdown(run_id, family, phase)
        report.query_times_ms['failure_breakdown'] = (time.time() - start) * 1000

        start = time.time()
        report.status_breakdown = db.get_status_breakdown(run_id, family)
        report.query_times_ms['status_breakdown'] = (time.time() - start) * 1000

        start = time.time()
        report.top_errors = db.get_top_errors(run_id, family, phase)
        report.query_times_ms['top_errors'] = (time.time() - start) * 1000

        start = time.time()
        report.needs_review = db.get_needs_review_stats(run_id, family, phase)
        report.query_times_ms['needs_review'] = (time.time() - start) * 1000

        start = time.time()
        report.timeouts = db.get_timeout_counts(run_id, family)
        report.query_times_ms['timeouts'] = (time.time() - start) * 1000

        start = time.time()
        report.drift_distribution = db.get_drift_distribution(run_id, family, phase)
        report.query_times_ms['drift_distribution'] = (time.time() - start) * 1000

        # Format and return
        if format_type.lower() == "json":
            return AnalyticsFormatter.to_json(report)
        else:
            return AnalyticsFormatter.to_text(report)

    finally:
        db.close()


def main():
    """Parse CLI arguments and run analytics."""
    parser = argparse.ArgumentParser(
        description="Failure Analytics Reporting Tool for Example Reviewer Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tools/report_failure_analytics.py --format json
  python tools/report_failure_analytics.py --family zip --format text
  python tools/report_failure_analytics.py --run-id abc123 --format json
        """
    )

    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="text",
        help="Output format (default: text)"
    )

    parser.add_argument(
        "--run-id",
        type=str,
        default=None,
        help="Filter by specific run ID"
    )

    parser.add_argument(
        "--family",
        type=str,
        default=None,
        help="Filter by product family (zip, pdf, words, etc.)"
    )

    parser.add_argument(
        "--phase",
        type=str,
        default=None,
        help="Filter by pipeline phase"
    )

    parser.add_argument(
        "--db",
        type=str,
        default=None,
        help="Path to database file (auto-detected if not provided)"
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Configure logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        report = run_analytics(
            format_type=args.format,
            run_id=args.run_id,
            family=args.family,
            phase=args.phase,
            db_path=args.db,
        )
        print(report)
        return 0
    except FileNotFoundError as e:
        logger.error(f"Error: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
