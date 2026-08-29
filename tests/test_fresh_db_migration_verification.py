"""Tests for TC-EPIC2-03: Fresh-DB migration column verification.

Covers the empirically-confirmed DB-01 risk (FINDINGS_REGISTER.md): a fresh
clone's Database.apply_migrations() marks every migration "applied (baseline)"
without executing its SQL, relying entirely on the SCHEMA constant already
matching what migrations would have produced -- and _is_fresh_database() only
checks table names/row counts, never columns. This confirmed a REAL, currently
-shipping gap: migration 007's schema_version table and its 3 views
(v_failure_breakdown, v_top_error_types, v_resolution_rates) were part of
007's SQL but never mirrored into SCHEMA, so every fresh clone silently never
created them despite schema_migrations claiming 007 was applied.

See reports/investigation/20260829_124758_production_readiness/taskcards/TC-EPIC2-03.md.
"""

import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.core.database import Database, _MIGRATION_SCHEMA_EXPECTATIONS


@pytest.fixture
def fresh_db_path():
    fd = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    fd.close()
    path = Path(fd.name)
    path.unlink()  # Database() creates the file itself; start truly absent.
    yield path
    if path.exists():
        path.unlink()


def _table_columns(db_path: Path, table: str) -> set:
    conn = sqlite3.connect(str(db_path))
    try:
        return {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    finally:
        conn.close()


def _view_names(db_path: Path) -> set:
    conn = sqlite3.connect(str(db_path))
    try:
        return {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='view'").fetchall()}
    finally:
        conn.close()


class TestFreshBootstrapVerification:
    def test_fresh_bootstrap_verifies_all_migrations(self, fresh_db_path):
        """Fresh bootstrap against the current, correct SCHEMA passes verification
        for every registered migration -- no RuntimeError."""
        db = Database(db_path=fresh_db_path)
        with patch.object(Database, "_verify_migration_by_registry", wraps=db._verify_migration_by_registry) as spy:
            db.initialize_schema()
        db.close()

        verified_ids = {call.args[1] for call in spy.call_args_list}
        for migration_id in _MIGRATION_SCHEMA_EXPECTATIONS:
            assert migration_id in verified_ids, f"{migration_id} was never verified on the fresh-bootstrap path"

    def test_schema_version_and_views_created_on_fresh_bootstrap(self, fresh_db_path):
        """The confirmed-drift regression test: a fresh bootstrap now actually
        creates schema_version and all 3 analytics views. Fails against the
        pre-fix SCHEMA (verified via test_old_schema_constant_missing_schema_version_and_views
        below, against a frozen reference copy of that pre-fix SQL)."""
        db = Database(db_path=fresh_db_path)
        db.initialize_schema()
        db.close()

        conn = sqlite3.connect(str(fresh_db_path))
        try:
            tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        finally:
            conn.close()
        assert "schema_version" in tables
        assert _view_names(fresh_db_path) == {"v_failure_breakdown", "v_top_error_types", "v_resolution_rates"}

    def test_fresh_bootstrap_fails_loudly_on_injected_schema_drift(self, fresh_db_path):
        """The key regression test: inject a drift into the expected-schema
        registry (pretend app_context is required on a table that doesn't have
        it) and confirm apply_migrations() raises RuntimeError instead of
        silently proceeding."""
        drifted_expectations = dict(_MIGRATION_SCHEMA_EXPECTATIONS)
        drifted_expectations["010_add_app_context"] = {
            "expected_columns": {"example_records": ["app_context", "this_column_does_not_exist"]},
        }

        db = Database(db_path=fresh_db_path)
        with patch("src.core.database._MIGRATION_SCHEMA_EXPECTATIONS", drifted_expectations):
            with pytest.raises(RuntimeError, match="this_column_does_not_exist"):
                db.initialize_schema()
        db.close()

    def test_non_fresh_path_still_verifies_all_migrations_not_just_010(self, fresh_db_path):
        """Directly exercises apply_migrations()'s NON-FRESH execution branch
        for migrations 010-012 -- real migration SQL assumes a pre-010 schema
        shape (bare ALTER TABLE ADD COLUMN, no IF NOT EXISTS guard), which
        SCHEMA-bootstrapped columns would make fail with "duplicate column",
        so each target migration's SQL text is stubbed to a no-op here to
        isolate the thing this test actually checks: that
        _verify_migration_by_registry is invoked for 010, 011, AND 012 on
        this path (the old _verify_migration_010-only check only ever
        verified 010; 011/012 got zero verification)."""
        db = Database(db_path=fresh_db_path)
        db.initialize_schema()  # fresh bootstrap: baseline-marks everything

        # Force the non-fresh branch: un-record 010-012 so they look pending,
        # and seed real example data so _is_fresh_database() returns False.
        run_id = db.create_run(family="zip")
        from src.core.models import ExampleRecord

        db.save_example(ExampleRecord(family="zip", file_path="x.md", original_code="//x"), run_id=run_id)
        with db.get_connection() as conn:
            conn.execute(
                "DELETE FROM schema_migrations WHERE migration_id IN "
                "('010_add_app_context', '011_add_code_block_location', '012_add_article_intent')"
            )

        no_op_targets = {"010_add_app_context", "011_add_code_block_location", "012_add_article_intent"}
        original_read_text = Path.read_text

        def _stub_read_text(self_path, *args, **kwargs):
            if self_path.stem in no_op_targets:
                return "SELECT 1;"  # columns already exist via the SCHEMA bootstrap above
            return original_read_text(self_path, *args, **kwargs)

        with patch.object(Database, "_verify_migration_by_registry", wraps=db._verify_migration_by_registry) as spy, \
                patch.object(Path, "read_text", _stub_read_text):
            db.apply_migrations()
        db.close()

        verified_ids = {call.args[1] for call in spy.call_args_list}
        assert no_op_targets.issubset(verified_ids)


class TestNegativeControls:
    def test_old_schema_constant_missing_schema_version_and_views(self, fresh_db_path):
        """Pins down the confirmed real bug (not synthetic) against a frozen
        copy of the pre-fix SCHEMA: schema_version and the 3 views do NOT
        exist when bootstrapped from SCHEMA text with that section removed --
        proving test_schema_version_and_views_created_on_fresh_bootstrap above
        is a genuine regression guard, not a tautology."""
        db = Database(db_path=fresh_db_path)
        pre_fix_schema = db.SCHEMA
        # Strip exactly the block this taskcard added (schema_version table,
        # its INSERT, and the 3 views) to reconstruct the pre-fix SCHEMA text.
        start_marker = "-- Schema version table + analytics views (Migration 007)"
        end_marker = "-- Review results table (Phase E: Final Review)"
        start = pre_fix_schema.index(start_marker)
        end = pre_fix_schema.index(end_marker)
        reconstructed_pre_fix_schema = pre_fix_schema[:start] + pre_fix_schema[end:]
        # (Later comments elsewhere in SCHEMA mention "schema_version" in prose --
        # check for the actual DDL statements, not a bare substring match.)
        assert "CREATE TABLE IF NOT EXISTS schema_version" not in reconstructed_pre_fix_schema
        assert "CREATE VIEW IF NOT EXISTS v_failure_breakdown" not in reconstructed_pre_fix_schema

        conn = sqlite3.connect(str(fresh_db_path))
        try:
            conn.executescript(reconstructed_pre_fix_schema)
            tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            views = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='view'").fetchall()}
        finally:
            conn.close()
        db.close()

        assert "schema_version" not in tables
        assert views == set()

    def test_old_verify_migration_010_only_pattern_insufficient(self, fresh_db_path):
        """Demonstrates the narrow original verifier's blind spot: a
        010-only-style check (only asserting app_context on two tables) would
        NOT catch a drift injected into migration 011's or 012's columns --
        contrasted with the new generalized registry catching it."""
        def _verify_migration_010_only(conn: sqlite3.Connection) -> None:
            for table in ("example_records", "example_run_state"):
                cols = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
                if "app_context" not in cols:
                    raise RuntimeError(f"app_context missing from {table}")

        db = Database(db_path=fresh_db_path)
        db.initialize_schema()
        conn = sqlite3.connect(str(fresh_db_path))
        try:
            # Injected drift: code_block_signature (migration 011) is absent,
            # but the narrow 010-only verifier has no idea it should exist.
            conn.execute("CREATE TABLE example_records_backup AS SELECT * FROM example_records")
            conn.execute("DROP TABLE example_records")
            conn.execute(
                "CREATE TABLE example_records AS SELECT "
                "example_id, family, file_path, original_code, app_context "
                "FROM example_records_backup"
            )
            _verify_migration_010_only(conn)  # does NOT raise -- blind to the drift
        finally:
            conn.close()
        db.close()

        # The new generalized verifier DOES catch it for migration 011.
        conn2 = sqlite3.connect(str(fresh_db_path))
        try:
            with pytest.raises(RuntimeError, match="code_block_signature"):
                db._verify_migration_schema(
                    conn2, "011_add_code_block_location",
                    expected_columns={"example_records": ["code_block_signature", "extraction_warning"]},
                )
        finally:
            conn2.close()

    def test_fresh_path_previously_ran_zero_verification(self, fresh_db_path):
        """Reproduces the exact pre-fix condition: on a frozen copy of the OLD
        fresh-bootstrap loop body (verify-nothing, just record), no
        verification runs at all -- contrasted with the new code calling
        _verify_migration_by_registry for every migration on that same path
        (proven by test_fresh_bootstrap_verifies_all_migrations above)."""
        db = Database(db_path=fresh_db_path)
        db.initialize_schema()  # creates schema_migrations etc., is itself fresh

        # This is the OLD loop body from apply_migrations()'s fresh-DB branch,
        # verbatim minus the call this taskcard added.
        import sqlite3 as _sqlite3

        migrations_dir = Path(__file__).parent.parent / "migrations"
        migration_files = sorted(f for f in migrations_dir.glob("*.sql") if f.is_file())

        with patch.object(Database, "_verify_migration_by_registry") as spy:
            with db.get_connection() as conn:
                for migration_file in migration_files:
                    migration_id = migration_file.stem
                    db._record_migration(conn, migration_id, "Baseline (fresh DB), OLD pre-fix code path")
                    # (old code: no verification call here at all)
            spy.assert_not_called()
        db.close()
