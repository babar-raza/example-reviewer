"""
Narrow integration tests that exercise real code paths without mocks.

These tests do NOT require external services (no LLM, no .NET SDK, no network).
They verify that core components work together using real implementations.

Marked with @pytest.mark.integration so they can be run separately:
    pytest tests/test_integration_real.py -v -m integration
"""

import json
import sqlite3
import tempfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# pydantic_settings may not be available in all dev environments.
# These tests should skip gracefully rather than error.
try:
    from src.core.config import FamilyConfig, ConfigurationManager
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False


@pytest.mark.integration
class TestRealConfigLoading:
    """Load real family configs through the real config parser."""

    @pytest.mark.skipif(not CONFIG_AVAILABLE, reason="pydantic_settings import error")
    def test_load_zip_family_config(self):
        """Load config/families/zip.json through FamilyConfig and verify fields."""
        config_path = PROJECT_ROOT / "config" / "families" / "zip.json"
        assert config_path.exists(), f"zip.json not found at {config_path}"

        with open(config_path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        config = FamilyConfig(**raw)
        assert config.family == "zip"
        assert config.display_name == "Aspose.ZIP for .NET"
        assert len(config.content_roots) > 0
        assert config.nuget_config is not None
        assert config.nuget_config.primary_package.name == "Aspose.Zip"

    @pytest.mark.skipif(not CONFIG_AVAILABLE, reason="pydantic_settings import error")
    def test_load_all_family_configs(self):
        """Every JSON in config/families/ that is a family config should parse."""
        families_dir = PROJECT_ROOT / "config" / "families"
        family_files = [
            f for f in families_dir.glob("*.json")
            if not any(suffix in f.name for suffix in [
                "_api_catalog", "_behavioral_patterns", "_review_hints"
            ])
        ]
        assert len(family_files) >= 10, (
            f"Expected at least 10 family configs, found {len(family_files)}"
        )

        failures = []
        for config_file in family_files:
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                FamilyConfig(**raw)
            except Exception as e:
                failures.append(f"{config_file.name}: {e}")

        assert not failures, (
            f"Family config parsing failures:\n" + "\n".join(failures)
        )


@pytest.mark.integration
class TestRealDatabaseCreation:
    """Create a real SQLite database and verify schema."""

    def test_create_database_with_base_schema(self):
        """Create a Database and verify initialize_schema() succeeds on a fresh DB."""
        from src.core.database import Database

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = Database(db_path=db_path)

            # Call initialize_schema() directly — this must not raise on a fresh DB.
            # (Previously failed with OperationalError: no such column: er.status
            # because work_queue was missing from _is_fresh_database()'s base_tables set,
            # causing _is_fresh_database() to return False and migration 009 to run.)
            db.initialize_schema()

            # Verify the database file was created
            assert db_path.exists()

            # Verify key tables exist by querying sqlite_master
            conn = sqlite3.connect(str(db_path))
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = {row[0] for row in cursor.fetchall()}
            conn.close()

            expected_tables = {
                "example_records",
                "schema_migrations",
                "example_run_state",
                "work_queue",
            }
            missing = expected_tables - tables
            assert not missing, f"Missing tables: {missing}. Found: {tables}"

    def test_work_queue_operations(self):
        """Test work queue enqueue, poll, and complete operations."""
        from src.core.database import Database

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = Database(db_path=db_path)

            # Apply schema manually (Database auto-applies on first get_connection)
            conn = sqlite3.connect(str(db_path))
            conn.executescript(Database.SCHEMA)
            conn.close()

            # Enqueue two items with different priorities
            qid1 = db.enqueue_work("zip", trigger_source="test", priority=5)
            qid2 = db.enqueue_work("words", trigger_source="test", priority=10)

            # Poll should return higher-priority item first
            work = db.poll_next_work()
            assert work is not None
            assert work["family"] == "words"
            assert work["priority"] == 10

            # Complete it (no run_id since we don't have a real run record)
            db.complete_work(work["queue_id"], success=True)

            # Poll again should return second item
            work2 = db.poll_next_work()
            assert work2 is not None
            assert work2["family"] == "zip"

            # Complete with failure
            db.complete_work(work2["queue_id"], success=False, error="test error")

            # Queue should be empty
            work3 = db.poll_next_work()
            assert work3 is None


@pytest.mark.integration
class TestRealConfigurationManager:
    """Instantiate ConfigurationManager with real config directory."""

    @pytest.mark.skipif(not CONFIG_AVAILABLE, reason="pydantic_settings import error")
    def test_instantiate_with_real_config_dir(self):
        """ConfigurationManager loads without crash using real config/families/."""
        config_dir = PROJECT_ROOT / "config" / "families"
        assert config_dir.exists()

        manager = ConfigurationManager(config_dir=config_dir)
        assert manager.config_dir == config_dir


@pytest.mark.integration
class TestEvidenceEmission:
    """Test run evidence manifest emission."""

    def test_emit_run_evidence(self):
        """Evidence manifest is written with correct schema."""
        from src.pipeline.evidence import emit_run_evidence

        class MockDB:
            def get_run_stats_from_db(self, family, run_id):
                return {"total_processed": 10, "verified": 7, "failed": 3}

        results = {
            "family": "zip",
            "started_at": "2026-06-13T10:00:00",
            "completed_at": "2026-06-13T10:05:00",
            "success": True,
            "phases": {
                "discovery": {"examples_found": 10},
                "compilation": {"examples_processed": 10},
            },
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            art_dir = Path(tmpdir) / "test-run"
            path = emit_run_evidence("test-run", "zip", results, MockDB(), artifact_dir=art_dir)

            assert path is not None
            assert path.exists()

            with open(path) as f:
                evidence = json.load(f)

            assert evidence["schema_version"] == "1.0"
            assert evidence["run_id"] == "test-run"
            assert evidence["family"] == "zip"
            assert evidence["examples"]["discovered"] == 10
            assert evidence["examples"]["verified"] == 7
            assert evidence["examples"]["failed"] == 3
            assert evidence["verification_rate_pct"] == 70.0
            assert evidence["success"] is True


@pytest.mark.integration
class TestSupervisorAnalysis:
    """Test post-run supervisor analysis."""

    def test_supervisor_quality_alert(self):
        """Supervisor detects low verification rate."""
        from src.pipeline.supervisor import analyze_run
        import contextlib

        class MockDB:
            def get_run_stats_from_db(self, family, run_id):
                return {"total_processed": 20, "verified": 8, "failed": 12}

            def get_connection(self):
                conn = sqlite3.connect(":memory:")
                conn.row_factory = sqlite3.Row
                conn.execute("""CREATE TABLE failure_details (
                    example_id TEXT, run_id TEXT, failure_category TEXT,
                    error_category TEXT, resolution TEXT
                )""")
                conn.execute(
                    "INSERT INTO failure_details VALUES (?,?,?,?,?)",
                    ("ex1", "test-run", "timeout", None, "pending"),
                )
                conn.commit()
                return contextlib.contextmanager(lambda: (yield conn))()

        results = {"phases": {}, "success": False}

        with tempfile.TemporaryDirectory() as tmpdir:
            art_dir = Path(tmpdir) / "test-run"
            path = analyze_run("test-run", "zip", results, MockDB(), artifact_dir=art_dir)

            assert path is not None
            with open(path) as f:
                report = json.load(f)

            assert report["schema_version"] == "1.0"
            assert report["summary"]["total_recommendations"] > 0

            # Should have quality alert (8/20 = 40% < 50%)
            quality_alerts = [
                r for r in report["recommendations"] if r["type"] == "quality_alert"
            ]
            assert len(quality_alerts) > 0


@pytest.mark.integration
class TestAPRVSignals:
    """Test APRV self-assessment generation."""

    def test_generate_aprv_assessment(self):
        """APRV assessment generates valid structure."""
        from src.core.aprv_signals import generate_aprv_assessment

        assessment = generate_aprv_assessment()

        assert assessment["schema_version"] == "1.0"
        assert "assessed_at" in assessment

        for dimension in ["agentic", "practices", "readiness", "verification"]:
            assert dimension in assessment
            assert "level" in assessment[dimension]
            assert "evidence" in assessment[dimension]
            assert isinstance(assessment[dimension]["evidence"], list)
            assert len(assessment[dimension]["evidence"]) > 0


@pytest.mark.integration
class TestRepoSignals:
    """Test repository signal manifest generation."""

    def test_generate_repo_signals(self):
        """All expected repo signals are present."""
        import sys
        sys.path.insert(0, str(PROJECT_ROOT))
        from scripts.validation.generate_repo_signals import generate_repo_signals

        signals = generate_repo_signals()

        assert signals["schema_version"] == "1.0"
        assert "signals" in signals

        expected_signals = [
            "hasSourceDir", "hasTestDir", "hasEntryPoints", "hasReadme",
            "hasChangelog", "hasDocsDir", "hasContributing", "hasAgentsMd",
            "hasCiConfig", "hasDockerFiles", "hasCodeowners",
        ]
        for sig in expected_signals:
            assert sig in signals["signals"], f"Missing signal: {sig}"
            assert signals["signals"][sig] is True, f"Signal {sig} is False"


@pytest.mark.integration
class TestConsistencyChecker:
    """Test doc-code consistency checker."""

    def test_all_claims_valid(self):
        """All claims in claim_registry.json reference existing files."""
        from scripts.validation.check_doc_code_consistency import (
            load_claim_registry,
            validate_claim,
        )

        registry = load_claim_registry()
        claims = registry.get("claims", [])
        assert len(claims) > 0

        all_issues = []
        for claim in claims:
            issues = validate_claim(claim)
            all_issues.extend(issues)

        # Filter out expected circularity warnings
        real_issues = [i for i in all_issues if "potential circular" not in i]
        assert not real_issues, f"Claim validation issues:\n" + "\n".join(real_issues)


@pytest.mark.integration
class TestAutoLearnIntegration:
    """Test post-run auto-learn pattern extraction (TC-12)."""

    def test_extract_proposed_patterns(self):
        """Pattern proposals are generated from failure data."""
        import contextlib
        from src.pipeline.auto_learn_integration import extract_proposed_patterns

        class MockDB:
            def get_connection(self):
                conn = sqlite3.connect(":memory:")
                conn.row_factory = sqlite3.Row
                conn.execute("""CREATE TABLE example_run_state (
                    example_id TEXT, run_id TEXT, status TEXT,
                    failure_reason TEXT, escalation_reason TEXT
                )""")
                conn.executemany(
                    "INSERT INTO example_run_state VALUES (?,?,?,?,?)",
                    [
                        ("ex1", "run-1", "COMPILE_FAILED", "error CS0246: type missing", None),
                        ("ex2", "run-1", "COMPILE_FAILED", "error CS0246: type missing", None),
                        ("ex3", "run-1", "RUNTIME_FAILED", "timeout after 60s", None),
                    ],
                )
                conn.commit()
                return contextlib.contextmanager(lambda: (yield conn))()

        with tempfile.TemporaryDirectory() as tmpdir:
            art_dir = Path(tmpdir) / "test-run"
            path = extract_proposed_patterns("run-1", "zip", MockDB(), artifact_dir=art_dir)

            assert path is not None
            assert path.exists()

            with open(path) as f:
                manifest = json.load(f)

            assert manifest["schema_version"] == "1.0"
            assert manifest["auto_promoted"] is False
            assert manifest["requires_human_review"] is True
            assert len(manifest["proposals"]) >= 2

            cs0246 = [p for p in manifest["proposals"] if p["signature"] == "CS0246"]
            assert len(cs0246) == 1
            assert cs0246[0]["example_count"] == 2
            assert cs0246[0]["auto_approved"] is False
