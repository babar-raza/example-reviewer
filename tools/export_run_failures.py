"""
Export detailed failure information for a specific run.

This tool exports comprehensive failure data from the database:
- Example metadata (id, file_path, status)
- Failure reasons and escalation details
- Last compile attempt: success, errors, compiler output excerpt
- Last runtime attempt: success, exception info, stdout excerpt
- Input file selections and example-repo substitution status

Usage:
    python tools/export_run_failures.py --db-path <path> --run-id <run_id> --out <output.json>

Output:
    JSON file containing detailed failure information for all examples in the run.
"""

import argparse
import json
import logging
import sqlite3
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


class FailureExporter:
    """Export detailed failure information from the database."""

    def __init__(self, db_path: str):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database

        Raises:
            FileNotFoundError: If database does not exist
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

    def get_run_examples(self, run_id: str) -> List[Dict[str, Any]]:
        """
        Get all examples for a specific run with their current state.

        Args:
            run_id: The run ID to query

        Returns:
            List of example records with run-specific state
        """
        query = """
        SELECT
            er.example_id,
            er.family,
            er.file_path,
            er.language,
            er.source_type,
            er.original_code,
            er.section_heading,
            er.description_context,
            er.topic,
            ers.status,
            ers.failure_reason,
            ers.escalation_reason,
            ers.compilable_code,
            ers.verified_code
        FROM example_records er
        JOIN example_run_state ers ON er.example_id = ers.example_id
        WHERE ers.run_id = ?
        ORDER BY er.file_path, er.example_id
        """

        cursor = self.connection.execute(query, (run_id,))
        rows = cursor.fetchall()

        examples = []
        for row in rows:
            example = {
                'example_id': row['example_id'],
                'family': row['family'],
                'file_path': row['file_path'],
                'language': row['language'],
                'source_type': row['source_type'],
                'status': row['status'],
                'failure_reason': row['failure_reason'],
                'escalation_reason': row['escalation_reason'],
                'section_heading': row['section_heading'],
                'description_context': row['description_context'],
                'topic': row['topic'],
                'has_original_code': bool(row['original_code']),
                'has_compilable_code': bool(row['compilable_code']),
                'has_verified_code': bool(row['verified_code']),
            }
            examples.append(example)

        logger.info(f"Found {len(examples)} examples for run {run_id}")
        return examples

    def get_last_compile_attempt(self, example_id: str, run_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the last compile attempt for an example in a specific run.

        Args:
            example_id: The example ID
            run_id: The run ID

        Returns:
            Dict with compile attempt details or None
        """
        query = """
        SELECT
            attempt_id,
            success,
            compiler_log_ref,
            input_code_ref,
            output_code_ref,
            error_messages,
            warnings,
            timestamp
        FROM compile_attempts
        WHERE example_id = ? AND run_id = ?
        ORDER BY timestamp DESC
        LIMIT 1
        """

        cursor = self.connection.execute(query, (example_id, run_id))
        row = cursor.fetchone()

        if not row:
            return None

        # Try to load error messages from JSON
        error_messages = []
        if row['error_messages']:
            try:
                error_messages = json.loads(row['error_messages'])
            except json.JSONDecodeError:
                error_messages = [row['error_messages']]

        # Load compiler log excerpt if available
        compiler_output = None
        if row['compiler_log_ref']:
            compiler_output = self._load_artifact_excerpt(row['compiler_log_ref'], max_lines=50)

        return {
            'attempt_id': row['attempt_id'],
            'success': bool(row['success']),
            'error_summary': '; '.join(error_messages[:5]) if error_messages else None,
            'error_messages': error_messages,
            'compiler_output_excerpt': compiler_output,
            'compiler_log_ref': row['compiler_log_ref'],
            'input_code_ref': row['input_code_ref'],
            'output_code_ref': row['output_code_ref'],
            'timestamp': row['timestamp'],
        }

    def get_last_runtime_attempt(self, example_id: str, run_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the last runtime attempt for an example in a specific run.

        Args:
            example_id: The example ID
            run_id: The run ID

        Returns:
            Dict with runtime attempt details or None
        """
        query = """
        SELECT
            attempt_id,
            success,
            sample_ref,
            scenario,
            exit_code,
            stdout,
            stderr,
            exception_type,
            exception_message,
            runtime_log_ref,
            timestamp
        FROM runtime_attempts
        WHERE example_id = ? AND run_id = ?
        ORDER BY timestamp DESC
        LIMIT 1
        """

        cursor = self.connection.execute(query, (example_id, run_id))
        row = cursor.fetchone()

        if not row:
            return None

        # Truncate stdout/stderr to reasonable size
        stdout_excerpt = row['stdout'][:1000] if row['stdout'] else None
        stderr_excerpt = row['stderr'][:1000] if row['stderr'] else None

        return {
            'attempt_id': row['attempt_id'],
            'success': bool(row['success']),
            'sample_ref': row['sample_ref'],
            'scenario': row['scenario'],
            'exit_code': row['exit_code'],
            'exception_type': row['exception_type'],
            'exception_message': row['exception_message'],
            'stdout_excerpt': stdout_excerpt,
            'stderr_excerpt': stderr_excerpt,
            'runtime_log_ref': row['runtime_log_ref'],
            'timestamp': row['timestamp'],
        }

    def get_compile_attempt_count(self, example_id: str, run_id: str) -> int:
        """Get total number of compile attempts for an example."""
        query = """
        SELECT COUNT(*) as count
        FROM compile_attempts
        WHERE example_id = ? AND run_id = ?
        """
        cursor = self.connection.execute(query, (example_id, run_id))
        row = cursor.fetchone()
        return row['count'] if row else 0

    def get_runtime_attempt_count(self, example_id: str, run_id: str) -> int:
        """Get total number of runtime attempts for an example."""
        query = """
        SELECT COUNT(*) as count
        FROM runtime_attempts
        WHERE example_id = ? AND run_id = ?
        """
        cursor = self.connection.execute(query, (example_id, run_id))
        row = cursor.fetchone()
        return row['count'] if row else 0

    def _load_artifact_excerpt(self, artifact_ref: str, max_lines: int = 50) -> Optional[str]:
        """
        Load excerpt from artifact file.

        Args:
            artifact_ref: Artifact file path
            max_lines: Maximum number of lines to read

        Returns:
            Text excerpt or None
        """
        if not artifact_ref:
            return None

        artifact_path = Path(artifact_ref)
        if not artifact_path.exists():
            # Try relative to database directory
            db_dir = Path(self.db_path).parent.parent
            artifact_path = db_dir / artifact_ref
            if not artifact_path.exists():
                return None

        try:
            with open(artifact_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = [f.readline() for _ in range(max_lines)]
                return ''.join(lines)
        except Exception as e:
            logger.warning(f"Could not load artifact {artifact_ref}: {e}")
            return None

    def export_run_failures(self, run_id: str) -> Dict[str, Any]:
        """
        Export all failure information for a run.

        Args:
            run_id: The run ID to export

        Returns:
            Dict containing comprehensive failure data
        """
        logger.info(f"Exporting failures for run {run_id}")

        examples = self.get_run_examples(run_id)

        # Enrich each example with attempt details
        for example in examples:
            example_id = example['example_id']

            # Add compile attempt info
            compile_count = self.get_compile_attempt_count(example_id, run_id)
            example['compile_attempts_count'] = compile_count

            last_compile = self.get_last_compile_attempt(example_id, run_id)
            example['last_compile_attempt'] = last_compile

            # Add runtime attempt info
            runtime_count = self.get_runtime_attempt_count(example_id, run_id)
            example['runtime_attempts_count'] = runtime_count

            last_runtime = self.get_last_runtime_attempt(example_id, run_id)
            example['last_runtime_attempt'] = last_runtime

        # Separate into categories
        failures_by_status = {}
        for example in examples:
            status = example['status']
            if status not in failures_by_status:
                failures_by_status[status] = []
            failures_by_status[status].append(example)

        # Build export structure
        export_data = {
            'run_id': run_id,
            'timestamp': datetime.utcnow().isoformat(),
            'database_path': self.db_path,
            'summary': {
                'total_examples': len(examples),
                'status_breakdown': {
                    status: len(items) for status, items in failures_by_status.items()
                }
            },
            'failures_by_status': failures_by_status,
            'all_examples': examples,
        }

        logger.info(f"Exported {len(examples)} examples")
        return export_data


def main():
    """Parse CLI arguments and export failures."""
    parser = argparse.ArgumentParser(
        description="Export detailed failure information for a specific run",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--db-path",
        type=str,
        required=True,
        help="Path to SQLite database"
    )

    parser.add_argument(
        "--run-id",
        type=str,
        required=True,
        help="Run ID to export failures for"
    )

    parser.add_argument(
        "--out",
        type=str,
        required=True,
        help="Output JSON file path"
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
        # Create output directory if needed
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        # Export failures
        exporter = FailureExporter(args.db_path)
        try:
            export_data = exporter.export_run_failures(args.run_id)

            # Write to file
            with open(out_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2)

            logger.info(f"Exported failures to {out_path}")
            logger.info(f"Total examples: {export_data['summary']['total_examples']}")
            logger.info(f"Status breakdown: {export_data['summary']['status_breakdown']}")

            return 0
        finally:
            exporter.close()

    except FileNotFoundError as e:
        logger.error(f"Error: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
