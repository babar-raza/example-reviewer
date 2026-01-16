"""
Test suite for configurable discovery patterns (CD-01).

Tests fence pattern detection, language normalization, and configurable validation.
"""

import pytest
import re
import time
from pathlib import Path
from unittest.mock import MagicMock

# Add src to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.config import DiscoveryPatternsConfig, GlobalConfig, FamilyConfig
from services.discovery_service import DiscoveryService
from core.database import Database


class TestDiscoveryPatternsConfig:
    """Test DiscoveryPatternsConfig model."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        config = DiscoveryPatternsConfig()

        assert config.fence_patterns == ["^```(\\w+|c#)\\s*\\n(.*?)^```"]
        assert "cs" in config.validatable_languages
        assert "csharp" in config.validatable_languages
        assert "c#" in config.validatable_languages
        assert config.normalize_to_canonical is True
        assert config.regex_timeout_seconds == 5.0

    def test_custom_values(self):
        """Test creating config with custom values."""
        config = DiscoveryPatternsConfig(
            fence_patterns=["^```(python)\\n(.*?)^```"],
            validatable_languages=["python", "py"],
            language_aliases={"python": ["py", "python3"]},
            normalize_to_canonical=False,
            regex_timeout_seconds=10.0
        )

        assert config.fence_patterns == ["^```(python)\\n(.*?)^```"]
        assert config.validatable_languages == ["python", "py"]
        assert config.normalize_to_canonical is False
        assert config.regex_timeout_seconds == 10.0

    def test_validation_constraints(self):
        """Test that field validation works."""
        # Test regex_timeout_seconds constraints
        config = DiscoveryPatternsConfig(regex_timeout_seconds=0.5)
        assert config.regex_timeout_seconds == 0.5

        # Test that values within range work
        config = DiscoveryPatternsConfig(regex_timeout_seconds=15.0)
        assert config.regex_timeout_seconds == 15.0


class TestLanguageNormalization:
    """Test language normalization functionality."""

    def test_normalize_csharp_variants(self):
        """Test that C# variants are normalized correctly."""
        config = DiscoveryPatternsConfig()
        db = MagicMock()
        service = DiscoveryService(db, global_config=GlobalConfig(discovery_patterns=config))

        # Test various C# aliases
        assert service.normalize_language("cs") == "csharp"
        assert service.normalize_language("c#") == "csharp"
        assert service.normalize_language("C#") == "csharp"
        assert service.normalize_language("csharp") == "csharp"
        assert service.normalize_language("CSharp") == "csharp"

    def test_normalize_python_variants(self):
        """Test that Python variants are normalized correctly."""
        config = DiscoveryPatternsConfig()
        db = MagicMock()
        service = DiscoveryService(db, global_config=GlobalConfig(discovery_patterns=config))

        # Test various Python aliases
        assert service.normalize_language("py") == "python"
        assert service.normalize_language("python") == "python"
        assert service.normalize_language("python3") == "python"

    def test_normalize_case_insensitive(self):
        """Test that normalization is case-insensitive."""
        config = DiscoveryPatternsConfig()
        db = MagicMock()
        service = DiscoveryService(db, global_config=GlobalConfig(discovery_patterns=config))

        assert service.normalize_language("CS") == "csharp"
        assert service.normalize_language("Cs") == "csharp"
        assert service.normalize_language("CSHARP") == "csharp"

    def test_normalize_unknown_language(self):
        """Test that unknown languages pass through unchanged."""
        config = DiscoveryPatternsConfig()
        db = MagicMock()
        service = DiscoveryService(db, global_config=GlobalConfig(discovery_patterns=config))

        assert service.normalize_language("javascript") == "javascript"
        assert service.normalize_language("rust") == "rust"

    def test_normalization_disabled(self):
        """Test that normalization can be disabled."""
        config = DiscoveryPatternsConfig(normalize_to_canonical=False)
        db = MagicMock()
        service = DiscoveryService(db, global_config=GlobalConfig(discovery_patterns=config))

        # When disabled, languages should pass through unchanged
        assert service.normalize_language("cs") == "cs"
        assert service.normalize_language("c#") == "c#"
        assert service.normalize_language("C#") == "C#"


class TestValidatableLanguages:
    """Test validatable language checking."""

    def test_validatable_languages_default(self):
        """Test default validatable languages."""
        config = DiscoveryPatternsConfig()
        db = MagicMock()
        service = DiscoveryService(db, global_config=GlobalConfig(discovery_patterns=config))

        # C# variants should be validatable
        assert service._is_validatable_language("cs")
        assert service._is_validatable_language("c#")
        assert service._is_validatable_language("C#")
        assert service._is_validatable_language("csharp")

        # Other languages should not be validatable by default
        assert not service._is_validatable_language("python")
        assert not service._is_validatable_language("javascript")

    def test_validatable_languages_custom(self):
        """Test custom validatable languages."""
        config = DiscoveryPatternsConfig(
            validatable_languages=["python"],
            language_aliases={"python": ["py", "python3"]}
        )
        db = MagicMock()
        service = DiscoveryService(db, global_config=GlobalConfig(discovery_patterns=config))

        # Python should be validatable
        assert service._is_validatable_language("python")
        assert service._is_validatable_language("py")
        assert service._is_validatable_language("python3")

        # C# should not be validatable
        assert not service._is_validatable_language("cs")
        assert not service._is_validatable_language("csharp")

    def test_validatable_case_insensitive(self):
        """Test that validatable check is case-insensitive."""
        config = DiscoveryPatternsConfig()
        db = MagicMock()
        service = DiscoveryService(db, global_config=GlobalConfig(discovery_patterns=config))

        assert service._is_validatable_language("CS")
        assert service._is_validatable_language("Cs")
        assert service._is_validatable_language("CSHARP")


