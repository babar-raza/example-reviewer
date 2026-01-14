"""
Database module for Example Review System.
Provides SQLite connection, queries, and data models.
"""

import sqlite3
import json
import hashlib
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
from contextlib import contextmanager


@dataclass
class Page:
    """Represents a markdown page containing code snippets."""
    page_id: Optional[int]
    file_path: str
    relative_path: str
    site: str
    family: str
    language: str = 'en'
    state: str = 'unscanned'
    content_hash: Optional[str] = None
    last_scanned_at: Optional[str] = None
    last_validated_at: Optional[str] = None
    last_patched_at: Optional[str] = None
    snippet_count: int = 0
    verified_snippet_count: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class Snippet:
    """Represents a code snippet within a page."""
    snippet_id: Optional[int]
    page_id: int
    snippet_ordinal: int
    locator_json: str
    snippet_type: str
    language: Optional[str]
    status: str = 'unverified'
    first_seen_at: Optional[str] = None
    last_validated_at: Optional[str] = None
    validation_attempts: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class SnippetVersion:
    """Represents a version of a snippet (original, fixed, current)."""
    version_id: Optional[int]
    snippet_id: int
    version_type: str
    code_content: str
    content_hash: str
    created_at: Optional[str] = None
    created_by: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class Run:
    """Represents an execution run (discovery, validation, patching)."""
    run_id: Optional[int]
    run_type: str
    family: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    status: str = 'running'
    pages_processed: int = 0
    snippets_processed: int = 0
    config_snapshot: Optional[str] = None
    error_message: Optional[str] = None


