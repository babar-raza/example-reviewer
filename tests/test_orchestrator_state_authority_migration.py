"""Tests for TC-EPIC2-02: migrate all update_example_status() call sites to
StateAuthority.

Covers the taskcard's own closeout proof (the lint script passes clean against
the real, migrated tree) and the concrete real-pipeline manifestation of Root
Cause 2 this taskcard closes: driving mark_committed() from a non-
FINAL_REVIEW_PASSED status is now rejected, not silently allowed.

See reports/investigation/20260829_124758_production_readiness/taskcards/TC-EPIC2-02.md.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.core.database import Database
from src.core.models import ExampleRecord, ExampleStatus
from src.core.state_authority import IllegalTransitionError, StateAuthority
from src.pipeline.orchestrator import PipelineOrchestrator as Orchestrator


def _apply_migration_014_directly(db_path) -> None:
    """See tests/test_state_authority.py's identical helper -- same F-038
    fresh-bootstrap gap (TC-EPIC2-03 fixed this for real DBs going forward by
    adding status_transitions to SCHEMA directly; this helper stays as an
    explicit, independent guarantee for this test file too)."""
    import sqlite3

    repo_root = Path(__file__).parent.parent
    migration_sql = (repo_root / "migrations" / "014_status_transitions_audit.sql").read_text(encoding="utf-8")
    conn = sqlite3.connect(str(db_path))
    try:
        conn.executescript(migration_sql)
    finally:
        conn.close()


class TestLintScriptCleanAgainstRealTree:
    def test_no_raw_update_example_status_calls_remain_in_orchestrator(self):
        """Closeout proof: the lint script (scripts/validation/check_no_raw_status_writes.py)
        finds ZERO violations in the real, migrated src/ tree -- contrasted with
        TC-EPIC2-01's captured baseline (58 violations: 54 in orchestrator.py, 1
        in error_router.py, 2 in markdown_service.py, 1 in timeout_manager.py)."""
        from scripts.validation.check_no_raw_status_writes import scan

        repo_root = Path(__file__).parent.parent
        violations = scan(repo_root / "src")
        assert violations == [], f"Expected zero violations, found: {[v.format(repo_root) for v in violations]}"

    def test_lint_script_now_passes_in_strict_mode(self):
        """Directly exercises main() in --strict mode against the real tree,
        matching how CI's state-authority-lint job now runs it."""
        from scripts.validation.check_no_raw_status_writes import main

        repo_root = Path(__file__).parent.parent
        exit_code = main([str(repo_root / "src"), "--strict"])
        assert exit_code == 0


class TestCommittedUnreachableWithoutFinalReviewPassed:
    def test_committed_status_unreachable_without_final_review_passed(self):
        """The concrete real-pipeline manifestation of Root Cause 2 this
        taskcard closes: attempt to drive an example straight from DISCOVERED
        to COMMITTED via StateAuthority.mark_committed() (the exact call
        _run_finalization_phase now makes) and confirm it's rejected.
        Database.update_example_status() itself (the still-unvalidated
        low-level primitive, per TC-EPIC2-01's own negative control) performs
        no such check -- only routing through StateAuthority prevents this."""
        import tempfile

        fd = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        fd.close()
        db_path = Path(fd.name)
        db_path.unlink()
        try:
            db = Database(db_path=db_path)
            db.initialize_schema()
            _apply_migration_014_directly(db_path)

            run_id = db.create_run(family="zip")
            example = ExampleRecord(
                family="zip", file_path="docs/x.md", original_code="//x", status=ExampleStatus.DISCOVERED
            )
            db.save_example(example, run_id=run_id)

            authority = StateAuthority(db)
            with pytest.raises(IllegalTransitionError):
                authority.mark_committed(example.example_id, run_id)

            assert db.get_example_run_status(run_id, example.example_id) == ExampleStatus.DISCOVERED
            db.close()
        finally:
            if db_path.exists():
                db_path.unlink()


class TestNewlyDiscoveredTransition:
    def test_verified_to_needs_review_now_modeled(self):
        """Regression guard for the one previously-unmodeled transition this
        migration's full-suite run surfaced (tests/test_md_update_multiblock.py's
        test_signature_mismatch_skips_update): markdown_service.py legitimately
        escalates a VERIFIED example to NEEDS_REVIEW when its code block's
        signature can no longer be located in the markdown file. Every other
        non-terminal ExampleStatus already allowed escalating to NEEDS_REVIEW;
        VERIFIED was the one inconsistent gap in models.py's transition table,
        closed here as a deliberate design decision (not silently loosened) --
        see src/core/models.py's can_transition_to() comment."""
        example = ExampleRecord(family="zip", file_path="x.md", original_code="//x", status=ExampleStatus.VERIFIED)
        assert example.can_transition_to(ExampleStatus.NEEDS_REVIEW) is True
        assert example.can_transition_to(ExampleStatus.MD_UPDATED) is True
        # VERIFIED must still not permit skipping straight to unrelated states.
        assert example.can_transition_to(ExampleStatus.COMMITTED) is False
        assert example.can_transition_to(ExampleStatus.COMPILABLE) is False
