"""
Regression tests for _run_finalization_phase() — SR-05.

Specifically verifies the boundary between `examples` (all FINAL_REVIEW_PASSED)
and `committed_examples` (only those whose files were actually staged by git).

Before the SR fix, `update_example_status` was called on the full `examples` list,
marking all FINAL_REVIEW_PASSED examples as COMMITTED even when their files had no
actual diff.  After the fix, only `committed_examples` (the subset matching staged
files) should be marked COMMITTED.

Test cases:
  1. test_only_staged_examples_get_committed_status  — partial staging (2 of 5)
  2. test_no_staged_files_returns_early              — empty git diff → no commit
  3. test_all_staged_files_all_committed             — all 5 files staged
  4. test_commit_record_saved_on_success             — save_commit_record called
  5. test_commit_record_not_saved_on_git_failure     — git commit fails → no DB write
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure project root on path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pipeline.orchestrator import PipelineOrchestrator as Orchestrator
from src.core.models import ExampleStatus, SourceType
from src.core.authority import Capability, PolicyDecisionPoint
from src.core.authority.policies.commit_git import commit_git_policy
from src.core.state_authority import StateAuthority


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

_GIT_ROOT = "/fake/content/repo"


def _make_orchestrator():
    """Minimal Orchestrator instance with mocked dependencies."""
    orch = object.__new__(Orchestrator)
    orch.db = MagicMock()
    orch.config_manager = MagicMock()
    orch._llm_fixed_example_ids = set()
    # Config stubs
    global_cfg = MagicMock()
    global_cfg.git.enabled = True
    global_cfg.telemetry.local_telemetry_enabled = False
    global_cfg.markdown_write.allow_markdown_write = False
    orch.config_manager.load_global_config.return_value = global_cfg
    family_cfg = MagicMock()
    family_cfg.auto_commit = True
    family_cfg.content_roots = [_GIT_ROOT + "/content"]
    orch.config_manager.load_family_config.return_value = family_cfg
    # Authorization Kernel (TC-EPIC1-03): _run_finalization_phase now consults
    # self.pdp directly; this helper bypasses __init__ via object.__new__, so the
    # PDP must be constructed and the COMMIT_GIT policy registered here too.
    orch.pdp = PolicyDecisionPoint()
    orch.pdp.register_policy(Capability.COMMIT_GIT, commit_git_policy)
    # State Authority (TC-EPIC2-02): mark_committed() now routes through here.
    # orch.db is a MagicMock, so get_example_run_status() must be told to
    # return a real ExampleStatus (not a MagicMock) or StateAuthority's
    # scratch-ExampleRecord construction fails Pydantic validation -- these
    # examples are realistically at FINAL_REVIEW_PASSED by the time the
    # finalization/commit phase runs, which is also the only status that
    # legally transitions to COMMITTED.
    orch.db.get_example_run_status.return_value = ExampleStatus.FINAL_REVIEW_PASSED
    orch.state_authority = StateAuthority(orch.db)
    return orch


def _make_example(example_id: str, file_path: str):
    """Create a mock ExampleRecord with the minimum attributes needed."""
    ex = MagicMock()
    ex.example_id = example_id
    ex.file_path = file_path
    ex.source_type = SourceType.INLINE
    ex.topic = ""
    return ex


def _abs(rel: str) -> str:
    """Turn a fake relative path into an absolute-looking path for this OS."""
    return str(Path(_GIT_ROOT) / rel)


def _make_subprocess_side_effect(staged_rel_paths: list[str], commit_ok: bool = True):
    """Return a side_effect function for subprocess.run.

    Fakes all git calls made by _run_finalization_phase:
      rev-parse --show-toplevel  → _GIT_ROOT
      rev-parse --abbrev-ref HEAD → "main"
      add <file>                 → success
      diff --cached --name-only  → newline-joined staged_rel_paths
      commit -m ...              → returncode 0 or 1
      rev-parse HEAD             → "deadbeefdeadbeef"
    """
    def side_effect(cmd, **kwargs):
        result = MagicMock()
        result.returncode = 0
        result.stderr = ""

        if "rev-parse" in cmd and "--show-toplevel" in cmd:
            result.stdout = _GIT_ROOT + "\n"
        elif "rev-parse" in cmd and "--abbrev-ref" in cmd:
            result.stdout = "main\n"
        elif "add" in cmd:
            result.stdout = ""
        elif "diff" in cmd and "--cached" in cmd:
            result.stdout = "\n".join(staged_rel_paths) + ("\n" if staged_rel_paths else "")
        elif "commit" in cmd and "-m" in cmd:
            result.returncode = 0 if commit_ok else 1
            result.stdout = "[main abc1234] fix(test): commit\n"
            result.stderr = "" if commit_ok else "nothing to commit"
        elif "rev-parse" in cmd and "HEAD" in cmd:
            result.stdout = "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef\n"
        else:
            result.stdout = ""
        return result

    return side_effect


# ---------------------------------------------------------------------------
# SR-05 test cases
# ---------------------------------------------------------------------------

class TestFinalizationCommittedBoundary:
    """Verify that only staged files produce COMMITTED status updates."""

    def _run(self, orch, staged_rel_paths, examples, commit_ok=True, dry_run=False):
        """Invoke _run_finalization_phase with mocked git and return stats."""
        orch.db.get_examples_by_family.return_value = examples
        side_effect = _make_subprocess_side_effect(staged_rel_paths, commit_ok=commit_ok)
        with patch("subprocess.run", side_effect=side_effect):
            return orch._run_finalization_phase(
                family="imaging",
                run_id="test-run-001",
                dry_run=dry_run,
                allow_commit=False,   # relies on global_config.git.enabled=True
            )

    # ── Test 1: partial staging (2 of 5 files have diffs) ──────────────────

    def test_only_staged_examples_get_committed_status(self):
        """
        5 FINAL_REVIEW_PASSED examples, but only 2 files have actual git diffs.
        DB update_example_status must be called exactly twice (for the 2 staged ones).

        This test FAILS on pre-fix code (which iterated `examples`, not
        `committed_examples`) and PASSES on the fixed code.
        """
        files = [_abs(f"content/post{i}/index.md") for i in range(5)]
        examples = [_make_example(f"ex-{i:02d}", files[i]) for i in range(5)]

        # Only the first two files are staged (have a diff)
        staged_rel = [
            "content/post0/index.md",
            "content/post1/index.md",
        ]

        orch = _make_orchestrator()
        stats = self._run(orch, staged_rel, examples)

        assert stats["committed"] is True
        assert stats["commit_hash"] == "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef"

        # Exactly 2 status updates
        update_calls = orch.db.update_example_status.call_args_list
        assert len(update_calls) == 2, (
            f"Expected 2 status updates (staged examples only), got {len(update_calls)}. "
            "Pre-fix code would call update for all 5 examples."
        )

        updated_ids = {c.args[0] for c in update_calls}
        assert updated_ids == {"ex-00", "ex-01"}

        for c in update_calls:
            assert c.args[1] == ExampleStatus.COMMITTED

    # ── Test 2: no staged files → early return, no commit ──────────────────

    def test_no_staged_files_returns_early(self):
        """
        git diff --cached returns empty string.
        Finalization must return early with committed=False and zero DB updates.
        """
        files = [_abs(f"content/post{i}/index.md") for i in range(3)]
        examples = [_make_example(f"ex-{i:02d}", files[i]) for i in range(3)]

        orch = _make_orchestrator()
        stats = self._run(orch, staged_rel_paths=[], examples=examples)

        assert stats["committed"] is False
        assert stats.get("commit_hash") is None
        orch.db.update_example_status.assert_not_called()
        orch.db.save_commit_record.assert_not_called()

    # ── Test 3: all files staged → all examples committed ──────────────────

    def test_all_staged_files_all_committed(self):
        """
        All 5 examples have staged files.
        All 5 must be marked COMMITTED.
        """
        files = [_abs(f"content/post{i}/index.md") for i in range(5)]
        staged_rel = [f"content/post{i}/index.md" for i in range(5)]
        examples = [_make_example(f"ex-{i:02d}", files[i]) for i in range(5)]

        orch = _make_orchestrator()
        stats = self._run(orch, staged_rel, examples)

        assert stats["committed"] is True
        update_calls = orch.db.update_example_status.call_args_list
        assert len(update_calls) == 5
        updated_ids = {c.args[0] for c in update_calls}
        assert updated_ids == {f"ex-{i:02d}" for i in range(5)}

    # ── Test 4: save_commit_record is called on success ────────────────────

    def test_commit_record_saved_on_success(self):
        """
        After a successful git commit, save_commit_record must be called once
        with the correct run_id, family, and commit_hash.
        """
        files = [_abs("content/post0/index.md")]
        examples = [_make_example("ex-00", files[0])]
        staged_rel = ["content/post0/index.md"]

        orch = _make_orchestrator()
        stats = self._run(orch, staged_rel, examples)

        assert stats["committed"] is True
        orch.db.save_commit_record.assert_called_once()
        kwargs = orch.db.save_commit_record.call_args.kwargs
        assert kwargs["run_id"] == "test-run-001"
        assert kwargs["family"] == "imaging"
        assert kwargs["commit_hash"] == "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef"
        assert isinstance(kwargs["touched_files"], list)
        assert len(kwargs["touched_files"]) == 1

    # ── Test 5: commit record NOT saved when git commit fails ──────────────

    def test_commit_record_not_saved_on_git_failure(self):
        """
        When git commit returns non-zero, neither commit_records nor example
        status updates should be written.
        """
        files = [_abs("content/post0/index.md")]
        examples = [_make_example("ex-00", files[0])]
        staged_rel = ["content/post0/index.md"]

        orch = _make_orchestrator()
        stats = self._run(orch, staged_rel, examples, commit_ok=False)

        assert stats["committed"] is False
        orch.db.save_commit_record.assert_not_called()
        orch.db.update_example_status.assert_not_called()

    # ── Test 6: dry_run skips all git and DB writes ─────────────────────────

    def test_dry_run_skips_commit(self):
        """dry_run=True must return immediately without any subprocess or DB calls."""
        files = [_abs("content/post0/index.md")]
        examples = [_make_example("ex-00", files[0])]

        orch = _make_orchestrator()
        with patch("subprocess.run") as mock_sub:
            stats = orch._run_finalization_phase(
                family="imaging",
                run_id="test-run-dry",
                dry_run=True,
            )
            mock_sub.assert_not_called()

        assert stats["committed"] is False
        orch.db.update_example_status.assert_not_called()
        orch.db.save_commit_record.assert_not_called()

    # ── Test 7: CS_FILE examples excluded from commit ──────────────────────

    def test_cs_file_examples_excluded(self):
        """
        CS_FILE source-type examples are reference-only and must not be committed.
        Only INLINE/GIST examples in staged files get COMMITTED status.
        """
        inline_file = _abs("content/post0/index.md")
        cs_file = _abs("content/post1/index.md")

        inline_ex = _make_example("ex-inline", inline_file)
        inline_ex.source_type = SourceType.INLINE
        cs_ex = _make_example("ex-cs", cs_file)
        cs_ex.source_type = SourceType.CS_FILE

        orch = _make_orchestrator()
        # get_examples_by_family returns both; only inline_ex should be committed
        orch.db.get_examples_by_family.return_value = [inline_ex, cs_ex]

        staged_rel = ["content/post0/index.md"]
        side_effect = _make_subprocess_side_effect(staged_rel)
        with patch("subprocess.run", side_effect=side_effect):
            stats = orch._run_finalization_phase(
                family="imaging",
                run_id="test-run-cs",
                dry_run=False,
                allow_commit=False,
            )

        update_calls = orch.db.update_example_status.call_args_list
        updated_ids = {c.args[0] for c in update_calls}
        assert "ex-inline" in updated_ids
        assert "ex-cs" not in updated_ids
