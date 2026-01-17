"""Compatibility database wrapper for legacy tests."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Any, Dict

from src.core.database import Database as CoreDatabase


@dataclass
class Snippet:
    snippet_id: int
    page_id: int
    snippet_ordinal: int
    locator_json: str
    snippet_type: str
    language: str
    status: str


class Database(CoreDatabase):
    """Compatibility wrapper with legacy helpers."""

    def connect(self) -> sqlite3.Connection:
        _ = self.conn
        return self._conn

    def initialize_schema(self, schema_path: Optional[Path] = None) -> None:
        if schema_path is None:
            super().initialize_schema()
            self._ensure_rollback_history()
            return
        schema_path = Path(schema_path)
        if not schema_path.exists():
            super().initialize_schema()
            self._ensure_rollback_history()
            return
        self.connect()
        sql = schema_path.read_text(encoding="utf-8")
        self._conn.executescript(sql)
        self._conn.commit()
        self._ensure_rollback_history()

    def _ensure_rollback_history(self) -> None:
        with self.get_connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS rollback_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    family TEXT NOT NULL,
                    commit_sha TEXT,
                    backup_branch TEXT,
                    backup_commit TEXT,
                    description TEXT,
                    modified_files TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

    def upsert_gist(
        self,
        gist_id: str,
        owner: str,
        description: Optional[str],
        updated_at: str,
        last_status: str,
        etag: Optional[str] = None,
        last_error: Optional[str] = None,
    ) -> None:
        self.connect()
        now = datetime.utcnow().isoformat()
        self._conn.execute(
            """
            INSERT INTO gists (
                gist_id, owner, description, updated_at, etag,
                last_fetched_at, last_status, last_error
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(gist_id) DO UPDATE SET
                owner=excluded.owner,
                description=excluded.description,
                updated_at=excluded.updated_at,
                etag=excluded.etag,
                last_fetched_at=excluded.last_fetched_at,
                last_status=excluded.last_status,
                last_error=excluded.last_error
            """,
            (gist_id, owner, description, updated_at, etag, now, last_status, last_error),
        )
        self._conn.commit()

    def upsert_gist_file(
        self,
        gist_id: str,
        filename: str,
        raw_url: str,
        language: Optional[str],
        content: str,
        content_hash: str,
        file_size: Optional[int],
    ) -> None:
        self.connect()
        now = datetime.utcnow().isoformat()
        self._conn.execute(
            """
            INSERT INTO gist_files (
                gist_id, filename, raw_url, language, content,
                content_hash, file_size, fetched_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(gist_id, filename) DO UPDATE SET
                raw_url=excluded.raw_url,
                language=excluded.language,
                content=excluded.content,
                content_hash=excluded.content_hash,
                file_size=excluded.file_size,
                fetched_at=excluded.fetched_at
            """,
            (gist_id, filename, raw_url, language, content, content_hash, file_size, now),
        )
        self._conn.commit()

    def get_gist(self, gist_id: str) -> Optional[sqlite3.Row]:
        self.connect()
        row = self._conn.execute(
            "SELECT * FROM gists WHERE gist_id = ?",
            (gist_id,),
        ).fetchone()
        return row

    def get_gist_file(self, gist_id: str, filename: str) -> Optional[sqlite3.Row]:
        self.connect()
        row = self._conn.execute(
            "SELECT * FROM gist_files WHERE gist_id = ? AND filename = ?",
            (gist_id, filename),
        ).fetchone()
        return row

    def get_gist_publication(self, snippet_id: int) -> Optional[sqlite3.Row]:
        self.connect()
        row = self._conn.execute(
            """
            SELECT *
            FROM gist_publications
            WHERE snippet_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (snippet_id,),
        ).fetchone()
        return row

    def save_gist_publication(self, data: Dict[str, Any]) -> None:
        self.connect()
        self._conn.execute(
            """
            INSERT INTO gist_publications (
                snippet_id, old_gist_id, old_gist_owner, old_gist_filename,
                new_gist_id, new_gist_owner, new_gist_filename, new_gist_url,
                new_gist_raw_url, status, error_message, code_hash
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data.get("snippet_id"),
                data.get("old_gist_id"),
                data.get("old_gist_owner"),
                data.get("old_gist_filename"),
                data.get("new_gist_id"),
                data.get("new_gist_owner"),
                data.get("new_gist_filename"),
                data.get("new_gist_url"),
                data.get("new_gist_raw_url"),
                data.get("status"),
                data.get("error_message"),
                data.get("code_hash"),
            ),
        )
        self._conn.commit()


__all__ = ["Database", "Snippet"]
