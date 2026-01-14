"""
Database module for Example Reviewer Pipeline.
Uses SQLite with WAL mode for concurrent access.
"""

import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

from .models import (
    ExampleRecord, ExampleStatus, SourceType, Location, GistInfo,
    CompileAttempt, RuntimeAttempt, MarkdownEdit, CommitRecord,
    RunRecord, TelemetryEvent, EditType
)

logger = logging.getLogger(__name__)


class Database:
    """
    SQLite database for Example Reviewer Pipeline.
    
    Provides CRUD operations for all pipeline entities:
    - Example records
    - Compile attempts
    - Runtime attempts
    - Markdown edits
    - Commit records
    - Run records
    - Telemetry events
    """
    
    SCHEMA = """
    -- Example records table
    CREATE TABLE IF NOT EXISTS example_records (
        example_id TEXT PRIMARY KEY,
        family TEXT NOT NULL,
        file_path TEXT NOT NULL,
        source_type TEXT NOT NULL DEFAULT 'inline',
        language TEXT NOT NULL DEFAULT 'csharp',
        location_block_index INTEGER DEFAULT 0,
        location_start_line INTEGER DEFAULT 0,
        location_end_line INTEGER DEFAULT 0,
        location_anchor TEXT DEFAULT '',
        gist_owner TEXT,
        gist_id TEXT,
        gist_filename TEXT,
        original_code TEXT NOT NULL,
        compilable_code TEXT,
        verified_code TEXT,
        status TEXT NOT NULL DEFAULT 'DISCOVERED',
        failure_reason TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    
    CREATE INDEX IF NOT EXISTS idx_examples_family ON example_records(family);
    CREATE INDEX IF NOT EXISTS idx_examples_status ON example_records(status);
    CREATE INDEX IF NOT EXISTS idx_examples_file_path ON example_records(file_path);
    
    -- Compile attempts table
    CREATE TABLE IF NOT EXISTS compile_attempts (
        attempt_id TEXT PRIMARY KEY,
        example_id TEXT NOT NULL,
        family TEXT NOT NULL,
        dll_version TEXT,
        success INTEGER NOT NULL DEFAULT 0,
        compiler_log_ref TEXT,
        input_code_ref TEXT,
        output_code_ref TEXT,
        llm_request_ref TEXT,
        llm_response_ref TEXT,
        error_messages TEXT,
        warnings TEXT,
        timestamp TEXT NOT NULL,
        FOREIGN KEY (example_id) REFERENCES example_records(example_id)
    );
    
    CREATE INDEX IF NOT EXISTS idx_compile_example ON compile_attempts(example_id);
    CREATE INDEX IF NOT EXISTS idx_compile_family ON compile_attempts(family);
    
    -- Runtime attempts table
    CREATE TABLE IF NOT EXISTS runtime_attempts (
        attempt_id TEXT PRIMARY KEY,
        example_id TEXT NOT NULL,
        family TEXT NOT NULL,
        sample_ref TEXT,
        scenario TEXT,
        success INTEGER NOT NULL DEFAULT 0,
        runtime_log_ref TEXT,
        exit_code INTEGER DEFAULT -1,
        stdout TEXT,
        stderr TEXT,
        exception_type TEXT,
        exception_message TEXT,
        output_files TEXT,
        environment TEXT,
        retrieved_examples_refs TEXT,
        llm_request_ref TEXT,
        llm_response_ref TEXT,
        timestamp TEXT NOT NULL,
        FOREIGN KEY (example_id) REFERENCES example_records(example_id)
    );
    
    CREATE INDEX IF NOT EXISTS idx_runtime_example ON runtime_attempts(example_id);
    CREATE INDEX IF NOT EXISTS idx_runtime_family ON runtime_attempts(family);
    
    -- Markdown edits table
    CREATE TABLE IF NOT EXISTS markdown_edits (
        edit_id TEXT PRIMARY KEY,
        file_path TEXT NOT NULL,
        example_id TEXT NOT NULL,
        family TEXT NOT NULL,
        edit_type TEXT NOT NULL DEFAULT 'inline_replace',
        diff_ref TEXT,
        old_code TEXT,
        new_code TEXT,
        timestamp TEXT NOT NULL,
        FOREIGN KEY (example_id) REFERENCES example_records(example_id)
    );
    
    CREATE INDEX IF NOT EXISTS idx_edits_example ON markdown_edits(example_id);
    CREATE INDEX IF NOT EXISTS idx_edits_file ON markdown_edits(file_path);
    
    -- Commit records table
    CREATE TABLE IF NOT EXISTS commit_records (
        commit_id TEXT PRIMARY KEY,
        run_id TEXT NOT NULL,
        family TEXT NOT NULL,
        hash TEXT,
        message TEXT,
        description TEXT,
        touched_files TEXT,
        timestamp TEXT NOT NULL
    );
    
    CREATE INDEX IF NOT EXISTS idx_commits_run ON commit_records(run_id);
    CREATE INDEX IF NOT EXISTS idx_commits_family ON commit_records(family);
    
    -- Run records table
    CREATE TABLE IF NOT EXISTS run_records (
        run_id TEXT PRIMARY KEY,
        family TEXT NOT NULL,
        started_at TEXT NOT NULL,
        completed_at TEXT,
        status TEXT NOT NULL DEFAULT 'running',
        phases_completed TEXT,
        current_phase TEXT,
        examples_processed INTEGER DEFAULT 0,
        examples_successful INTEGER DEFAULT 0,
        examples_failed INTEGER DEFAULT 0,
        error TEXT
    );
    
    CREATE INDEX IF NOT EXISTS idx_runs_family ON run_records(family);
    CREATE INDEX IF NOT EXISTS idx_runs_status ON run_records(status);
    
    -- Telemetry events table
    CREATE TABLE IF NOT EXISTS telemetry_events (
        event_id TEXT PRIMARY KEY,
        run_id TEXT NOT NULL,
        family TEXT NOT NULL,
        event_type TEXT NOT NULL,
        phase TEXT,
        example_id TEXT,
        duration_ms INTEGER,
        success INTEGER DEFAULT 1,
        metadata TEXT,
        timestamp TEXT NOT NULL
    );
    
    CREATE INDEX IF NOT EXISTS idx_telemetry_run ON telemetry_events(run_id);
    CREATE INDEX IF NOT EXISTS idx_telemetry_type ON telemetry_events(event_type);
    
    -- API reference cache table
    CREATE TABLE IF NOT EXISTS api_reference_cache (
        cache_id TEXT PRIMARY KEY,
        family TEXT NOT NULL,
        namespace TEXT NOT NULL,
        class_name TEXT NOT NULL,
        method_name TEXT,
        content TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    
    CREATE INDEX IF NOT EXISTS idx_api_family ON api_reference_cache(family);
    CREATE INDEX IF NOT EXISTS idx_api_namespace ON api_reference_cache(namespace);
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path) if db_path else Path("data/example_reviewer.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
    
    @contextmanager
    def get_connection(self):
        """Get a database connection with context management."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    @property
    def conn(self) -> sqlite3.Connection:
        """Get persistent connection (for backward compatibility)."""
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn
    
    def initialize_schema(self) -> None:
        """Initialize database schema."""
        with self.get_connection() as conn:
            conn.executescript(self.SCHEMA)
        logger.info(f"Database initialized at {self.db_path}")
    
    def close(self) -> None:
        """Close persistent connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
    
    # =========================================================================
    # EXAMPLE RECORDS
    # =========================================================================
    
    def save_example(self, example: ExampleRecord) -> str:
        """Save or update an example record."""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO example_records (
                    example_id, family, file_path, source_type, language,
                    location_block_index, location_start_line, location_end_line, location_anchor,
                    gist_owner, gist_id, gist_filename,
                    original_code, compilable_code, verified_code,
                    status, failure_reason, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                example.example_id,
                example.family,
                example.file_path,
                example.source_type.value,
                example.language,
                example.location.block_index,
                example.location.start_line,
                example.location.end_line,
                example.location.anchor,
                example.gist.owner if example.gist else None,
                example.gist.gist_id if example.gist else None,
                example.gist.filename if example.gist else None,
                example.original_code,
                example.compilable_code,
                example.verified_code,
                example.status.value,
                example.failure_reason,
                example.created_at.isoformat(),
                example.updated_at.isoformat(),
            ))
        return example.example_id
    
    def get_example(self, example_id: str) -> Optional[ExampleRecord]:
        """Get an example by ID."""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM example_records WHERE example_id = ?",
                (example_id,)
            ).fetchone()
            
            if row:
                return self._row_to_example(row)
        return None
    
    def get_examples_by_family(
        self,
        family: str,
        status: Optional[ExampleStatus] = None,
        limit: Optional[int] = None,
    ) -> List[ExampleRecord]:
        """Get examples for a family, optionally filtered by status."""
        with self.get_connection() as conn:
            query = "SELECT * FROM example_records WHERE family = ?"
            params = [family]
            
            if status:
                query += " AND status = ?"
                params.append(status.value)
            
            query += " ORDER BY created_at"
            
            if limit:
                query += " LIMIT ?"
                params.append(limit)
            
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_example(row) for row in rows]
    
    def get_examples_by_file(self, file_path: str) -> List[ExampleRecord]:
        """Get all examples from a specific file."""
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM example_records WHERE file_path = ? ORDER BY location_block_index",
                (file_path,)
            ).fetchall()
            return [self._row_to_example(row) for row in rows]
    
    def update_example_status(
        self,
        example_id: str,
        status: ExampleStatus,
        failure_reason: Optional[str] = None,
    ) -> bool:
        """Update example status."""
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE example_records
                SET status = ?, failure_reason = ?, updated_at = ?
                WHERE example_id = ?
            """, (status.value, failure_reason, datetime.utcnow().isoformat(), example_id))
            return conn.total_changes > 0
    
    def update_example_code(
        self,
        example_id: str,
        compilable_code: Optional[str] = None,
        verified_code: Optional[str] = None,
    ) -> bool:
        """Update example code fields."""
        with self.get_connection() as conn:
            updates = []
            params = []
            
            if compilable_code is not None:
                updates.append("compilable_code = ?")
                params.append(compilable_code)
            
            if verified_code is not None:
                updates.append("verified_code = ?")
                params.append(verified_code)
            
            if not updates:
                return False
            
            updates.append("updated_at = ?")
            params.append(datetime.utcnow().isoformat())
            params.append(example_id)
            
            conn.execute(
                f"UPDATE example_records SET {', '.join(updates)} WHERE example_id = ?",
                params
            )
            return conn.total_changes > 0
    
    def delete_examples_by_family(self, family: str) -> int:
        """Delete all examples for a family."""
        with self.get_connection() as conn:
            conn.execute("DELETE FROM example_records WHERE family = ?", (family,))
            return conn.total_changes
    
    def _row_to_example(self, row: sqlite3.Row) -> ExampleRecord:
        """Convert database row to ExampleRecord."""
        gist = None
        if row['gist_owner'] or row['gist_id']:
            gist = GistInfo(
                owner=row['gist_owner'] or '',
                gist_id=row['gist_id'] or '',
                filename=row['gist_filename'] or '',
            )
        
        return ExampleRecord(
            example_id=row['example_id'],
            family=row['family'],
            file_path=row['file_path'],
            source_type=SourceType(row['source_type']),
            language=row['language'],
            location=Location(
                block_index=row['location_block_index'],
                start_line=row['location_start_line'],
                end_line=row['location_end_line'],
                anchor=row['location_anchor'] or '',
            ),
            gist=gist,
            original_code=row['original_code'],
            compilable_code=row['compilable_code'],
            verified_code=row['verified_code'],
            status=ExampleStatus(row['status']),
            failure_reason=row['failure_reason'],
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at']),
        )
    
    # =========================================================================
    # COMPILE ATTEMPTS
    # =========================================================================
    
    def save_compile_attempt(self, attempt: CompileAttempt) -> str:
        """Save a compile attempt."""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO compile_attempts (
                    attempt_id, example_id, family, dll_version, success,
                    compiler_log_ref, input_code_ref, output_code_ref,
                    llm_request_ref, llm_response_ref,
                    error_messages, warnings, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                attempt.attempt_id,
                attempt.example_id,
                attempt.family,
                attempt.dll_version,
                1 if attempt.success else 0,
                attempt.compiler_log_ref,
                attempt.input_code_ref,
                attempt.output_code_ref,
                attempt.llm_request_ref,
                attempt.llm_response_ref,
                json.dumps(attempt.error_messages),
                json.dumps(attempt.warnings),
                attempt.timestamp.isoformat(),
            ))
        return attempt.attempt_id
    
    def get_compile_attempts(self, example_id: str) -> List[CompileAttempt]:
        """Get all compile attempts for an example."""
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM compile_attempts WHERE example_id = ? ORDER BY timestamp",
                (example_id,)
            ).fetchall()
            
            return [self._row_to_compile_attempt(row) for row in rows]
    
    def _row_to_compile_attempt(self, row: sqlite3.Row) -> CompileAttempt:
        """Convert database row to CompileAttempt."""
        return CompileAttempt(
            attempt_id=row['attempt_id'],
            example_id=row['example_id'],
            family=row['family'],
            dll_version=row['dll_version'] or '',
            success=bool(row['success']),
            compiler_log_ref=row['compiler_log_ref'] or '',
            input_code_ref=row['input_code_ref'] or '',
            output_code_ref=row['output_code_ref'] or '',
            llm_request_ref=row['llm_request_ref'] or '',
            llm_response_ref=row['llm_response_ref'] or '',
            error_messages=json.loads(row['error_messages'] or '[]'),
            warnings=json.loads(row['warnings'] or '[]'),
            timestamp=datetime.fromisoformat(row['timestamp']),
        )
    
    # =========================================================================
    # RUNTIME ATTEMPTS
    # =========================================================================
    
    def save_runtime_attempt(self, attempt: RuntimeAttempt) -> str:
        """Save a runtime attempt."""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO runtime_attempts (
                    attempt_id, example_id, family, sample_ref, scenario,
                    success, runtime_log_ref, exit_code, stdout, stderr,
                    exception_type, exception_message, output_files,
                    environment, retrieved_examples_refs,
                    llm_request_ref, llm_response_ref, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                attempt.attempt_id,
                attempt.example_id,
                attempt.family,
                attempt.sample_ref,
                attempt.scenario,
                1 if attempt.success else 0,
                attempt.runtime_log_ref,
                attempt.exit_code,
                attempt.stdout,
                attempt.stderr,
                attempt.exception_type,
                attempt.exception_message,
                json.dumps(attempt.output_files),
                json.dumps(attempt.environment),
                json.dumps(attempt.retrieved_examples_refs),
                attempt.llm_request_ref,
                attempt.llm_response_ref,
                attempt.timestamp.isoformat(),
            ))
        return attempt.attempt_id
    
    def get_runtime_attempts(self, example_id: str) -> List[RuntimeAttempt]:
        """Get all runtime attempts for an example."""
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM runtime_attempts WHERE example_id = ? ORDER BY timestamp",
                (example_id,)
            ).fetchall()
            
            return [self._row_to_runtime_attempt(row) for row in rows]
    
    def _row_to_runtime_attempt(self, row: sqlite3.Row) -> RuntimeAttempt:
        """Convert database row to RuntimeAttempt."""
        return RuntimeAttempt(
            attempt_id=row['attempt_id'],
            example_id=row['example_id'],
            family=row['family'],
            sample_ref=row['sample_ref'] or '',
            scenario=row['scenario'] or '',
            success=bool(row['success']),
            runtime_log_ref=row['runtime_log_ref'] or '',
            exit_code=row['exit_code'],
            stdout=row['stdout'] or '',
            stderr=row['stderr'] or '',
            exception_type=row['exception_type'],
            exception_message=row['exception_message'],
            output_files=json.loads(row['output_files'] or '[]'),
            environment=json.loads(row['environment'] or '{}'),
            retrieved_examples_refs=json.loads(row['retrieved_examples_refs'] or '[]'),
            llm_request_ref=row['llm_request_ref'] or '',
            llm_response_ref=row['llm_response_ref'] or '',
            timestamp=datetime.fromisoformat(row['timestamp']),
        )
    
    # =========================================================================
    # MARKDOWN EDITS
    # =========================================================================
    
    def save_markdown_edit(self, edit: MarkdownEdit) -> str:
        """Save a markdown edit."""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO markdown_edits (
                    edit_id, file_path, example_id, family,
                    edit_type, diff_ref, old_code, new_code, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                edit.edit_id,
                edit.file_path,
                edit.example_id,
                edit.family,
                edit.edit_type.value,
                edit.diff_ref,
                edit.old_code,
                edit.new_code,
                edit.timestamp.isoformat(),
            ))
        return edit.edit_id
    
    def get_edits_by_file(self, file_path: str) -> List[MarkdownEdit]:
        """Get all edits for a file."""
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM markdown_edits WHERE file_path = ? ORDER BY timestamp",
                (file_path,)
            ).fetchall()
            
            return [self._row_to_edit(row) for row in rows]
    
    def _row_to_edit(self, row: sqlite3.Row) -> MarkdownEdit:
        """Convert database row to MarkdownEdit."""
        return MarkdownEdit(
            edit_id=row['edit_id'],
            file_path=row['file_path'],
            example_id=row['example_id'],
            family=row['family'],
            edit_type=EditType(row['edit_type']),
            diff_ref=row['diff_ref'] or '',
            old_code=row['old_code'] or '',
            new_code=row['new_code'] or '',
            timestamp=datetime.fromisoformat(row['timestamp']),
        )
    
    # =========================================================================
    # RUN RECORDS
    # =========================================================================
    
    def create_run(self, family: str, current_phase: str = "") -> str:
        """Create a new run record."""
        run = RunRecord(family=family, current_phase=current_phase)
        
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO run_records (
                    run_id, family, started_at, status, current_phase,
                    phases_completed, examples_processed, examples_successful, examples_failed
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run.run_id,
                run.family,
                run.started_at.isoformat(),
                run.status,
                run.current_phase,
                json.dumps(run.phases_completed),
                run.examples_processed,
                run.examples_successful,
                run.examples_failed,
            ))
        
        return run.run_id
    
    def complete_run(
        self,
        run_id: str,
        status: str = "completed",
        examples_processed: int = 0,
        examples_verified: int = 0,
        error: Optional[str] = None,
    ) -> None:
        """Mark a run as completed."""
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE run_records
                SET completed_at = ?, status = ?, examples_processed = ?,
                    examples_successful = ?, error = ?
                WHERE run_id = ?
            """, (
                datetime.utcnow().isoformat(),
                status,
                examples_processed,
                examples_verified,
                error,
                run_id,
            ))
    
    def get_run(self, run_id: str) -> Optional[RunRecord]:
        """Get a run by ID."""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM run_records WHERE run_id = ?",
                (run_id,)
            ).fetchone()
            
            if row:
                return self._row_to_run(row)
        return None
    
    def _row_to_run(self, row: sqlite3.Row) -> RunRecord:
        """Convert database row to RunRecord."""
        return RunRecord(
            run_id=row['run_id'],
            family=row['family'],
            started_at=datetime.fromisoformat(row['started_at']),
            completed_at=datetime.fromisoformat(row['completed_at']) if row['completed_at'] else None,
            status=row['status'],
            phases_completed=json.loads(row['phases_completed'] or '[]'),
            current_phase=row['current_phase'] or '',
            examples_processed=row['examples_processed'],
            examples_successful=row['examples_successful'],
            examples_failed=row['examples_failed'],
            error=row['error'],
        )
    
    # =========================================================================
    # TELEMETRY
    # =========================================================================
    
    def save_telemetry_event(self, event: TelemetryEvent) -> str:
        """Save a telemetry event."""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO telemetry_events (
                    event_id, run_id, family, event_type, phase,
                    example_id, duration_ms, success, metadata, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event.event_id,
                event.run_id,
                event.family,
                event.event_type,
                event.phase,
                event.example_id,
                event.duration_ms,
                1 if event.success else 0,
                json.dumps(event.metadata),
                event.timestamp.isoformat(),
            ))
        return event.event_id
    
    # =========================================================================
    # STATISTICS
    # =========================================================================
    
    def get_family_stats(self, family: str) -> Dict[str, Any]:
        """Get statistics for a family."""
        with self.get_connection() as conn:
            # Count by status
            rows = conn.execute("""
                SELECT status, COUNT(*) as count
                FROM example_records
                WHERE family = ?
                GROUP BY status
            """, (family,)).fetchall()
            
            status_counts = {row['status']: row['count'] for row in rows}
            total = sum(status_counts.values())
            
            # Get recent runs
            recent_runs = conn.execute("""
                SELECT * FROM run_records
                WHERE family = ?
                ORDER BY started_at DESC
                LIMIT 5
            """, (family,)).fetchall()
            
            return {
                'family': family,
                'total_examples': total,
                'by_status': status_counts,
                'recent_runs': [
                    {
                        'run_id': r['run_id'],
                        'status': r['status'],
                        'started_at': r['started_at'],
                        'examples_processed': r['examples_processed'],
                    }
                    for r in recent_runs
                ],
            }
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Get statistics for all families."""
        with self.get_connection() as conn:
            # Get all families
            families = conn.execute(
                "SELECT DISTINCT family FROM example_records"
            ).fetchall()
            
            stats = {}
            for row in families:
                family = row['family']
                stats[family] = self.get_family_stats(family)
            
            return stats
