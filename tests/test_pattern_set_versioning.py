"""Tests for TC-EPIC3-04: pattern-set versioning/snapshotting.

Covers the confirmed reproducibility bug: query_patterns() (via
_boost_by_historical_success()) re-read pattern_performance live -- including
rows the SAME run's own record_application() had just written -- and a
newly-auto-learned pattern could become visible to a run that started before
it existed, purely because of when auto-learn happened to fire. See
reports/investigation/20260829_124758_production_readiness/taskcards/TC-EPIC3-04.md.
"""

import sqlite3
import tempfile
from pathlib import Path

import pytest

from src.services.learned_patterns_service import LearnedPatternsService, capture_pattern_set_version


@pytest.fixture
def temp_db():
    """Temp database with the real learned_patterns/pattern_performance schema."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    conn = sqlite3.connect(str(db_path))
    conn.executescript("""
        CREATE TABLE learned_patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            family TEXT NOT NULL,
            pattern_type TEXT NOT NULL,
            error_signature TEXT,
            match_condition TEXT,
            fix_template TEXT NOT NULL,
            fix_type TEXT DEFAULT 'template',
            fix_code TEXT,
            confidence REAL DEFAULT 0.5,
            auto_approved BOOLEAN DEFAULT FALSE,
            priority INTEGER DEFAULT 50,
            requires_llm BOOLEAN DEFAULT FALSE,
            example_before TEXT,
            example_after TEXT,
            source TEXT,
            scope TEXT DEFAULT 'family',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE pattern_performance (
            pattern_id INTEGER PRIMARY KEY,
            family TEXT NOT NULL,
            times_applied INTEGER DEFAULT 0,
            times_succeeded INTEGER DEFAULT 0,
            success_rate REAL DEFAULT 0.0,
            last_used TEXT
        );
    """)
    conn.commit()
    conn.close()

    yield db_path
    db_path.unlink(missing_ok=True)


def _insert_pattern(db_path, error_signature="CS0246", confidence=0.7):
    conn = sqlite3.connect(str(db_path))
    cursor = conn.execute(
        """INSERT INTO learned_patterns
           (family, pattern_type, error_signature, fix_template, fix_type,
            confidence, auto_approved, source)
           VALUES ('zip', 'compile_error', ?, 'Fix', 'using_directive', ?, TRUE, 'auto_learn')""",
        (error_signature, confidence),
    )
    pattern_id = cursor.lastrowid
    conn.execute("INSERT INTO pattern_performance (pattern_id, family) VALUES (?, 'zip')", (pattern_id,))
    conn.commit()
    conn.close()
    return pattern_id


class TestCapturePatternSetVersion:
    def test_returns_none_for_nonexistent_db(self, tmp_path):
        assert capture_pattern_set_version(tmp_path / "does_not_exist.db") is None

    def test_returns_zero_for_empty_table(self, temp_db):
        assert capture_pattern_set_version(temp_db) == 0

    def test_returns_max_existing_id(self, temp_db):
        _insert_pattern(temp_db)
        second_id = _insert_pattern(temp_db)
        assert capture_pattern_set_version(temp_db) == second_id

    def test_is_a_monotonic_integer_not_a_timestamp(self, temp_db):
        """Deliberately not a wall-clock timestamp -- see
        capture_pattern_set_version()'s docstring for why (SQLite's
        datetime('now') has only whole-second precision, which would make a
        version captured and a pattern stored in the same second
        indistinguishable)."""
        version = capture_pattern_set_version(temp_db)
        assert isinstance(version, int)


class TestQuerySnapshotIsolation:
    def test_new_pattern_stored_mid_run_is_invisible_to_that_runs_own_queries(self, temp_db):
        """The core negative control: store a new pattern mid-simulated-run
        and confirm query_patterns() within that SAME run does NOT return it."""
        version = capture_pattern_set_version(temp_db)
        service = LearnedPatternsService("zip", db_path=temp_db, pattern_set_version=version)

        # Nothing exists yet.
        assert service.query_patterns("CS0246", min_confidence=0.0) == []

        # Auto-learn (mid-run) stores a new pattern.
        service.store_pattern(
            error_signature="CS0246", pattern_type="compile_error", fix_type="using_directive",
            fix_code={"directive": "using System.Collections;"}, fix_template="Fix", auto_approved=True,
        )

        # THIS run's own query must still not see it.
        assert service.query_patterns("CS0246", min_confidence=0.0) == []
        service.close()

    def test_pattern_stored_by_prior_run_is_visible_to_a_run_with_a_newer_version(self, temp_db):
        """query_patterns() called with a NEWER pattern_set_version (simulating
        a subsequent run) DOES see the pattern a prior run's auto-learn stored."""
        version_1 = capture_pattern_set_version(temp_db)
        run_1 = LearnedPatternsService("zip", db_path=temp_db, pattern_set_version=version_1)
        run_1.store_pattern(
            error_signature="CS0246", pattern_type="compile_error", fix_type="using_directive",
            fix_code={"directive": "using System.Collections;"}, fix_template="Fix", auto_approved=True,
        )
        assert run_1.query_patterns("CS0246", min_confidence=0.0) == []
        run_1.close()

        version_2 = capture_pattern_set_version(temp_db)
        assert version_2 > version_1
        run_2 = LearnedPatternsService("zip", db_path=temp_db, pattern_set_version=version_2)
        results = run_2.query_patterns("CS0246", min_confidence=0.0)
        assert len(results) == 1
        run_2.close()

    def test_preload_all_patterns_also_respects_version(self, temp_db):
        """Same isolation guarantee via the preload path (the common,
        performance-optimized path used after Phase A discovery)."""
        version = capture_pattern_set_version(temp_db)
        service = LearnedPatternsService("zip", db_path=temp_db, pattern_set_version=version)
        service.preload_all_patterns()
        assert service.query_patterns("CS0246", min_confidence=0.0) == []

        service.store_pattern(
            error_signature="CS0246", pattern_type="compile_error", fix_type="using_directive",
            fix_code={"directive": "using System.Collections;"}, fix_template="Fix", auto_approved=True,
        )
        # Re-preloading (simulating a cache-invalidation-triggered reconstruction
        # mid-run) with the SAME frozen version must still exclude it.
        service._preloaded_cache.clear()
        service.preload_all_patterns()
        assert service.query_patterns("CS0246", min_confidence=0.0) == []
        service.close()

    def test_none_version_is_legacy_unfiltered_behavior(self, temp_db):
        """Backward compatibility: pattern_set_version=None (the default)
        preserves today's behavior -- no filtering at all."""
        _insert_pattern(temp_db)
        service = LearnedPatternsService("zip", db_path=temp_db, pattern_set_version=None)
        results = service.query_patterns("CS0246", min_confidence=0.0)
        assert len(results) == 1
        service.close()

    def test_zero_version_excludes_everything_inserted_after_capture(self, temp_db):
        """version=0 (an empty table at capture time) correctly excludes any
        pattern inserted afterward -- the id-based scheme's equivalent of
        'this run started before the table had any rows'."""
        service = LearnedPatternsService("zip", db_path=temp_db, pattern_set_version=0)
        service.store_pattern(
            error_signature="CS0246", pattern_type="compile_error", fix_type="using_directive",
            fix_code={"directive": "using System.Collections;"}, fix_template="Fix", auto_approved=True,
        )
        assert service.query_patterns("CS0246", min_confidence=0.0) == []
        service.close()


