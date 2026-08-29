"""Tests for TC-EPIC2-01: State Authority.

Covers src/core/state_authority.py: StateAuthority.transition(), the 6 named
convenience methods, and the negative control proving the underlying
Database.update_example_status() primitive remains exactly as unvalidated as
today by itself -- StateAuthority (plus TC-EPIC2-02's call-site migration and
the CI lint script) is the enforcement mechanism, not a change to that
primitive's own signature. See
reports/investigation/20260829_124758_production_readiness/taskcards/TC-EPIC2-01.md.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.core.database import Database
from src.core.models import ExampleRecord, ExampleStatus
from src.core.state_authority import IllegalTransitionError, StateAuthority, TransitionResult


def _apply_migration_014_directly(db_path) -> None:
    """Execute migrations/014_status_transitions_audit.sql directly against db_path.

    A brand-new temp_db is a "fresh database" per Database._is_fresh_database(), so
    the normal apply_migrations() path marks migration 014 as applied WITHOUT
    executing its SQL (the same F-038 fresh-bootstrap gap test_authority_pdp.py's
    _apply_migration_013_directly() works around for migration 013 -- TC-EPIC2-03
    is the taskcard that generally fixes this). Applying the migration file
    directly here tests StateAuthority against the real schema, independent of
    that known, separately-tracked gap.
    """
    import sqlite3

    repo_root = Path(__file__).parent.parent
    migration_sql = (repo_root / "migrations" / "014_status_transitions_audit.sql").read_text(encoding="utf-8")
    conn = sqlite3.connect(str(db_path))
    try:
        conn.executescript(migration_sql)
    finally:
        conn.close()


@pytest.fixture
def db(temp_db):
    database = Database(db_path=temp_db)
    database.initialize_schema()
    _apply_migration_014_directly(temp_db)
    yield database
    database.close()


def _seed_discovered(database: Database, example_id: str) -> str:
    """Create a real run_records row (example_run_state.run_id has a FK to it)
    and a canonical example_records row (example_run_state.example_id has a FK
    to that too), matching real discovery's order of operations. Returns the
    created run_id."""
    run_id = database.create_run(family="zip")
    example = ExampleRecord(
        example_id=example_id,
        family="zip",
        file_path="docs/example.md",
        original_code="// example",
        status=ExampleStatus.DISCOVERED,
    )
    database.save_example(example, run_id=run_id)
    return run_id


class TestTransition:
    def test_legal_transition_succeeds_and_is_audited(self, db):
        run_id = _seed_discovered(db, "ex-1")
        authority = StateAuthority(db)

        result = authority.transition("ex-1", run_id, ExampleStatus.COMPILABLE)

        assert result.success is True
        assert result.from_status == ExampleStatus.DISCOVERED
        assert result.to_status == ExampleStatus.COMPILABLE
        assert db.get_example_run_status(run_id, "ex-1") == ExampleStatus.COMPILABLE

        import sqlite3

        conn = sqlite3.connect(str(db.db_path))
        try:
            rows = conn.execute(
                "SELECT from_status, to_status FROM status_transitions WHERE example_id = ?", ("ex-1",)
            ).fetchall()
        finally:
            conn.close()
        assert rows == [("DISCOVERED", "COMPILABLE")]

    def test_illegal_transition_raises(self, db):
        run_id = _seed_discovered(db, "ex-1")
        authority = StateAuthority(db)
        # Drive it to a real terminal state first (legally), then attempt an
        # illegal jump out of it.
        authority.transition("ex-1", run_id, ExampleStatus.COMPILABLE)
        authority.transition("ex-1", run_id, ExampleStatus.RUNTIME_FAILED)
        authority.transition("ex-1", run_id, ExampleStatus.VERIFIED)
        authority.transition("ex-1", run_id, ExampleStatus.MD_UPDATED)
        authority.transition("ex-1", run_id, ExampleStatus.FINAL_REVIEW_FAILED)

        with pytest.raises(IllegalTransitionError) as excinfo:
            authority.transition("ex-1", run_id, ExampleStatus.VERIFIED)

        assert excinfo.value.from_status == ExampleStatus.FINAL_REVIEW_FAILED
        assert excinfo.value.to_status == ExampleStatus.VERIFIED
        # The write must NOT have happened -- status stays at FINAL_REVIEW_FAILED.
        assert db.get_example_run_status(run_id, "ex-1") == ExampleStatus.FINAL_REVIEW_FAILED

        import sqlite3

        conn = sqlite3.connect(str(db.db_path))
        try:
            rows = conn.execute(
                "SELECT from_status, to_status FROM status_transitions "
                "WHERE example_id = ? AND to_status = 'VERIFIED' AND from_status = 'FINAL_REVIEW_FAILED'",
                ("ex-1",),
            ).fetchall()
        finally:
            conn.close()
        assert rows == [("FINAL_REVIEW_FAILED", "VERIFIED")]

    def test_illegal_transition_with_no_prior_run_state_raises(self, db):
        """No example_run_state row at all -- legality can't be determined, so
        this must also raise, not silently treat a missing row as "anything goes"."""
        run_id = db.create_run(family="zip")
        authority = StateAuthority(db)
        with pytest.raises(IllegalTransitionError) as excinfo:
            authority.transition("ex-missing", run_id, ExampleStatus.COMMITTED)
        assert excinfo.value.from_status is None


class TestConvenienceMethods:
    def test_mark_compiled_mark_verified_etc_route_through_transition(self):
        authority = StateAuthority(db=MagicMock())
        with patch.object(StateAuthority, "transition") as mock_transition:
            authority.mark_compiled("ex-1", "run-1")
            mock_transition.assert_called_with("ex-1", "run-1", ExampleStatus.COMPILABLE, evidence_ref=None)

            authority.mark_verified("ex-1", "run-1")
            mock_transition.assert_called_with("ex-1", "run-1", ExampleStatus.VERIFIED, evidence_ref=None)

            authority.mark_committed("ex-1", "run-1")
            mock_transition.assert_called_with("ex-1", "run-1", ExampleStatus.COMMITTED, evidence_ref=None)

            authority.mark_infra_blocked("ex-1", "run-1", failure_reason="missing fixture")
            mock_transition.assert_called_with(
                "ex-1", "run-1", ExampleStatus.INFRA_BLOCKED, failure_reason="missing fixture", evidence_ref=None
            )

            authority.mark_final_review_passed("ex-1", "run-1")
            mock_transition.assert_called_with("ex-1", "run-1", ExampleStatus.FINAL_REVIEW_PASSED, evidence_ref=None)

            authority.mark_final_review_failed("ex-1", "run-1", failure_reason="drift detected")
            mock_transition.assert_called_with(
                "ex-1", "run-1", ExampleStatus.FINAL_REVIEW_FAILED, failure_reason="drift detected", evidence_ref=None
            )

        assert mock_transition.call_count == 6


class TestReusesModelsTransitionTable:
    def test_state_authority_reuses_models_can_transition_to(self, db):
        """Proves StateAuthority doesn't duplicate the transition table -- it
        calls ExampleRecord.can_transition_to() itself."""
        run_id = _seed_discovered(db, "ex-1")
        authority = StateAuthority(db)

        with patch.object(ExampleRecord, "can_transition_to", return_value=True) as mock_can_transition:
            authority.transition("ex-1", run_id, ExampleStatus.COMPILABLE)

        mock_can_transition.assert_called_once_with(ExampleStatus.COMPILABLE)


class TestNegativeControls:
    def test_raw_update_example_status_bypasses_authority_by_design(self, db):
        """NEGATIVE CONTROL: the low-level Database.update_example_status()
        primitive itself performs NO legality check -- calling it directly
        (not through StateAuthority) still succeeds even for an illegal jump.
        This documents the shape of the bug StateAuthority + the CI lint
        script (scripts/validation/check_no_raw_status_writes.py) close as an
        ecosystem; it does not claim the primitive itself became safe."""
        run_id = _seed_discovered(db, "ex-1")

        result = db.update_example_status("ex-1", ExampleStatus.COMMITTED, run_id=run_id)

        assert result is True
        assert db.get_example_run_status(run_id, "ex-1") == ExampleStatus.COMMITTED

    def test_lint_script_flags_current_error_router_dead_code(self):
        """Proves the lint script's detection fires on the real, previously-
        uncited bypass this investigation surfaced (error_router.py:300's
        direct .status = assignment inside the currently-uncalled
        escalate_to_review()), not just a synthetic fixture."""
        from scripts.validation.check_no_raw_status_writes import scan

        repo_root = Path(__file__).parent.parent
        violations = scan(repo_root / "src")
        error_router_hits = [v for v in violations if v.path.name == "error_router.py"]
        assert any(v.line == 300 for v in error_router_hits), (
            f"Expected a violation at error_router.py:300, got lines: "
            f"{[v.line for v in error_router_hits]}"
        )
