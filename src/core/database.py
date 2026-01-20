"""
Database module for Example Reviewer Pipeline.
Uses SQLite with WAL mode for concurrent access.
"""

import sqlite3
import json
import logging
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

from .models import (
    ExampleRecord, ExampleStatus, SourceType, Location, GistInfo,
    CompileAttempt, RuntimeAttempt, MarkdownEdit, CommitRecord,
    RunRecord, TelemetryEvent, TelemetryRun, EditType,
    ReviewResult, ReviewIssue, IssueSeverity, IssueType
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
        updated_at TEXT NOT NULL,
        section_heading TEXT,
        description_context TEXT,
        topic TEXT,
        drift_score REAL,
        drift_similarity REAL,
        example_key TEXT
    );

    CREATE INDEX IF NOT EXISTS idx_examples_family ON example_records(family);
    CREATE INDEX IF NOT EXISTS idx_examples_status ON example_records(status);
    CREATE INDEX IF NOT EXISTS idx_examples_file_path ON example_records(file_path);
    CREATE INDEX IF NOT EXISTS idx_examples_drift ON example_records(drift_score);
    CREATE UNIQUE INDEX IF NOT EXISTS idx_example_key ON example_records(family, example_key);

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

    -- Review results table (Phase E: Final Review)
    CREATE TABLE IF NOT EXISTS review_results (
        review_id TEXT PRIMARY KEY,
        file_path TEXT NOT NULL,
        run_id TEXT NOT NULL,
        family TEXT NOT NULL,
        approved INTEGER NOT NULL DEFAULT 0,
        review_attempt INTEGER DEFAULT 1,
        llm_response TEXT,
        timestamp TEXT NOT NULL,
        FOREIGN KEY (run_id) REFERENCES run_records(run_id)
    );

    CREATE INDEX IF NOT EXISTS idx_review_run ON review_results(run_id);
    CREATE INDEX IF NOT EXISTS idx_review_file ON review_results(file_path);
    CREATE INDEX IF NOT EXISTS idx_review_family ON review_results(family);

    -- Review issues table (issues found during final review)
    CREATE TABLE IF NOT EXISTS review_issues (
        issue_id TEXT PRIMARY KEY,
        review_id TEXT NOT NULL,
        example_id TEXT NOT NULL,
        issue_type TEXT NOT NULL DEFAULT 'other',
        description TEXT NOT NULL,
        suggestion TEXT,
        severity TEXT DEFAULT 'warning',
        resolved INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        FOREIGN KEY (review_id) REFERENCES review_results(review_id),
        FOREIGN KEY (example_id) REFERENCES example_records(example_id)
    );

    CREATE INDEX IF NOT EXISTS idx_issue_review ON review_issues(review_id);
    CREATE INDEX IF NOT EXISTS idx_issue_example ON review_issues(example_id);
    CREATE INDEX IF NOT EXISTS idx_issue_severity ON review_issues(severity);

    -- Gist publications table (track gist uploads)
    CREATE TABLE IF NOT EXISTS gist_publications (
        publication_id TEXT PRIMARY KEY,
        example_id TEXT NOT NULL,
        family TEXT NOT NULL,
        old_gist_id TEXT,
        new_gist_id TEXT NOT NULL,
        new_gist_url TEXT NOT NULL,
        code_hash TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'published',
        timestamp TEXT NOT NULL,
        FOREIGN KEY (example_id) REFERENCES example_records(example_id)
    );

    CREATE INDEX IF NOT EXISTS idx_gist_pub_example ON gist_publications(example_id);
    CREATE INDEX IF NOT EXISTS idx_gist_pub_family ON gist_publications(family);

    -- Telemetry runs table (full HTTP API schema ~40 fields)
    CREATE TABLE IF NOT EXISTS telemetry_runs (
        event_id TEXT PRIMARY KEY,
        run_id TEXT NOT NULL,
        created_at TEXT NOT NULL,
        start_time TEXT NOT NULL,
        agent_name TEXT NOT NULL DEFAULT 'example-reviewer',
        job_type TEXT NOT NULL,
        end_time TEXT,
        status TEXT NOT NULL DEFAULT 'running',
        product TEXT DEFAULT '',
        product_family TEXT DEFAULT '',
        platform TEXT DEFAULT 'dotnet',
        subdomain TEXT DEFAULT '',
        website TEXT DEFAULT '',
        website_section TEXT DEFAULT '',
        item_name TEXT DEFAULT '',
        items_discovered INTEGER DEFAULT 0,
        items_succeeded INTEGER DEFAULT 0,
        items_failed INTEGER DEFAULT 0,
        items_skipped INTEGER DEFAULT 0,
        duration_ms INTEGER DEFAULT 0,
        input_summary TEXT DEFAULT '',
        output_summary TEXT DEFAULT '',
        source_ref TEXT DEFAULT '',
        target_ref TEXT DEFAULT '',
        error_summary TEXT,
        error_details TEXT,
        git_repo TEXT DEFAULT '',
        git_branch TEXT DEFAULT '',
        git_commit_hash TEXT DEFAULT '',
        git_run_tag TEXT DEFAULT '',
        git_commit_source TEXT DEFAULT 'llm',
        git_commit_author TEXT DEFAULT 'Example Reviewer <example-reviewer@aspose.net>',
        git_commit_timestamp TEXT,
        host TEXT DEFAULT '',
        environment TEXT DEFAULT 'dev',
        trigger_type TEXT DEFAULT 'manual',
        metrics_json TEXT DEFAULT '{}',
        context_json TEXT DEFAULT '{}',
        api_posted INTEGER DEFAULT 0,
        api_posted_at TEXT,
        api_retry_count INTEGER DEFAULT 0,
        insight_id TEXT,
        parent_run_id TEXT
    );

    CREATE INDEX IF NOT EXISTS idx_telemetry_runs_run ON telemetry_runs(run_id);
    CREATE INDEX IF NOT EXISTS idx_telemetry_runs_status ON telemetry_runs(status);
    CREATE INDEX IF NOT EXISTS idx_telemetry_runs_family ON telemetry_runs(product_family);
    CREATE INDEX IF NOT EXISTS idx_telemetry_runs_agent ON telemetry_runs(agent_name);

    -- Run fingerprints table (Track 1: C.8)
    CREATE TABLE IF NOT EXISTS run_fingerprints (
        run_id TEXT PRIMARY KEY,
        config_hash TEXT NOT NULL,
        selection_hash TEXT,
        fingerprint_json TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (run_id) REFERENCES run_records(run_id)
    );

    CREATE INDEX IF NOT EXISTS idx_fingerprints_config_hash ON run_fingerprints(config_hash);
    CREATE INDEX IF NOT EXISTS idx_fingerprints_selection_hash ON run_fingerprints(selection_hash);
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

    def connect(self) -> sqlite3.Connection:
        """Open and return a persistent connection (legacy API)."""
        return self.conn
    
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
            existing = conn.execute(
                "SELECT family FROM example_records WHERE example_id = ?",
                (example.example_id,),
            ).fetchone()
            if existing and existing["family"] != example.family:
                example.example_id = example.generate_id()

            # Ensure example_key is populated
            if not example.example_key:
                example.example_key = example.generate_example_key()

            conn.execute("""
                INSERT OR REPLACE INTO example_records (
                    example_id, family, file_path, source_type, language,
                    location_block_index, location_start_line, location_end_line, location_anchor,
                    gist_owner, gist_id, gist_filename,
                    original_code, compilable_code, verified_code,
                    status, failure_reason, created_at, updated_at,
                    section_heading, description_context, topic, example_key
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                example.section_heading,
                example.description_context,
                example.topic,
                example.example_key,
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

            # Deterministic ordering: example_key (primary), then example_id (tie-breaker)
            query += " ORDER BY example_key ASC, example_id ASC"

            if limit:
                query += " LIMIT ?"
                params.append(limit)

            rows = conn.execute(query, params).fetchall()
            return [self._row_to_example(row) for row in rows]
    
    def get_examples_by_file(self, file_path: str) -> List[ExampleRecord]:
        """Get all examples from a specific file."""
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM example_records WHERE file_path = ? ORDER BY location_block_index, example_key ASC, example_id ASC",
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

    def update_example_original_code(
        self,
        example_id: str,
        original_code: str,
    ) -> bool:
        """
        Update the original_code field for an example.

        Used by gist backfill to populate gist source content after discovery.

        Args:
            example_id: Example identifier
            original_code: The fetched gist source code

        Returns:
            True if update successful, False otherwise
        """
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE example_records
                SET original_code = ?, updated_at = ?
                WHERE example_id = ?
            """, (original_code, datetime.utcnow().isoformat(), example_id))
            return conn.total_changes > 0

    def update_snippet(
        self,
        example_id: str,
        drift_score: Optional[float] = None,
        drift_similarity: Optional[float] = None,
    ) -> bool:
        """
        Update drift tracking fields for an example.

        Used by drift detector to store drift scores after each LLM fix iteration.

        Args:
            example_id: Example identifier
            drift_score: Drift score (0.0=identical, 1.0=completely different)
            drift_similarity: Similarity score (1.0=identical, 0.0=completely different)

        Returns:
            True if update successful, False otherwise
        """
        with self.get_connection() as conn:
            updates = []
            params = []

            if drift_score is not None:
                updates.append("drift_score = ?")
                params.append(drift_score)

            if drift_similarity is not None:
                updates.append("drift_similarity = ?")
                params.append(drift_similarity)

            if not updates:
                return False

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

        # Handle new context fields (may be None for old records)
        section_heading = row['section_heading'] if 'section_heading' in row.keys() else None
        description_context = row['description_context'] if 'description_context' in row.keys() else None
        topic = row['topic'] if 'topic' in row.keys() else None
        example_key = row['example_key'] if 'example_key' in row.keys() else ""

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
            section_heading=section_heading,
            description_context=description_context,
            topic=topic,
            example_key=example_key,
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

    def get_run_stats_from_db(
        self,
        family: str,
        run_id: Optional[str] = None,
    ) -> Dict[str, int]:
        """
        Compute run statistics from actual DB state (not stale counters).

        Queries example_records to get accurate counts based on status.
        This ensures stats reflect true DB state, not accumulated counters.

        Args:
            family: Family identifier
            run_id: Optional run ID to filter by (for future multi-run tracking)

        Returns:
            Dictionary with total_processed, verified, failed counts
        """
        with self.get_connection() as conn:
            # Count examples by status for this family
            counts = conn.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'VERIFIED' OR status = 'MD_UPDATED' OR status = 'FINAL_REVIEW_PASSED' THEN 1 ELSE 0 END) as verified,
                    SUM(CASE WHEN status LIKE '%FAILED%' THEN 1 ELSE 0 END) as failed
                FROM example_records
                WHERE family = ?
            """, (family,)).fetchone()

            return {
                'total_processed': counts['total'] or 0,
                'verified': counts['verified'] or 0,
                'failed': counts['failed'] or 0,
            }

    def complete_run(
        self,
        run_id: str,
        status: str = "completed",
        examples_processed: Optional[int] = None,
        examples_verified: Optional[int] = None,
        error: Optional[str] = None,
        family: Optional[str] = None,
    ) -> None:
        """
        Mark a run as completed.

        If examples_processed or examples_verified are not provided, they will be
        computed from the database state to ensure accuracy.

        Args:
            run_id: Run identifier
            status: Run status ('completed', 'failed', etc.)
            examples_processed: Total examples processed (computed from DB if None)
            examples_verified: Successfully verified examples (computed from DB if None)
            error: Error message if failed
            family: Family identifier (required if examples_processed/verified not provided)
        """
        # If stats not provided, compute from DB
        if examples_processed is None or examples_verified is None:
            if family is None:
                # Get family from run record
                with self.get_connection() as conn:
                    run = conn.execute(
                        "SELECT family FROM run_records WHERE run_id = ?",
                        (run_id,)
                    ).fetchone()
                    if run:
                        family = run['family']

            if family:
                db_stats = self.get_run_stats_from_db(family, run_id)
                examples_processed = db_stats['total_processed']
                examples_verified = db_stats['verified']
            else:
                # Fallback to 0 if family unknown
                examples_processed = 0
                examples_verified = 0

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

    def get_latest_run(self, family: str) -> Optional[RunRecord]:
        """
        Get the most recent run for a family.

        Args:
            family: Product family identifier

        Returns:
            Most recent RunRecord or None if no runs exist
        """
        with self.get_connection() as conn:
            row = conn.execute("""
                SELECT * FROM run_records
                WHERE family = ?
                ORDER BY started_at DESC
                LIMIT 1
            """, (family,)).fetchone()

            if row:
                return self._row_to_run(row)
        return None

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
    # TELEMETRY RUNS (Full HTTP API schema)
    # =========================================================================

    def save_telemetry_run(self, run: TelemetryRun) -> str:
        """
        Save a telemetry run record.

        Args:
            run: TelemetryRun with full ~40 field schema

        Returns:
            event_id of saved record
        """
        with self.get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO telemetry_runs (
                    event_id, run_id, created_at, start_time, agent_name, job_type,
                    end_time, status, product, product_family, platform, subdomain,
                    website, website_section, item_name, items_discovered,
                    items_succeeded, items_failed, items_skipped, duration_ms,
                    input_summary, output_summary, source_ref, target_ref,
                    error_summary, error_details, git_repo, git_branch,
                    git_commit_hash, git_run_tag, git_commit_source, git_commit_author,
                    git_commit_timestamp, host, environment, trigger_type,
                    metrics_json, context_json, api_posted, api_posted_at,
                    api_retry_count, insight_id, parent_run_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run.event_id,
                run.run_id,
                run.created_at.isoformat(),
                run.start_time.isoformat(),
                run.agent_name,
                run.job_type,
                run.end_time.isoformat() if run.end_time else None,
                run.status,
                run.product,
                run.product_family,
                run.platform,
                run.subdomain,
                run.website,
                run.website_section,
                run.item_name,
                run.items_discovered,
                run.items_succeeded,
                run.items_failed,
                run.items_skipped,
                run.duration_ms,
                run.input_summary,
                run.output_summary,
                run.source_ref,
                run.target_ref,
                run.error_summary,
                run.error_details,
                run.git_repo,
                run.git_branch,
                run.git_commit_hash,
                run.git_run_tag,
                run.git_commit_source,
                run.git_commit_author,
                run.git_commit_timestamp.isoformat() if run.git_commit_timestamp else None,
                run.host,
                run.environment,
                run.trigger_type,
                json.dumps(run.metrics_json),
                json.dumps(run.context_json),
                1 if run.api_posted else 0,
                run.api_posted_at.isoformat() if run.api_posted_at else None,
                run.api_retry_count,
                run.insight_id,
                run.parent_run_id,
            ))
        return run.event_id

    def get_telemetry_run(self, event_id: str) -> Optional[TelemetryRun]:
        """
        Get a telemetry run by event_id.

        Args:
            event_id: Unique event identifier

        Returns:
            TelemetryRun or None if not found
        """
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM telemetry_runs WHERE event_id = ?",
                (event_id,)
            ).fetchone()

            if row:
                return self._row_to_telemetry_run(row)
        return None

    def update_telemetry_run(self, event_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update specific fields of a telemetry run.

        Args:
            event_id: Event to update
            updates: Dictionary of field->value pairs to update

        Returns:
            True if updated successfully
        """
        if not updates:
            return False

        # Build dynamic update query
        set_clauses = []
        params = []

        # Map Python field names to column names
        for field, value in updates.items():
            if field in ['metrics_json', 'context_json']:
                set_clauses.append(f"{field} = ?")
                params.append(json.dumps(value))
            elif field in ['end_time', 'created_at', 'start_time', 'git_commit_timestamp', 'api_posted_at']:
                set_clauses.append(f"{field} = ?")
                params.append(value.isoformat() if value else None)
            elif field == 'api_posted':
                set_clauses.append(f"{field} = ?")
                params.append(1 if value else 0)
            else:
                set_clauses.append(f"{field} = ?")
                params.append(value)

        params.append(event_id)

        with self.get_connection() as conn:
            conn.execute(
                f"UPDATE telemetry_runs SET {', '.join(set_clauses)} WHERE event_id = ?",
                params
            )
            return conn.total_changes > 0

    def get_telemetry_runs_by_run_id(self, run_id: str) -> List[TelemetryRun]:
        """Get all telemetry runs for a pipeline run."""
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM telemetry_runs WHERE run_id = ? ORDER BY created_at",
                (run_id,)
            ).fetchall()

            return [self._row_to_telemetry_run(row) for row in rows]

    def _row_to_telemetry_run(self, row: sqlite3.Row) -> TelemetryRun:
        """Convert database row to TelemetryRun."""
        from datetime import timezone

        def parse_dt(val):
            if val:
                dt = datetime.fromisoformat(val)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            return None

        return TelemetryRun(
            event_id=row['event_id'],
            run_id=row['run_id'],
            created_at=parse_dt(row['created_at']) or datetime.now(timezone.utc),
            start_time=parse_dt(row['start_time']) or datetime.now(timezone.utc),
            agent_name=row['agent_name'] or 'example-reviewer',
            job_type=row['job_type'],
            end_time=parse_dt(row['end_time']),
            status=row['status'] or 'running',
            product=row['product'] or '',
            product_family=row['product_family'] or '',
            platform=row['platform'] or 'dotnet',
            subdomain=row['subdomain'] or '',
            website=row['website'] or '',
            website_section=row['website_section'] or '',
            item_name=row['item_name'] or '',
            items_discovered=row['items_discovered'] or 0,
            items_succeeded=row['items_succeeded'] or 0,
            items_failed=row['items_failed'] or 0,
            items_skipped=row['items_skipped'] or 0,
            duration_ms=row['duration_ms'] or 0,
            input_summary=row['input_summary'] or '',
            output_summary=row['output_summary'] or '',
            source_ref=row['source_ref'] or '',
            target_ref=row['target_ref'] or '',
            error_summary=row['error_summary'],
            error_details=row['error_details'],
            git_repo=row['git_repo'] or '',
            git_branch=row['git_branch'] or '',
            git_commit_hash=row['git_commit_hash'] or '',
            git_run_tag=row['git_run_tag'] or '',
            git_commit_source=row['git_commit_source'] or 'llm',
            git_commit_author=row['git_commit_author'] or 'Example Reviewer <example-reviewer@aspose.net>',
            git_commit_timestamp=parse_dt(row['git_commit_timestamp']),
            host=row['host'] or '',
            environment=row['environment'] or 'dev',
            trigger_type=row['trigger_type'] or 'manual',
            metrics_json=json.loads(row['metrics_json']) if row['metrics_json'] else {},
            context_json=json.loads(row['context_json']) if row['context_json'] else {},
            api_posted=bool(row['api_posted']),
            api_posted_at=parse_dt(row['api_posted_at']),
            api_retry_count=row['api_retry_count'] or 0,
            insight_id=row['insight_id'],
            parent_run_id=row['parent_run_id'],
        )

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

    # =========================================================================
    # TELEMETRY AGGREGATION
    # =========================================================================

    def get_phase_timings(self, run_id: str) -> List[Dict[str, Any]]:
        """
        Get phase timing data for a run.

        Args:
            run_id: Pipeline run ID

        Returns:
            List of phase timing records with phase name, duration, and success status
        """
        with self.get_connection() as conn:
            rows = conn.execute("""
                SELECT
                    phase,
                    duration_ms,
                    success,
                    timestamp,
                    metadata
                FROM telemetry_events
                WHERE run_id = ?
                  AND event_type = 'phase_timing'
                ORDER BY timestamp
            """, (run_id,)).fetchall()

            return [
                {
                    'phase': row['phase'],
                    'duration_ms': row['duration_ms'],
                    'success': bool(row['success']),
                    'timestamp': row['timestamp'],
                    'metadata': json.loads(row['metadata']) if row['metadata'] else {},
                }
                for row in rows
            ]

    def get_attempt_counts(self, run_id: str) -> Dict[str, Any]:
        """
        Get compilation and runtime attempt statistics for a run.

        Args:
            run_id: Pipeline run ID

        Returns:
            Dictionary with attempt counts by type
        """
        with self.get_connection() as conn:
            # Get compilation attempts
            compile_rows = conn.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(success) as successful
                FROM compile_attempts
                WHERE example_id IN (
                    SELECT example_id
                    FROM example_records
                    WHERE example_id IN (
                        SELECT DISTINCT example_id
                        FROM compile_attempts
                        WHERE timestamp >= (
                            SELECT started_at
                            FROM run_records
                            WHERE run_id = ?
                        )
                    )
                )
            """, (run_id,)).fetchone()

            # Get runtime attempts
            runtime_rows = conn.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(success) as successful
                FROM runtime_attempts
                WHERE example_id IN (
                    SELECT example_id
                    FROM example_records
                    WHERE example_id IN (
                        SELECT DISTINCT example_id
                        FROM runtime_attempts
                        WHERE timestamp >= (
                            SELECT started_at
                            FROM run_records
                            WHERE run_id = ?
                        )
                    )
                )
            """, (run_id,)).fetchone()

            return {
                'compilation': {
                    'total_attempts': compile_rows['total'] or 0,
                    'successful': compile_rows['successful'] or 0,
                    'failed': (compile_rows['total'] or 0) - (compile_rows['successful'] or 0),
                },
                'runtime': {
                    'total_attempts': runtime_rows['total'] or 0,
                    'successful': runtime_rows['successful'] or 0,
                    'failed': (runtime_rows['total'] or 0) - (runtime_rows['successful'] or 0),
                },
            }

    def get_failure_breakdown(self, family: str) -> Dict[str, Any]:
        """
        Get failure breakdown by status for a family.

        Args:
            family: Product family identifier

        Returns:
            Dictionary with failure counts and common error patterns
        """
        with self.get_connection() as conn:
            # Get failure counts by status
            status_rows = conn.execute("""
                SELECT
                    status,
                    COUNT(*) as count
                FROM example_records
                WHERE family = ?
                  AND status IN ('COMPILE_FAILED', 'RUNTIME_FAILED', 'FINAL_REVIEW_FAILED')
                GROUP BY status
            """, (family,)).fetchall()

            failure_counts = {
                row['status']: row['count']
                for row in status_rows
            }

            # Get sample failure reasons
            failure_samples = {}
            for status in ['COMPILE_FAILED', 'RUNTIME_FAILED', 'FINAL_REVIEW_FAILED']:
                samples = conn.execute("""
                    SELECT failure_reason
                    FROM example_records
                    WHERE family = ? AND status = ? AND failure_reason IS NOT NULL
                    LIMIT 5
                """, (family, status)).fetchall()

                failure_samples[status] = [
                    row['failure_reason'][:200]  # Truncate to 200 chars
                    for row in samples
                ]

            return {
                'failure_counts': failure_counts,
                'failure_samples': failure_samples,
                'total_failures': sum(failure_counts.values()),
            }

    def compute_selection_hash(self, example_keys: List[str]) -> str:
        """
        Compute deterministic selection_hash from example_keys.

        Formula: sha256("\\n".join(sorted(example_keys))).hexdigest()

        This hash proves the exact set of examples selected for a run,
        enabling determinism verification across runs.

        Args:
            example_keys: List of example_key values from selected examples

        Returns:
            64-character hex SHA256 hash of sorted example keys
        """
        if not example_keys:
            return hashlib.sha256(b"").hexdigest()

        # Sort keys for deterministic ordering
        sorted_keys = sorted(example_keys)

        # Join with newlines and hash
        content = "\n".join(sorted_keys)
        return hashlib.sha256(content.encode()).hexdigest()

    # =========================================================================
    # RUN FINGERPRINTS (Track 1: C.8)
    # =========================================================================

    def save_run_fingerprint(self, fingerprint: 'RunFingerprint') -> str:
        """
        Save run fingerprint to database.

        Args:
            fingerprint: RunFingerprint instance

        Returns:
            run_id
        """
        with self.get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO run_fingerprints (
                    run_id, config_hash, selection_hash,
                    fingerprint_json, created_at
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                fingerprint.run_id,
                fingerprint.config_hash,
                fingerprint.selection_hash,
                fingerprint.to_json(),
                fingerprint.timestamp.isoformat() if fingerprint.timestamp else datetime.utcnow().isoformat(),
            ))
        return fingerprint.run_id

    def get_run_fingerprint(self, run_id: str) -> Optional['RunFingerprint']:
        """
        Get run fingerprint from database.

        Args:
            run_id: Run identifier

        Returns:
            RunFingerprint or None if not found
        """
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM run_fingerprints WHERE run_id = ?",
                (run_id,)
            ).fetchone()

            if row:
                # Import here to avoid circular dependency
                from .fingerprint import RunFingerprint
                return RunFingerprint.from_json(row['fingerprint_json'])
        return None

    def get_fingerprints_by_config_hash(self, config_hash: str) -> List['RunFingerprint']:
        """
        Get all fingerprints with matching config_hash.

        Useful for finding runs with identical configuration.

        Args:
            config_hash: Configuration hash

        Returns:
            List of RunFingerprint instances
        """
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM run_fingerprints WHERE config_hash = ? ORDER BY created_at DESC",
                (config_hash,)
            ).fetchall()

            from .fingerprint import RunFingerprint
            return [RunFingerprint.from_json(row['fingerprint_json']) for row in rows]

    def get_fingerprints_by_selection_hash(self, selection_hash: str) -> List['RunFingerprint']:
        """
        Get all fingerprints with matching selection_hash.

        Useful for finding runs that processed the same example set.

        Args:
            selection_hash: Selection hash

        Returns:
            List of RunFingerprint instances
        """
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM run_fingerprints WHERE selection_hash = ? ORDER BY created_at DESC",
                (selection_hash,)
            ).fetchall()

            from .fingerprint import RunFingerprint
            return [RunFingerprint.from_json(row['fingerprint_json']) for row in rows]

    # =========================================================================
    # REVIEW RESULTS
    # =========================================================================

    def save_review_result(self, result: ReviewResult) -> str:
        """
        Save a review result with its issues.

        Args:
            result: ReviewResult with issues

        Returns:
            review_id
        """
        with self.get_connection() as conn:
            run_row = conn.execute(
                "SELECT 1 FROM run_records WHERE run_id = ?",
                (result.run_id,),
            ).fetchone()
            if not run_row:
                conn.execute(
                    """
                    INSERT INTO run_records (
                        run_id, family, started_at, status, phases_completed,
                        examples_processed, examples_successful, examples_failed
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result.run_id,
                        result.family,
                        datetime.utcnow().isoformat(),
                        "review",
                        json.dumps([]),
                        0,
                        0,
                        0,
                    ),
                )

            # Save the review result
            conn.execute("""
                INSERT OR REPLACE INTO review_results (
                    review_id, file_path, run_id, family,
                    approved, review_attempt, llm_response, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result.review_id,
                result.file_path,
                result.run_id,
                result.family,
                1 if result.approved else 0,
                result.review_attempt,
                result.llm_response,
                result.timestamp.isoformat(),
            ))

            # Save all issues
            for issue in result.issues:
                # Skip issues with invalid example_id to avoid FK constraint violations
                if not issue.example_id or issue.example_id == 'unknown':
                    logger.warning(f"Skipping review issue with invalid example_id: {issue.example_id}")
                    continue

                example_row = conn.execute(
                    "SELECT 1 FROM example_records WHERE example_id = ?",
                    (issue.example_id,),
                ).fetchone()
                if not example_row:
                    now = datetime.utcnow().isoformat()
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO example_records (
                            example_id, family, file_path, source_type, language,
                            location_block_index, location_start_line, location_end_line, location_anchor,
                            gist_owner, gist_id, gist_filename,
                            original_code, compilable_code, verified_code,
                            status, failure_reason, created_at, updated_at,
                            section_heading, description_context, topic,
                            drift_score, drift_similarity
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            issue.example_id,
                            result.family,
                            result.file_path,
                            SourceType.INLINE.value,
                            "csharp",
                            0,
                            0,
                            0,
                            "",
                            None,
                            None,
                            None,
                            "",
                            None,
                            None,
                            ExampleStatus.DISCOVERED.value,
                            None,
                            now,
                            now,
                            None,
                            None,
                            None,
                            None,
                            None,
                        ),
                    )

                issue_review_id = result.review_id
                conn.execute("""
                    INSERT OR REPLACE INTO review_issues (
                        issue_id, review_id, example_id,
                        issue_type, description, suggestion,
                        severity, resolved, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    issue.issue_id,
                    issue_review_id,
                    issue.example_id,
                    issue.issue_type.value,
                    issue.description,
                    issue.suggestion,
                    issue.severity.value,
                    1 if issue.resolved else 0,
                    issue.created_at.isoformat(),
                ))

        return result.review_id

    def get_review_result(self, review_id: str) -> Optional[ReviewResult]:
        """Get a review result by ID with its issues."""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM review_results WHERE review_id = ?",
                (review_id,)
            ).fetchone()

            if not row:
                return None

            # Get issues for this review
            issue_rows = conn.execute(
                "SELECT * FROM review_issues WHERE review_id = ? ORDER BY created_at",
                (review_id,)
            ).fetchall()

            issues = [self._row_to_review_issue(ir) for ir in issue_rows]

            return self._row_to_review_result(row, issues)

    def get_review_results_by_run(self, run_id: str) -> List[ReviewResult]:
        """Get all review results for a run."""
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM review_results WHERE run_id = ? ORDER BY timestamp",
                (run_id,)
            ).fetchall()

            results = []
            for row in rows:
                # Get issues for each review
                issue_rows = conn.execute(
                    "SELECT * FROM review_issues WHERE review_id = ?",
                    (row['review_id'],)
                ).fetchall()
                issues = [self._row_to_review_issue(ir) for ir in issue_rows]
                results.append(self._row_to_review_result(row, issues))

            return results

    def get_review_results_by_file(self, file_path: str, run_id: Optional[str] = None) -> List[ReviewResult]:
        """Get review results for a file, optionally filtered by run."""
        with self.get_connection() as conn:
            query = "SELECT * FROM review_results WHERE file_path = ?"
            params = [file_path]

            if run_id:
                query += " AND run_id = ?"
                params.append(run_id)

            query += " ORDER BY review_attempt DESC"

            rows = conn.execute(query, params).fetchall()

            results = []
            for row in rows:
                issue_rows = conn.execute(
                    "SELECT * FROM review_issues WHERE review_id = ?",
                    (row['review_id'],)
                ).fetchall()
                issues = [self._row_to_review_issue(ir) for ir in issue_rows]
                results.append(self._row_to_review_result(row, issues))

            return results

    def get_latest_review_attempt(self, file_path: str, run_id: str) -> int:
        """Get the latest review attempt number for a file in a run."""
        with self.get_connection() as conn:
            row = conn.execute("""
                SELECT MAX(review_attempt) as max_attempt
                FROM review_results
                WHERE file_path = ? AND run_id = ?
            """, (file_path, run_id)).fetchone()

            return row['max_attempt'] if row and row['max_attempt'] else 0

    def get_unresolved_issues_for_file(self, file_path: str, run_id: Optional[str] = None) -> List[ReviewIssue]:
        """Get unresolved issues for a file."""
        with self.get_connection() as conn:
            query = """
                SELECT ri.*
                FROM review_issues ri
                JOIN review_results rr ON ri.review_id = rr.review_id
                WHERE rr.file_path = ? AND ri.resolved = 0
            """
            params = [file_path]

            if run_id:
                query += " AND rr.run_id = ?"
                params.append(run_id)

            query += " ORDER BY ri.created_at"

            rows = conn.execute(query, params).fetchall()
            return [self._row_to_review_issue(row) for row in rows]

    def resolve_issue(self, issue_id: str) -> bool:
        """Mark an issue as resolved."""
        with self.get_connection() as conn:
            conn.execute(
                "UPDATE review_issues SET resolved = 1 WHERE issue_id = ?",
                (issue_id,)
            )
            return conn.total_changes > 0

    def get_review_stats_by_family(self, family: str) -> Dict[str, Any]:
        """Get review statistics for a family."""
        with self.get_connection() as conn:
            # Total reviews
            total_rows = conn.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(approved) as approved
                FROM review_results
                WHERE family = ?
            """, (family,)).fetchone()

            # Issues by severity
            severity_rows = conn.execute("""
                SELECT
                    ri.severity,
                    COUNT(*) as count
                FROM review_issues ri
                JOIN review_results rr ON ri.review_id = rr.review_id
                WHERE rr.family = ?
                GROUP BY ri.severity
            """, (family,)).fetchall()

            # Issues by type
            type_rows = conn.execute("""
                SELECT
                    ri.issue_type,
                    COUNT(*) as count
                FROM review_issues ri
                JOIN review_results rr ON ri.review_id = rr.review_id
                WHERE rr.family = ?
                GROUP BY ri.issue_type
            """, (family,)).fetchall()

            return {
                'total_reviews': total_rows['total'] or 0,
                'approved': total_rows['approved'] or 0,
                'rejected': (total_rows['total'] or 0) - (total_rows['approved'] or 0),
                'issues_by_severity': {row['severity']: row['count'] for row in severity_rows},
                'issues_by_type': {row['issue_type']: row['count'] for row in type_rows},
            }

    def _row_to_review_result(self, row: sqlite3.Row, issues: List[ReviewIssue]) -> ReviewResult:
        """Convert database row to ReviewResult."""
        return ReviewResult(
            review_id=row['review_id'],
            file_path=row['file_path'],
            run_id=row['run_id'],
            family=row['family'],
            approved=bool(row['approved']),
            review_attempt=row['review_attempt'],
            issues=issues,
            llm_response=row['llm_response'],
            timestamp=datetime.fromisoformat(row['timestamp']),
        )

    def _row_to_review_issue(self, row: sqlite3.Row) -> ReviewIssue:
        """Convert database row to ReviewIssue."""
        return ReviewIssue(
            issue_id=row['issue_id'],
            review_id=row['review_id'],
            example_id=row['example_id'],
            issue_type=IssueType(row['issue_type']),
            description=row['description'],
            suggestion=row['suggestion'],
            severity=IssueSeverity(row['severity']),
            resolved=bool(row['resolved']),
            created_at=datetime.fromisoformat(row['created_at']),
        )
