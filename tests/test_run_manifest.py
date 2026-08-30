"""Tests for TC-EPIC3-05: RunManifest schema + writer.

Covers src/core/run_manifest.py's capture functions and build/finalize
lifecycle, Database.save_run_manifest()/get_run_manifest(), and the
orchestrator run_full_pipeline() integration (captured at run start,
finalized at every return point, always best-effort/non-fatal). See
reports/investigation/20260829_124758_production_readiness/taskcards/TC-EPIC3-05.md.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.core.database import Database
from src.core.run_manifest import (
    RunManifest,
    build_run_manifest,
    capture_docker_image_digest,
    capture_git_sha,
    capture_resolved_nuget_versions,
    finalize_run_manifest,
)


@pytest.fixture
def temp_db_instance():
    fd = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    fd.close()
    path = Path(fd.name)
    path.unlink()
    db = Database(db_path=path)
    db.initialize_schema()
    yield db
    db.close()
    if path.exists():
        path.unlink()


class TestCaptureGitSha:
    def test_returns_real_sha_in_this_repo(self):
        sha = capture_git_sha(Path(__file__).parent.parent)
        assert sha is not None
        assert len(sha) == 40
        assert all(c in "0123456789abcdef" for c in sha)

    def test_returns_none_outside_a_git_repo(self, tmp_path):
        """Negative control: git SHA lookup failure (no repo here) must not
        raise -- the manifest field is simply left None."""
        assert capture_git_sha(tmp_path) is None


class TestCaptureDockerImageDigest:
    def test_returns_none_when_env_var_unset(self, monkeypatch):
        monkeypatch.delenv("EXAMPLE_REVIEWER_IMAGE_DIGEST", raising=False)
        assert capture_docker_image_digest() is None

    def test_returns_env_var_value_when_set(self, monkeypatch):
        monkeypatch.setenv("EXAMPLE_REVIEWER_IMAGE_DIGEST", "sha256:abc123")
        assert capture_docker_image_digest() == "sha256:abc123"


class TestCaptureResolvedNugetVersions:
    def test_returns_empty_dict_for_none_family_config(self):
        assert capture_resolved_nuget_versions(None) == {}

    def test_extracts_primary_package_version(self):
        from src.core.config import FamilyConfig, NuGetConfig, NuGetPackage

        family_config = FamilyConfig(
            family="zip",
            nuget_config=NuGetConfig(primary_package=NuGetPackage(name="Aspose.Zip", version="26.8.0")),
        )
        assert capture_resolved_nuget_versions(family_config) == {"Aspose.Zip": "26.8.0"}

    def test_extracts_additional_packages_too(self):
        from src.core.config import FamilyConfig, NuGetConfig, NuGetPackage

        family_config = FamilyConfig(
            family="pdf",
            nuget_config=NuGetConfig(
                primary_package=NuGetPackage(name="Aspose.PDF", version="26.8.0"),
                additional_packages=[NuGetPackage(name="Newtonsoft.Json", version="13.0.4")],
            ),
        )
        result = capture_resolved_nuget_versions(family_config)
        assert result == {"Aspose.PDF": "26.8.0", "Newtonsoft.Json": "13.0.4"}

    def test_omits_unpinned_packages(self):
        """Dev/exploration mode (no pin, restore_mode='floating') -- an empty
        or partial dict is the honest answer, not an error."""
        from src.core.config import FamilyConfig, NuGetConfig, NuGetPackage

        family_config = FamilyConfig(
            family="zip", nuget_config=NuGetConfig(primary_package=NuGetPackage(name="Aspose.Zip"))
        )
        assert capture_resolved_nuget_versions(family_config) == {}


class TestBuildAndFinalize:
    def test_build_captures_static_fields(self):
        manifest = build_run_manifest(
            run_id="run-1", pattern_set_version=3,
            circuit_breaker_state_at_start={"state": "closed"},
            repo_root=Path(__file__).parent.parent,
        )
        assert manifest.run_id == "run-1"
        assert manifest.pattern_set_version == 3
        assert manifest.circuit_breaker_state_at_start == {"state": "closed"}
        assert manifest.git_sha is not None
        assert manifest.finalized_at is None
        assert manifest.llm_call_stats == {}

    def test_finalize_sets_dynamic_fields_without_mutating_input(self):
        manifest = build_run_manifest(run_id="run-1")
        finalized = finalize_run_manifest(manifest, llm_call_stats={"total_calls": 5})

        assert finalized.llm_call_stats == {"total_calls": 5}
        assert finalized.finalized_at is not None
        # Pure function -- the original is untouched.
        assert manifest.finalized_at is None
        assert manifest.llm_call_stats == {}

    def test_finalize_with_no_stats_defaults_to_empty_dict(self):
        manifest = build_run_manifest(run_id="run-1")
        finalized = finalize_run_manifest(manifest)
        assert finalized.llm_call_stats == {}


class TestDatabasePersistence:
    def test_save_and_get_round_trip(self, temp_db_instance):
        manifest = build_run_manifest(
            run_id="run-1", pattern_set_version=7,
            circuit_breaker_state_at_start={"state": "open", "consecutive_failures": 3},
        )
        temp_db_instance.save_run_manifest(manifest)

        fetched = temp_db_instance.get_run_manifest("run-1")
        assert fetched is not None
        assert fetched.run_id == "run-1"
        assert fetched.pattern_set_version == 7
        assert fetched.circuit_breaker_state_at_start == {"state": "open", "consecutive_failures": 3}
        assert fetched.finalized_at is None

    def test_get_unknown_run_id_returns_none(self, temp_db_instance):
        assert temp_db_instance.get_run_manifest("does-not-exist") is None

    def test_save_is_idempotent_upsert_not_duplicate(self, temp_db_instance):
        """Negative control: a manifest is never silently duplicated for the
        same run_id -- save_run_manifest() upserts."""
        manifest = build_run_manifest(run_id="run-1", pattern_set_version=1)
        temp_db_instance.save_run_manifest(manifest)

        finalized = finalize_run_manifest(manifest, llm_call_stats={"total_calls": 2})
        temp_db_instance.save_run_manifest(finalized)

        fetched = temp_db_instance.get_run_manifest("run-1")
        assert fetched.llm_call_stats == {"total_calls": 2}
        assert fetched.finalized_at is not None

        with temp_db_instance.get_connection() as conn:
            count = conn.execute("SELECT COUNT(*) FROM run_manifests WHERE run_id = ?", ("run-1",)).fetchone()[0]
        assert count == 1

    def test_full_lifecycle_all_six_field_categories_populated(self, temp_db_instance):
        """Integration test (this taskcard's own requirement): a simulated
        run produces a manifest with all field categories populated from
        mocked upstream sources."""
        from src.core.config import FamilyConfig, NuGetConfig, NuGetPackage

        family_config = FamilyConfig(
            family="zip",
            nuget_config=NuGetConfig(primary_package=NuGetPackage(name="Aspose.Zip", version="26.8.0")),
        )
        with patch("src.core.run_manifest.capture_docker_image_digest", return_value="sha256:deadbeef"):
            manifest = build_run_manifest(
                run_id="run-full",
                family_config=family_config,
                pattern_set_version=12,
                circuit_breaker_state_at_start={"state": "closed", "consecutive_failures": 0},
                repo_root=Path(__file__).parent.parent,
            )
        temp_db_instance.save_run_manifest(manifest)
        finalized = finalize_run_manifest(manifest, llm_call_stats={"total_calls": 4, "total_tokens": 1200})
        temp_db_instance.save_run_manifest(finalized)

        fetched = temp_db_instance.get_run_manifest("run-full")
        assert fetched.git_sha is not None
        assert fetched.resolved_nuget_versions == {"Aspose.Zip": "26.8.0"}
        assert fetched.docker_image_digest == "sha256:deadbeef"
        assert fetched.pattern_set_version == 12
        assert fetched.circuit_breaker_state_at_start == {"state": "closed", "consecutive_failures": 0}
        assert fetched.llm_call_stats == {"total_calls": 4, "total_tokens": 1200}
        assert fetched.finalized_at is not None


class TestOrchestratorIntegration:
    def _make_orchestrator_stub(self):
        from src.pipeline.orchestrator import PipelineOrchestrator as Orchestrator

        orch = object.__new__(Orchestrator)
        orch.db = MagicMock()
        orch.db.create_run.return_value = "test-run-manifest-001"
        orch.config_manager = MagicMock()
        # A MagicMock's attribute chain (e.g. .nuget_config.primary_package.version)
        # returns further MagicMocks, which fail RunManifest's Pydantic
        # validation (not a real string) -- use a real, minimal FamilyConfig
        # instead so this stub matches what a real family config's shape
        # actually looks like.
        from src.core.config import FamilyConfig

        orch.config_manager.load_family_config.return_value = FamilyConfig(family="zip", nuget_config=None)
        orch.config_manager.load_global_config.side_effect = RuntimeError("STOP: test boundary")
        orch.registry = MagicMock()
        orch._current_family = None
        orch._vector_db_startup_decision = {}
        orch._drift_enabled = False
        orch._llm_metrics = {"total_calls": 0}
        primed_llm_service = MagicMock()
        primed_llm_service.get_circuit_breaker_snapshot.return_value = None
        orch._llm_service = primed_llm_service
        return orch

    def test_manifest_built_and_saved_at_run_start(self):
        orch = self._make_orchestrator_stub()
        with patch("src.pipeline.orchestrator.capture_pattern_set_version", return_value=None):
            with pytest.raises(RuntimeError, match="STOP: test boundary"):
                orch.run_full_pipeline(family="zip")

        orch.db.save_run_manifest.assert_called_once()
        saved_manifest = orch.db.save_run_manifest.call_args[0][0]
        assert saved_manifest.run_id == "test-run-manifest-001"
        assert saved_manifest.finalized_at is None  # not yet reached a return point

    def test_manifest_capture_failure_is_non_fatal_to_the_run(self):
        """Negative control: a manifest build/save failure must not fail the
        underlying pipeline run."""
        orch = self._make_orchestrator_stub()
        orch.db.save_run_manifest.side_effect = RuntimeError("db boom")

        with patch("src.pipeline.orchestrator.capture_pattern_set_version", return_value=None):
            # If manifest capture failure were fatal, this would raise
            # "db boom" instead of reaching the stub's STOP boundary.
            with pytest.raises(RuntimeError, match="STOP: test boundary"):
                orch.run_full_pipeline(family="zip")
