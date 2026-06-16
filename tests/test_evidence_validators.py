"""
Unit tests for evidence integrity validators.

Tests check_evidence_circularity.py, check_baseline_coverage.py,
and check_assessment_freshness.py edge cases.
"""
import json
import os
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest import mock

import pytest


# ---------------------------------------------------------------------------
# check_evidence_circularity tests
# ---------------------------------------------------------------------------

class TestEvidenceCircularity:
    """Tests for scripts/validation/check_evidence_circularity.py."""

    def _run_validator(self, registry_data, tmp_path):
        """Run the circularity validator with a temp claim_registry.json."""
        registry_file = tmp_path / "evals" / "claim_registry.json"
        registry_file.parent.mkdir(parents=True, exist_ok=True)
        registry_file.write_text(json.dumps(registry_data))

        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "check_evidence_circularity",
            "scripts/validation/check_evidence_circularity.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.CLAIM_REGISTRY = registry_file
        return mod.main()

    def test_all_grounded_claims(self, tmp_path):
        data = {"claims": [
            {"claim_id": "CR-001", "status": "grounded", "claim_text": "Test claim"},
        ]}
        assert self._run_validator(data, tmp_path) == 0

    def test_circular_with_grounding_gap_passes(self, tmp_path):
        data = {"claims": [
            {"claim_id": "CR-001", "status": "self-reported",
             "claim_text": "Circular claim", "grounding_gap": "Known gap"},
        ]}
        assert self._run_validator(data, tmp_path) == 0

    def test_circular_without_grounding_gap_fails(self, tmp_path):
        data = {"claims": [
            {"claim_id": "CR-001", "status": "self-reported",
             "claim_text": "Missing gap explanation"},
        ]}
        assert self._run_validator(data, tmp_path) == 1

    def test_empty_claims(self, tmp_path):
        data = {"claims": []}
        assert self._run_validator(data, tmp_path) == 0

    def test_missing_file(self, tmp_path):
        """Validator should skip if claim_registry.json doesn't exist."""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "check_evidence_circularity",
            "scripts/validation/check_evidence_circularity.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.CLAIM_REGISTRY = tmp_path / "nonexistent.json"
        assert mod.main() == 0


# ---------------------------------------------------------------------------
# check_baseline_coverage tests
# ---------------------------------------------------------------------------

class TestBaselineCoverage:
    """Tests for scripts/validation/check_baseline_coverage.py."""

    def _run_validator(self, families, baselines, tmp_path, max_missing=3):
        """Set up dirs and run the baseline coverage validator."""
        families_dir = tmp_path / "config" / "families"
        families_dir.mkdir(parents=True, exist_ok=True)
        baselines_dir = tmp_path / ".benchmarks" / "baselines"
        baselines_dir.mkdir(parents=True, exist_ok=True)

        for f in families:
            (families_dir / f"{f}.json").write_text("{}")
        for b in baselines:
            (baselines_dir / f"{b}_baseline.json").write_text("{}")

        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "check_baseline_coverage",
            "scripts/validation/check_baseline_coverage.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.FAMILIES_DIR = families_dir
        mod.BASELINES_DIR = baselines_dir
        mod.MAX_MISSING_ALLOWED = max_missing
        return mod.main()

    def test_all_baselines_present(self, tmp_path):
        assert self._run_validator(["zip", "words"], ["zip", "words"], tmp_path) == 0

    def test_missing_within_tolerance(self, tmp_path):
        assert self._run_validator(
            ["zip", "words", "pdf", "psd"],
            ["zip"],
            tmp_path,
            max_missing=3,
        ) == 0

    def test_missing_over_tolerance(self, tmp_path):
        assert self._run_validator(
            ["zip", "words", "pdf", "psd", "ocr"],
            ["zip"],
            tmp_path,
            max_missing=3,
        ) == 1

    def test_no_families_dir(self, tmp_path):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "check_baseline_coverage",
            "scripts/validation/check_baseline_coverage.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.FAMILIES_DIR = tmp_path / "nonexistent"
        assert mod.main() == 0


# ---------------------------------------------------------------------------
# check_assessment_freshness tests
# ---------------------------------------------------------------------------

class TestAssessmentFreshness:
    """Tests for scripts/validation/check_assessment_freshness.py."""

    def _run_validator(self, data, tmp_path, max_age=30):
        """Write assessment file and run the freshness validator."""
        assessment_file = tmp_path / "aprv_self_assessment.json"
        assessment_file.write_text(json.dumps(data))

        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "check_assessment_freshness",
            "scripts/validation/check_assessment_freshness.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.ASSESSMENT_FILE = assessment_file
        mod.MAX_AGE_DAYS = max_age
        return mod.main()

    def test_recent_assessment_passes(self, tmp_path):
        now = datetime.now(timezone.utc).isoformat()
        data = {"assessed_at": now}
        assert self._run_validator(data, tmp_path) == 0

    def test_stale_assessment_fails(self, tmp_path):
        old = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat()
        data = {"assessed_at": old}
        assert self._run_validator(data, tmp_path) == 1

    def test_missing_file_fails(self, tmp_path):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "check_assessment_freshness",
            "scripts/validation/check_assessment_freshness.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.ASSESSMENT_FILE = tmp_path / "nonexistent.json"
        assert mod.main() == 1

    def test_missing_timestamp_fails(self, tmp_path):
        data = {"schema_version": "1.0"}
        assert self._run_validator(data, tmp_path) == 1

    def test_unparseable_timestamp_fails(self, tmp_path):
        data = {"assessed_at": "not-a-date"}
        assert self._run_validator(data, tmp_path) == 1
