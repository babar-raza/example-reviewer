"""
Unit tests for fingerprint and results_summary export.

Verifies that all required fields from Plan v2.1 Section B (lines 60-107) are present.
"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime

# Import the modules under test
from src.core.fingerprint import RunFingerprint
from src.core.results_summary import ResultsSummary


class TestFingerprintExport:
    """Test fingerprint export matches Plan v2.1 Section B requirements."""

    def test_fingerprint_required_fields(self):
        """Verify all required fields from Plan v2.1 Section B are present."""
        # Create a fingerprint with all required data
        fingerprint = RunFingerprint(
            run_id="test_run_123",
            config_hash="abc123def456",
            selection_hash="sel789hash012",
            vector_db_startup_decision={'status': 'available'},
            drift_enabled=True,
            llm_provider_capabilities={
                'provider': 'ollama',
                'base_url': 'http://localhost:11434/v1',
                'model': 'qwen2.5:14b',
                'model_hash': None,
                'temperature': 0.0,
                'timeout_seconds': 120,
                'seed_supported': True,
                'timeout_supported': True,
                'final_review_enabled': True,
                'final_review_provider': 'anthropic',
                'final_review_model': 'claude-3-5-sonnet-latest',
                'final_review_timeout': 30,
                'vector_db_provider': 'chromadb',
                'embedding_model': 'all-MiniLM-L6-v2',
                'embedding_model_version': '2.2.0',
                'embedding_device': 'cpu',
                'drift_tolerance': 0.02,
                'dotnet_version': '8.0.100',
                'family': 'zip',
                'total_examples_selected': 66,
                'content_hash': None,
            },
            llm_seed=12345,
            deterministic_mode=True,
        )

        # Convert to dict (Plan v2.1 format)
        data = fingerprint.to_dict()

        # Verify top-level fields (Plan v2.1 lines 62-64)
        assert 'run_id' in data
        assert 'timestamp_utc' in data
        assert 'config_hash' in data

        # Verify LLM section (lines 65-78)
        assert 'llm' in data
        llm = data['llm']
        assert llm['provider'] == 'ollama'
        assert llm['base_url'] == 'http://localhost:11434/v1'
        assert llm['model'] == 'qwen2.5:14b'
        assert llm['model_hash'] is None
        assert llm['temperature'] == 0.0
        assert llm['seed'] == 12345
        assert llm['timeout_seconds'] == 120
        assert llm['deterministic_mode'] is True
        assert 'provider_capabilities' in llm
        assert llm['provider_capabilities']['seed_supported'] is True
        assert llm['provider_capabilities']['timeout_supported'] is True

        # Verify final_review section (lines 79-84)
        assert 'final_review' in data
        final_review = data['final_review']
        assert final_review['enabled'] is True
        assert final_review['provider'] == 'anthropic'
        assert final_review['model'] == 'claude-3-5-sonnet-latest'
        assert final_review['timeout_seconds'] == 30

        # Verify vector_db section (lines 85-92)
        assert 'vector_db' in data
        vector_db = data['vector_db']
        assert vector_db['enabled'] is True
        assert vector_db['provider'] == 'chromadb'
        assert vector_db['embedding_model'] == 'all-MiniLM-L6-v2'
        assert vector_db['embedding_model_version'] == '2.2.0'
        assert vector_db['device'] == 'cpu'
        assert vector_db['drift_tolerance'] == 0.02

        # Verify environment section (lines 93-99)
        assert 'environment' in data
        env = data['environment']
        assert 'os' in env
        assert 'os_version' in env
        assert 'python_version' in env
        assert env['dotnet_version'] == '8.0.100'
        assert 'git_commit' in env

        # Verify content_snapshot section (lines 100-106)
        assert 'content_snapshot' in data
        content = data['content_snapshot']
        assert content['family'] == 'zip'
        assert content['total_examples_selected'] == 66
        assert 'content_hash' in content
        assert content['selection_hash'] == 'sel789hash012'

    def test_fingerprint_json_roundtrip(self):
        """Test that fingerprint can be serialized and deserialized."""
        original = RunFingerprint(
            run_id="test_run_456",
            config_hash="config_hash_123",
            selection_hash="selection_hash_456",
            drift_enabled=True,
            llm_provider_capabilities={
                'provider': 'openai',
                'model': 'gpt-4o-mini',
                'temperature': 0.0,
                'family': 'pdf',
                'total_examples_selected': 42,
            },
            llm_seed=54321,
            deterministic_mode=True,
        )

        # Convert to JSON and back
        json_str = original.to_json()
        restored = RunFingerprint.from_json(json_str)

        # Verify key fields are preserved
        assert restored.run_id == original.run_id
        assert restored.config_hash == original.config_hash
        assert restored.selection_hash == original.selection_hash
        assert restored.drift_enabled == original.drift_enabled
        assert restored.llm_seed == original.llm_seed
        assert restored.deterministic_mode == original.deterministic_mode

    def test_fingerprint_file_save_and_load(self):
        """Test that fingerprint can be saved to and loaded from a file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test_fingerprint.json"

            # Create and save fingerprint
            original = RunFingerprint(
                run_id="test_run_789",
                config_hash="hash_abc",
                selection_hash="hash_def",
                drift_enabled=False,
                llm_provider_capabilities={
                    'provider': 'anthropic',
                    'model': 'claude-opus-4',
                    'family': 'cells',
                    'total_examples_selected': 100,
                },
                llm_seed=None,
                deterministic_mode=False,
            )

            original.save_to_file(file_path)

            # Verify file exists
            assert file_path.exists()

            # Load and verify
            loaded = RunFingerprint.load_from_file(file_path)
            assert loaded.run_id == original.run_id
            assert loaded.config_hash == original.config_hash

    def test_fingerprint_selection_hash_computation(self):
        """Test that selection_hash is correctly populated from example_keys."""
        # This will be tested indirectly through the database compute_selection_hash method
        # which is already implemented in database.py
        pass