class Database:
    """Database connection and operations manager."""

    def __init__(self, db_path: Path):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None

    def connect(self):
        """Establish database connection with WAL mode."""
        if self._conn is None:
            self._conn = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
                isolation_level=None  # Autocommit mode
            )
            self._conn.row_factory = sqlite3.Row
            # Enable WAL mode and foreign keys
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")

    def close(self):
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    @contextmanager
    def transaction(self):
        """Context manager for transactions."""
        self.connect()
        try:
            self._conn.execute("BEGIN")
            yield
            self._conn.execute("COMMIT")
        except Exception:
            self._conn.execute("ROLLBACK")
            raise

    def initialize_schema(self, schema_path: Path):
        """
        Initialize database schema from SQL file.

        Args:
            schema_path: Path to schema.sql file
        """
        self.connect()
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        self._conn.executescript(schema_sql)
        self._conn.commit()

    # ========================================================================
    # PAGE OPERATIONS
    # ========================================================================

    def get_or_create_page(self, file_path: str, relative_path: str, site: str,
                          family: str, language: str = 'en') -> int:
        """
        Get existing page or create new one.

        Args:
            file_path: Absolute file path
            relative_path: Relative path from content root
            site: Site name (blog, docs, kb, reference, products)
            family: Product family (zip, words, pdf, etc.)
            language: Language code (en, de, es, etc.)

        Returns:
            page_id
        """
        self.connect()

        # Try to get existing
        cursor = self._conn.execute(
            "SELECT page_id FROM pages WHERE file_path = ?",
            (file_path,)
        )
        row = cursor.fetchone()
        if row:
            return row['page_id']

        # Create new
        cursor = self._conn.execute(
            """
            INSERT INTO pages (file_path, relative_path, site, family, language)
            VALUES (?, ?, ?, ?, ?)
            """,
            (file_path, relative_path, site, family, language)
        )
        return cursor.lastrowid

    def update_page(self, page_id: int, **kwargs):
        """Update page fields."""
        self.connect()
        if not kwargs:
            return

        set_clause = ", ".join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [page_id]

        self._conn.execute(
            f"UPDATE pages SET {set_clause} WHERE page_id = ?",
            values
        )

    def get_page(self, page_id: int) -> Optional[Page]:
        """Get page by ID."""
        self.connect()
        cursor = self._conn.execute(
            "SELECT * FROM pages WHERE page_id = ?",
            (page_id,)
        )
        row = cursor.fetchone()
        if row:
            return Page(**dict(row))
        return None

    def get_pages_by_family(self, family: str, state: Optional[str] = None) -> List[Page]:
        """Get all pages for a family, optionally filtered by state."""
        self.connect()
        if state:
            cursor = self._conn.execute(
                "SELECT * FROM pages WHERE family = ? AND state = ?",
                (family, state)
            )
        else:
            cursor = self._conn.execute(
                "SELECT * FROM pages WHERE family = ?",
                (family,)
            )

        return [Page(**dict(row)) for row in cursor.fetchall()]

    # ========================================================================
    # SNIPPET OPERATIONS
    # ========================================================================

    def create_snippet(self, page_id: int, snippet_ordinal: int, locator_json: str,
                      snippet_type: str, language: Optional[str]) -> int:
        """
        Create a new snippet.

        Args:
            page_id: Parent page ID
            snippet_ordinal: Position on page (1-indexed)
            locator_json: JSON-serialized SnippetLocator
            snippet_type: 'fence' or 'gist'
            language: Programming language

        Returns:
            snippet_id
        """
        self.connect()
        cursor = self._conn.execute(
            """
            INSERT INTO snippets (page_id, snippet_ordinal, locator_json, snippet_type, language)
            VALUES (?, ?, ?, ?, ?)
            """,
            (page_id, snippet_ordinal, locator_json, snippet_type, language)
        )
        return cursor.lastrowid

    def update_snippet(self, snippet_id: int, **kwargs):
        """Update snippet fields."""
        self.connect()
        if not kwargs:
            return

        set_clause = ", ".join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [snippet_id]

        self._conn.execute(
            f"UPDATE snippets SET {set_clause} WHERE snippet_id = ?",
            values
        )

    def get_snippet(self, snippet_id: int) -> Optional[Snippet]:
        """Get snippet by ID."""
        self.connect()
        cursor = self._conn.execute(
            "SELECT * FROM snippets WHERE snippet_id = ?",
            (snippet_id,)
        )
        row = cursor.fetchone()
        if row:
            return Snippet(**dict(row))
        return None

    def get_snippets_by_page(self, page_id: int) -> List[Snippet]:
        """Get all snippets for a page."""
        self.connect()
        cursor = self._conn.execute(
            "SELECT * FROM snippets WHERE page_id = ? ORDER BY snippet_ordinal",
            (page_id,)
        )
        return [Snippet(**dict(row)) for row in cursor.fetchall()]

    def get_snippets_by_status(self, family: str, status: str) -> List[Tuple[Snippet, Page]]:
        """Get all snippets with a specific status for a family."""
        self.connect()
        cursor = self._conn.execute(
            """
            SELECT s.*, p.*
            FROM snippets s
            JOIN pages p ON s.page_id = p.page_id
            WHERE p.family = ? AND s.status = ?
            ORDER BY p.relative_path, s.snippet_ordinal
            """,
            (family, status)
        )

        results = []
        for row in cursor.fetchall():
            row_dict = dict(row)
            # Split into snippet and page
            snippet_data = {k: v for k, v in row_dict.items() if k in Snippet.__annotations__}
            page_data = {k: v for k, v in row_dict.items() if k in Page.__annotations__}
            results.append((Snippet(**snippet_data), Page(**page_data)))

        return results

    # ========================================================================
    # SNIPPET VERSION OPERATIONS
    # ========================================================================

    def create_snippet_version(self, snippet_id: int, version_type: str,
                             code_content: str, created_by: Optional[str] = None,
                             notes: Optional[str] = None) -> int:
        """
        Create a new snippet version.

        Args:
            snippet_id: Parent snippet ID
            version_type: 'original', 'fixed', 'current', 'before_fix'
            code_content: Code content
            created_by: Creator (system, pattern, ollama, manual)
            notes: Optional notes

        Returns:
            version_id
        """
        self.connect()
        content_hash = hashlib.sha256(code_content.encode('utf-8')).hexdigest()

        cursor = self._conn.execute(
            """
            INSERT INTO snippet_versions (snippet_id, version_type, code_content, content_hash, created_by, notes)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (snippet_id, version_type, code_content, content_hash, created_by, notes)
        )
        return cursor.lastrowid

    def get_snippet_version(self, version_id: int) -> Optional[SnippetVersion]:
        """Get snippet version by ID."""
        self.connect()
        cursor = self._conn.execute(
            "SELECT * FROM snippet_versions WHERE version_id = ?",
            (version_id,)
        )
        row = cursor.fetchone()
        if row:
            return SnippetVersion(**dict(row))
        return None

    def get_latest_snippet_version(self, snippet_id: int, version_type: Optional[str] = None) -> Optional[SnippetVersion]:
        """Get latest version of a snippet."""
        self.connect()
        if version_type:
            cursor = self._conn.execute(
                """
                SELECT * FROM snippet_versions
                WHERE snippet_id = ? AND version_type = ?
                ORDER BY created_at DESC LIMIT 1
                """,
                (snippet_id, version_type)
            )
        else:
            cursor = self._conn.execute(
                """
                SELECT * FROM snippet_versions
                WHERE snippet_id = ?
                ORDER BY created_at DESC LIMIT 1
                """,
                (snippet_id,)
            )

        row = cursor.fetchone()
        if row:
            return SnippetVersion(**dict(row))
        return None

    # ========================================================================
    # RUN OPERATIONS
    # ========================================================================

    def create_run(self, run_type: str, family: str, config_snapshot: Optional[Dict] = None) -> int:
        """
        Create a new run.

        Args:
            run_type: 'discovery', 'validation', 'patching', 'verification'
            family: Product family
            config_snapshot: Configuration snapshot (will be JSON serialized)

        Returns:
            run_id
        """
        self.connect()
        config_json = json.dumps(config_snapshot) if config_snapshot else None

        cursor = self._conn.execute(
            """
            INSERT INTO runs (run_type, family, config_snapshot)
            VALUES (?, ?, ?)
            """,
            (run_type, family, config_json)
        )
        return cursor.lastrowid

    def update_run(self, run_id: int, **kwargs):
        """Update run fields."""
        self.connect()
        if not kwargs:
            return

        set_clause = ", ".join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [run_id]

        self._conn.execute(
            f"UPDATE runs SET {set_clause} WHERE run_id = ?",
            values
        )

    def complete_run(self, run_id: int, status: str = 'completed', error_message: Optional[str] = None):
        """Mark run as completed."""
        self.update_run(
            run_id,
            completed_at=datetime.utcnow().isoformat(),
            status=status,
            error_message=error_message
        )

    def get_run(self, run_id: int) -> Optional[Run]:
        """Get run by ID."""
        self.connect()
        cursor = self._conn.execute(
            "SELECT * FROM runs WHERE run_id = ?",
            (run_id,)
        )
        row = cursor.fetchone()
        if row:
            return Run(**dict(row))
        return None

    # ========================================================================
    # RUN EVENT OPERATIONS
    # ========================================================================

    def log_event(self, run_id: int, event_type: str, severity: str, message: str,
                 details: Optional[Dict] = None):
        """
        Log an event for a run.

        Args:
            run_id: Run ID
            event_type: Event type identifier
            severity: 'debug', 'info', 'warning', 'error'
            message: Event message
            details: Optional details dictionary (will be JSON serialized)
        """
        self.connect()
        details_json = json.dumps(details) if details else None

        self._conn.execute(
            """
            INSERT INTO run_events (run_id, event_type, severity, message, details_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (run_id, event_type, severity, message, details_json)
        )

    # ========================================================================
    # ISSUE AND FIX TRACKING
    # ========================================================================

    def create_issue(self, snippet_id: int, issue_type: str, description: str,
                    severity: str = 'error') -> int:
        """Create a snippet issue."""
        self.connect()
        cursor = self._conn.execute(
            """
            INSERT INTO snippet_issues (snippet_id, issue_type, description, severity)
            VALUES (?, ?, ?, ?)
            """,
            (snippet_id, issue_type, description, severity)
        )
        return cursor.lastrowid

    def resolve_issue(self, issue_id: int):
        """Mark issue as resolved."""
        self.connect()
        self._conn.execute(
            "UPDATE snippet_issues SET resolved_at = datetime('now') WHERE issue_id = ?",
            (issue_id,)
        )

    def create_fix(self, snippet_id: int, fix_type: str, description: str,
                  successful: bool, issue_id: Optional[int] = None,
                  before_version_id: Optional[int] = None,
                  after_version_id: Optional[int] = None,
                  model_used: Optional[str] = None,
                  iteration_count: int = 1,
                  context_inferred: bool = False) -> int:
        """Create a fix record."""
        self.connect()
        cursor = self._conn.execute(
            """
            INSERT INTO fixes_applied (snippet_id, issue_id, fix_type, description, successful,
                                      before_version_id, after_version_id, model_used,
                                      iteration_count, context_inferred)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (snippet_id, issue_id, fix_type, description, successful,
             before_version_id, after_version_id, model_used,
             iteration_count, 1 if context_inferred else 0)
        )
        return cursor.lastrowid

    def create_build_attempt(self, snippet_id: int, version_id: int, run_id: int,
                           success: bool, compiler_output: Optional[str] = None,
                           error_count: int = 0, warning_count: int = 0,
                           model_used: Optional[str] = None,
                           fix_session_id: Optional[str] = None) -> int:
        """Create a build attempt record."""
        self.connect()
        cursor = self._conn.execute(
            """
            INSERT INTO build_attempts (snippet_id, version_id, run_id, success,
                                       compiler_output, error_count, warning_count,
                                       model_used, fix_session_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (snippet_id, version_id, run_id, success, compiler_output,
             error_count, warning_count, model_used, fix_session_id)
        )
        return cursor.lastrowid

    def create_fix_session(self, session_id: str, snippet_id: int, run_id: int,
                          total_iterations: int = 0, models_tried: str = '[]',
                          error_history: str = '[]', final_status: Optional[str] = None,
                          context_inferred: bool = False) -> str:
        """Create a new fix session record."""
        self.connect()
        self._conn.execute(
            """
            INSERT INTO fix_sessions (session_id, snippet_id, run_id, total_iterations,
                                     models_tried, error_history, final_status, context_inferred)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (session_id, snippet_id, run_id, total_iterations, models_tried, error_history,
             final_status, 1 if context_inferred else 0)
        )
        return session_id

    def update_fix_session(self, session_id: str,
                          total_iterations: Optional[int] = None,
                          models_tried: Optional[str] = None,
                          final_status: Optional[str] = None,
                          context_inferred: Optional[bool] = None,
                          final_version_id: Optional[int] = None,
                          error_history: Optional[str] = None,
                          duration_seconds: Optional[int] = None,
                          notes: Optional[str] = None) -> None:
        """Update a fix session with progress or completion data."""
        self.connect()

        # Build dynamic UPDATE query for only provided fields
        updates = []
        params = []

        if total_iterations is not None:
            updates.append("total_iterations = ?")
            params.append(total_iterations)

        if models_tried is not None:
            updates.append("models_tried = ?")
            params.append(models_tried)

        if final_status is not None:
            updates.append("final_status = ?")
            params.append(final_status)
            # Set completed_at when final status is set
            updates.append("completed_at = datetime('now')")

        if context_inferred is not None:
            updates.append("context_inferred = ?")
            params.append(1 if context_inferred else 0)

        if final_version_id is not None:
            updates.append("final_version_id = ?")
            params.append(final_version_id)

        if error_history is not None:
            updates.append("error_history = ?")
            params.append(error_history)

        if duration_seconds is not None:
            updates.append("duration_seconds = ?")
            params.append(duration_seconds)

        if notes is not None:
            updates.append("notes = ?")
            params.append(notes)

        if not updates:
            return  # Nothing to update

        params.append(session_id)
        query = f"UPDATE fix_sessions SET {', '.join(updates)} WHERE session_id = ?"
        self._conn.execute(query, params)

    def get_fix_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get fix session by ID."""
        self.connect()
        cursor = self._conn.execute(
            """
            SELECT session_id, snippet_id, run_id, started_at, completed_at,
                   total_iterations, models_tried, final_status, context_inferred,
                   final_version_id, error_history, duration_seconds, notes
            FROM fix_sessions
            WHERE session_id = ?
            """,
            (session_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    # ========================================================================
    # REPORTING QUERIES
    # ========================================================================

    def get_family_statistics(self, family: str) -> Dict[str, Any]:
        """Get statistics for a family."""
        self.connect()

        cursor = self._conn.execute(
            """
            SELECT
                COUNT(DISTINCT p.page_id) as total_pages,
                COUNT(s.snippet_id) as total_snippets,
                COUNT(CASE WHEN s.status = 'verified' THEN 1 END) as verified,
                COUNT(CASE WHEN s.status = 'needs-fix' THEN 1 END) as needs_fix,
                COUNT(CASE WHEN s.status = 'unverified' THEN 1 END) as unverified,
                COUNT(CASE WHEN s.status = 'skipped' THEN 1 END) as skipped
            FROM pages p
            LEFT JOIN snippets s ON p.page_id = s.page_id
            WHERE p.family = ?
            """,
            (family,)
        )

        row = cursor.fetchone()
        return dict(row) if row else {}

    def get_validation_summary(self, run_id: int) -> Dict[str, Any]:
        """Get validation summary for a run."""
        self.connect()

        cursor = self._conn.execute(
            """
            SELECT
                r.run_type,
                r.family,
                r.started_at,
                r.completed_at,
                r.status,
                r.pages_processed,
                r.snippets_processed,
                (SELECT COUNT(*) FROM run_events WHERE run_id = r.run_id AND severity = 'error') as errors,
                (SELECT COUNT(*) FROM run_events WHERE run_id = r.run_id AND severity = 'warning') as warnings
            FROM runs r
            WHERE r.run_id = ?
            """,
            (run_id,)
        )

        row = cursor.fetchone()
        return dict(row) if row else {}

    # =========================================================================
    # GIST OPERATIONS
    # =========================================================================

    def upsert_gist(self, gist_id: str, owner: str, description: Optional[str],
                   updated_at: Optional[str], last_status: str,
                   last_error: Optional[str] = None, etag: Optional[str] = None):
        """
        Insert or update gist metadata.

        Args:
            gist_id: GitHub gist ID
            owner: Gist owner username
            description: Gist description
            updated_at: Last updated timestamp from GitHub
            last_status: Fetch status (success, not_found, rate_limited, error)
            last_error: Error message if fetch failed
            etag: ETag from GitHub API response
        """
        self.connect()

        self._conn.execute(
            """
            INSERT INTO gists (gist_id, owner, description, updated_at, etag, last_status, last_error)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(gist_id) DO UPDATE SET
                owner = excluded.owner,
                description = excluded.description,
                updated_at = excluded.updated_at,
                etag = excluded.etag,
                last_fetched_at = datetime('now'),
                last_status = excluded.last_status,
                last_error = excluded.last_error
            """,
            (gist_id, owner, description, updated_at, etag, last_status, last_error)
        )
        self._conn.commit()

    def upsert_gist_file(self, gist_id: str, filename: str, raw_url: str,
                        language: Optional[str], content: str, content_hash: str,
                        file_size: Optional[int] = None):
        """
        Insert or update gist file content.

        Args:
            gist_id: GitHub gist ID
            filename: Filename within gist
            raw_url: Raw content URL from GitHub
            language: Programming language detected by GitHub
            content: File content
            content_hash: SHA256 hash of content
            file_size: File size in bytes
        """
        self.connect()

        self._conn.execute(
            """
            INSERT INTO gist_files (gist_id, filename, raw_url, language, content, content_hash, file_size)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(gist_id, filename) DO UPDATE SET
                raw_url = excluded.raw_url,
                language = excluded.language,
                content = excluded.content,
                content_hash = excluded.content_hash,
                file_size = excluded.file_size,
                fetched_at = datetime('now')
            """,
            (gist_id, filename, raw_url, language, content, content_hash, file_size)
        )
        self._conn.commit()

    def get_gist(self, gist_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve gist metadata from database.

        Args:
            gist_id: GitHub gist ID

        Returns:
            Dictionary with gist metadata or None if not found
        """
        self.connect()

        cursor = self._conn.execute(
            """
            SELECT gist_id, owner, description, is_public, updated_at, etag,
                   last_fetched_at, last_status, last_error, created_at
            FROM gists
            WHERE gist_id = ?
            """,
            (gist_id,)
        )

        row = cursor.fetchone()
        return dict(row) if row else None

    def get_gist_file(self, gist_id: str, filename: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Retrieve gist file content from database.

        Args:
            gist_id: GitHub gist ID
            filename: Optional filename (if None, returns first C# file found)

        Returns:
            Dictionary with file data or None if not found
        """
        self.connect()

        if filename:
            cursor = self._conn.execute(
                """
                SELECT gist_id, filename, raw_url, language, content, content_hash, file_size, fetched_at
                FROM gist_files
                WHERE gist_id = ? AND filename = ?
                """,
                (gist_id, filename)
            )
        else:
            # Get first C# file
            cursor = self._conn.execute(
                """
                SELECT gist_id, filename, raw_url, language, content, content_hash, file_size, fetched_at
                FROM gist_files
                WHERE gist_id = ?
                  AND (LOWER(filename) LIKE '%.cs' OR LOWER(filename) LIKE '%.csx')
                ORDER BY filename
                LIMIT 1
                """,
                (gist_id,)
            )

        row = cursor.fetchone()
        return dict(row) if row else None

    # =========================================================================
    # GIST PUBLICATION OPERATIONS (Phase 5)
    # =========================================================================

    def create_gist_publication(self, snippet_id: int, old_gist_id: str, old_owner: str,
                               old_filename: str, new_gist_id: str, new_owner: str,
                               new_filename: str, new_url: str, new_raw_url: str,
                               code_hash: str, status: str, error_message: str = None) -> int:
        """
        Insert gist publication record.

        Args:
            snippet_id: Snippet ID
            old_gist_id: Original gist ID (empty string if none)
            old_owner: Original gist owner (empty string if none)
            old_filename: Original filename
            new_gist_id: New published gist ID
            new_owner: New gist owner
            new_filename: New filename
            new_url: New gist HTML URL
            new_raw_url: New gist raw URL
            code_hash: SHA256 hash of published code
            status: Publication status ('success', 'failed', 'pending')
            error_message: Error message if failed (optional)

        Returns:
            publication_id
        """
        self.connect()

        cursor = self._conn.execute(
            """
            INSERT INTO gist_publications
            (snippet_id, old_gist_id, old_gist_owner, old_gist_filename,
             new_gist_id, new_gist_owner, new_gist_filename,
             new_gist_url, new_gist_raw_url, code_hash, status, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (snippet_id, old_gist_id, old_owner, old_filename,
             new_gist_id, new_owner, new_filename,
             new_url, new_raw_url, code_hash, status, error_message)
        )
        return cursor.lastrowid

    def get_gist_publication(self, snippet_id: int) -> Optional[Dict[str, Any]]:
        """
        Get latest publication for a snippet.

        Args:
            snippet_id: Snippet ID

        Returns:
            Dictionary with publication data or None if not found
        """
        self.connect()

        cursor = self._conn.execute(
            """
            SELECT publication_id, snippet_id, old_gist_id, old_gist_owner, old_gist_filename,
                   new_gist_id, new_gist_owner, new_gist_filename,
                   new_gist_url, new_gist_raw_url, published_at, status, error_message,
                   code_hash, created_at
            FROM gist_publications
            WHERE snippet_id = ?
            ORDER BY published_at DESC
            LIMIT 1
            """,
            (snippet_id,)
        )

        row = cursor.fetchone()
        return dict(row) if row else None

    def get_all_publications(self, status: str = None) -> List[Dict[str, Any]]:
        """
        Get all publications, optionally filtered by status.

        Args:
            status: Optional status filter ('success', 'failed', 'pending')

        Returns:
            List of publication dictionaries
        """
        self.connect()

        if status:
            cursor = self._conn.execute(
                """
                SELECT publication_id, snippet_id, old_gist_id, old_gist_owner, old_gist_filename,
                       new_gist_id, new_gist_owner, new_gist_filename,
                       new_gist_url, new_gist_raw_url, published_at, status, error_message,
                       code_hash, created_at
                FROM gist_publications
                WHERE status = ?
                ORDER BY published_at DESC
                """,
                (status,)
            )
        else:
            cursor = self._conn.execute(
                """
                SELECT publication_id, snippet_id, old_gist_id, old_gist_owner, old_gist_filename,
                       new_gist_id, new_gist_owner, new_gist_filename,
                       new_gist_url, new_gist_raw_url, published_at, status, error_message,
                       code_hash, created_at
                FROM gist_publications
                ORDER BY published_at DESC
                """
            )

        return [dict(row) for row in cursor.fetchall()]

    def query_api_reference(self, family: str, class_names: List[str],
                           member_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Query API reference index.

        Args:
            family: Product family
            class_names: List of class names to query
            member_types: Optional filter for member types

        Returns:
            List of dictionaries with API member information
        """
        self.connect()

        placeholders = ','.join('?' * len(class_names))
        query = f"""
            SELECT api_id, family, namespace, class_name, member_type, member_name,
                   signature, description, example_code, notes, assembly_version,
                   is_static, is_readonly, return_type, parameters
            FROM api_reference
            WHERE family = ? AND class_name IN ({placeholders})
        """

        params = [family] + class_names

        if member_types:
            type_placeholders = ','.join('?' * len(member_types))
            query += f" AND member_type IN ({type_placeholders})"
            params.extend(member_types)

        query += " ORDER BY class_name, member_type, member_name"

        cursor = self._conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def get_api_index_stats(self, family: Optional[str] = None) -> Dict[str, Any]:
        """Get statistics about API reference index."""
        self.connect()

        if family:
            cursor = self._conn.execute(
                """
                SELECT
                    COUNT(DISTINCT class_name) as class_count,
                    COUNT(*) as member_count,
                    COUNT(DISTINCT namespace) as namespace_count
                FROM api_reference
                WHERE family = ?
                """,
                (family,)
            )
        else:
            cursor = self._conn.execute(
                """
                SELECT
                    COUNT(DISTINCT family) as family_count,
                    COUNT(DISTINCT class_name) as class_count,
                    COUNT(*) as member_count
                FROM api_reference
                """
            )

        row = cursor.fetchone()
        if row:
            return dict(row)
        return {}

    def create_rollback_entry(
        self,
        family: str,
        commit_sha: Optional[str],
        backup_branch: Optional[str],
        backup_commit: Optional[str],
        description: str,
        modified_files: List[str]
    ) -> None:
        """Create a rollback history entry."""
        self.connect()
        self._conn.execute(
            """
            INSERT INTO rollback_history
                (family, commit_sha, backup_branch, backup_commit, description, modified_files)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                family,
                commit_sha,
                backup_branch,
                backup_commit,
                description,
                json.dumps(modified_files)
            )
        )

    def get_rollback_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Return rollback history entries, most recent first."""
        self.connect()
        cursor = self._conn.execute(
            """
            SELECT id, created_at, family, commit_sha, backup_branch, backup_commit,
                   description, modified_files
            FROM rollback_history
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,)
        )
        entries = []
        for row in cursor.fetchall():
            entry = dict(row)
            if entry.get("modified_files"):
                entry["modified_files"] = json.loads(entry["modified_files"])
            entries.append(entry)
        return entries

    def get_last_rollback(self) -> Optional[Dict[str, Any]]:
        """Return the most recent rollback entry, if any."""
        entries = self.get_rollback_history(limit=1)
        return entries[0] if entries else None
