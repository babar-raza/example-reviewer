"""
Test suite for configurable gist pattern detection (CD-03).

Tests gist extraction configuration, pattern compilation, owner filtering, and multi-platform support.
"""

import pytest
import re
from pathlib import Path
from unittest.mock import MagicMock

# Add src to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.config import GistPatternsConfig, DiscoveryPatternsConfig, GlobalConfig, FamilyConfig
from services.discovery_service import DiscoveryService
from core.database import Database


class TestGistPatternsConfig:
    """Test GistPatternsConfig model."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        config = GistPatternsConfig()

        assert config.enabled is True
        assert len(config.shortcode_patterns) == 1
        assert len(config.script_patterns) == 1
        assert config.allowed_owners == []
        assert config.blocked_owners == []

    def test_custom_values(self):
        """Test creating config with custom values."""
        config = GistPatternsConfig(
            enabled=False,
            shortcode_patterns=[r'\[gist:([^/]+)/([^/]+)\]'],
            script_patterns=[r'<script.*gitlab.*>'],
            allowed_owners=["test-owner"],
            blocked_owners=["spam-owner"]
        )

        assert config.enabled is False
        assert len(config.shortcode_patterns) == 1
        assert config.allowed_owners == ["test-owner"]
        assert config.blocked_owners == ["spam-owner"]

    def test_default_github_shortcode_pattern(self):
        """Test that default shortcode pattern matches Hugo gist syntax."""
        config = GistPatternsConfig()
        patterns = config.compile_shortcode_patterns()

        assert len(patterns) > 0

        # Test standard Hugo gist shortcode
        test_line = '{{< gist username abc123def >}}'
        match = patterns[0].search(test_line)

        assert match is not None
        assert match.group(1) == "username"
        assert match.group(2) == "abc123def"

    def test_default_github_script_pattern(self):
        """Test that default script pattern matches GitHub gist script tags."""
        config = GistPatternsConfig()
        patterns = config.compile_script_patterns()

        assert len(patterns) > 0

        # Test GitHub gist script tag
        test_line = '<script src="https://gist.github.com/username/abc123def.js"></script>'
        match = patterns[0].search(test_line)

        assert match is not None
        assert match.group(1) == "username"
        assert match.group(2) == "abc123def"


class TestPatternCompilation:
    """Test pattern compilation with error handling."""

    def test_compile_valid_shortcode_patterns(self):
        """Test that valid patterns compile successfully."""
        config = GistPatternsConfig(
            shortcode_patterns=[
                r'\{\{<\s*gist\s+([^\s]+)\s+([^\s]+)\s*>\}\}',
                r'\[gist:([^/]+)/([^/]+)\]'
            ]
        )

        patterns = config.compile_shortcode_patterns()
        assert len(patterns) == 2
        assert all(isinstance(p, type(re.compile(""))) for p in patterns)

    def test_compile_valid_script_patterns(self):
        """Test that valid script patterns compile successfully."""
        config = GistPatternsConfig(
            script_patterns=[
                r'<script\s+src=["\']https://gist\.github\.com/([^/]+)/([^.]+)\.js["\']',
                r'<script\s+src=["\']https://gitlab\.com/([^/]+)/-/snippets/([^/]+)\.js["\']'
            ]
        )

        patterns = config.compile_script_patterns()
        assert len(patterns) == 2

    def test_invalid_pattern_handling(self):
        """Test that invalid patterns are skipped gracefully."""
        config = GistPatternsConfig(
            shortcode_patterns=[
                r'[invalid[regex',  # Invalid regex
                r'\{\{<\s*gist\s+([^\s]+)\s+([^\s]+)\s*>\}\}'  # Valid regex
            ]
        )

        patterns = config.compile_shortcode_patterns()
        # Should compile the valid one and skip the invalid
        assert len(patterns) == 1

    def test_all_invalid_patterns(self):
        """Test behavior when all patterns are invalid."""
        config = GistPatternsConfig(
            shortcode_patterns=['[invalid[', '(unclosed']
        )

        patterns = config.compile_shortcode_patterns()
        # Should return empty list, fallback handled in DiscoveryService
        assert len(patterns) == 0


class TestOwnerFiltering:
    """Test owner filtering logic."""

    def test_allowed_owners_filter(self):
        """Test that allowed_owners whitelist works."""
        config = GistPatternsConfig(
            allowed_owners=["aspose-com-gists", "aspose-zip"]
        )

        # Allowed owners should pass
        should_include, reason = config.should_include_owner("aspose-com-gists")
        assert should_include is True
        assert reason is None

        should_include, reason = config.should_include_owner("aspose-zip")
        assert should_include is True
        assert reason is None

        # Non-allowed owners should fail
        should_include, reason = config.should_include_owner("random-user")
        assert should_include is False
        assert "not_in_allowed_owners" in reason

    def test_blocked_owners_filter(self):
        """Test that blocked_owners blacklist works."""
        config = GistPatternsConfig(
            blocked_owners=["spam-account", "blocked-user"]
        )

        # Blocked owners should fail
        should_include, reason = config.should_include_owner("spam-account")
        assert should_include is False
        assert "blocked_owner" in reason

        # Non-blocked owners should pass (empty allowed_owners = all allowed)
        should_include, reason = config.should_include_owner("valid-user")
        assert should_include is True
        assert reason is None

    def test_blocked_takes_precedence(self):
        """Test that blocked list takes precedence over allowed list."""
        config = GistPatternsConfig(
            allowed_owners=["user1", "user2"],
            blocked_owners=["user2"]  # user2 is both allowed and blocked
        )

        # user1 should be allowed
        should_include, reason = config.should_include_owner("user1")
        assert should_include is True

        # user2 should be blocked (blocked takes precedence)
        should_include, reason = config.should_include_owner("user2")
        assert should_include is False
        assert "blocked_owner" in reason

    def test_empty_filters_allow_all(self):
        """Test that empty filters allow all owners."""
        config = GistPatternsConfig(
            allowed_owners=[],
            blocked_owners=[]
        )

        # Any owner should be allowed
        should_include, reason = config.should_include_owner("any-user")
        assert should_include is True
        assert reason is None


class TestGistExtraction:
    """Test gist extraction with configurable patterns."""

    def test_default_gist_shortcode_extraction(self, tmp_path):
        """Test extraction with default shortcode pattern."""
        db = Database(str(tmp_path / "test.db"))
        db.initialize_schema()

        global_config = GlobalConfig()
        service = DiscoveryService(db, global_config=global_config)

        content = """# Test File

