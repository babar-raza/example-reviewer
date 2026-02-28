"""Tests for ExampleReviewerTools core tool methods with a mocked orchestrator."""
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from pathlib import Path

from src.mcp_tools.tools import ExampleReviewerTools, ToolResult


@pytest.fixture
def mock_orchestrator():
    """Create a fully mocked PipelineOrchestrator."""
    orch = MagicMock()
    orch.config_manager.load_family_config.return_value = MagicMock()
    orch.config_manager.load_global_config.return_value = MagicMock()
    orch.db.get_latest_run_id.return_value = "run-123"
    orch.db.create_run.return_value = "run-456"
    orch.discovery_service.discover_family.return_value = {
        "files_found": 10,
        "files_processed": 8,
        "examples_found": 15,
        "inline_examples": 12,
        "gist_examples": 3,
        "errors": [],
    }
    orch._run_compilation_phase.return_value = {"compiled": 10, "failed": 2}
    orch._run_runtime_phase.return_value = {"verified": 8, "failed": 2}
    orch._run_markdown_update_phase.return_value = {"updated": 5}
    orch._run_final_review_phase.return_value = {"reviewed": 5, "passed": 4}
    orch._run_finalization_phase.return_value = {"committed": True, "commit_hash": "abc123"}
    orch.get_status.return_value = {"family": "zip", "total": 50}
    orch.run_full_pipeline.return_value = {"success": True, "family": "zip"}
    orch.vector_db_service = MagicMock()

    # Mock db.get_connection() as context manager returning a mock conn
    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchone.return_value = ("run-completed-789",)
    orch.db.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
    orch.db.get_connection.return_value.__exit__ = MagicMock(return_value=False)

    return orch


@pytest.fixture
def tools(mock_orchestrator):
    """Create ExampleReviewerTools with mocked orchestrator (bypass lazy init)."""
    t = ExampleReviewerTools.__new__(ExampleReviewerTools)
    t.config_dir = Path("config/families")
    t.db_path = Path("data/test.db")
    t.prod_db_path = None
    t.workspace_dir = Path("workspace")
    t.cli_overrides = {}
    t.use_workspace_copy = False
    t.sqlite_config = {}
    t._orchestrator = mock_orchestrator
    return t


# =========================================================================
# ToolResult
# =========================================================================

class TestToolResult:
    def test_to_dict_excludes_none(self):
        """to_dict omits None fields."""
        r = ToolResult(success=True, data={"x": 1})
        d = r.to_dict()
        assert "error" not in d
        assert d["success"] is True
        assert d["data"] == {"x": 1}

    def test_to_dict_includes_error(self):
        """to_dict includes error when present."""
        r = ToolResult(success=False, error="boom")
        d = r.to_dict()
        assert "data" not in d
        assert d["error"] == "boom"

    def test_to_json_roundtrip(self):
        """to_json produces valid JSON string."""
        import json
        r = ToolResult(success=True, data={"count": 42})
        parsed = json.loads(r.to_json())
        assert parsed["success"] is True
        assert parsed["data"]["count"] == 42


# =========================================================================
# SCAN
# =========================================================================

class TestScan:
    def test_scan_directory_mode(self, tools, tmp_path):
        """Scan with directory parameter returns file list."""
        (tmp_path / "test.md").write_text("# Test")
        (tmp_path / "other.md").write_text("# Other")
        result = tools.scan(directory=str(tmp_path))
        assert result.success is True
        assert result.data["mode"] == "directory"
        assert result.data["file_count"] == 2

    def test_scan_directory_not_found(self, tools):
        """Scan with nonexistent directory returns error."""
        result = tools.scan(directory="/nonexistent/path/xyz")
        assert result.success is False
        assert "not found" in result.error.lower()

    def test_scan_no_args(self, tools):
        """Scan with neither family nor directory returns error."""
        result = tools.scan()
        assert result.success is False
        assert "family" in result.error.lower() or "directory" in result.error.lower()

    def test_scan_max_files(self, tools, tmp_path):
        """max_files limits results."""
        for i in range(5):
            (tmp_path / f"test{i}.md").write_text(f"# Test {i}")
        result = tools.scan(directory=str(tmp_path), max_files=2)
        assert result.success is True
        assert result.data["file_count"] == 2

    def test_scan_family_mode(self, tools, mock_orchestrator):
        """Scan with family uses orchestrator discovery service."""
        mock_discovery = MagicMock()
        mock_discovery._find_markdown_files.return_value = ["a.md", "b.md", "c.md"]
        with patch("src.services.discovery_service.DiscoveryService", return_value=mock_discovery):
            result = tools.scan(family="zip")
            assert result.success is True
            assert result.data["mode"] == "family"
            assert result.data["family"] == "zip"
            assert result.data["file_count"] == 3

    def test_scan_exception_in_family_mode(self, tools, mock_orchestrator):
        """Exception in scan returns error ToolResult."""
        mock_orchestrator.config_manager.load_family_config.side_effect = RuntimeError("config error")
        result = tools.scan(family="zip")
        assert result.success is False
        assert "config error" in result.error

    def test_scan_directory_no_md_files(self, tools, tmp_path):
        """Scan directory with no .md files returns zero count."""
        (tmp_path / "readme.txt").write_text("not markdown")
        result = tools.scan(directory=str(tmp_path))
        assert result.success is True
        assert result.data["file_count"] == 0


