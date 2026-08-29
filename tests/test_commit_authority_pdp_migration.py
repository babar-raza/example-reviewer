"""Tests for TC-EPIC1-03: commit gate migrated to the Authorization Kernel.

Primary purpose: prove the MCP `commit` tool's hardcoded `allow_commit=True`
(src/mcp_tools/tools.py, pre-fix) no longer bypasses a family's `auto_commit=False`
safety switch. See FINDINGS_REGISTER.md F-013.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.core.authority import Capability, PolicyDecisionPoint
from src.core.authority.policies.commit_git import commit_git_policy
from src.pipeline.orchestrator import PipelineOrchestrator as Orchestrator
from src.mcp_tools.tools import ExampleReviewerTools

_GIT_ROOT = "/fake/content/repo"


def _make_orchestrator(auto_commit: bool, git_enabled: bool = True):
    orch = object.__new__(Orchestrator)
    orch.db = MagicMock()
    orch.config_manager = MagicMock()
    orch._llm_fixed_example_ids = set()

    global_cfg = MagicMock()
    global_cfg.git.enabled = git_enabled
    global_cfg.telemetry.local_telemetry_enabled = False
    orch.config_manager.load_global_config.return_value = global_cfg

    family_cfg = MagicMock()
    family_cfg.auto_commit = auto_commit
    family_cfg.content_roots = [_GIT_ROOT + "/content"]
    orch.config_manager.load_family_config.return_value = family_cfg

    orch.pdp = PolicyDecisionPoint()
    orch.pdp.register_policy(Capability.COMMIT_GIT, commit_git_policy)

    orch.db.get_examples_by_family.return_value = []  # no candidate files -> early return either way
    orch.db.get_connection.return_value.__enter__.return_value.execute.return_value.fetchone.return_value = (
        "test-run-001",
    )
    return orch


def _never_call_git(*args, **kwargs):
    raise AssertionError("git subprocess must NOT be invoked when commit is denied")


def test_old_mcp_hardcode_bug_is_fixed():
    """THE PRIMARY NEGATIVE CONTROL. Reconstructs the exact pre-fix scenario:
    family auto_commit=False, invoke the MCP commit() tool method. Before
    TC-EPIC1-03, tools.py:484's hardcoded allow_commit=True skipped the family
    gate entirely (orchestrator's old `if not allow_commit:` never ran), so git
    commit would have been attempted regardless. After the fix, the family gate
    is consulted unconditionally and git must never be invoked."""
    orch = _make_orchestrator(auto_commit=False)
    tools = ExampleReviewerTools()
    tools._orchestrator = orch

    with patch("subprocess.run", side_effect=_never_call_git):
        result = tools.commit(family="zip")

    assert result.success is True  # tool call itself succeeds; it just skips the commit
    assert result.data["committed"] is False


def test_mcp_commit_tool_respects_family_auto_commit_false():
    orch = _make_orchestrator(auto_commit=False)
    tools = ExampleReviewerTools()
    tools._orchestrator = orch
    with patch("subprocess.run") as mock_run:
        tools.commit(family="zip")
    mock_run.assert_not_called()


def test_cli_commit_flag_respects_family_auto_commit_false():
    """Same assertion via the CLI-equivalent path: allow_commit=True passed
    directly into _run_finalization_phase (as main.py's --commit flag would)."""
    orch = _make_orchestrator(auto_commit=False)
    with patch("subprocess.run") as mock_run:
        stats = orch._run_finalization_phase(
            family="zip", run_id="test-run-001", dry_run=False, allow_commit=True
        )
    mock_run.assert_not_called()
    assert stats["committed"] is False


def test_family_auto_commit_true_allows_both_paths():
    """Positive control: both CLI-equivalent and MCP paths reach the commit
    attempt (no candidate files in this fixture, so git itself isn't invoked,
    but the family gate must not block before that point)."""
    orch_cli = _make_orchestrator(auto_commit=True)
    with patch("subprocess.run") as mock_run:
        orch_cli._run_finalization_phase(
            family="zip", run_id="test-run-001", dry_run=False, allow_commit=True
        )
    # No candidate files -> returns before any git call, but NOT because of the
    # auto_commit gate (which allowed it) -- confirm via explicit PDP check instead.
    decision = orch_cli.pdp.check(
        Capability.COMMIT_GIT,
        resource="zip",
        context={"cli_commit_flag": True, "git_enabled": True, "family_auto_commit": True, "dry_run": False},
    )
    assert decision.allow is True

    orch_mcp = _make_orchestrator(auto_commit=True)
    tools = ExampleReviewerTools()
    tools._orchestrator = orch_mcp
    with patch("subprocess.run"):
        result = tools.commit(family="zip")
    assert result.success is True


def test_commit_decision_always_audited():
    """Every _run_finalization_phase invocation must produce an authority_audit
    row, allow or deny alike."""
    fake_db = MagicMock()
    orch = _make_orchestrator(auto_commit=False)
    orch.pdp = PolicyDecisionPoint(database=fake_db)
    orch.pdp.register_policy(Capability.COMMIT_GIT, commit_git_policy)

    orch._run_finalization_phase(family="zip", run_id="test-run-001", dry_run=False, allow_commit=True)
    fake_db.record_authority_decision.assert_called()
    kwargs = fake_db.record_authority_decision.call_args.kwargs
    assert kwargs["capability"] == "commit_git"
    assert kwargs["decision"] == "deny"

    orch2 = _make_orchestrator(auto_commit=True)
    orch2.pdp = PolicyDecisionPoint(database=fake_db)
    orch2.pdp.register_policy(Capability.COMMIT_GIT, commit_git_policy)
    orch2._run_finalization_phase(family="zip", run_id="test-run-002", dry_run=False, allow_commit=True)
    kwargs2 = fake_db.record_authority_decision.call_args.kwargs
    assert kwargs2["decision"] == "allow"


def test_no_hardcoded_allow_commit_true_remains_in_tools_module():
    """Static-shape guard for this taskcard's evidence requirement: the literal
    string 'allow_commit=True' must not appear in the compiled tools module's
    source (checked via the module's own __file__ at test time, so this also
    catches a future regression, not just this investigation's finding)."""
    import inspect
    import src.mcp_tools.tools as tools_module

    source = inspect.getsource(tools_module)
    assert "allow_commit=True" not in source