Some text here.

{{< gist aspose-com-gists abc123def "example.cs" >}}

More text.
"""

        examples = service._extract_gist_examples(content, "test.md", "test")

        assert len(examples) == 1
        assert examples[0].gist.owner == "aspose-com-gists"
        assert examples[0].gist.gist_id == "abc123def"
        assert examples[0].gist.filename == "example.cs"

    def test_default_gist_script_extraction(self, tmp_path):
        """Test extraction with default script pattern."""
        db = Database(str(tmp_path / "test.db"))
        db.initialize_schema()

        global_config = GlobalConfig()
        service = DiscoveryService(db, global_config=global_config)

        content = """# Test File

<script src="https://gist.github.com/aspose-com-gists/abc123def.js?file=example.cs"></script>
"""

        examples = service._extract_gist_examples(content, "test.md", "test")

        assert len(examples) == 1
        assert examples[0].gist.owner == "aspose-com-gists"
        assert examples[0].gist.gist_id == "abc123def"
        assert examples[0].gist.filename == "example.cs"

    def test_custom_shortcode_pattern(self, tmp_path):
        """Test extraction with custom shortcode pattern."""
        db = Database(str(tmp_path / "test.db"))
        db.initialize_schema()

        custom_config = DiscoveryPatternsConfig(
            gist_extraction=GistPatternsConfig(
                shortcode_patterns=[r'\[gist:([^/]+)/([^/]+)(?:/([^\]]+))?\]']
            )
        )

        global_config = GlobalConfig(discovery_patterns=custom_config)
        service = DiscoveryService(db, global_config=global_config)

        content = """# Test File

[gist:username/abc123def/example.cs]
"""

        examples = service._extract_gist_examples(content, "test.md", "test")

        assert len(examples) == 1
        assert examples[0].gist.owner == "username"
        assert examples[0].gist.gist_id == "abc123def"
        assert examples[0].gist.filename == "example.cs"

    def test_multiple_gist_patterns(self, tmp_path):
        """Test that multiple patterns can coexist."""
        db = Database(str(tmp_path / "test.db"))
        db.initialize_schema()

        custom_config = DiscoveryPatternsConfig(
            gist_extraction=GistPatternsConfig(
                shortcode_patterns=[
                    r'\{\{<\s*gist\s+([^\s]+)\s+([^\s]+)(?:\s+["\']?([^"\'>\s]+)["\']?)?\s*>\}\}',
                    r'\[gist:([^/]+)/([^/]+)(?:/([^\]]+))?\]'
                ]
            )
        )

        global_config = GlobalConfig(discovery_patterns=custom_config)
        service = DiscoveryService(db, global_config=global_config)

        content = """# Test File