# =========================================================================
# EXTRACT
# =========================================================================

class TestExtract:
    def test_extract_success(self, tools, mock_orchestrator):
        """Extract returns discovery statistics."""
        result = tools.extract(family="zip")
        assert result.success is True
        assert result.data["examples_found"] == 15
        assert result.data["inline_examples"] == 12
        assert result.data["gist_examples"] == 3
        assert result.data["family"] == "zip"
        mock_orchestrator.discovery_service.discover_family.assert_called_once()

    def test_extract_passes_max_files(self, tools, mock_orchestrator):
        """max_files is forwarded to discover_family."""
        tools.extract(family="zip", max_files=5)
        call_kwargs = mock_orchestrator.discovery_service.discover_family.call_args
        assert call_kwargs[1]["max_files"] == 5
        assert call_kwargs[1]["max_examples"] is None

    def test_extract_exception(self, tools, mock_orchestrator):
        """Exception in extract returns error."""
        mock_orchestrator.discovery_service.discover_family.side_effect = RuntimeError("discovery failed")
        result = tools.extract(family="zip")
        assert result.success is False
        assert "discovery failed" in result.error


# =========================================================================
# COMPILE_VERIFY
# =========================================================================

class TestCompileVerify:
    def test_compile_verify_success(self, tools, mock_orchestrator):
        """compile_verify returns compilation stats."""
        result = tools.compile_verify(family="zip")
        assert result.success is True
        assert result.data["compiled"] == 10
        mock_orchestrator._run_compilation_phase.assert_called_once()

    def test_compile_verify_skip_llm_fixes_true(self, tools, mock_orchestrator):
        """compile_verify passes skip_llm_fixes=True."""
        tools.compile_verify(family="zip")
        call_args = mock_orchestrator._run_compilation_phase.call_args
        # Positional: (run_id, family, family_config, max_examples, skip_llm_fixes=True)
        assert call_args[1].get("skip_llm_fixes") is True or call_args[0][4] is True

    def test_compile_verify_uses_existing_run(self, tools, mock_orchestrator):
        """Uses existing run_id from get_latest_run_id."""
        tools.compile_verify(family="zip")
        call_args = mock_orchestrator._run_compilation_phase.call_args[0]
        assert call_args[0] == "run-123"  # from get_latest_run_id
        mock_orchestrator.db.create_run.assert_not_called()

    def test_compile_verify_creates_new_run_if_needed(self, tools, mock_orchestrator):
        """Creates a new run when no existing run found."""
        mock_orchestrator.db.get_latest_run_id.return_value = None
        tools.compile_verify(family="zip")
        mock_orchestrator.db.create_run.assert_called_once()
        call_args = mock_orchestrator._run_compilation_phase.call_args[0]
        assert call_args[0] == "run-456"  # from create_run

    def test_compile_verify_exception(self, tools, mock_orchestrator):
        """Exception returns error."""
        mock_orchestrator._run_compilation_phase.side_effect = RuntimeError("compile boom")
        result = tools.compile_verify(family="zip")
        assert result.success is False
        assert "compile boom" in result.error


# =========================================================================
# COMPILE_FIX
# =========================================================================