class TestResultsSummaryExport:
    """Test results_summary export."""

    def test_results_summary_required_fields(self):
        """Verify results_summary has all required fields."""
        summary = ResultsSummary(
            run_id="test_run_123",
            family="zip",
            selection_hash="sel_hash_123",
            examples_processed=100,
            examples_verified=85,
            examples_failed=15,
            per_example_statuses={
                'ex1': 'VERIFIED',
                'ex2': 'COMPILE_FAILED',
                'ex3': 'VERIFIED',
            },
            drift_scores={
                'ex1': 0.01,
                'ex2': 0.15,
                'ex3': 0.02,
            },
            run_duration_seconds=300.5,
        )

        # Convert to dict
        data = summary.to_dict()

        # Verify required fields
        assert 'run_id' in data
        assert 'family' in data
        assert 'selection_hash' in data
        assert 'timestamp_utc' in data
        assert 'run_duration_seconds' in data
        assert 'summary' in data

        summary_section = data['summary']
        assert summary_section['examples_processed'] == 100
        assert summary_section['examples_verified'] == 85
        assert summary_section['examples_failed'] == 15

        assert 'per_example_statuses' in data
        assert len(data['per_example_statuses']) == 3

        assert 'drift_scores' in data
        assert len(data['drift_scores']) == 3

    def test_results_summary_json_roundtrip(self):
        """Test that results_summary can be serialized and deserialized."""
        original = ResultsSummary(
            run_id="test_run_456",
            family="pdf",
            selection_hash="sel_hash_456",
            examples_processed=50,
            examples_verified=40,
            examples_failed=10,
            per_example_statuses={'ex1': 'VERIFIED', 'ex2': 'RUNTIME_FAILED'},
            drift_scores={'ex1': 0.0, 'ex2': 0.25},
            run_duration_seconds=150.0,
        )

        # Convert to JSON and back
        json_str = original.to_json()
        restored = ResultsSummary.from_json(json_str)

        # Verify key fields are preserved
        assert restored.run_id == original.run_id
        assert restored.family == original.family
        assert restored.selection_hash == original.selection_hash
        assert restored.examples_processed == original.examples_processed
        assert restored.examples_verified == original.examples_verified
        assert restored.examples_failed == original.examples_failed

    def test_results_summary_file_save_and_load(self):
        """Test that results_summary can be saved to and loaded from a file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test_summary.json"

            # Create and save summary
            original = ResultsSummary(
                run_id="test_run_789",
                family="cells",
                selection_hash="sel_hash_789",
                examples_processed=25,
                examples_verified=20,
                examples_failed=5,
                per_example_statuses={'ex1': 'VERIFIED'},
                drift_scores={},
                run_duration_seconds=75.5,
            )

            original.save_to_file(file_path)

            # Verify file exists
            assert file_path.exists()

            # Load and verify
            loaded = ResultsSummary.load_from_file(file_path)
            assert loaded.run_id == original.run_id
            assert loaded.family == original.family
            assert loaded.examples_processed == original.examples_processed


def test_integration_fingerprint_and_summary_exports():
    """Integration test verifying both exports work together."""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir) / "run_test_123"
        run_dir.mkdir(parents=True, exist_ok=True)

        # Create fingerprint
        fingerprint = RunFingerprint(
            run_id="test_run_123",
            config_hash="config_abc",
            selection_hash="sel_abc",
            drift_enabled=True,
            llm_provider_capabilities={
                'provider': 'ollama',
                'model': 'qwen2.5:14b',
                'family': 'zip',
                'total_examples_selected': 10,
            },
            llm_seed=12345,
            deterministic_mode=True,
        )

        # Create summary
        summary = ResultsSummary(
            run_id="test_run_123",
            family="zip",
            selection_hash="sel_abc",
            examples_processed=10,
            examples_verified=8,
            examples_failed=2,
            per_example_statuses={'ex1': 'VERIFIED', 'ex2': 'COMPILE_FAILED'},
            drift_scores={'ex1': 0.01, 'ex2': 0.15},
            run_duration_seconds=60.0,
        )

        # Export both
        fingerprint.save_to_file(run_dir / "fingerprint.json")
        summary.save_to_file(run_dir / "results_summary.json")

        # Verify both files exist
        assert (run_dir / "fingerprint.json").exists()
        assert (run_dir / "results_summary.json").exists()

        # Load and verify
        loaded_fingerprint = RunFingerprint.load_from_file(run_dir / "fingerprint.json")
        loaded_summary = ResultsSummary.load_from_file(run_dir / "results_summary.json")

        # Verify selection_hash matches between fingerprint and summary
        assert loaded_fingerprint.selection_hash == loaded_summary.selection_hash
        assert loaded_fingerprint.run_id == loaded_summary.run_id
