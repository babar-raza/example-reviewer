"""
Unit tests for config loading mechanism.

Tests that config values from JSON files are correctly loaded into Pydantic models,
specifically addressing the AutoLearnConfig loading bug (SR-01-B).
"""

import pytest
import json
import tempfile
from pathlib import Path
from src.core.config import (
    AutoLearnConfig,
    GlobalConfig,
    ConfigurationManager,
)


class TestAutoLearnConfigDirect:
    """Test AutoLearnConfig model directly."""

    def test_auto_learn_config_from_dict(self):
        """Test that AutoLearnConfig correctly loads from dict."""
        json_data = {
            "enabled": True,
            "use_llm": False,
            "timeout_seconds": 300
        }
        config = AutoLearnConfig(**json_data)

        assert config.enabled is True
        assert config.use_llm is False
        assert config.timeout_seconds == 300

    def test_auto_learn_config_defaults(self):
        """Test that AutoLearnConfig uses correct defaults when not specified."""
        config = AutoLearnConfig()

        assert config.enabled is False  # Default
        assert config.use_llm is False
        assert config.timeout_seconds == 300

    def test_auto_learn_config_enabled_false(self):
        """Test that AutoLearnConfig respects enabled=false."""
        json_data = {
            "enabled": False,
            "use_llm": True,
            "timeout_seconds": 600
        }
        config = AutoLearnConfig(**json_data)

        assert config.enabled is False
        assert config.use_llm is True
        assert config.timeout_seconds == 600


class TestGlobalConfigLoading:
    """Test GlobalConfig loading from JSON files."""

    def test_global_config_loads_auto_learn_enabled_true(self, tmp_path):
        """
        Regression test for SR-01-B bug.

        Verifies that when global.json has auto_learn.enabled=true,
        the GlobalConfig object correctly loads it as True (not False).
        """
        # Create temporary global.json
        global_json = tmp_path / "global.json"
        config_data = {
            "auto_learn": {
                "enabled": True,
                "use_llm": False,
                "timeout_seconds": 300
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

        # Verify auto_learn was loaded correctly
        assert global_config.auto_learn is not None
        assert isinstance(global_config.auto_learn, AutoLearnConfig)
        assert global_config.auto_learn.enabled is True
        assert global_config.auto_learn.use_llm is False
        assert global_config.auto_learn.timeout_seconds == 300

    def test_global_config_loads_auto_learn_enabled_false(self, tmp_path):
        """Test that disabled state is correctly loaded."""
        # Create temporary global.json
        global_json = tmp_path / "global.json"
        config_data = {
            "auto_learn": {
                "enabled": False,
                "use_llm": True,
                "timeout_seconds": 600
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

        # Verify auto_learn respects disabled state
        assert global_config.auto_learn.enabled is False
        assert global_config.auto_learn.use_llm is True
        assert global_config.auto_learn.timeout_seconds == 600

    def test_global_config_auto_learn_missing_uses_defaults(self, tmp_path):
        """Test that missing auto_learn section uses default values."""
        # Create temporary global.json WITHOUT auto_learn section
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

        # Verify auto_learn uses defaults when not in JSON
        assert global_config.auto_learn is not None
        assert global_config.auto_learn.enabled is False  # Default
        assert global_config.auto_learn.use_llm is False
        assert global_config.auto_learn.timeout_seconds == 300


class TestRealGlobalConfigFile:
    """Test against the actual global.json file."""

    def test_real_global_json_auto_learn_values(self):
        """
        Integration test to verify auto_learn section from real global.json.

        This directly tests the JSON content without going through ConfigurationManager
        to avoid unrelated validation errors.
        """
        # Read real global.json
        global_json_path = Path("config/global.json")
        with open(global_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Verify auto_learn section exists in JSON
        assert 'auto_learn' in data
        auto_learn_data = data['auto_learn']

        # Verify JSON has correct values (updated for SR-02-A: use_llm now true)
        assert auto_learn_data['enabled'] is True
        assert auto_learn_data['use_llm'] is True  # Changed in SR-02-A
        assert auto_learn_data['timeout_seconds'] == 300

        # Verify it loads into AutoLearnConfig correctly
        config = AutoLearnConfig(**auto_learn_data)
        assert config.enabled is True
        assert config.use_llm is True  # Changed in SR-02-A
        assert config.timeout_seconds == 300
