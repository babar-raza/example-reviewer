"""Tests for the Authorization Kernel (TC-EPIC1-01).

Covers Capability, Decision, PolicyDecisionPoint.check(), and
Database.record_authority_decision(). See
reports/investigation/20260829_124758_production_readiness/taskcards/TC-EPIC1-01.md
for the full taskcard this file closes out.
"""

import sqlite3
from unittest.mock import MagicMock, patch

import pytest

from src.core.authority import Capability, Decision, PolicyDecisionDeniedError, PolicyDecisionPoint
from src.core.database import Database


def test_capability_enum_has_8_members():
    """Locks the enum surface so a future PR can't silently add/remove a capability."""
    assert len(list(Capability)) == 8
    assert {c.value for c in Capability} == {
        "write_markdown",
        "write_artifact",
        "execute_code",
        "commit_git",
        "push_git",
        "publish_gist",
        "call_llm_external",
        "call_llm_local",
    }


def test_decision_is_immutable():
    decision = Decision(
        allow=True, reason="test", policy_id="test.policy", capability=Capability.WRITE_MARKDOWN
    )
    with pytest.raises(Exception):
        decision.allow = False  # type: ignore[misc]


def test_check_returns_decision_never_raises():
    pdp = PolicyDecisionPoint()
    decision = pdp.check(Capability.EXECUTE_CODE, resource="some/path.cs", context={})
    assert isinstance(decision, Decision)
    assert decision.allow is False


def test_check_fails_closed_for_unknown_capability():
    """No policy registered for a capability -> fail closed, never allow-by-default.

    This is the negative control proving the kernel cannot be tricked into
    allow-by-default the way the now-deleted check_provenance_enabled()
    (provenance_guard.py, removed in TC-EPIC1-05) used to trivially echo back
    whatever boolean it was handed.
    """
    pdp = PolicyDecisionPoint()
    decision = pdp.check(Capability.COMMIT_GIT, resource="repo", context={})
    assert decision.allow is False
    assert decision.policy_id == "no_policy_registered"


def test_registered_policy_is_consulted():
    pdp = PolicyDecisionPoint()

    def allow_everything(resource, context):
        return Decision(
            allow=True, reason="test policy", policy_id="test.always_allow",
            capability=Capability.WRITE_ARTIFACT, resource=resource,
        )

    pdp.register_policy(Capability.WRITE_ARTIFACT, allow_everything)
    decision = pdp.check(Capability.WRITE_ARTIFACT, resource="workspace/x.txt")
    assert decision.allow is True
    assert decision.policy_id == "test.always_allow"


def test_require_raises_on_deny():
    pdp = PolicyDecisionPoint()
    with pytest.raises(PolicyDecisionDeniedError):
        pdp.require(Capability.PUSH_GIT, resource="origin/main")


def test_require_does_not_raise_on_allow():
    pdp = PolicyDecisionPoint()
    pdp.register_policy(
        Capability.CALL_LLM_LOCAL,
        lambda resource, context: Decision(
            allow=True, reason="local", policy_id="test.local", capability=Capability.CALL_LLM_LOCAL,
        ),
    )
    decision = pdp.require(Capability.CALL_LLM_LOCAL)
    assert decision.allow is True


def test_check_records_to_audit_table_on_allow_and_deny():
    fake_db = MagicMock()
    pdp = PolicyDecisionPoint(database=fake_db)

    pdp.check(Capability.WRITE_MARKDOWN, resource="content/foo.md", context={"run_id": "run-1"})
    assert fake_db.record_authority_decision.call_count == 1
    kwargs = fake_db.record_authority_decision.call_args.kwargs
    assert kwargs["decision"] == "deny"
    assert kwargs["run_id"] == "run-1"

    pdp.register_policy(
        Capability.WRITE_MARKDOWN,
        lambda resource, context: Decision(
            allow=True, reason="ok", policy_id="test.allow",
            capability=Capability.WRITE_MARKDOWN, resource=resource,
        ),
    )
    pdp.check(Capability.WRITE_MARKDOWN, resource="content/foo.md", context={"run_id": "run-2"})
    assert fake_db.record_authority_decision.call_count == 2
    kwargs2 = fake_db.record_authority_decision.call_args.kwargs
    assert kwargs2["decision"] == "allow"


def test_audit_row_written_even_when_denied():
    """Proves this kernel cannot reproduce the current silent-failure mode where a
    hardcoded allow_commit=True at src/mcp_tools/tools.py:484 leaves zero audit
    trail today (there is no equivalent table in the current schema)."""
    fake_db = MagicMock()
    pdp = PolicyDecisionPoint(database=fake_db)
    decision = pdp.check(Capability.COMMIT_GIT, resource="repo")
    assert decision.allow is False
    fake_db.record_authority_decision.assert_called_once()
    assert fake_db.record_authority_decision.call_args.kwargs["decision"] == "deny"


def _apply_migration_013_directly(db_path) -> None:
    """Execute migrations/013_authority_audit_table.sql directly against db_path.

    NOTE: a brand-new temp_db is a "fresh database" per Database._is_fresh_database(),
    so the normal apply_migrations() path marks migration 013 as applied WITHOUT
    executing its SQL (this is the exact F-038 fresh-bootstrap behavior documented in
    FINDINGS_REGISTER.md, and TC-EPIC1-01's own "Migration/backward-compatibility
    requirements" section explicitly defers fixing this for authority_audit to
    TC-EPIC2-03, which will add authority_audit to SCHEMA/base_tables at the same
    time it hardens _is_fresh_database()). Applying the migration file directly here
    tests the SQL itself, independent of that known, separately-tracked gap.
    """
    from pathlib import Path

    repo_root = Path(__file__).parent.parent
    migration_sql = (repo_root / "migrations" / "013_authority_audit_table.sql").read_text(encoding="utf-8")
    conn = sqlite3.connect(str(db_path))
    try:
        conn.executescript(migration_sql)
    finally:
        conn.close()


def test_record_authority_decision_uses_write_lock(temp_db):
    """Regression guard: record_authority_decision must acquire the write lock,
    matching the convention already used at 8 other call sites in database.py."""
    db = Database(db_path=temp_db)
    _apply_migration_013_directly(temp_db)
    with patch.object(db, "_write_lock", wraps=db._write_lock) as lock_spy:
        db.record_authority_decision(
            capability="write_markdown", resource="x", decision="allow",
            policy_id="test.policy", run_id=None, reason="test",
        )
    lock_spy.__enter__.assert_called()
    db.close()


def test_migration_013_is_idempotent(temp_db):
    """Migration 013's SQL applies cleanly, twice in a row (CREATE TABLE/INDEX IF
    NOT EXISTS), and produces the expected authority_audit column set."""
    db0 = Database(db_path=temp_db)  # initializes base schema first
    db0.close()
    _apply_migration_013_directly(temp_db)
    _apply_migration_013_directly(temp_db)  # idempotency: must not raise

    conn = sqlite3.connect(str(temp_db))
    try:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(authority_audit)").fetchall()}
    finally:
        conn.close()
    assert columns == {
        "id", "capability", "resource", "decision", "policy_id", "run_id", "reason", "timestamp",
    }

    db2 = Database(db_path=temp_db)
    db2.record_authority_decision(
        capability="execute_code", resource="a.cs", decision="deny",
        policy_id="no_policy_registered", run_id="run-x", reason="fail closed",
    )
    db2.close()
    conn = sqlite3.connect(str(temp_db))
    try:
        count = conn.execute("SELECT COUNT(*) FROM authority_audit").fetchone()[0]
    finally:
        conn.close()
    assert count == 1