{{< gist owner1 id1 "file1.cs" >}}

[gist:owner2/id2/file2.cs]
"""

        examples = service._extract_gist_examples(content, "test.md", "test")

        assert len(examples) == 2
        assert examples[0].gist.owner == "owner1"
        assert examples[1].gist.owner == "owner2"


class TestGistExtractionDisabling:
    """Test disabling gist extraction."""

    def test_gist_extraction_disabled(self, tmp_path):
        """Test that gists are not extracted when disabled."""
        db = Database(str(tmp_path / "test.db"))
        db.initialize_schema()

        custom_config = DiscoveryPatternsConfig(
            gist_extraction=GistPatternsConfig(enabled=False)
        )

        global_config = GlobalConfig(discovery_patterns=custom_config)
        service = DiscoveryService(db, global_config=global_config)

        content = """# Test File

{{< gist aspose-com-gists abc123def "example.cs" >}}
"""

        examples = service._extract_gist_examples(content, "test.md", "test")

        # Should return empty list when disabled
        assert len(examples) == 0

    def test_gist_patterns_not_compiled_when_disabled(self, tmp_path):
        """Test that patterns are not compiled when extraction is disabled."""
        db = Database(str(tmp_path / "test.db"))
        db.initialize_schema()

        custom_config = DiscoveryPatternsConfig(
            gist_extraction=GistPatternsConfig(enabled=False)
        )

        global_config = GlobalConfig(discovery_patterns=custom_config)
        service = DiscoveryService(db, global_config=global_config)

        # Compiled pattern lists should be empty
        assert len(service.compiled_gist_shortcode_patterns) == 0
        assert len(service.compiled_gist_script_patterns) == 0


class TestOwnerFilteringIntegration:
    """Test owner filtering in discovery pipeline."""

    def test_allowed_owners_in_discovery(self, tmp_path):
        """Test that allowed_owners filter works in discovery."""
        db = Database(str(tmp_path / "test.db"))
        db.initialize_schema()

        custom_config = DiscoveryPatternsConfig(
            gist_extraction=GistPatternsConfig(
                allowed_owners=["aspose-com-gists"]
            )
        )

        global_config = GlobalConfig(discovery_patterns=custom_config)
        service = DiscoveryService(db, global_config=global_config)

        content = """# Test File

{{< gist aspose-com-gists abc123 "file1.cs" >}}
{{< gist random-user xyz789 "file2.cs" >}}
"""

        examples = service._extract_gist_examples(content, "test.md", "test")

        # Only the allowed owner should be extracted
        assert len(examples) == 1
        assert examples[0].gist.owner == "aspose-com-gists"

        # Check that filtered gist was tracked
        stats = service.get_filter_stats()
        assert stats['filtered_gists'] == 1

    def test_blocked_owners_in_discovery(self, tmp_path):
        """Test that blocked_owners filter works in discovery."""
        db = Database(str(tmp_path / "test.db"))
        db.initialize_schema()

        custom_config = DiscoveryPatternsConfig(
            gist_extraction=GistPatternsConfig(
                blocked_owners=["spam-account"]
            )
        )

        global_config = GlobalConfig(discovery_patterns=custom_config)
        service = DiscoveryService(db, global_config=global_config)

        content = """# Test File

{{< gist valid-user abc123 "file1.cs" >}}
{{< gist spam-account xyz789 "file2.cs" >}}
"""

        examples = service._extract_gist_examples(content, "test.md", "test")

        # Only the non-blocked owner should be extracted
        assert len(examples) == 1
        assert examples[0].gist.owner == "valid-user"

        # Check that filtered gist was tracked
        stats = service.get_filter_stats()
        assert stats['filtered_gists'] == 1


class TestMultiPlatformPatterns:
    """Test multi-platform gist pattern support."""

    def test_gitlab_snippet_pattern(self, tmp_path):
        """Test that GitLab snippet pattern works."""
        db = Database(str(tmp_path / "test.db"))
        db.initialize_schema()

        custom_config = DiscoveryPatternsConfig(
            gist_extraction=GistPatternsConfig(
                script_patterns=[
                    r'<script\s+src=["\']https://gitlab\.com/([^/]+)/-/snippets/([^/]+)\.js["\']'
                ]
            )
        )

        global_config = GlobalConfig(discovery_patterns=custom_config)
        service = DiscoveryService(db, global_config=global_config)

        content = """# Test File