class TestCompileFix:
    def test_compile_fix_success(self, tools, mock_orchestrator):
        """compile_fix returns compilation stats."""
        result = tools.compile_fix(family="zip")
        assert result.success is True
        assert result.data["compiled"] == 10

    def test_compile_fix_skip_llm_fixes_false(self, tools, mock_orchestrator):
        """compile_fix passes skip_llm_fixes=False (enables LLM fixes)."""
        tools.compile_fix(family="zip")
        call_args = mock_orchestrator._run_compilation_phase.call_args
        assert call_args[1].get("skip_llm_fixes") is False or call_args[0][4] is False

    def test_compile_fix_exception(self, tools, mock_orchestrator):
        """Exception returns error."""
        mock_orchestrator._run_compilation_phase.side_effect = RuntimeError("fix boom")
        result = tools.compile_fix(family="zip")
        assert result.success is False
        assert "fix boom" in result.error


# =========================================================================
# RUNTIME_VERIFY
# =========================================================================

class TestRuntimeVerify:
    def test_runtime_verify_success(self, tools, mock_orchestrator):
        """runtime_verify returns runtime stats."""
        result = tools.runtime_verify(family="zip")
        assert result.success is True
        assert result.data["verified"] == 8
        assert result.data["failed"] == 2

    def test_runtime_verify_skip_llm_fixes_true(self, tools, mock_orchestrator):
        """runtime_verify passes skip_llm_fixes=True."""
        tools.runtime_verify(family="zip")
        call_args = mock_orchestrator._run_runtime_phase.call_args
        assert call_args[1].get("skip_llm_fixes") is True or call_args[0][4] is True

    def test_runtime_verify_exception(self, tools, mock_orchestrator):
        """Exception returns error."""
        mock_orchestrator._run_runtime_phase.side_effect = RuntimeError("runtime boom")
        result = tools.runtime_verify(family="zip")
        assert result.success is False
        assert "runtime boom" in result.error


# =========================================================================
# RUNTIME_FIX
# =========================================================================

class TestRuntimeFix:
    def test_runtime_fix_success(self, tools, mock_orchestrator):
        """runtime_fix returns runtime stats."""
        result = tools.runtime_fix(family="zip")
        assert result.success is True
        assert result.data["verified"] == 8
        mock_orchestrator._run_runtime_phase.assert_called_once()

    def test_runtime_fix_skip_llm_fixes_false(self, tools, mock_orchestrator):
        """runtime_fix passes skip_llm_fixes=False (enables LLM fixes)."""
        tools.runtime_fix(family="zip")
        call_args = mock_orchestrator._run_runtime_phase.call_args
        assert call_args[1].get("skip_llm_fixes") is False or call_args[0][4] is False

    def test_runtime_fix_exception(self, tools, mock_orchestrator):
        """Exception returns error."""
        mock_orchestrator._run_runtime_phase.side_effect = RuntimeError("fix boom")
        result = tools.runtime_fix(family="zip")
        assert result.success is False
        assert "fix boom" in result.error


# =========================================================================
# MD_UPDATE
# =========================================================================

class TestMdUpdate:
    def test_md_update_success(self, tools, mock_orchestrator):
        """md_update finds completed run and calls update phase."""
        result = tools.md_update(family="zip")
        assert result.success is True
        assert result.data["updated"] == 5
        mock_orchestrator._run_markdown_update_phase.assert_called_once()

    def test_md_update_passes_run_id(self, tools, mock_orchestrator):
        """md_update passes the run_id from DB query."""
        tools.md_update(family="zip")
        call_args = mock_orchestrator._run_markdown_update_phase.call_args[0]
        assert call_args[0] == "run-completed-789"  # from mock_conn fetchone
        assert call_args[1] == "zip"

    def test_md_update_no_completed_runs(self, tools, mock_orchestrator):
        """md_update returns error when no completed runs exist."""
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = None
        mock_orchestrator.db.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_orchestrator.db.get_connection.return_value.__exit__ = MagicMock(return_value=False)
        result = tools.md_update(family="zip")
        assert result.success is False
        assert "no completed runs" in result.error.lower()

    def test_md_update_passes_allow_md_write(self, tools, mock_orchestrator):
        """allow_md_write is forwarded to the update phase."""
        tools.md_update(family="zip", allow_md_write=True)
        call_kwargs = mock_orchestrator._run_markdown_update_phase.call_args[1]
        assert call_kwargs["allow_md_write"] is True

    def test_md_update_passes_dry_run(self, tools, mock_orchestrator):
        """dry_run is forwarded as positional arg to the update phase."""
        tools.md_update(family="zip", dry_run=True)
        call_args = mock_orchestrator._run_markdown_update_phase.call_args[0]
        # (run_id, family, dry_run) are positional
        assert call_args[2] is True

    def test_md_update_exception(self, tools, mock_orchestrator):
        """Exception in md_update returns error."""
        mock_orchestrator.db.get_connection.side_effect = RuntimeError("db error")
        result = tools.md_update(family="zip")
        assert result.success is False
        assert "db error" in result.error