class TestPerformanceSnapshotFrozen:
    def test_boost_ordering_stable_across_record_application_mid_run(self, temp_db):
        """The core fix: _boost_by_historical_success() must not re-read live
        pattern_performance mid-run -- record_application() commits a new row
        for THIS run's own earlier attempt, but the SAME service instance's
        later query_patterns() call must not see it."""
        # Two patterns, initially identical performance (both untested).
        id_1 = _insert_pattern(temp_db, confidence=0.8)
        id_2 = _insert_pattern(temp_db, confidence=0.7)

        service = LearnedPatternsService("zip", db_path=temp_db)
        first = service.query_patterns("CS0246", min_confidence=0.0)
        first_order = [p.id for p in first]

        # Simulate this run recording repeated successes for pattern 2 (which
        # would, if read live, reorder pattern 2 ahead of pattern 1 on the
        # next call).
        for _ in range(10):
            service.record_application(id_2, example_id="ex-1", run_id="run-1", success=True)

        second = service.query_patterns("CS0246", min_confidence=0.0)
        second_order = [p.id for p in second]

        assert first_order == second_order == [id_1, id_2]
        service.close()

    def test_performance_snapshot_populated_once_not_requeried(self, temp_db):
        id_1 = _insert_pattern(temp_db)
        id_2 = _insert_pattern(temp_db)
        service = LearnedPatternsService("zip", db_path=temp_db)
        assert service._performance_snapshot is None

        # Two patterns for the same signature -- _boost_by_historical_success()
        # only runs (and populates the snapshot) when len(patterns) > 1.
        service.query_patterns("CS0246", min_confidence=0.0)
        assert service._performance_snapshot is not None
        snapshot_before = dict(service._performance_snapshot)

        # Directly mutate pattern_performance out from under the snapshot.
        conn = sqlite3.connect(str(temp_db))
        conn.execute("UPDATE pattern_performance SET success_rate = 0.99, times_applied = 100 WHERE pattern_id = ?", (id_1,))
        conn.commit()
        conn.close()

        service.query_patterns("CS0246", min_confidence=0.0)
        assert service._performance_snapshot == snapshot_before  # unchanged -- frozen
        service.close()


class TestOrchestratorIntegration:
    def test_registry_threads_pattern_set_version_into_new_services(self, tmp_path, temp_db):
        from src.core.config import ConfigurationManager
        from src.pipeline.family_service_registry import FamilyServiceRegistry

        registry = FamilyServiceRegistry(ConfigurationManager(Path("config/families")), tmp_path)
        registry.set_pattern_set_version(7)

        # _create_learned_patterns validates family config exists; use the real
        # 'zip' family config (present in this repo) and just check the version
        # was threaded through onto the constructed service.
        import src.services.learned_patterns_service as lps_module
        original_default = lps_module.DEFAULT_DB_PATH
        try:
            lps_module.DEFAULT_DB_PATH = temp_db
            created = registry._create_learned_patterns("zip")
        finally:
            lps_module.DEFAULT_DB_PATH = original_default

        assert created.pattern_set_version == 7
        created.close()
