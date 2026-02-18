"""
Unit tests for pattern retirement policy configuration.

Tests that retirement policy configuration is correctly loaded and validated,
following the same patterns as AutoLearnConfig (SR-01-B fix).
"""

import pytest
import json
import tempfile
from pathlib import Path
from src.core.config import (
    RetirementPolicyConfig,
    GlobalConfig,
    ConfigurationManager,
)


class TestRetirementPolicyConfigDirect:
    """Test RetirementPolicyConfig model directly."""

    def test_retirement_config_defaults(self):
        """Test default retirement policy values."""
        config = RetirementPolicyConfig()
        assert config.enabled == False
        assert config.min_attempts == 10
        assert config.max_success_rate == 0.1
        assert config.max_age_days == 90
        assert config.dry_run == True

    def test_retirement_config_from_dict(self):
        """Test loading retirement policy from dict."""
        data = {
            "enabled": True,
            "min_attempts": 20,
            "max_success_rate": 0.05,
            "max_age_days": 60,
            "dry_run": False
        }
        config = RetirementPolicyConfig(**data)
        assert config.enabled == True
        assert config.min_attempts == 20
        assert config.max_success_rate == 0.05
        assert config.max_age_days == 60
        assert config.dry_run == False

    def test_retirement_config_validation_min_attempts(self):
        """Test min_attempts validation (must be >= 1)."""
        with pytest.raises(ValueError):
            RetirementPolicyConfig(min_attempts=0)

        with pytest.raises(ValueError):
            RetirementPolicyConfig(min_attempts=-5)

    def test_retirement_config_validation_max_success_rate(self):
        """Test max_success_rate validation (must be in [0, 1])."""
        # Test upper bound
        with pytest.raises(ValueError):
            RetirementPolicyConfig(max_success_rate=1.5)

        with pytest.raises(ValueError):
            RetirementPolicyConfig(max_success_rate=2.0)

        # Test lower bound
        with pytest.raises(ValueError):
            RetirementPolicyConfig(max_success_rate=-0.1)

        # Test valid boundaries
        config_zero = RetirementPolicyConfig(max_success_rate=0.0)
        assert config_zero.max_success_rate == 0.0

        config_one = RetirementPolicyConfig(max_success_rate=1.0)
        assert config_one.max_success_rate == 1.0

    def test_retirement_config_validation_max_age_days(self):
        """Test max_age_days validation (must be >= 1)."""
        with pytest.raises(ValueError):
            RetirementPolicyConfig(max_age_days=0)

        with pytest.raises(ValueError):
            RetirementPolicyConfig(max_age_days=-30)


class TestGlobalConfigRetirementLoading:
    """Test GlobalConfig loading retirement policy from JSON files."""

    def test_global_config_loads_retirement_enabled_true(self, tmp_path):
        """
        Test that when global.json has pattern_retirement.enabled=true,
        the GlobalConfig object correctly loads it as True.
        """
        # Create temporary global.json
        global_json = tmp_path / "global.json"
        config_data = {
            "pattern_retirement": {
                "enabled": True,
                "min_attempts": 15,
                "max_success_rate": 0.08,
                "max_age_days": 120,
                "dry_run": False
            }
        }

        with open(global_json, 'w', encoding='utf-8') as f:
            json.dump(config_data, f)

        # Load config
        config_mgr = ConfigurationManager(
            config_dir=tmp_path / "families",
            global_config_path=global_json
        )
        global_config = config_mgr.load_global_config()

        # Verify pattern_retirement was loaded correctly
        assert global_config.pattern_retirement is not None
        assert isinstance(global_config.pattern_retirement, RetirementPolicyConfig)
        assert global_config.pattern_retirement.enabled is True
        assert global_config.pattern_retirement.min_attempts == 15
        assert global_config.pattern_retirement.max_success_rate == 0.08
        assert global_config.pattern_retirement.max_age_days == 120
        assert global_config.pattern_retirement.dry_run is False

    def test_global_config_loads_retirement_enabled_false(self, tmp_path):
        """Test that disabled state is correctly loaded."""
        # Create temporary global.json
        global_json = tmp_path / "global.json"
        config_data = {
            "pattern_retirement": {
                "enabled": False,
                "min_attempts": 5,
                "max_success_rate": 0.2,
                "max_age_days": 30,
                "dry_run": True
            }
        }

        with open(global_json, 'w', encoding='utf-8') as f:
            json.dump(config_data, f)

        # Load config
        config_mgr = ConfigurationManager(
            config_dir=tmp_path / "families",
            global_config_path=global_json
        )
        global_config = config_mgr.load_global_config()

        # Verify pattern_retirement respects disabled state
        assert global_config.pattern_retirement.enabled is False
        assert global_config.pattern_retirement.min_attempts == 5
        assert global_config.pattern_retirement.max_success_rate == 0.2
        assert global_config.pattern_retirement.max_age_days == 30
        assert global_config.pattern_retirement.dry_run is True

    def test_global_config_retirement_missing_uses_defaults(self, tmp_path):
        """Test that missing pattern_retirement section uses default values."""
        # Create temporary global.json WITHOUT pattern_retirement section
        global_json = tmp_path / "global.json"
        config_data = {
            "llm": {
                "provider": "openai",
                "model": "gpt-4o-mini"
            }
        }

        with open(global_json, 'w', encoding='utf-8') as f:
            json.dump(config_data, f)

        # Load config
        config_mgr = ConfigurationManager(
            config_dir=tmp_path / "families",
            global_config_path=global_json
        )
        global_config = config_mgr.load_global_config()

        # Verify pattern_retirement uses defaults when not in JSON
        assert global_config.pattern_retirement is not None
        assert global_config.pattern_retirement.enabled is False  # Default
        assert global_config.pattern_retirement.min_attempts == 10
        assert global_config.pattern_retirement.max_success_rate == 0.1
        assert global_config.pattern_retirement.max_age_days == 90
        assert global_config.pattern_retirement.dry_run is True