# =========================================================================
# FINAL_REVIEW
# =========================================================================

class TestFinalReview:
    def test_final_review_success(self, tools, mock_orchestrator):
        """final_review finds completed run and returns review stats."""
        result = tools.final_review(family="zip")
        assert result.success is True
        assert result.data["reviewed"] == 5
        assert result.data["passed"] == 4

    def test_final_review_passes_run_id_and_family(self, tools, mock_orchestrator):
        """final_review passes correct run_id and family."""
        tools.final_review(family="zip")
        call_args = mock_orchestrator._run_final_review_phase.call_args[0]
        assert call_args[0] == "run-completed-789"
        assert call_args[1] == "zip"

    def test_final_review_no_completed_runs(self, tools, mock_orchestrator):
        """final_review returns error when no completed runs exist."""
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = None
        mock_orchestrator.db.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_orchestrator.db.get_connection.return_value.__exit__ = MagicMock(return_value=False)
        result = tools.final_review(family="zip")
        assert result.success is False
        assert "no completed runs" in result.error.lower()

    def test_final_review_exception(self, tools, mock_orchestrator):
        """Exception in final_review returns error."""
        mock_orchestrator.db.get_connection.side_effect = RuntimeError("db error")
        result = tools.final_review(family="zip")
        assert result.success is False
        assert "db error" in result.error


# =========================================================================
# COMMIT
# =========================================================================

class TestCommit:
    def test_commit_success(self, tools, mock_orchestrator):
        """commit finds completed run and returns finalization stats."""
        result = tools.commit(family="zip")
        assert result.success is True
        assert result.data["committed"] is True
        assert result.data["commit_hash"] == "abc123"

    def test_commit_passes_correct_args(self, tools, mock_orchestrator):
        """commit passes (family, run_id, dry_run=False, allow_commit=True)."""
        tools.commit(family="zip")
        call_args = mock_orchestrator._run_finalization_phase.call_args
        assert call_args[0][0] == "zip"
        assert call_args[0][1] == "run-completed-789"
        assert call_args[1]["dry_run"] is False
        assert call_args[1]["allow_commit"] is True

    def test_commit_no_completed_runs(self, tools, mock_orchestrator):
        """commit returns error when no completed runs exist."""
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = None
        mock_orchestrator.db.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_orchestrator.db.get_connection.return_value.__exit__ = MagicMock(return_value=False)
        result = tools.commit(family="zip")
        assert result.success is False
        assert "no completed runs" in result.error.lower()

    def test_commit_exception(self, tools, mock_orchestrator):
        """Exception in commit returns error."""
        mock_orchestrator.db.get_connection.side_effect = RuntimeError("db error")
        result = tools.commit(family="zip")
        assert result.success is False
        assert "db error" in result.error


# =========================================================================
# BACKFILL
# =========================================================================

class TestBackfill:
    @patch("src.mcp_tools.tools.BackfillService", create=True)
    def test_backfill_test_data(self, MockBackfillService, tools, mock_orchestrator):
        """Backfill test_data target calls service correctly."""
        mock_service = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.files_copied = 5
        mock_result.skipped = False
        mock_result.skip_reason = None
        mock_result.error = None
        mock_result.duration_seconds = 1.5
        mock_service.backfill_test_data.return_value = mock_result
        MockBackfillService.return_value = mock_service

        mock_global = MagicMock()
        mock_global.backfill.github_timeout_seconds = 30
        mock_orchestrator.config_manager.load_global_config.return_value = mock_global

        with patch("src.services.backfill_service.BackfillService", MockBackfillService):
            result = tools.backfill(family="zip", targets=["test_data"])
        assert result.success is True
        assert result.data["results"]["test_data"]["files_copied"] == 5

    @patch("src.mcp_tools.tools.BackfillService", create=True)
    def test_backfill_unknown_target(self, MockBackfillService, tools, mock_orchestrator):
        """Unknown target produces an error entry."""
        mock_global = MagicMock()
        mock_global.backfill.github_timeout_seconds = 30
        mock_orchestrator.config_manager.load_global_config.return_value = mock_global

        with patch("src.services.backfill_service.BackfillService", MockBackfillService):
            result = tools.backfill(family="zip", targets=["nonexistent_target"])
        # Unknown target causes overall_success to be False
        assert result.success is False
        assert "Unknown backfill target" in result.data["results"]["nonexistent_target"]["error"]

    def test_backfill_exception(self, tools, mock_orchestrator):
        """Exception in backfill returns error."""
        mock_orchestrator.config_manager.load_global_config.side_effect = RuntimeError("config error")
        result = tools.backfill(family="zip")
        assert result.success is False
        assert "config error" in result.error


