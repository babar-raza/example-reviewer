"""
Unit tests for config determinism: hash stability, CLI overrides, strict schema.

Tests that effective config hashing is deterministic and that unknown keys fail fast.
"""

import json
import pytest
import tempfile
from pathlib import Path
from pydantic import ValidationError

from src.core.config import (
    ConfigurationManager,
    GlobalConfig,
    LLMConfig,
    VectorDBConfig,
    FinalReviewConfig,
    TimeoutsConfig,
    ConfigAccessTracker,
    LimitsConfig,
    GitConfig,
    GistConfig,
    TelemetryConfig,
    BackfillConfig,
    DriftConfig,
    MarkdownWriteConfig,
    NuGetPackage,
    NuGetConfig,
    RuntimeValidationConfig,
    DiscoveryPatternsConfig,
    ContextExtractionConfig,
    GistPatternsConfig,
)


class TestConfigHashStability:
    """Test that config hash is stable for identical configs."""

    def test_same_config_same_hash(self, temp_config_dir):
        """Same config should produce same hash."""
        manager = ConfigurationManager(
            config_dir=temp_config_dir / "families",
            global_config_path=temp_config_dir / "global.json"
        )

        # Compute hash twice
        hash1 = manager.compute_config_hash("test_family")
        hash2 = manager.compute_config_hash("test_family")

        assert hash1 == hash2, "Same config should produce same hash"
        assert len(hash1) == 64, "Hash should be SHA256 (64 hex chars)"

    def test_different_cli_overrides_different_hash(self, temp_config_dir):
        """Different CLI overrides should produce different hashes."""
        manager = ConfigurationManager(
            config_dir=temp_config_dir / "families",
            global_config_path=temp_config_dir / "global.json"
        )

        hash1 = manager.compute_config_hash("test_family", cli_overrides=None)
        hash2 = manager.compute_config_hash("test_family", cli_overrides={"llm": {"seed": 12345}})
        hash3 = manager.compute_config_hash("test_family", cli_overrides={"llm": {"seed": 67890}})

        assert hash1 != hash2, "Different CLI overrides should produce different hash"
        assert hash2 != hash3, "Different seed values should produce different hash"

    def test_cli_override_included_in_effective_config(self, temp_config_dir):
        """CLI overrides should be reflected in effective config."""
        manager = ConfigurationManager(
            config_dir=temp_config_dir / "families",
            global_config_path=temp_config_dir / "global.json"
        )

        effective = manager.get_effective_config(
            "test_family",
            cli_overrides={"llm": {"seed": 99999, "temperature": 0.0}}
        )

        assert "cli_overrides" in effective
        assert effective["cli_overrides"]["llm"]["seed"] == 99999
        assert effective["cli_overrides"]["llm"]["temperature"] == 0.0


