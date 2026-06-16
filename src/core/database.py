"""
Database module for Example Reviewer Pipeline.
Uses SQLite with WAL mode for concurrent access.
"""

import sqlite3
import json
import logging
import hashlib
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

from .models import (
    ExampleRecord, ExampleStatus, SourceType, Location, GistInfo,
    CompileAttempt, RuntimeAttempt, MarkdownEdit, CommitRecord,
    RunRecord, TelemetryEvent, TelemetryRun, EditType,
    ReviewResult, ReviewIssue, IssueSeverity, IssueType,
    FailureDetail, FailureCategory, FailureResolution
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
    -- Schema migrations tracking table
    CREATE TABLE IF NOT EXISTS schema_migrations (
        migration_id TEXT PRIMARY KEY,
        description TEXT NOT NULL,
        applied_at TEXT NOT NULL
    );

    -- Example records table (canonical per-example metadata)
    -- Note: run_id is NOT here - it's in example_run_state
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
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        section_heading TEXT,
        description_context TEXT,
        topic TEXT,
        example_key TEXT,
        app_context TEXT DEFAULT NULL,
        code_block_signature TEXT DEFAULT NULL,
        extraction_warning TEXT DEFAULT NULL,
        article_intent TEXT DEFAULT NULL
    );

    CREATE INDEX IF NOT EXISTS idx_examples_family ON example_records(family);
    CREATE INDEX IF NOT EXISTS idx_examples_file_path ON example_records(file_path);
    CREATE UNIQUE INDEX IF NOT EXISTS idx_example_key ON example_records(family, example_key);
    CREATE INDEX IF NOT EXISTS idx_example_records_signature ON example_records(code_block_signature);

    -- Example run state table (per-run state for each example)
    -- This is the production-grade approach: keyed by (run_id, example_id)
    CREATE TABLE IF NOT EXISTS example_run_state (
        run_id TEXT NOT NULL,
        example_id TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'discovered',
        failure_reason TEXT,
        escalation_reason TEXT,
        compilable_code TEXT,
        verified_code TEXT,
        drift_score REAL DEFAULT 0.0,
        drift_similarity REAL DEFAULT 0.0,
        needs_human_review INTEGER DEFAULT 0,
        app_context TEXT DEFAULT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        PRIMARY KEY (run_id, example_id),
        FOREIGN KEY (run_id) REFERENCES run_records(run_id) ON DELETE CASCADE,
        FOREIGN KEY (example_id) REFERENCES example_records(example_id) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_run_state_run ON example_run_state(run_id);
    CREATE INDEX IF NOT EXISTS idx_run_state_example ON example_run_state(example_id);
    CREATE INDEX IF NOT EXISTS idx_run_state_status ON example_run_state(run_id, status);
    CREATE INDEX IF NOT EXISTS idx_run_state_drift ON example_run_state(run_id, drift_score);
    CREATE INDEX IF NOT EXISTS idx_example_records_app_context ON example_records(app_context);
    CREATE INDEX IF NOT EXISTS idx_example_run_state_app_context ON example_run_state(run_id, app_context);

    -- Compile attempts table
    CREATE TABLE IF NOT EXISTS compile_attempts (
        attempt_id TEXT PRIMARY KEY,
        example_id TEXT NOT NULL,
        family TEXT NOT NULL,
        run_id TEXT,
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
        FOREIGN KEY (example_id) REFERENCES example_records(example_id),
        FOREIGN KEY (run_id) REFERENCES run_records(run_id) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_compile_example ON compile_attempts(example_id);
    CREATE INDEX IF NOT EXISTS idx_compile_family ON compile_attempts(family);
    CREATE INDEX IF NOT EXISTS idx_compile_run ON compile_attempts(run_id);
    CREATE INDEX IF NOT EXISTS idx_compile_example_run ON compile_attempts(example_id, run_id);

    -- Runtime attempts table
    CREATE TABLE IF NOT EXISTS runtime_attempts (
        attempt_id TEXT PRIMARY KEY,
        example_id TEXT NOT NULL,
        family TEXT NOT NULL,
        run_id TEXT,
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
        FOREIGN KEY (example_id) REFERENCES example_records(example_id),
        FOREIGN KEY (run_id) REFERENCES run_records(run_id) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_runtime_example ON runtime_attempts(example_id);
    CREATE INDEX IF NOT EXISTS idx_runtime_family ON runtime_attempts(family);
    CREATE INDEX IF NOT EXISTS idx_runtime_run ON runtime_attempts(run_id);
    CREATE INDEX IF NOT EXISTS idx_runtime_example_run ON runtime_attempts(example_id, run_id);

    -- Markdown edits table
    CREATE TABLE IF NOT EXISTS markdown_edits (
        edit_id TEXT PRIMARY KEY,
        file_path TEXT NOT NULL,
        example_id TEXT NOT NULL,
        family TEXT NOT NULL,
        run_id TEXT,
        edit_type TEXT NOT NULL DEFAULT 'inline_replace',
        diff_ref TEXT,
        old_code TEXT,
        new_code TEXT,
        timestamp TEXT NOT NULL,
        FOREIGN KEY (example_id) REFERENCES example_records(example_id),
        FOREIGN KEY (run_id) REFERENCES run_records(run_id) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_edits_example ON markdown_edits(example_id);
    CREATE INDEX IF NOT EXISTS idx_edits_file ON markdown_edits(file_path);
    CREATE INDEX IF NOT EXISTS idx_edits_run ON markdown_edits(run_id);
    
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

    -- Failure details table (Track all failure reasons, including LLM rejections)
    -- Schema from Migration 007
    CREATE TABLE IF NOT EXISTS failure_details (
        failure_id TEXT PRIMARY KEY,
        run_id TEXT NOT NULL,
        example_id TEXT,
        phase TEXT NOT NULL,
        failure_category TEXT NOT NULL CHECK(failure_category IN (
            'timeout',
            'drift_exceeded',
            'api_context_missing',
            'llm_response_rejected',
            'escalated_to_review',
            'compile_error',
            'runtime_error',
            'review_failed',
            'infra_missing_test_data',
            'infra_blocked_rar_fixture',
            'infra_blocked_7z_fixture',
            'infra_blocked_password',
            'infra_blocked_format',
            'infra_blocked_external',
            'precheck_only',
            'other'
        )),
        error_category TEXT,
        error_message TEXT,
        resolution TEXT CHECK(resolution IN ('fixed', 'needs_review', 'abandoned', 'pending')),
        metadata TEXT,
        timestamp TEXT NOT NULL,
        FOREIGN KEY (run_id) REFERENCES run_records(run_id) ON DELETE CASCADE,
        FOREIGN KEY (example_id) REFERENCES example_records(example_id) ON DELETE SET NULL
    );

    CREATE INDEX IF NOT EXISTS idx_failure_run_phase ON failure_details(run_id, phase);
    CREATE INDEX IF NOT EXISTS idx_failure_category ON failure_details(failure_category);
    CREATE INDEX IF NOT EXISTS idx_failure_error_category ON failure_details(error_category);
    CREATE INDEX IF NOT EXISTS idx_failure_resolution ON failure_details(resolution);
    CREATE INDEX IF NOT EXISTS idx_failure_timestamp ON failure_details(timestamp);
    CREATE INDEX IF NOT EXISTS idx_failure_example ON failure_details(example_id);

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

    -- Semantic signatures table (DRIFT-02: API-level fingerprinting)
    CREATE TABLE IF NOT EXISTS semantic_signatures (
        signature_id TEXT PRIMARY KEY,
        example_id TEXT NOT NULL,
        run_id TEXT NOT NULL,
        attempt_type TEXT NOT NULL,
        attempt_id TEXT,
        enum_values TEXT,
        method_calls TEXT,
        constructor_types TEXT,
        property_assignments TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (example_id) REFERENCES example_records(example_id),
        FOREIGN KEY (run_id) REFERENCES run_records(run_id) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_sig_example ON semantic_signatures(example_id);
    CREATE INDEX IF NOT EXISTS idx_sig_run ON semantic_signatures(run_id);
    CREATE INDEX IF NOT EXISTS idx_sig_type ON semantic_signatures(attempt_type);

    -- Drift rejections table (DRIFT-02: tracks rejected fixes)
    CREATE TABLE IF NOT EXISTS drift_rejections (
        rejection_id TEXT PRIMARY KEY,
        example_id TEXT NOT NULL,
        run_id TEXT NOT NULL,
        attempt_id TEXT NOT NULL,
        phase TEXT NOT NULL,
        rejection_reason TEXT NOT NULL,
        drift_score REAL NOT NULL,
        signature_drift TEXT,
        critical_enum_changes TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (example_id) REFERENCES example_records(example_id),
        FOREIGN KEY (run_id) REFERENCES run_records(run_id) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_rejection_example ON drift_rejections(example_id);
    CREATE INDEX IF NOT EXISTS idx_rejection_run ON drift_rejections(run_id);
    CREATE INDEX IF NOT EXISTS idx_rejection_phase ON drift_rejections(phase);

    -- Work queue table (TC-06: autonomous task selection)
    CREATE TABLE IF NOT EXISTS work_queue (
        queue_id TEXT PRIMARY KEY,
        family TEXT NOT NULL,
        trigger_source TEXT NOT NULL DEFAULT 'manual',
        priority INTEGER NOT NULL DEFAULT 5,
        status TEXT NOT NULL DEFAULT 'pending'
            CHECK(status IN ('pending', 'claimed', 'completed', 'failed', 'cancelled')),
        max_examples INTEGER,
        skip_llm INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        claimed_at TEXT,
        completed_at TEXT,
        run_id TEXT,
        error TEXT,
        FOREIGN KEY (run_id) REFERENCES run_records(run_id)
    );

    CREATE INDEX IF NOT EXISTS idx_work_queue_status ON work_queue(status, priority DESC);
    CREATE INDEX IF NOT EXISTS idx_work_queue_family ON work_queue(family);
    """
    
    def __init__(
        self,
        db_path: Optional[Path] = None,
        production_db_path: Optional[Path] = None,
        busy_timeout_ms: int = 120000,
        wal_enabled: bool = True
    ):
        """
        Initialize database connection(s).

        Args:
            db_path: Path to development SQLite database file
            production_db_path: Optional path to production database (enables dual-DB mode)
            busy_timeout_ms: SQLite busy timeout in milliseconds (default: 120000)
            wal_enabled: Enable WAL mode (default: True)
        """
        self.db_path = Path(db_path) if db_path else Path("data/example_reviewer.db")
        self.production_db_path = Path(production_db_path) if production_db_path else None
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        if self.production_db_path:
            self.production_db_path.parent.mkdir(parents=True, exist_ok=True)
            logger.info(f"Dual-database mode enabled: prod_db={self.production_db_path}")

        self._conn: Optional[sqlite3.Connection] = None
        self.busy_timeout_ms = busy_timeout_ms
        self.wal_enabled = wal_enabled

        # Task 2B: Single-writer protection lock
        self._write_lock = threading.RLock()

        logger.info(
            f"Database initialized: path={self.db_path}, "
            f"busy_timeout={busy_timeout_ms}ms, wal_enabled={wal_enabled}"
        )


    @contextmanager
    def get_connection(self):
        """
        Get a database connection with context management.

        Task 2A: Enforces WAL mode and sane pragmas on every connection.
        """
        # Convert milliseconds to seconds for SQLite timeout
        timeout_seconds = self.busy_timeout_ms / 1000.0
        conn = sqlite3.connect(str(self.db_path), timeout=timeout_seconds)
        conn.row_factory = sqlite3.Row

        # Task 2A: Enforce all required pragmas
        if self.wal_enabled:
            conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA temp_store=MEMORY")
        conn.execute(f"PRAGMA busy_timeout={self.busy_timeout_ms}")
        conn.execute("PRAGMA foreign_keys=ON")

        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @contextmanager
    def get_production_connection(self):
        """
        Get production database connection with same pragmas as dev DB.

        Raises:
            RuntimeError: If production database not configured
        """
        if not self.production_db_path:
            raise RuntimeError("Production database not configured")

        timeout_seconds = self.busy_timeout_ms / 1000.0
        conn = sqlite3.connect(str(self.production_db_path), timeout=timeout_seconds)
        conn.row_factory = sqlite3.Row

        # Same pragmas as dev DB
        if self.wal_enabled:
            conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA temp_store=MEMORY")
        conn.execute(f"PRAGMA busy_timeout={self.busy_timeout_ms}")
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
            self._conn = sqlite3.connect(str(self.db_path), timeout=120.0)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    def connect(self) -> sqlite3.Connection:
        """Open and return a persistent connection (legacy API)."""
        return self.conn
    
    def initialize_schema(self) -> None:
        """
        Initialize database schema and apply migrations.

        This method:
        1. Creates base schema (all tables with CREATE TABLE IF NOT EXISTS)
        2. Applies any pending migrations from migrations/ directory
        """
        with self.get_connection() as conn:
            conn.executescript(self.SCHEMA)
        logger.info(f"Database schema initialized at {self.db_path}")

        # Apply migrations
        self.apply_migrations()

    def apply_migrations(self) -> None:
        """
        Apply pending migrations from migrations/ directory.

        Migrations are SQL files named XXX_description.sql (e.g., 008_run_scoping.sql).
        Each migration is applied once and recorded in schema_migrations table.

        Fresh DB Bootstrap:
        If this is a fresh database (only schema_migrations exists after SCHEMA),
        all migrations are marked as applied (baseline) without execution.
        This prevents applying upgrade scripts to a latest-schema DB.
        """
        # Resolve migrations directory relative to repo root
        # database.py is at <repo>/src/core/database.py, so repo root is 2 levels up
        repo_root = Path(__file__).parent.parent.parent
        migrations_dir = repo_root / "migrations"

        if not migrations_dir.exists():
            logger.debug(f"No migrations directory found at {migrations_dir}, skipping migrations")
            return

        # Get all migration files (exclude _legacy subdirectory)
        migration_files = sorted([f for f in migrations_dir.glob("*.sql") if f.is_file()])
        if not migration_files:
            logger.debug("No migration files found")
            return

        with self.get_connection() as conn:
            # Get applied migrations
            applied = set()
            try:
                rows = conn.execute("SELECT migration_id FROM schema_migrations").fetchall()
                applied = {row["migration_id"] for row in rows}
            except sqlite3.OperationalError:
                # schema_migrations table doesn't exist yet (very first run)
                logger.debug("schema_migrations table not found, will be created by SCHEMA")

            # Check if this is a fresh database (only schema_migrations exists after base SCHEMA)
            is_fresh_db = self._is_fresh_database(conn)

            if is_fresh_db:
                logger.info("Fresh database detected - marking all migrations as applied (baseline)")
                # Mark all migrations as applied without executing them
                for migration_file in migration_files:
                    migration_id = migration_file.stem
                    if migration_id not in applied:
                        self._record_migration(conn, migration_id, f"Baseline (fresh DB)")
                        logger.debug(f"Migration {migration_id} marked as applied (baseline)")
                return

            # Apply pending migrations for existing databases
            for migration_file in migration_files:
                migration_id = migration_file.stem  # e.g., "008_run_scoping"

                if migration_id in applied:
                    logger.debug(f"Migration {migration_id} already applied, skipping")
                    continue

                logger.info(f"Applying migration: {migration_id}")
                try:
                    migration_sql = migration_file.read_text(encoding='utf-8')
                    if migration_id == "008_run_scoping":
                        migration_sql = self._prepare_migration_008_sql(conn, migration_sql)
                    conn.executescript(migration_sql)

                    # Record migration in schema_migrations (engine records it, not the SQL)
                    self._record_migration(conn, migration_id, f"Applied from {migration_file.name}")

                    # Verify migration 010 specifically (app_context column must exist)
                    if migration_id == "010_add_app_context":
                        self._verify_migration_010(conn)

                    logger.info(f"Migration {migration_id} applied successfully")
                except Exception as e:
                    logger.error(f"Failed to apply migration {migration_id}: {e}")
                    raise

    def _column_exists(self, conn: sqlite3.Connection, table_name: str, column_name: str) -> bool:
        """Check whether a column exists in the specified table."""
        try:
            cursor = conn.execute(f"PRAGMA table_info({table_name})")
            return any(row[1] == column_name for row in cursor.fetchall())
        except sqlite3.OperationalError:
            return False

    def _prepare_migration_008_sql(self, conn: sqlite3.Connection, migration_sql: str) -> str:
        """
        Make migration 008 safe on databases where run_id columns already exist.

        SQLite does not support `ADD COLUMN IF NOT EXISTS`, so we strip only the
        duplicate-prone ALTER statements when the target column is already present.
        """
        run_id_targets = [
            "compile_attempts",
            "runtime_attempts",
            "markdown_edits",
        ]
        prepared_sql = migration_sql
        for table_name in run_id_targets:
            if self._column_exists(conn, table_name, "run_id"):
                stmt = f"ALTER TABLE {table_name} ADD COLUMN run_id TEXT;"
                prepared_sql = prepared_sql.replace(
                    stmt,
                    f"-- Skipped by migration engine: {table_name}.run_id already exists",
                )
        return prepared_sql

    def _is_fresh_database(self, conn: sqlite3.Connection) -> bool:
        """
        Check if database is fresh (only schema_migrations and base schema tables exist).

        A fresh database has base schema tables but no run-scoped data.

        Returns:
            True if fresh database, False otherwise
        """
        try:
            # Get all user tables (exclude sqlite internal tables)
            cursor = conn.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """)
            tables = {row["name"] for row in cursor.fetchall()}

            # Expected base schema tables (from SCHEMA constant)
            base_tables = {
                'schema_migrations',
                'example_records',
                'example_run_state',
                'compile_attempts',
                'runtime_attempts',
                'markdown_edits',
                'commit_records',
                'run_records',
                'telemetry_events',
                'telemetry_runs',
                'api_reference_cache',
                'failure_details',
                'review_results',
                'review_issues',
                'gist_publications',
                'run_fingerprints',
                'semantic_signatures',
                'drift_rejections',
                'work_queue',  # Added: in SCHEMA but was missing from this set
            }

            # Check if we have the base schema tables (or subset)
            if not tables.issubset(base_tables):
                # Has tables not in base schema = not fresh
                return False

            # Check if run_records table exists
            if 'run_records' not in tables:
                # Very fresh - no tables created yet (shouldn't happen after SCHEMA runs)
                return True

            # Check if run_records is empty (no runs have been executed)
            cursor = conn.execute("SELECT COUNT(*) as count FROM run_records")
            run_count = cursor.fetchone()["count"]

            # Fresh if no runs have been recorded AND example_records is empty
            # (i.e., no data has been loaded yet)
            if run_count == 0:
                # Also check if example_records is empty
                cursor = conn.execute("SELECT COUNT(*) as count FROM example_records")
                example_count = cursor.fetchone()["count"]
                return example_count == 0

            return False

        except sqlite3.OperationalError as e:
            # If query fails, log and assume NOT fresh (safer default)
            logger.debug(f"_is_fresh_database check failed: {e}")
            return False

    def _record_migration(self, conn: sqlite3.Connection, migration_id: str, description: str) -> None:
        """
        Record a migration in schema_migrations table.

        Args:
            conn: Database connection
            migration_id: Migration identifier (e.g., "008_run_scoping")
            description: Migration description
        """
        now = datetime.now(timezone.utc).isoformat()
        conn.execute("""
            INSERT OR IGNORE INTO schema_migrations (migration_id, description, applied_at)
            VALUES (?, ?, ?)
        """, (migration_id, description, now))

    def _verify_migration_010(self, conn: sqlite3.Connection) -> None:
        """
        Verify that migration 010 (app_context) was applied correctly.

        Raises:
            RuntimeError: If app_context column is missing from required tables
        """
        # Check example_records table
        cursor = conn.execute("PRAGMA table_info(example_records)")
        example_cols = {row[1] for row in cursor.fetchall()}
        if 'app_context' not in example_cols:
            raise RuntimeError(
                "Migration 010 verification failed: app_context column missing from example_records table. "
                "Available columns: " + ", ".join(sorted(example_cols))
            )

        # Check example_run_state table
        cursor = conn.execute("PRAGMA table_info(example_run_state)")
        run_state_cols = {row[1] for row in cursor.fetchall()}
        if 'app_context' not in run_state_cols:
            raise RuntimeError(
                "Migration 010 verification failed: app_context column missing from example_run_state table. "
                "Available columns: " + ", ".join(sorted(run_state_cols))
            )

        logger.info("Migration 010 verification passed: app_context columns exist in all required tables")

    def close(self) -> None:
        """Close persistent connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
    
    # =========================================================================
    # EXAMPLE RECORDS
    # =========================================================================
    
    def save_example(self, example: ExampleRecord, run_id: Optional[str] = None) -> str:
        """
        Save or update an example record.

        This method saves ONLY canonical fields to example_records (no status, code, etc.).
        If run_id is provided, it also creates/updates example_run_state with run-scoped fields.

        Args:
            example: Example record to save
            run_id: Optional run_id for run-scoped tracking

        Returns:
            example_id
        """
        # Task 2B: Single-writer protection
        with self._write_lock:
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

                # Handle (family, example_key) UNIQUE constraint:
                # If an example with same key exists under a different ID, reuse that ID
                existing_by_key = conn.execute(
                    "SELECT example_id FROM example_records WHERE family = ? AND example_key = ?",
                    (example.family, example.example_key),
                ).fetchone()
                if existing_by_key and existing_by_key["example_id"] != example.example_id:
                    example.example_id = existing_by_key["example_id"]

                # Save ONLY canonical fields to example_records
                # Use ON CONFLICT DO UPDATE instead of INSERT OR REPLACE to avoid
                # DELETE+INSERT which triggers FK violations on child tables
                # (compile_attempts, runtime_attempts, markdown_edits use ON DELETE NO ACTION)
                conn.execute("""
                    INSERT INTO example_records (
                        example_id, family, file_path, source_type, language,
                        location_block_index, location_start_line, location_end_line, location_anchor,
                        gist_owner, gist_id, gist_filename,
                        original_code, created_at, updated_at,
                        section_heading, description_context, topic, app_context, example_key,
                        code_block_signature, extraction_warning, article_intent
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(example_id) DO UPDATE SET
                        family = excluded.family,
                        file_path = excluded.file_path,
                        source_type = excluded.source_type,
                        language = excluded.language,
                        location_block_index = excluded.location_block_index,
                        location_start_line = excluded.location_start_line,
                        location_end_line = excluded.location_end_line,
                        location_anchor = excluded.location_anchor,
                        gist_owner = excluded.gist_owner,
                        gist_id = excluded.gist_id,
                        gist_filename = excluded.gist_filename,
                        original_code = excluded.original_code,
                        updated_at = excluded.updated_at,
                        section_heading = excluded.section_heading,
                        description_context = excluded.description_context,
                        topic = excluded.topic,
                        app_context = excluded.app_context,
                        example_key = excluded.example_key,
                        code_block_signature = excluded.code_block_signature,
                        extraction_warning = excluded.extraction_warning,
                        article_intent = excluded.article_intent
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
                    example.created_at.isoformat(),
                    example.updated_at.isoformat(),
                    example.section_heading,
                    example.description_context,
                    example.topic,
                    example.app_context,
                    example.example_key,
                    example.code_block_signature,
                    example.extraction_warning,
                    example.article_intent,
                ))

            # If run_id provided, also save/update run-scoped state (outside conn context)
            if run_id:
                # Note: save_example_run_state will acquire its own write lock
                self.save_example_run_state(
                    run_id=run_id,
                    example_id=example.example_id,
                    status=example.status,
                    failure_reason=example.failure_reason,
                    escalation_reason=example.escalation_reason,
                    compilable_code=example.compilable_code,
                    verified_code=example.verified_code,
                    app_context=example.app_context,
                )

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
        run_id: Optional[str] = None,
    ) -> List[ExampleRecord]:
        """
        Get examples for a family, optionally filtered by status and run_id.

        If run_id is provided, this method JOINs with example_run_state to get
        run-scoped status and code fields. Otherwise, it returns canonical records only.

        Args:
            family: Product family
            status: Optional status filter (applied to run_state if run_id provided)
            limit: Optional result limit
            run_id: Optional run_id for run-scoped queries

        Returns:
            List of example records with run-scoped fields populated if run_id provided
        """
        with self.get_connection() as conn:
            if run_id:
                # Run-scoped query: JOIN with example_run_state
                query = """
                    SELECT
                        er.*,
                        ers.status as run_status,
                        ers.failure_reason as run_failure_reason,
                        ers.escalation_reason as run_escalation_reason,
                        ers.compilable_code as run_compilable_code,
                        ers.verified_code as run_verified_code
                    FROM example_records er
                    INNER JOIN example_run_state ers ON er.example_id = ers.example_id
                    WHERE er.family = ? AND ers.run_id = ?
                """
                params = [family, run_id]

                if status:
                    query += " AND ers.status = ?"
                    params.append(status.value)

                query += " ORDER BY er.example_key ASC, er.example_id ASC"

                if limit:
                    query += " LIMIT ?"
                    params.append(limit)

                rows = conn.execute(query, params).fetchall()
                return [self._row_to_example_with_run_state(row) for row in rows]
            else:
                # Canonical query: no run state
                query = "SELECT * FROM example_records WHERE family = ?"
                params = [family]

                # Without run_id, we can't filter by status (status is per-run)
                if status:
                    logger.warning(f"Status filter ignored without run_id in get_examples_by_family")

                query += " ORDER BY example_key ASC, example_id ASC"

                if limit:
                    query += " LIMIT ?"
                    params.append(limit)

                rows = conn.execute(query, params).fetchall()
                return [self._row_to_example(row) for row in rows]

    def get_examples_with_applicable_patterns(
        self, family: str, status: List[ExampleStatus], max_examples: Optional[int] = None, run_id: Optional[str] = None
    ) -> List[ExampleRecord]:
        """Get examples that could benefit from pattern-based fixes."""
        with self.get_connection() as conn:
            if run_id:
                status_placeholders = ','.join('?' * len(status))
                query = f"""
                    SELECT
                        er.*,
                        ers.status as run_status,
                        ers.failure_reason as run_failure_reason,
                        ers.escalation_reason as run_escalation_reason,
                        ers.compilable_code as run_compilable_code,
                        ers.verified_code as run_verified_code
                    FROM example_records er
                    INNER JOIN example_run_state ers ON er.example_id = ers.example_id
                    WHERE er.family = ? AND ers.run_id = ?
                      AND ers.status IN ({status_placeholders})
                    ORDER BY er.example_key ASC
                """  # nosec B608
                params = [family, run_id] + [s.value for s in status]
                if max_examples:
                    query += " LIMIT ?"
                    params.append(max_examples)

                rows = conn.execute(query, params).fetchall()
                return [self._row_to_example_with_run_state(row) for row in rows]
            return []

    def get_recent_runs(self, family: str, limit: int = 5) -> List['RunRecord']:
        """Get recent runs for a family."""
        with self.get_connection() as conn:
            query = """
                SELECT * FROM run_records
                WHERE family = ? ORDER BY started_at DESC LIMIT ?
            """
            rows = conn.execute(query, (family, limit)).fetchall()
            return [self._row_to_run_record(row) for row in rows]

    def get_examples_by_file(self, file_path: str, run_id: Optional[str] = None) -> List[ExampleRecord]:
        """
        Get all examples from a specific file.

        If run_id is provided, this method JOINs with example_run_state to get
        run-scoped status and code fields.

        Args:
            file_path: File path to filter by
            run_id: Optional run_id for run-scoped queries

        Returns:
            List of example records with run-scoped fields populated if run_id provided
        """
        with self.get_connection() as conn:
            if run_id:
                # Run-scoped query: JOIN with example_run_state
                query = """
                    SELECT
                        er.*,
                        ers.status as run_status,
                        ers.failure_reason as run_failure_reason,
                        ers.escalation_reason as run_escalation_reason,
                        ers.compilable_code as run_compilable_code,
                        ers.verified_code as run_verified_code
                    FROM example_records er
                    INNER JOIN example_run_state ers ON er.example_id = ers.example_id
                    WHERE er.file_path = ? AND ers.run_id = ?
                    ORDER BY er.location_block_index, er.example_key ASC, er.example_id ASC
                """
                rows = conn.execute(query, (file_path, run_id)).fetchall()
                return [self._row_to_example_with_run_state(row) for row in rows]
            else:
                # Canonical query: no run state
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
        run_id: Optional[str] = None,
        escalation_reason: Optional[str] = None,
    ) -> bool:
        """
        Update example status (run-scoped).

        Args:
            example_id: Example identifier
            status: New status
            failure_reason: Optional failure reason
            run_id: Run identifier (required for run-scoped updates)
            escalation_reason: Optional escalation reason (controlled vocabulary)

        Returns:
            True if successful, False otherwise
        """
        if not run_id:
            logger.warning(f"update_example_status called without run_id for {example_id}")
            return False

        # Task 2B: Single-writer protection
        with self._write_lock:
            with self.get_connection() as conn:
                now = datetime.now(timezone.utc).isoformat()
                conn.execute("""
                    UPDATE example_run_state
                    SET status = ?, failure_reason = ?, escalation_reason = ?, updated_at = ?
                    WHERE run_id = ? AND example_id = ?
                """, (status.value, failure_reason, escalation_reason, now, run_id, example_id))
                return conn.total_changes > 0
    
    def update_example_code(
        self,
        example_id: str,
        compilable_code: Optional[str] = None,
        verified_code: Optional[str] = None,
        run_id: Optional[str] = None,
    ) -> bool:
        """
        Update example code fields (run-scoped).

        Args:
            example_id: Example identifier
            compilable_code: Optional compiled code
            verified_code: Optional verified code
            run_id: Run identifier (required for run-scoped updates)

        Returns:
            True if successful, False otherwise
        """
        if not run_id:
            logger.warning(f"update_example_code called without run_id for {example_id}")
            return False

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
            params.append(datetime.now(timezone.utc).isoformat())
            params.extend([run_id, example_id])

            conn.execute(
                f"UPDATE example_run_state SET {', '.join(updates)} WHERE run_id = ? AND example_id = ?",  # nosec B608
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
            """, (original_code, datetime.now(timezone.utc).isoformat(), example_id))
            return conn.total_changes > 0

    # =========================================================================
    # EXAMPLE RUN STATE (Per-run state management)
    # =========================================================================

    def save_example_run_state(
        self,
        run_id: str,
        example_id: str,
        status: ExampleStatus = ExampleStatus.DISCOVERED,
        failure_reason: Optional[str] = None,
        escalation_reason: Optional[str] = None,
        compilable_code: Optional[str] = None,
        verified_code: Optional[str] = None,
        drift_score: float = 0.0,
        drift_similarity: float = 0.0,
        app_context: Optional[str] = None,
    ) -> bool:
        """
        Save or update example run state for a specific run.

        Args:
            run_id: Run identifier
            example_id: Example identifier
            status: Example status
            failure_reason: Optional failure reason
            escalation_reason: Optional escalation reason
            compilable_code: Code after compilation fixes
            verified_code: Code after runtime verification
            drift_score: Drift score
            drift_similarity: Drift similarity score
            app_context: Application architecture context

        Returns:
            True if successful
        """
        # Task 2B: Single-writer protection
        with self._write_lock:
            with self.get_connection() as conn:
                now = datetime.now(timezone.utc).isoformat()
                conn.execute("""
                    INSERT OR REPLACE INTO example_run_state (
                        run_id, example_id, status, failure_reason, escalation_reason,
                        compilable_code, verified_code, drift_score, drift_similarity,
                        app_context, needs_human_review, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    run_id,
                    example_id,
                    status.value,
                    failure_reason,
                    escalation_reason,
                    compilable_code,
                    verified_code,
                    drift_score,
                    drift_similarity,
                    app_context,
                    1 if status == ExampleStatus.NEEDS_REVIEW else 0,
                    now,
                    now,
                ))
                return True

    def get_example_run_state(
        self,
        run_id: str,
        example_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get example run state for a specific run.

        Args:
            run_id: Run identifier
            example_id: Example identifier

        Returns:
            Dictionary with run state or None if not found
        """
        with self.get_connection() as conn:
            row = conn.execute("""
                SELECT * FROM example_run_state
                WHERE run_id = ? AND example_id = ?
            """, (run_id, example_id)).fetchone()

            if row:
                return dict(row)
        return None

    def get_run_states_by_status(
        self,
        run_id: str,
        status: ExampleStatus,
        family: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get all example run states for a run filtered by status.

        Args:
            run_id: Run identifier
            status: Status filter
            family: Optional family filter
            limit: Optional result limit

        Returns:
            List of run state dictionaries
        """
        with self.get_connection() as conn:
            query = """
                SELECT ers.*, er.family, er.file_path, er.original_code
                FROM example_run_state ers
                JOIN example_records er ON ers.example_id = er.example_id
                WHERE ers.run_id = ? AND ers.status = ?
            """
            params = [run_id, status.value]

            if family:
                query += " AND er.family = ?"
                params.append(family)

            query += " ORDER BY er.example_key ASC, er.example_id ASC"

            if limit:
                query += " LIMIT ?"
                params.append(limit)

            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    def update_example_run_state_status(
        self,
        run_id: str,
        example_id: str,
        status: ExampleStatus,
        failure_reason: Optional[str] = None,
        escalation_reason: Optional[str] = None,
    ) -> bool:
        """
        Update status for an example in a specific run.

        Args:
            run_id: Run identifier
            example_id: Example identifier
            status: New status
            failure_reason: Optional failure reason
            escalation_reason: Optional escalation reason

        Returns:
            True if successful
        """
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE example_run_state
                SET status = ?, failure_reason = ?, escalation_reason = ?, updated_at = ?
                WHERE run_id = ? AND example_id = ?
            """, (
                status.value,
                failure_reason,
                escalation_reason,
                datetime.now(timezone.utc).isoformat(),
                run_id,
                example_id,
            ))
            return conn.total_changes > 0

    def update_example_run_state_code(
        self,
        run_id: str,
        example_id: str,
        compilable_code: Optional[str] = None,
        verified_code: Optional[str] = None,
    ) -> bool:
        """
        Update code fields for an example in a specific run.

        Args:
            run_id: Run identifier
            example_id: Example identifier
            compilable_code: Code after compilation fixes
            verified_code: Code after runtime verification

        Returns:
            True if successful
        """
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
            params.append(datetime.now(timezone.utc).isoformat())
            params.extend([run_id, example_id])

            conn.execute(
                f"UPDATE example_run_state SET {', '.join(updates)} WHERE run_id = ? AND example_id = ?",  # nosec B608
                params
            )
            return conn.total_changes > 0

    def count_run_states_by_status(
        self,
        run_id: str,
        family: Optional[str] = None,
    ) -> Dict[str, int]:
        """
        Count example run states grouped by status for a run.

        Args:
            run_id: Run identifier
            family: Optional family filter

        Returns:
            Dictionary mapping status to count
        """
        with self.get_connection() as conn:
            query = """
                SELECT ers.status, COUNT(*) as count
                FROM example_run_state ers
            """

            params = [run_id]

            if family:
                query += """
                    JOIN example_records er ON ers.example_id = er.example_id
                    WHERE ers.run_id = ? AND er.family = ?
                """
                params.append(family)
            else:
                query += " WHERE ers.run_id = ?"

            query += " GROUP BY ers.status"

            rows = conn.execute(query, params).fetchall()
            return {row['status']: row['count'] for row in rows}

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
                f"UPDATE example_run_state SET {', '.join(updates)} WHERE example_id = ?",  # nosec B608
                params
            )
            return conn.total_changes > 0

    def get_needs_review_examples(
        self,
        family: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[ExampleRecord]:
        """
        Get all examples in NEEDS_REVIEW state.

        Args:
            family: Optional family filter
            limit: Optional limit on results

        Returns:
            List of ExampleRecord instances requiring human review
        """
        with self.get_connection() as conn:
            query = "SELECT * FROM example_records WHERE status = ?"
            params = [ExampleStatus.NEEDS_REVIEW.value]

            if family:
                query += " AND family = ?"
                params.append(family)

            # Deterministic ordering: example_key (primary), then example_id (tie-breaker)
            query += " ORDER BY example_key ASC, example_id ASC"

            if limit:
                query += " LIMIT ?"
                params.append(limit)

            rows = conn.execute(query, params).fetchall()
            return [self._row_to_example(row) for row in rows]

    def _row_to_example(self, row: sqlite3.Row) -> ExampleRecord:
        """
        Convert database row to ExampleRecord (canonical fields only).

        This method reads ONLY canonical fields from example_records.
        Run-scoped fields (status, code, etc.) are set to defaults.
        """
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

        # Handle code block location fields (Migration 011)
        code_block_signature = row['code_block_signature'] if 'code_block_signature' in row.keys() else None
        extraction_warning = row['extraction_warning'] if 'extraction_warning' in row.keys() else None
        app_context = row['app_context'] if 'app_context' in row.keys() else None
        # Handle article_intent field (Migration 012)
        article_intent = row['article_intent'] if 'article_intent' in row.keys() else None

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
            # Run-scoped fields default to None/DISCOVERED
            compilable_code=None,
            verified_code=None,
            status=ExampleStatus.DISCOVERED,
            failure_reason=None,
            escalation_reason=None,
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at']),
            section_heading=section_heading,
            description_context=description_context,
            topic=topic,
            article_intent=article_intent,
            example_key=example_key,
            app_context=app_context,
            code_block_signature=code_block_signature,
            extraction_warning=extraction_warning,
        )

    def _row_to_example_with_run_state(self, row: sqlite3.Row) -> ExampleRecord:
        """
        Convert database row to ExampleRecord with run-scoped fields.

        This method reads canonical fields from example_records and
        run-scoped fields from the JOIN with example_run_state.
        """
        gist = None
        if row['gist_owner'] or row['gist_id']:
            gist = GistInfo(
                owner=row['gist_owner'] or '',
                gist_id=row['gist_id'] or '',
                filename=row['gist_filename'] or '',
            )

        # Handle context fields
        section_heading = row['section_heading'] if 'section_heading' in row.keys() else None
        description_context = row['description_context'] if 'description_context' in row.keys() else None
        topic = row['topic'] if 'topic' in row.keys() else None
        example_key = row['example_key'] if 'example_key' in row.keys() else ""

        # Handle code block location fields (Migration 011)
        code_block_signature = row['code_block_signature'] if 'code_block_signature' in row.keys() else None
        extraction_warning = row['extraction_warning'] if 'extraction_warning' in row.keys() else None
        app_context = row['app_context'] if 'app_context' in row.keys() else None
        # Handle article_intent field (Migration 012)
        article_intent = row['article_intent'] if 'article_intent' in row.keys() else None

        # Read run-scoped fields (prefixed with run_)
        status = ExampleStatus(row['run_status']) if 'run_status' in row.keys() else ExampleStatus.DISCOVERED
        failure_reason = row['run_failure_reason'] if 'run_failure_reason' in row.keys() else None
        escalation_reason = row['run_escalation_reason'] if 'run_escalation_reason' in row.keys() else None
        compilable_code = row['run_compilable_code'] if 'run_compilable_code' in row.keys() else None
        verified_code = row['run_verified_code'] if 'run_verified_code' in row.keys() else None

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
            # Run-scoped fields from example_run_state
            compilable_code=compilable_code,
            verified_code=verified_code,
            status=status,
            failure_reason=failure_reason,
            escalation_reason=escalation_reason,
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at']),
            section_heading=section_heading,
            description_context=description_context,
            topic=topic,
            article_intent=article_intent,
            example_key=example_key,
            app_context=app_context,
            code_block_signature=code_block_signature,
            extraction_warning=extraction_warning,
        )

    def _row_to_run_record(self, row: sqlite3.Row) -> 'RunRecord':
        """Convert database row to RunRecord."""
        from .models import RunRecord

        return RunRecord(
            run_id=row['run_id'],
            family=row['family'],
            started_at=datetime.fromisoformat(row['started_at']),
            completed_at=datetime.fromisoformat(row['completed_at']) if row['completed_at'] else None,
            status=row['status'],
            phases_completed=json.loads(row['phases_completed']) if row['phases_completed'] else [],
            current_phase=row['current_phase'] or '',
            examples_processed=row['examples_processed'] or 0,
            examples_successful=row['examples_successful'] or 0,
            examples_failed=row['examples_failed'] or 0,
            error=row['error'],
        )

    # =========================================================================
    # COMPILE ATTEMPTS
    # =========================================================================
    
    def save_compile_attempt(self, attempt: CompileAttempt, run_id: Optional[str] = None) -> str:
        """
        Save a compile attempt.

        Args:
            attempt: Compile attempt to save
            run_id: Optional run_id for run-scoped tracking

        Returns:
            attempt_id
        """
        # Task 2B: Single-writer protection
        with self._write_lock:
            with self.get_connection() as conn:
                conn.execute("""
                    INSERT INTO compile_attempts (
                        attempt_id, example_id, family, dll_version, success,
                        compiler_log_ref, input_code_ref, output_code_ref,
                        llm_request_ref, llm_response_ref,
                        error_messages, warnings, timestamp, run_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    run_id,  # NEW: run_id parameter
                ))
            return attempt.attempt_id
    
    def get_compile_attempts(self, example_id: str, run_id: Optional[str] = None) -> List[CompileAttempt]:
        """
        Get all compile attempts for an example, optionally filtered by run_id.

        Args:
            example_id: Example identifier
            run_id: Optional run_id filter for run-scoped queries

        Returns:
            List of compile attempts
        """
        with self.get_connection() as conn:
            query = "SELECT * FROM compile_attempts WHERE example_id = ?"
            params = [example_id]

            # NEW: Filter by run_id if provided
            if run_id:
                query += " AND run_id = ?"
                params.append(run_id)

            query += " ORDER BY timestamp"

            rows = conn.execute(query, params).fetchall()
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
    
    def save_runtime_attempt(self, attempt: RuntimeAttempt, run_id: Optional[str] = None) -> str:
        """
        Save a runtime attempt.

        Args:
            attempt: Runtime attempt to save
            run_id: Optional run_id for run-scoped tracking

        Returns:
            attempt_id
        """
        # Task 2B: Single-writer protection
        with self._write_lock:
            with self.get_connection() as conn:
                conn.execute("""
                    INSERT INTO runtime_attempts (
                        attempt_id, example_id, family, sample_ref, scenario,
                        success, runtime_log_ref, exit_code, stdout, stderr,
                        exception_type, exception_message, output_files,
                        environment, retrieved_examples_refs,
                        llm_request_ref, llm_response_ref, timestamp, run_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    run_id,  # NEW: run_id parameter
                ))
            return attempt.attempt_id
    
    def get_runtime_attempts(self, example_id: str, run_id: Optional[str] = None) -> List[RuntimeAttempt]:
        """
        Get all runtime attempts for an example, optionally filtered by run_id.

        Args:
            example_id: Example identifier
            run_id: Optional run_id filter for run-scoped queries

        Returns:
            List of runtime attempts
        """
        with self.get_connection() as conn:
            query = "SELECT * FROM runtime_attempts WHERE example_id = ?"
            params = [example_id]

            # NEW: Filter by run_id if provided
            if run_id:
                query += " AND run_id = ?"
                params.append(run_id)

            query += " ORDER BY timestamp"

            rows = conn.execute(query, params).fetchall()
            
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
    # FAILURE DETAILS (Track 2: Agent C - Multi-Level Timeouts)
    # =========================================================================

    def insert_failure_detail(
        self,
        example_id: str,
        family: str,
        phase: Optional[str],
        failure_type: str,
        failure_reason: str,
        operation: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        DEPRECATED: Use failure_tracking.FailureTracker.save_failure_detail() instead.

        This method is kept for backward compatibility but will be removed in a future version.
        The new failure tracking API uses FailureDetail model with failure_category instead of failure_type.
        """
        logger.warning(
            "insert_failure_detail() is deprecated. Use failure_tracking.FailureTracker.save_failure_detail() instead"
        )
        raise NotImplementedError(
            "insert_failure_detail() has been deprecated. "
            "Use failure_tracking.FailureTracker.save_failure_detail() with FailureDetail model instead. "
            "See migrations/007_failure_details_tracking.sql for the new schema."
        )

    def get_failure_details(self, example_id: str) -> List[Dict[str, Any]]:
        """
        Get all failure details for an example.

        Args:
            example_id: Example identifier

        Returns:
            List of failure detail records
        """
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM failure_details WHERE example_id = ? ORDER BY timestamp",
                (example_id,)
            ).fetchall()

            return [dict(row) for row in rows]

    def get_timeout_failures(self, run_id: str) -> List[Dict[str, Any]]:
        """
        Get all timeout failures for a run.

        Args:
            run_id: Run identifier

        Returns:
            List of timeout failure records
        """
        with self.get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM failure_details
                WHERE run_id = ? AND failure_category = 'timeout'
                ORDER BY timestamp DESC
            """, (run_id,)).fetchall()

            return [dict(row) for row in rows]

    # =========================================================================
    # MARKDOWN EDITS
    # =========================================================================
    
    def save_markdown_edit(self, edit: MarkdownEdit, run_id: Optional[str] = None) -> str:
        """
        Save a markdown edit.

        Args:
            edit: Markdown edit to save
            run_id: Optional run_id for run-scoped tracking

        Returns:
            edit_id
        """
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO markdown_edits (
                    edit_id, file_path, example_id, family,
                    edit_type, diff_ref, old_code, new_code, timestamp, run_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                run_id,  # NEW: run_id parameter
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
    # COMMIT RECORDS
    # =========================================================================

    def save_commit_record(
        self,
        run_id: str,
        family: str,
        commit_hash: str,
        message: str,
        touched_files: List[str],
        description: str = "",
    ) -> str:
        """Persist a git commit record for a pipeline run.

        Args:
            run_id: Pipeline run that produced this commit.
            family: Family identifier (e.g. "imaging").
            commit_hash: Full SHA-1 from ``git rev-parse HEAD``.
            message: First line of the git commit message.
            touched_files: Absolute or repo-relative paths that were staged.
            description: Optional extended body of the commit message.

        Returns:
            commit_id (UUID string)
        """
        import uuid
        commit_id = str(uuid.uuid4())
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO commit_records
                    (commit_id, run_id, family, hash, message, description,
                     touched_files, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    commit_id,
                    run_id,
                    family,
                    commit_hash,
                    message,
                    description,
                    "\n".join(touched_files),
                    datetime.utcnow().isoformat(),
                ),
            )
        return commit_id

    def get_commit_records(self, run_id: str) -> List[dict]:
        """Return all commit records for a given run_id."""
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM commit_records WHERE run_id = ? ORDER BY timestamp",
                (run_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    # =========================================================================
    # RUN RECORDS
    # =========================================================================

    def get_latest_run_id(self, family: str) -> Optional[str]:
        """Get the primary run_id for a family (the one with the most examples)."""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT run_id FROM example_run_state WHERE run_id IS NOT NULL "
                "GROUP BY run_id ORDER BY COUNT(*) DESC LIMIT 1"
            ).fetchone()
            return row[0] if row else None

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

        Queries example_run_state to get accurate counts based on status.
        This ensures stats reflect true DB state, not accumulated counters.

        Args:
            family: Family identifier
            run_id: Optional run ID to filter by (for run-scoped tracking)

        Returns:
            Dictionary with total_processed, verified, failed counts
        """
        with self.get_connection() as conn:
            # Count examples by status for this family and run
            if run_id:
                counts = conn.execute("""
                    SELECT
                        COUNT(*) as total,
                        SUM(CASE WHEN ers.status = 'VERIFIED' OR ers.status = 'MD_UPDATED' OR ers.status = 'FINAL_REVIEW_PASSED' OR ers.status = 'COMMITTED' THEN 1 ELSE 0 END) as verified,
                        SUM(CASE WHEN ers.status LIKE '%FAILED%' THEN 1 ELSE 0 END) as failed
                    FROM example_records er
                    JOIN example_run_state ers ON er.example_id = ers.example_id
                    WHERE er.family = ? AND ers.run_id = ?
                """, (family, run_id)).fetchone()
            else:
                # Fallback: count all examples for family across all runs
                counts = conn.execute("""
                    SELECT
                        COUNT(*) as total,
                        SUM(CASE WHEN ers.status = 'VERIFIED' OR ers.status = 'MD_UPDATED' OR ers.status = 'FINAL_REVIEW_PASSED' OR ers.status = 'COMMITTED' THEN 1 ELSE 0 END) as verified,
                        SUM(CASE WHEN ers.status LIKE '%FAILED%' THEN 1 ELSE 0 END) as failed
                    FROM example_records er
                    JOIN example_run_state ers ON er.example_id = ers.example_id
                    WHERE er.family = ?
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
                datetime.now(timezone.utc).isoformat(),
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
                f"UPDATE telemetry_runs SET {', '.join(set_clauses)} WHERE event_id = ?",  # nosec B608
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

    def get_runtime_kpis(self, run_id: Optional[str] = None, family: Optional[str] = None) -> Dict[str, Any]:
        """
        Calculate runtime KPIs excluding infrastructure failures.

        This method calculates key performance indicators for runtime validation
        while excluding examples that failed due to infrastructure issues
        (missing test data). This provides a clearer picture of actual runtime
        success rate vs infrastructure blockers.

        Args:
            run_id: Optional run_id to filter by specific run
            family: Optional family to filter by specific family

        Returns:
            Dict with KPIs:
                - total_runtime_attempted: Total examples that reached runtime phase
                - verified_count: Examples that passed runtime validation
                - infra_blocked_count: Examples blocked by missing test data
                - runtime_error_count: Examples that failed runtime (excluding infra)
                - runtime_verified_rate_excluding_infra: verified / (total - infra_blocked)
                - infra_blocked_rate: infra_blocked / total
        """
        with self.get_connection() as conn:
            # Build query conditions
            where_conditions = []
            params = []

            if run_id:
                where_conditions.append("fd.run_id = ?")
                params.append(run_id)
            if family:
                where_conditions.append("er.family = ?")
                params.append(family)

            # Proper WHERE clause construction with parentheses
            where_clause = ""
            if where_conditions:
                where_clause = " AND (" + " AND ".join(where_conditions) + ")"

            # Get failure counts by category
            # Uses failure_details (which has run_id) joined with example_records (for family)
            query = f"""
                SELECT
                    fd.failure_category,
                    COUNT(*) as count
                FROM failure_details fd
                JOIN example_records er ON fd.example_id = er.example_id
                WHERE (fd.phase = 'Phase C (Pre-Runtime)' OR fd.phase LIKE 'Phase C%')
                {where_clause}
                GROUP BY fd.failure_category
            """  # nosec B608

            failure_rows = conn.execute(query, tuple(params)).fetchall()
            failure_counts = {row['failure_category']: row['count'] for row in failure_rows}

            # Get verified count from example_run_state (not example_records!)
            # FIXED: Query from example_run_state which has run_id and status
            verified_where_conditions = []
            verified_params = []

            if run_id and family:
                # Both run_id and family - need to join with example_records
                verified_query = """
                    SELECT COUNT(*) as count
                    FROM example_run_state ers
                    JOIN example_records er ON ers.example_id = er.example_id
                    WHERE ers.run_id = ? AND ers.status = 'VERIFIED' AND er.family = ?
                """
                verified_params = [run_id, family]
            elif run_id:
                # Only run_id - can query example_run_state directly
                verified_query = """
                    SELECT COUNT(*) as count
                    FROM example_run_state ers
                    WHERE ers.run_id = ? AND ers.status = 'VERIFIED'
                """
                verified_params = [run_id]
            elif family:
                # Only family - need to join with example_records but no run filter
                # This queries across ALL runs for this family
                verified_query = """
                    SELECT COUNT(*) as count
                    FROM example_run_state ers
                    JOIN example_records er ON ers.example_id = er.example_id
                    WHERE ers.status = 'VERIFIED' AND er.family = ?
                """
                verified_params = [family]
            else:
                # No filters - count all VERIFIED across all runs
                verified_query = """
                    SELECT COUNT(*) as count
                    FROM example_run_state ers
                    WHERE ers.status = 'VERIFIED'
                """
                verified_params = []

            verified_count = conn.execute(verified_query, tuple(verified_params)).fetchone()['count']

            # Calculate metrics
            infra_blocked = failure_counts.get('infra_missing_test_data', 0)
            runtime_errors = sum(
                count for category, count in failure_counts.items()
                if category in ['runtime_error', 'timeout', 'compile_error']
            )
            total_attempted = verified_count + infra_blocked + runtime_errors

            # Calculate rates
            total_excluding_infra = total_attempted - infra_blocked
            runtime_verified_rate_excluding_infra = (
                (verified_count / total_excluding_infra * 100) if total_excluding_infra > 0 else 0.0
            )
            infra_blocked_rate = (
                (infra_blocked / total_attempted * 100) if total_attempted > 0 else 0.0
            )

            return {
                'total_runtime_attempted': total_attempted,
                'verified_count': verified_count,
                'infra_blocked_count': infra_blocked,
                'runtime_error_count': runtime_errors,
                'runtime_verified_rate_excluding_infra': round(runtime_verified_rate_excluding_infra, 2),
                'infra_blocked_rate': round(infra_blocked_rate, 2),
                'total_excluding_infra': total_excluding_infra,
            }

    def get_phase2_metrics(self, run_id: str, family: str) -> Dict[str, Any]:
        """
        Calculate comprehensive Phase-2 metrics including all 3 required rates.

        Phase-2 Metrics:
        1. overall_verified_rate = VERIFIED / total_examples
        2. eligible_verified_rate = VERIFIED / eligible_examples
        3. runtime_verified_rate = verified_runtime / runtime_attempted

        Where:
        - eligible_examples = total_examples - INFRA_BLOCKED - NEEDS_REVIEW(precheck_only)
        - INFRA_BLOCKED includes: missing fixtures, password issues, unsupported formats
        - NEEDS_REVIEW(precheck_only) includes: empty code, comments only, incomplete

        Args:
            run_id: Pipeline run ID
            family: Product family

        Returns:
            Dict with all Phase-2 metrics and denominators
        """
        with self.get_connection() as conn:
            # Get total examples in run
            total_row = conn.execute("""
                SELECT COUNT(*) as count
                FROM example_run_state ers
                JOIN example_records er ON ers.example_id = er.example_id
                WHERE ers.run_id = ? AND er.family = ?
            """, (run_id, family)).fetchone()
            total_examples = total_row['count'] if total_row else 0

            # Get status counts
            status_rows = conn.execute("""
                SELECT ers.status, COUNT(*) as count
                FROM example_run_state ers
                JOIN example_records er ON ers.example_id = er.example_id
                WHERE ers.run_id = ? AND er.family = ?
                GROUP BY ers.status
            """, (run_id, family)).fetchall()
            status_counts = {row['status']: row['count'] for row in status_rows}

            # Get verified count
            verified_count = status_counts.get('VERIFIED', 0)

            # Get INFRA_BLOCKED count (from status)
            infra_blocked_status = status_counts.get('INFRA_BLOCKED', 0)

            # Get NEEDS_REVIEW count
            needs_review_count = status_counts.get('NEEDS_REVIEW', 0)

            # Get detailed failure breakdown by category
            failure_rows = conn.execute("""
                SELECT fd.failure_category, COUNT(*) as count
                FROM failure_details fd
                JOIN example_records er ON fd.example_id = er.example_id
                WHERE fd.run_id = ? AND er.family = ?
                GROUP BY fd.failure_category
            """, (run_id, family)).fetchall()
            failure_counts = {row['failure_category']: row['count'] for row in failure_rows}

            # Calculate INFRA_BLOCKED from failures (may be more accurate than status)
            infra_blocked_failures = (
                failure_counts.get('infra_missing_test_data', 0) +
                failure_counts.get('infra_blocked_rar_fixture', 0) +
                failure_counts.get('infra_blocked_7z_fixture', 0) +
                failure_counts.get('infra_blocked_password', 0) +
                failure_counts.get('infra_blocked_format', 0) +
                failure_counts.get('infra_blocked_external', 0)
            )
            infra_blocked_count = max(infra_blocked_status, infra_blocked_failures)

            # Get NEEDS_REVIEW that are precheck_only failures
            precheck_count = failure_counts.get('precheck_only', 0)
            # Also count NEEDS_REVIEW with precheck-related escalation reasons
            precheck_escalation_row = conn.execute("""
                SELECT COUNT(*) as count
                FROM example_run_state ers
                JOIN example_records er ON ers.example_id = er.example_id
                WHERE ers.run_id = ? AND er.family = ?
                  AND ers.status = 'NEEDS_REVIEW'
                  AND (
                      ers.escalation_reason IN (
                          'empty_code', 'only_comments', 'no_csharp_code_block',
                          'snippet_too_incomplete'
                      )
                  )
            """, (run_id, family)).fetchone()
            precheck_escalation_count = precheck_escalation_row['count'] if precheck_escalation_row else 0
            precheck_only_count = max(precheck_count, precheck_escalation_count)

            # Calculate eligible examples
            eligible_examples = total_examples - infra_blocked_count - precheck_only_count

            # Get runtime-specific metrics
            # Runtime attempted = COMPILABLE that entered runtime phase
            compilable_count = status_counts.get('COMPILABLE', 0)
            runtime_failed_count = status_counts.get('RUNTIME_FAILED', 0)
            runtime_attempted = verified_count + runtime_failed_count

            # Calculate the 3 required rates
            overall_verified_rate = (
                (verified_count / total_examples * 100) if total_examples > 0 else 0.0
            )
            eligible_verified_rate = (
                (verified_count / eligible_examples * 100) if eligible_examples > 0 else 0.0
            )
            runtime_verified_rate = (
                (verified_count / runtime_attempted * 100) if runtime_attempted > 0 else 0.0
            )

            # Closure gate evaluation
            gate_a_pass = overall_verified_rate >= 90.0
            gate_b_pass = eligible_verified_rate >= 90.0

            return {
                # Counts
                'total_examples': total_examples,
                'eligible_examples': eligible_examples,
                'verified_count': verified_count,
                'infra_blocked_count': infra_blocked_count,
                'precheck_only_count': precheck_only_count,
                'needs_review_count': needs_review_count,
                'compile_failed_count': status_counts.get('COMPILE_FAILED', 0),
                'compilable_count': compilable_count,
                'runtime_failed_count': runtime_failed_count,
                'runtime_attempted': runtime_attempted,

                # The 3 required rates (as percentages)
                'overall_verified_rate': round(overall_verified_rate, 2),
                'eligible_verified_rate': round(eligible_verified_rate, 2),
                'runtime_verified_rate': round(runtime_verified_rate, 2),

                # Closure gate results
                'gate_a_pass': gate_a_pass,
                'gate_b_pass': gate_b_pass,
                'gate_selected': 'B',  # Gate B is recommended
                'gate_pass': gate_b_pass,

                # Status breakdown
                'status_counts': status_counts,

                # Infra blockers breakdown
                'infra_breakdown': {
                    'missing_test_data': failure_counts.get('infra_missing_test_data', 0),
                    'missing_rar_fixture': failure_counts.get('infra_blocked_rar_fixture', 0),
                    'missing_7z_fixture': failure_counts.get('infra_blocked_7z_fixture', 0),
                    'requires_password': failure_counts.get('infra_blocked_password', 0),
                    'unsupported_format': failure_counts.get('infra_blocked_format', 0),
                    'external_dependency': failure_counts.get('infra_blocked_external', 0),
                },
            }

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
                fingerprint.timestamp.isoformat() if fingerprint.timestamp else datetime.now(timezone.utc).isoformat(),
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
                        datetime.now(timezone.utc).isoformat(),
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
                    now = datetime.now(timezone.utc).isoformat()
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

    # =========================================================================
    # FAILURE TRACKING
    # =========================================================================

    def save_failure_detail(self, failure: 'FailureDetail') -> str:
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

    def get_failure_details_by_run(self, run_id: str) -> List['FailureDetail']:
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

            return [self._row_to_failure_detail(row) for row in rows]

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

    def update_failure_resolution(self, failure_id: str, resolution: 'FailureResolution') -> bool:
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

    def copy_run_to_production(self, run_id: str, commit_hash: str) -> bool:
        """
        Copy entire run to production database after successful commit.

        This includes:
        - run_records
        - example_records (canonical)
        - example_run_state (run-scoped)
        - compile_attempts, runtime_attempts, markdown_edits
        - telemetry_runs, telemetry_events
        - failure_details, review_results

        Args:
            run_id: Run identifier
            commit_hash: Git commit hash (for verification)

        Returns:
            True if copy succeeded, False otherwise
        """
        if not self.production_db_path:
            return False  # Production DB not configured

        try:
            with self._write_lock:
                # 1. Query all data for this run from dev DB
                with self.get_connection() as dev_conn:
                    # Get run record
                    run = dev_conn.execute(
                        "SELECT * FROM run_records WHERE run_id = ?", (run_id,)
                    ).fetchone()

                    # Get telemetry (verify commit_hash if provided)
                    if commit_hash:
                        telemetry = dev_conn.execute(
                            "SELECT * FROM telemetry_runs WHERE run_id = ? AND git_commit_hash = ?",
                            (run_id, commit_hash)
                        ).fetchone()
                    else:
                        # CS_FILE-only runs have no commit — get telemetry by run_id alone
                        telemetry = dev_conn.execute(
                            "SELECT * FROM telemetry_runs WHERE run_id = ?",
                            (run_id,)
                        ).fetchone()

                    if not telemetry:
                        logger.warning(f"No telemetry for run {run_id}")
                        return False

                    # Get all example_ids for this run
                    example_ids = [
                        row['example_id'] for row in dev_conn.execute(
                            "SELECT DISTINCT example_id FROM example_run_state WHERE run_id = ?",
                            (run_id,)
                        ).fetchall()
                    ]

                    # Collect all related data
                    examples = []
                    for eid in example_ids:
                        ex = dev_conn.execute(
                            "SELECT * FROM example_records WHERE example_id = ?", (eid,)
                        ).fetchone()
                        if ex:
                            examples.append(ex)

                    run_states = dev_conn.execute(
                        "SELECT * FROM example_run_state WHERE run_id = ?", (run_id,)
                    ).fetchall()

                    compile_attempts = dev_conn.execute(
                        "SELECT * FROM compile_attempts WHERE run_id = ?", (run_id,)
                    ).fetchall()

                    runtime_attempts = dev_conn.execute(
                        "SELECT * FROM runtime_attempts WHERE run_id = ?", (run_id,)
                    ).fetchall()

                    markdown_edits = dev_conn.execute(
                        "SELECT * FROM markdown_edits WHERE run_id = ?", (run_id,)
                    ).fetchall()

                    failure_details = dev_conn.execute(
                        "SELECT * FROM failure_details WHERE run_id = ?", (run_id,)
                    ).fetchall()

                    review_results = dev_conn.execute(
                        "SELECT * FROM review_results WHERE run_id = ?", (run_id,)
                    ).fetchall()

                    telemetry_events = dev_conn.execute(
                        "SELECT * FROM telemetry_events WHERE run_id = ?", (run_id,)
                    ).fetchall()

                # 2. Write to production DB in transaction
                with self.get_production_connection() as prod_conn:
                    # Insert run_records
                    if run:
                        placeholders = ','.join(['?' for _ in run])
                        prod_conn.execute(
                            f"INSERT OR REPLACE INTO run_records VALUES ({placeholders})",  # nosec B608
                            tuple(run)
                        )

                    # Insert example_records (may already exist, use INSERT OR IGNORE)
                    for example in examples:
                        placeholders = ','.join(['?' for _ in example])
                        prod_conn.execute(
                            f"INSERT OR IGNORE INTO example_records VALUES ({placeholders})",  # nosec B608
                            tuple(example)
                        )

                    # Insert example_run_state
                    for state in run_states:
                        placeholders = ','.join(['?' for _ in state])
                        prod_conn.execute(
                            f"INSERT OR REPLACE INTO example_run_state VALUES ({placeholders})",  # nosec B608
                            tuple(state)
                        )

                    # Insert compile_attempts
                    for attempt in compile_attempts:
                        placeholders = ','.join(['?' for _ in attempt])
                        prod_conn.execute(
                            f"INSERT OR IGNORE INTO compile_attempts VALUES ({placeholders})",  # nosec B608
                            tuple(attempt)
                        )

                    # Insert runtime_attempts
                    for attempt in runtime_attempts:
                        placeholders = ','.join(['?' for _ in attempt])
                        prod_conn.execute(
                            f"INSERT OR IGNORE INTO runtime_attempts VALUES ({placeholders})",  # nosec B608
                            tuple(attempt)
                        )

                    # Insert markdown_edits
                    for edit in markdown_edits:
                        placeholders = ','.join(['?' for _ in edit])
                        prod_conn.execute(
                            f"INSERT OR IGNORE INTO markdown_edits VALUES ({placeholders})",  # nosec B608
                            tuple(edit)
                        )

                    # Insert telemetry_runs
                    placeholders = ','.join(['?' for _ in telemetry])
                    prod_conn.execute(
                        f"INSERT OR REPLACE INTO telemetry_runs VALUES ({placeholders})",  # nosec B608
                        tuple(telemetry)
                    )

                    # Insert failure_details
                    for detail in failure_details:
                        placeholders = ','.join(['?' for _ in detail])
                        prod_conn.execute(
                            f"INSERT OR IGNORE INTO failure_details VALUES ({placeholders})",  # nosec B608
                            tuple(detail)
                        )

                    # Insert review_results
                    for result in review_results:
                        placeholders = ','.join(['?' for _ in result])
                        prod_conn.execute(
                            f"INSERT OR IGNORE INTO review_results VALUES ({placeholders})",  # nosec B608
                            tuple(result)
                        )

                    # Insert telemetry_events
                    for event in telemetry_events:
                        placeholders = ','.join(['?' for _ in event])
                        prod_conn.execute(
                            f"INSERT OR IGNORE INTO telemetry_events VALUES ({placeholders})",  # nosec B608
                            tuple(event)
                        )

            logger.info(f"Successfully copied run {run_id} to production database")
            return True

        except Exception as e:
            logger.error(f"Failed to copy run {run_id} to production DB: {e}")
            return False

    def _row_to_failure_detail(self, row: sqlite3.Row) -> 'FailureDetail':
        """Convert database row to FailureDetail."""
        from .models import FailureDetail, FailureCategory, FailureResolution

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

    # =========================================================================
    # SEMANTIC SIGNATURES & DRIFT REJECTIONS (DRIFT-02)
    # =========================================================================

    def save_semantic_signature(
        self,
        example_id: str,
        run_id: str,
        attempt_type: str,
        signature_data: Dict[str, Any],
        attempt_id: Optional[str] = None,
    ) -> str:
        """
        Save a semantic signature for an example at a given attempt.

        Args:
            example_id: Example identifier
            run_id: Pipeline run ID
            attempt_type: 'original', 'compile_attempt', or 'runtime_attempt'
            signature_data: Dict with enum_values, method_calls, constructor_types, property_assignments
            attempt_id: Optional compile/runtime attempt ID

        Returns:
            signature_id
        """
        sig_id = hashlib.sha256(
            f"{example_id}:{run_id}:{attempt_type}:{attempt_id or ''}".encode()
        ).hexdigest()[:16]

        with self._write_lock:
            with self.get_connection() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO semantic_signatures (
                        signature_id, example_id, run_id, attempt_type, attempt_id,
                        enum_values, method_calls, constructor_types,
                        property_assignments, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    sig_id,
                    example_id,
                    run_id,
                    attempt_type,
                    attempt_id,
                    json.dumps(signature_data.get('enum_values', {})),
                    json.dumps(signature_data.get('method_calls', [])),
                    json.dumps(signature_data.get('constructor_types', [])),
                    json.dumps(signature_data.get('property_assignments', {})),
                    datetime.now(timezone.utc).isoformat(),
                ))
        return sig_id

    def save_drift_rejection(
        self,
        example_id: str,
        run_id: str,
        attempt_id: str,
        phase: str,
        rejection_reason: str,
        drift_score: float,
        signature_drift: Optional[Dict[str, Any]] = None,
        critical_enum_changes: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Save a drift rejection record.

        Args:
            example_id: Example identifier
            run_id: Pipeline run ID
            attempt_id: Compile/runtime attempt ID
            phase: 'compilation' or 'runtime'
            rejection_reason: Human-readable reason for rejection
            drift_score: Computed drift score
            signature_drift: Full signature drift details (JSON)
            critical_enum_changes: Critical enum changes detected (JSON)

        Returns:
            rejection_id
        """
        rej_id = hashlib.sha256(
            f"{example_id}:{run_id}:{attempt_id}:{phase}".encode()
        ).hexdigest()[:16]

        with self._write_lock:
            with self.get_connection() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO drift_rejections (
                        rejection_id, example_id, run_id, attempt_id, phase,
                        rejection_reason, drift_score, signature_drift,
                        critical_enum_changes, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    rej_id,
                    example_id,
                    run_id,
                    attempt_id,
                    phase,
                    rejection_reason,
                    drift_score,
                    json.dumps(signature_drift) if signature_drift else None,
                    json.dumps(critical_enum_changes) if critical_enum_changes else None,
                    datetime.now(timezone.utc).isoformat(),
                ))
        return rej_id

    def get_drift_rejections(
        self,
        run_id: str,
        phase: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get all drift rejections for a run, optionally filtered by phase.

        Args:
            run_id: Pipeline run ID
            phase: Optional filter ('compilation' or 'runtime')

        Returns:
            List of rejection records as dicts
        """
        with self.get_connection() as conn:
            if phase:
                rows = conn.execute(
                    "SELECT * FROM drift_rejections WHERE run_id = ? AND phase = ? ORDER BY created_at",
                    (run_id, phase),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM drift_rejections WHERE run_id = ? ORDER BY created_at",
                    (run_id,),
                ).fetchall()
            return [dict(r) for r in rows]

    def get_semantic_signatures(
        self,
        example_id: str,
        run_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get semantic signatures for an example, optionally filtered by run.

        Args:
            example_id: Example identifier
            run_id: Optional pipeline run ID filter

        Returns:
            List of signature records as dicts
        """
        with self.get_connection() as conn:
            if run_id:
                rows = conn.execute(
                    "SELECT * FROM semantic_signatures WHERE example_id = ? AND run_id = ? ORDER BY created_at",
                    (example_id, run_id),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM semantic_signatures WHERE example_id = ? ORDER BY created_at",
                    (example_id,),
                ).fetchall()
            return [dict(r) for r in rows]

    def get_drift_rejection_rate(self, run_id: str) -> Dict[str, Any]:
        """
        Compute drift rejection statistics for a run.

        Args:
            run_id: Pipeline run ID

        Returns:
            Dict with total, by_phase, by_reason counts
        """
        with self.get_connection() as conn:
            total = conn.execute(
                "SELECT COUNT(*) FROM drift_rejections WHERE run_id = ?",
                (run_id,),
            ).fetchone()[0]

            by_phase = {}
            for row in conn.execute(
                "SELECT phase, COUNT(*) as cnt FROM drift_rejections WHERE run_id = ? GROUP BY phase",
                (run_id,),
            ).fetchall():
                by_phase[row[0]] = row[1]

            by_reason = {}
            for row in conn.execute(
                "SELECT rejection_reason, COUNT(*) as cnt FROM drift_rejections WHERE run_id = ? GROUP BY rejection_reason ORDER BY cnt DESC LIMIT 10",
                (run_id,),
            ).fetchall():
                by_reason[row[0]] = row[1]

            return {
                "total": total,
                "by_phase": by_phase,
                "by_reason": by_reason,
            }

    # ── TC-06: Work Queue Methods ──────────────────────────────────

    def enqueue_work(
        self,
        family: str,
        trigger_source: str = "manual",
        priority: int = 5,
        max_examples: Optional[int] = None,
        skip_llm: bool = False,
    ) -> str:
        """Enqueue a work item for autonomous processing."""
        import uuid
        queue_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO work_queue
                    (queue_id, family, trigger_source, priority, status,
                     max_examples, skip_llm, created_at)
                VALUES (?, ?, ?, ?, 'pending', ?, ?, ?)
            """, (queue_id, family, trigger_source, priority,
                  max_examples, 1 if skip_llm else 0, now))
            conn.commit()

        logger.info(f"Enqueued work: {queue_id} family={family} priority={priority}")
        return queue_id

    def poll_next_work(self) -> Optional[Dict[str, Any]]:
        """
        Atomically claim the highest-priority pending work item.
        Returns the work item dict or None if queue is empty.
        """
        now = datetime.now(timezone.utc).isoformat()

        with self._write_lock:
            with self.get_connection() as conn:
                row = conn.execute("""
                    SELECT queue_id, family, trigger_source, priority,
                           max_examples, skip_llm, created_at
                    FROM work_queue
                    WHERE status = 'pending'
                    ORDER BY priority DESC, created_at ASC
                    LIMIT 1
                """).fetchone()

                if not row:
                    return None

                queue_id = row["queue_id"]
                conn.execute("""
                    UPDATE work_queue
                    SET status = 'claimed', claimed_at = ?
                    WHERE queue_id = ? AND status = 'pending'
                """, (now, queue_id))
                conn.commit()

                return {
                    "queue_id": queue_id,
                    "family": row["family"],
                    "trigger_source": row["trigger_source"],
                    "priority": row["priority"],
                    "max_examples": row["max_examples"],
                    "skip_llm": bool(row["skip_llm"]),
                }

    def complete_work(
        self,
        queue_id: str,
        run_id: Optional[str] = None,
        success: bool = True,
        error: Optional[str] = None,
    ) -> None:
        """Mark a work queue item as completed or failed."""
        now = datetime.now(timezone.utc).isoformat()
        status = "completed" if success else "failed"

        with self.get_connection() as conn:
            conn.execute("""
                UPDATE work_queue
                SET status = ?, completed_at = ?, run_id = ?, error = ?
                WHERE queue_id = ?
            """, (status, now, run_id, error, queue_id))
            conn.commit()