# =========================================================================
# STATUS
# =========================================================================

class TestStatus:
    def test_status_with_family(self, tools, mock_orchestrator):
        """status with family returns family-specific stats."""
        result = tools.status(family="zip")
        assert result.success is True
        assert result.data["family"] == "zip"
        mock_orchestrator.get_status.assert_called_once_with("zip")

    def test_status_without_family(self, tools, mock_orchestrator):
        """status without family returns all stats."""
        result = tools.status()
        assert result.success is True
        mock_orchestrator.get_status.assert_called_once_with(None)

    def test_status_exception(self, tools, mock_orchestrator):
        """Exception in status returns error."""
        mock_orchestrator.get_status.side_effect = RuntimeError("status error")
        result = tools.status()
        assert result.success is False
        assert "status error" in result.error


# =========================================================================
# RUN_PIPELINE
# =========================================================================

class TestRunPipeline:
    def test_run_pipeline_success(self, tools, mock_orchestrator):
        """run_pipeline returns pipeline results."""
        result = tools.run_pipeline(family="zip")
        assert result.success is True
        assert result.data["family"] == "zip"
        mock_orchestrator.run_full_pipeline.assert_called_once()

    def test_run_pipeline_success_field_from_results(self, tools, mock_orchestrator):
        """run_pipeline ToolResult.success mirrors results['success']."""
        mock_orchestrator.run_full_pipeline.return_value = {"success": False, "error": "partial failure"}
        result = tools.run_pipeline(family="zip")
        assert result.success is False
        assert result.data["error"] == "partial failure"

    def test_run_pipeline_forwards_all_kwargs(self, tools, mock_orchestrator):
        """All parameters are forwarded to orchestrator."""
        strategy = {"enable_transformers": True}
        tools.run_pipeline(
            family="zip",
            max_examples=10,
            skip_runtime=True,
            skip_llm_fixes=True,
            skip_llm_runtime_fixes=True,
            dry_run=True,
            allow_md_write=True,
            allow_commit=True,
            strategy_config=strategy,
        )
        call_kwargs = mock_orchestrator.run_full_pipeline.call_args
        assert call_kwargs[0][0] == "zip"  # positional family arg
        assert call_kwargs[1]["max_examples"] == 10
        assert call_kwargs[1]["skip_runtime"] is True
        assert call_kwargs[1]["skip_llm_fixes"] is True
        assert call_kwargs[1]["skip_llm_runtime_fixes"] is True
        assert call_kwargs[1]["dry_run"] is True
        assert call_kwargs[1]["allow_md_write"] is True
        assert call_kwargs[1]["allow_commit"] is True
        assert call_kwargs[1]["strategy_config"] == strategy

    def test_run_pipeline_exception(self, tools, mock_orchestrator):
        """Exception in run_pipeline returns error."""
        mock_orchestrator.run_full_pipeline.side_effect = RuntimeError("pipeline boom")
        result = tools.run_pipeline(family="zip")
        assert result.success is False
        assert "pipeline boom" in result.error

    def test_run_pipeline_defaults(self, tools, mock_orchestrator):
        """Default parameter values are forwarded correctly."""
        tools.run_pipeline(family="zip")
        call_kwargs = mock_orchestrator.run_full_pipeline.call_args[1]
        assert call_kwargs["max_examples"] is None
        assert call_kwargs["skip_runtime"] is False
        assert call_kwargs["skip_llm_fixes"] is False
        assert call_kwargs["skip_llm_runtime_fixes"] is False
        assert call_kwargs["dry_run"] is False
        assert call_kwargs["allow_md_write"] is False
        assert call_kwargs["allow_commit"] is False
        assert call_kwargs["strategy_config"] is None