class TestFencePatternCompilation:
    """Test fence pattern compilation."""

    def test_default_pattern_compiles(self):
        """Test that default pattern compiles successfully."""
        config = DiscoveryPatternsConfig()
        db = MagicMock()
        service = DiscoveryService(db, global_config=GlobalConfig(discovery_patterns=config))

        assert len(service.compiled_fence_patterns) > 0
        assert all(isinstance(p, type(re.compile(""))) for p in service.compiled_fence_patterns)

    def test_custom_pattern_compiles(self):
        """Test that custom patterns compile successfully."""
        config = DiscoveryPatternsConfig(
            fence_patterns=["^```(python)\\n(.*?)^```", "^```(js)\\n(.*?)^```"]
        )
        db = MagicMock()
        service = DiscoveryService(db, global_config=GlobalConfig(discovery_patterns=config))

        assert len(service.compiled_fence_patterns) == 2

    def test_invalid_pattern_fallback(self):
        """Test that invalid patterns are handled gracefully."""
        config = DiscoveryPatternsConfig(
            fence_patterns=["^```(invalid[", "^```(\\w+)\\n(.*?)^```"]
        )
        db = MagicMock()
        service = DiscoveryService(db, global_config=GlobalConfig(discovery_patterns=config))

        # Should compile valid pattern and skip invalid one
        assert len(service.compiled_fence_patterns) >= 1


class TestFamilyConfigOverrides:
    """Test that family config overrides global config."""

    def test_family_overrides_global(self):
        """Test that family patterns override global patterns."""
        global_config = GlobalConfig(
            discovery_patterns=DiscoveryPatternsConfig(
                validatable_languages=["cs", "csharp"]
            )
        )

        family_config = FamilyConfig(
            family="test",
            discovery_patterns=DiscoveryPatternsConfig(
                validatable_languages=["python"]
            )
        )

        db = MagicMock()
        service = DiscoveryService(
            db,
            global_config=global_config,
            family_config=family_config
        )

        # Family config should take precedence
        assert service._is_validatable_language("python")
        assert not service._is_validatable_language("cs")

    def test_global_used_when_no_family_override(self):
        """Test that global config is used when family has no override."""
        global_config = GlobalConfig(
            discovery_patterns=DiscoveryPatternsConfig(
                validatable_languages=["cs", "csharp"]
            )
        )

        family_config = FamilyConfig(
            family="test",
            discovery_patterns=None
        )

        db = MagicMock()
        service = DiscoveryService(
            db,
            global_config=global_config,
            family_config=family_config
        )

        # Global config should be used
        assert service._is_validatable_language("cs")


class TestRegexSafety:
    """Test regex safety and performance."""

    def test_large_file_performance(self):
        """Test that regex performs well on large files."""
        # Create a large markdown content (10,000 lines)
        lines = []
        for i in range(5000):
            lines.append(f"# Heading {i}\n")
            lines.append("Some text content here.\n")
            lines.append("```csharp\n")
            lines.append("var x = 1;\n")
            lines.append("```\n")

        content = "\n".join(lines)

        config = DiscoveryPatternsConfig()
        db = MagicMock()
        service = DiscoveryService(db, global_config=GlobalConfig(discovery_patterns=config))

        # Time the extraction
        start_time = time.time()
        examples = service._extract_inline_examples(content, "test.md", "test")
        elapsed = time.time() - start_time

        # Should complete in reasonable time (< 1 second for 10k lines)
        assert elapsed < 1.0, f"Regex took {elapsed}s, expected < 1s"

        # Should find examples
        assert len(examples) > 0

    def test_regex_timeout_setting(self):
        """Test that regex timeout setting is configurable."""
        config = DiscoveryPatternsConfig(regex_timeout_seconds=0.5)
        assert config.regex_timeout_seconds == 0.5

        config = DiscoveryPatternsConfig(regex_timeout_seconds=10.0)
        assert config.regex_timeout_seconds == 10.0


class TestIntegration:
    """Integration tests for discovery patterns."""

    def test_end_to_end_normalization(self):
        """Test end-to-end language normalization in discovery."""
        # Create test markdown content with various C# fence tags
        content = """
# Test File

Some text here.

```c#
var x = 1;
Console.WriteLine(x);
```

More text.

```cs
var y = 2;
Console.WriteLine(y);
```

And more.

```C#
var z = 3;
Console.WriteLine(z);
```
"""

        config = DiscoveryPatternsConfig()
        db = MagicMock()
        service = DiscoveryService(db, global_config=GlobalConfig(discovery_patterns=config))

        examples = service._extract_inline_examples(content, "test.md", "test")

        # Should find all 3 examples
        assert len(examples) == 3

        # All should be normalized to 'csharp'
        for example in examples:
            assert example.language == "csharp"

    def test_config_loading_from_dict(self):
        """Test that config can be loaded from dictionary."""
        config_dict = {
            "fence_patterns": ["^```(\\w+)\\n(.*?)^```"],
            "validatable_languages": ["python"],
            "language_aliases": {"python": ["py"]},
            "normalize_to_canonical": True,
            "regex_timeout_seconds": 3.0
        }

        config = DiscoveryPatternsConfig(**config_dict)

        assert config.fence_patterns == ["^```(\\w+)\\n(.*?)^```"]
        assert config.validatable_languages == ["python"]
        assert config.regex_timeout_seconds == 3.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