<script src="https://gitlab.com/username/-/snippets/123456.js"></script>
"""

        examples = service._extract_gist_examples(content, "test.md", "test")

        assert len(examples) == 1
        assert examples[0].gist.owner == "username"
        assert examples[0].gist.gist_id == "123456"

    def test_github_and_gitlab_patterns_coexist(self, tmp_path):
        """Test that GitHub and GitLab patterns can coexist."""
        db = Database(str(tmp_path / "test.db"))
        db.initialize_schema()

        custom_config = DiscoveryPatternsConfig(
            gist_extraction=GistPatternsConfig(
                script_patterns=[
                    r'<script\s+src=["\']https://gist\.github\.com/([^/]+)/([^.]+)\.js(?:\?file=([^"\']+))?["\']',
                    r'<script\s+src=["\']https://gitlab\.com/([^/]+)/-/snippets/([^/]+)\.js["\']'
                ]
            )
        )

        global_config = GlobalConfig(discovery_patterns=custom_config)
        service = DiscoveryService(db, global_config=global_config)

        content = """# Test File

<script src="https://gist.github.com/github-user/abc123.js"></script>
<script src="https://gitlab.com/gitlab-user/-/snippets/456789.js"></script>
"""

        examples = service._extract_gist_examples(content, "test.md", "test")

        assert len(examples) == 2
        assert examples[0].gist.owner == "github-user"
        assert examples[1].gist.owner == "gitlab-user"


class TestFamilyConfigOverrides:
    """Test that family config can override global gist patterns."""

    def test_family_overrides_global_gist_config(self, tmp_path):
        """Test that family gist config overrides global config."""
        db = Database(str(tmp_path / "test.db"))
        db.initialize_schema()

        global_config = GlobalConfig(
            discovery_patterns=DiscoveryPatternsConfig(
                gist_extraction=GistPatternsConfig(
                    allowed_owners=[]  # Global allows all
                )
            )
        )

        family_config = FamilyConfig(
            family="zip",
            discovery_patterns=DiscoveryPatternsConfig(
                gist_extraction=GistPatternsConfig(
                    allowed_owners=["aspose-zip"]  # Family restricts to specific owner
                )
            )
        )

        service = DiscoveryService(
            db,
            global_config=global_config,
            family_config=family_config
        )

        content = """# Test File

{{< gist aspose-zip abc123 "file1.cs" >}}
{{< gist other-user xyz789 "file2.cs" >}}
"""

        examples = service._extract_gist_examples(content, "test.md", "zip")

        # Family config should take precedence
        assert len(examples) == 1
        assert examples[0].gist.owner == "aspose-zip"


class TestStatisticsTracking:
    """Test that gist filtering statistics are tracked."""

    def test_filtered_gists_tracked(self, tmp_path):
        """Test that filtered gists are counted in statistics."""
        db = Database(str(tmp_path / "test.db"))
        db.initialize_schema()

        custom_config = DiscoveryPatternsConfig(
            gist_extraction=GistPatternsConfig(
                allowed_owners=["allowed-user"]
            )
        )

        global_config = GlobalConfig(discovery_patterns=custom_config)
        service = DiscoveryService(db, global_config=global_config)

        content = """# Test File

{{< gist allowed-user abc123 >}}
{{< gist blocked1 xyz789 >}}
{{< gist blocked2 def456 >}}
"""

        examples = service._extract_gist_examples(content, "test.md", "test")

        assert len(examples) == 1

        stats = service.get_filter_stats()
        assert stats['filtered_gists'] == 2

    def test_filtered_gists_in_discover_family_stats(self, tmp_path):
        """Test that filtered_gists appears in discover_family stats."""
        db = Database(str(tmp_path / "test.db"))
        db.initialize_schema()

        # Create a temporary markdown file
        test_file = tmp_path / "test.md"
        test_file.write_text("""# Test

{{< gist allowed-user abc123 >}}
{{< gist blocked-user xyz789 >}}
""")

        custom_config = DiscoveryPatternsConfig(
            gist_extraction=GistPatternsConfig(
                allowed_owners=["allowed-user"]
            )
        )

        family_config = FamilyConfig(
            family="test",
            content_roots=[str(tmp_path)],
            discovery_patterns=custom_config
        )

        service = DiscoveryService(db)

        stats = service.discover_family("test", family_config)

        # Check that filtered_gists key exists and has correct count
        assert 'filtered_gists' in stats
        assert stats['filtered_gists'] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