class TestStrictSchemaEnforcement:
    """Test that unknown config keys fail fast (pydantic extra=forbid)."""

    def test_unknown_llm_key_fails(self):
        """Unknown key in LLMConfig should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            LLMConfig(
                provider="openai",
                model="gpt-4",
                unknown_field="should_fail"
            )

        error_msg = str(exc_info.value)
        assert "Extra inputs are not permitted" in error_msg or "extra fields not permitted" in error_msg.lower()

    def test_unknown_vector_db_key_fails(self):
        """Unknown key in VectorDBConfig should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            VectorDBConfig(
                enabled=True,
                provider="chromadb",
                nonexistent_option="invalid"
            )

        error_msg = str(exc_info.value)
        assert "Extra inputs are not permitted" in error_msg or "extra fields not permitted" in error_msg.lower()

    def test_unknown_final_review_key_fails(self):
        """Unknown key in FinalReviewConfig should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            FinalReviewConfig(
                enabled=True,
                provider="anthropic",
                invalid_key="bad"
            )

        error_msg = str(exc_info.value)
        assert "Extra inputs are not permitted" in error_msg or "extra fields not permitted" in error_msg.lower()

    def test_unknown_timeouts_key_fails(self):
        """Unknown key in TimeoutsConfig should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            TimeoutsConfig(
                llm_call_seconds=120,
                fake_timeout=999
            )

        error_msg = str(exc_info.value)
        assert "Extra inputs are not permitted" in error_msg or "extra fields not permitted" in error_msg.lower()

    def test_valid_config_parses(self):
        """Valid config with all known keys should parse successfully."""
        config = LLMConfig(
            provider="openai",
            model="gpt-4",
            temperature=0.0,
            seed=12345,
            timeout_seconds=120,
            deterministic_mode=True,
        )

        assert config.provider == "openai"
        assert config.seed == 12345
        assert config.deterministic_mode is True

    def test_unknown_key_in_global_json_fails(self, temp_config_dir):
        """Unknown key in global.json should raise ValidationError when loaded."""
        # Create global.json with unknown key
        global_config_invalid = {
            "llm": {
                "provider": "openai",
                "model": "gpt-4",
                "temperature": 0.2,
                "unknown_llm_field": "should_fail"  # Unknown key
            },
            "database_path": "./data/test.db"
        }

        global_json_path = temp_config_dir / "global.json"
        global_json_path.write_text(json.dumps(global_config_invalid, indent=2))

        manager = ConfigurationManager(
            config_dir=temp_config_dir / "families",
            global_config_path=global_json_path
        )

        with pytest.raises(ValidationError) as exc_info:
            manager.load_global_config()

        error_msg = str(exc_info.value)
        assert "Extra inputs are not permitted" in error_msg or "extra fields not permitted" in error_msg.lower()

    def test_unknown_key_in_family_nuget_config_fails(self, temp_config_dir):
        """Unknown key in nested family config (nuget_config) should raise ValidationError."""
        # Create family config with unknown key in nuget_config (nested)
        family_config_invalid = {
            "family": "test_family",
            "display_name": "Test Family",
            "content_roots": ["./test-content"],
            "nuget_config": {
                "primary_package": {
                    "name": "Aspose.Test",
                    "version_strategy": "latest_stable",
                    "unknown_package_field": "should_fail"  # Unknown key in nested config
                },
                "target_frameworks": ["net8.0"]
            }
        }

        family_json_path = temp_config_dir / "families" / "test_family.json"
        family_json_path.write_text(json.dumps(family_config_invalid, indent=2))

        manager = ConfigurationManager(
            config_dir=temp_config_dir / "families",
            global_config_path=temp_config_dir / "global.json"
        )

        with pytest.raises(ValidationError) as exc_info:
            manager.load_family_config("test_family")

        error_msg = str(exc_info.value)
        assert "Extra inputs are not permitted" in error_msg or "extra fields not permitted" in error_msg.lower()

    def test_unknown_key_in_nested_config_fails(self, temp_config_dir):
        """Unknown key in nested config (e.g., runtime_validation) should fail."""
        family_config_invalid = {
            "family": "test_family",
            "display_name": "Test Family",
            "content_roots": ["./test-content"],
            "runtime_validation": {
                "enabled": True,
                "mode": "strict",
                "timeout_seconds": 30,
                "unknown_nested_field": "should_fail"  # Unknown key in nested config
            }
        }

        family_json_path = temp_config_dir / "families" / "test_family.json"
        family_json_path.write_text(json.dumps(family_config_invalid, indent=2))

        manager = ConfigurationManager(
            config_dir=temp_config_dir / "families",
            global_config_path=temp_config_dir / "global.json"
        )

        with pytest.raises(ValidationError) as exc_info:
            manager.load_family_config("test_family")

        error_msg = str(exc_info.value)
        assert "Extra inputs are not permitted" in error_msg or "extra fields not permitted" in error_msg.lower()

    def test_all_config_models_forbid_extra_fields(self):
        """Comprehensive test: all config models should forbid extra fields."""
        test_cases = [
            (LimitsConfig, {"cpu_max_percent": 90, "unknown": "bad"}),
            (GitConfig, {"enabled": True, "unknown": "bad"}),
            (GistConfig, {"enabled": True, "target_account": "test", "unknown": "bad"}),
            (TelemetryConfig, {"internal_enabled": True, "unknown": "bad"}),
            (BackfillConfig, {"auto_enabled": False, "unknown": "bad"}),
            (DriftConfig, {"enabled": True, "threshold": 0.3, "unknown": "bad"}),
            (MarkdownWriteConfig, {"allow_markdown_write": False, "unknown": "bad"}),
            (NuGetPackage, {"name": "Aspose.Zip", "unknown": "bad"}),
            (RuntimeValidationConfig, {"enabled": True, "mode": "strict", "unknown": "bad"}),
            (ContextExtractionConfig, {"enabled": True, "unknown": "bad"}),
            (GistPatternsConfig, {"enabled": True, "unknown": "bad"}),
            (DiscoveryPatternsConfig, {"unknown": "bad"}),
        ]

        for config_class, test_data in test_cases:
            with pytest.raises(ValidationError) as exc_info:
                config_class(**test_data)

            error_msg = str(exc_info.value)
            assert "Extra inputs are not permitted" in error_msg or "extra fields not permitted" in error_msg.lower(), \
                f"{config_class.__name__} should reject unknown fields but got: {error_msg}"