class TestRealGlobalConfigFile:
    """Test against the actual global.json file."""

    def test_real_global_json_retirement_values(self):
        """
        Integration test to verify pattern_retirement section from real global.json.
        """
        # Read real global.json
        global_json_path = Path("config/global.json")
        with open(global_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Verify pattern_retirement section exists in JSON
        assert 'pattern_retirement' in data
        retirement_data = data['pattern_retirement']

        # Verify JSON has correct values (retirement enabled for production)
        assert retirement_data['enabled'] is True
        assert retirement_data['min_attempts'] == 10
        assert retirement_data['max_success_rate'] == 0.1
        assert retirement_data['max_age_days'] == 90
        assert retirement_data['dry_run'] is False

        # Verify it loads into RetirementPolicyConfig correctly
        config = RetirementPolicyConfig(**retirement_data)
        assert config.enabled is True
        assert config.min_attempts == 10
        assert config.max_success_rate == 0.1
        assert config.max_age_days == 90
        assert config.dry_run is False

    def test_real_global_config_manager_loads_retirement(self):
        """
        Full integration test using ConfigurationManager with real files.
        """
        config_mgr = ConfigurationManager(
            config_dir=Path('config/families'),
            global_config_path=Path('config/global.json')
        )
        global_config = config_mgr.load_global_config()

        # Verify pattern_retirement is accessible and correct
        assert hasattr(global_config, 'pattern_retirement')
        assert isinstance(global_config.pattern_retirement, RetirementPolicyConfig)
        assert global_config.pattern_retirement.enabled is True
        assert global_config.pattern_retirement.min_attempts == 10
        assert global_config.pattern_retirement.max_success_rate == 0.1
        assert global_config.pattern_retirement.max_age_days == 90
        assert global_config.pattern_retirement.dry_run is False


class TestRetirementPolicyEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_retirement_config_extreme_values(self):
        """Test extreme but valid configuration values."""
        config = RetirementPolicyConfig(
            enabled=True,
            min_attempts=1,  # Minimum allowed
            max_success_rate=0.0,  # Minimum allowed (retire everything)
            max_age_days=1,  # Minimum allowed (retire after 1 day)
            dry_run=False
        )
        assert config.enabled is True
        assert config.min_attempts == 1
        assert config.max_success_rate == 0.0
        assert config.max_age_days == 1
        assert config.dry_run is False

    def test_retirement_config_max_success_rate_boundary(self):
        """Test max_success_rate boundary at 1.0 (never retire)."""
        config = RetirementPolicyConfig(max_success_rate=1.0)
        assert config.max_success_rate == 1.0

    def test_retirement_config_large_values(self):
        """Test large but reasonable values."""
        config = RetirementPolicyConfig(
            min_attempts=1000,
            max_age_days=365
        )
        assert config.min_attempts == 1000
        assert config.max_age_days == 365

    def test_retirement_config_forbids_extra_fields(self):
        """Test that extra fields are rejected (Pydantic extra='forbid')."""
        with pytest.raises(ValueError):
            RetirementPolicyConfig(
                enabled=True,
                unknown_field="value"
            )
