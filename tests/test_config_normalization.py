"""Tests for family config normalization and validation."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config_utils import normalize_family_config, validate_family_config


class TestConfigNormalization:
    """Test config normalization from legacy to canonical format."""

    def test_legacy_format_conversion(self):
        """Test conversion of legacy flat format to canonical."""
        legacy_config = {
            "name": "test",
            "package_id": "Newtonsoft.Json",
            "version": "latest_stable",
            "target_framework": "net6.0",
            "skip_patterns": [],
            "ollama_enabled": False
        }

        normalized = normalize_family_config(legacy_config)

        assert normalized['family'] == 'test'
        assert normalized['nuget_config']['primary_package']['name'] == 'Newtonsoft.Json'
        assert normalized['nuget_config']['primary_package']['version_strategy'] == 'latest_stable'
        assert normalized['nuget_config']['target_frameworks'] == ['net6.0']
        assert 'code_defaults' in normalized
        assert 'default_usings' in normalized['code_defaults']

    def test_canonical_format_preserved(self):
        """Test that canonical format is preserved with defaults."""
        canonical_config = {
            "family": "zip",
            "display_name": "Aspose.ZIP",
            "nuget_config": {
                "primary_package": {
                    "name": "Aspose.Zip",
                    "version_strategy": "latest_stable"
                },
                "target_frameworks": ["net8.0"]
            },
            "code_defaults": {
                "default_usings": ["Aspose.Zip"]
            }
        }

        normalized = normalize_family_config(canonical_config)

        assert normalized['family'] == 'zip'
        assert normalized['display_name'] == 'Aspose.ZIP'
        assert normalized['nuget_config']['primary_package']['name'] == 'Aspose.Zip'
        assert normalized['code_defaults']['default_usings'] == ['Aspose.Zip']
        # Defaults applied
        assert 'patterns' in normalized
        assert 'non_existent_apis' in normalized

    def test_pinned_version_conversion(self):
        """Test conversion of pinned version format."""
        legacy_config = {
            "name": "words",
            "package_id": "Aspose.Words",
            "version": "24.1.0",  # Specific version
            "target_framework": "net8.0"
        }

        normalized = normalize_family_config(legacy_config)

        assert normalized['nuget_config']['primary_package']['version_strategy'] == 'pinned'
        assert normalized['nuget_config']['primary_package']['pinned_version'] == '24.1.0'

    def test_target_frameworks_array_conversion(self):
        """Test singular target_framework converted to array."""
        legacy_config = {
            "name": "test",
            "package_id": "Test.Package",
            "target_framework": "net6.0"
        }

        normalized = normalize_family_config(legacy_config)

        assert normalized['nuget_config']['target_frameworks'] == ['net6.0']
        assert isinstance(normalized['nuget_config']['target_frameworks'], list)

    def test_additional_packages_preserved(self):
        """Test that additional_packages are preserved."""
        config = {
            "family": "words",
            "nuget_config": {
                "primary_package": {
                    "name": "Aspose.Words",
                    "version_strategy": "latest_stable"
                },
                "additional_packages": [
                    {"name": "System.Drawing.Common", "version": "8.0.0"}
                ],
                "target_frameworks": ["net8.0"]
            }
        }

        normalized = normalize_family_config(config)

        assert len(normalized['nuget_config']['additional_packages']) == 1
        assert normalized['nuget_config']['additional_packages'][0]['name'] == 'System.Drawing.Common'

    def test_default_usings_preserved(self):
        """Test that default_usings are preserved."""
        config = {
            "family": "zip",
            "nuget_config": {
                "primary_package": {
                    "name": "Aspose.Zip",
                    "version_strategy": "latest_stable"
                },
                "target_frameworks": ["net8.0"]
            },
            "code_defaults": {
                "default_usings": [
                    "Aspose.Zip",
                    "Aspose.Zip.Saving"
                ]
            }
        }

        normalized = normalize_family_config(config)

        assert normalized['code_defaults']['default_usings'] == [
            "Aspose.Zip",
            "Aspose.Zip.Saving"
        ]

    def test_empty_config_gets_defaults(self):
        """Test that minimal config gets sensible defaults."""
        minimal_config = {
            "family": "test"
        }

        normalized = normalize_family_config(minimal_config)

        assert normalized['family'] == 'test'
        assert normalized['code_defaults']['default_usings'] == []
        assert normalized['patterns'] == []
        assert normalized['non_existent_apis'] == []


class TestConfigValidation:
    """Test config validation rules."""

    def test_valid_canonical_config(self):
        """Test that valid canonical config passes validation."""
        config = {
            "family": "zip",
            "nuget_config": {
                "primary_package": {
                    "name": "Aspose.Zip",
                    "version_strategy": "latest_stable"
                },
                "target_frameworks": ["net8.0"]
            },
            "code_defaults": {
                "default_usings": []
            }
        }

        is_valid, errors = validate_family_config(config)

        assert is_valid
        assert len(errors) == 0

    def test_missing_family(self):
        """Test that missing 'family' field fails validation."""
        config = {
            "nuget_config": {
                "primary_package": {
                    "name": "Test.Package",
                    "version_strategy": "latest_stable"
                },
                "target_frameworks": ["net8.0"]
            }
        }

        is_valid, errors = validate_family_config(config)

        assert not is_valid
        assert any("family" in err.lower() for err in errors)

    def test_invalid_version_strategy(self):
        """Test that invalid version_strategy fails validation."""
        config = {
            "family": "test",
            "nuget_config": {
                "primary_package": {
                    "name": "Test.Package",
                    "version_strategy": "invalid_strategy"
                },
                "target_frameworks": ["net8.0"]
            }
        }

        is_valid, errors = validate_family_config(config)

        assert not is_valid
        assert any("version_strategy" in err for err in errors)

    def test_pinned_without_version(self):
        """Test that pinned version_strategy without pinned_version fails."""
        config = {
            "family": "test",
            "nuget_config": {
                "primary_package": {
                    "name": "Test.Package",
                    "version_strategy": "pinned"
                    # Missing pinned_version
                },
                "target_frameworks": ["net8.0"]
            }
        }

        is_valid, errors = validate_family_config(config)

        assert not is_valid
        assert any("pinned_version" in err for err in errors)

    def test_empty_target_frameworks(self):
        """Test that empty target_frameworks fails validation."""
        config = {
            "family": "test",
            "nuget_config": {
                "primary_package": {
                    "name": "Test.Package",
                    "version_strategy": "latest_stable"
                },
                "target_frameworks": []  # Empty
            }
        }

        is_valid, errors = validate_family_config(config)

        assert not is_valid
        assert any("target_frameworks" in err for err in errors)

    def test_invalid_family_name_format(self):
        """Test that invalid family name format fails validation."""
        config = {
            "family": "Invalid Name With Spaces",
            "nuget_config": {
                "primary_package": {
                    "name": "Test.Package",
                    "version_strategy": "latest_stable"
                },
                "target_frameworks": ["net8.0"]
            }
        }

        is_valid, errors = validate_family_config(config)

        assert not is_valid
        assert any("family name" in err.lower() for err in errors)

    def test_uppercase_family_name_fails(self):
        """Test that uppercase family names fail validation."""
        config = {
            "family": "TEST",  # Should be lowercase
            "nuget_config": {
                "primary_package": {
                    "name": "Test.Package",
                    "version_strategy": "latest_stable"
                },
                "target_frameworks": ["net8.0"]
            }
        }

        is_valid, errors = validate_family_config(config)

        assert not is_valid
        assert any("lowercase" in err for err in errors)