class TestConfigAccessTracker:
    """Test config access tracking for runtime enforcement."""

    def test_access_tracking_records_fields(self):
        """Config access tracker should record accessed fields."""
        tracker = ConfigAccessTracker()

        tracker.record_access("llm.seed")
        tracker.record_access("llm.temperature")
        tracker.record_access("vector_db.enabled")

        accesses = tracker.get_accesses()

        assert "llm.seed" in accesses
        assert "llm.temperature" in accesses
        assert "vector_db.enabled" in accesses
        assert len(accesses) == 3

    def test_access_tracking_deduplicates(self):
        """Config access tracker should deduplicate multiple accesses."""
        tracker = ConfigAccessTracker()

        tracker.record_access("llm.seed")
        tracker.record_access("llm.seed")
        tracker.record_access("llm.seed")

        accesses = tracker.get_accesses()

        assert accesses.count("llm.seed") == 1

    def test_access_tracking_exports_to_file(self, tmp_path):
        """Config access tracker should export to JSON file."""
        tracker = ConfigAccessTracker()

        tracker.record_access("llm.provider")
        tracker.record_access("timeouts.llm_call_seconds")
        tracker.record_access("final_review.enabled")

        export_path = tmp_path / "config_access.json"
        tracker.export_to_file(export_path)

        assert export_path.exists()

        with open(export_path) as f:
            data = json.load(f)

        assert data["total_accesses"] == 3
        assert "llm.provider" in data["accessed_fields"]
        assert "timeouts.llm_call_seconds" in data["accessed_fields"]
        assert "final_review.enabled" in data["accessed_fields"]

    def test_access_tracking_can_be_disabled(self):
        """Config access tracker should support disabling."""
        tracker = ConfigAccessTracker()
        tracker.disable()

        tracker.record_access("llm.seed")
        tracker.record_access("vector_db.enabled")

        accesses = tracker.get_accesses()

        assert len(accesses) == 0, "Disabled tracker should not record accesses"


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_config_dir(tmp_path):
    """
    Create temporary config directory with valid global and family configs.

    Returns:
        Path: Temporary config directory
    """
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    families_dir = config_dir / "families"
    families_dir.mkdir()

    # Create valid global.json
    global_config = {
        "llm": {
            "provider": "openai",
            "model": "gpt-4",
            "temperature": 0.2,
            "max_retries": 3,
            "retry_backoff_seconds": 5,
            "timeout_seconds": 120,
            "seed": None,
            "deterministic_mode": False,
            "enforce_timeout": True,
        },
        "vector_db": {
            "enabled": True,
            "provider": "chromadb",
            "embedding_model": "all-MiniLM-L6-v2",
            "require_on_startup": False,
            "deterministic_search": True,
            "embedding_device": "cpu",
            "drift_tolerance": 0.02,
        },
        "final_review": {
            "enabled": True,
            "provider": "anthropic",
            "model": "claude-3-5-sonnet-latest",
            "timeout_seconds": 30,
            "enforce_model": True,
        },
        "timeouts": {
            "llm_call_seconds": 120,
            "code_execution_seconds": 30,
            "per_example_seconds": 300,
            "per_phase_seconds": 1800,
            "hard_run_timeout_seconds": 2400,
            "allow_timeout_override": False,
        },
        "database_path": "./data/test.db",
        "artifact_store_path": "./artifacts",
    }

    (config_dir / "global.json").write_text(json.dumps(global_config, indent=2))

    # Create valid family config
    family_config = {
        "family": "test_family",
        "display_name": "Test Family",
        "content_roots": ["./test-content"],
    }

    (families_dir / "test_family.json").write_text(json.dumps(family_config, indent=2))

    return config_dir
