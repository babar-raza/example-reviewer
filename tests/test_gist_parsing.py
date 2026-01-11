"""Regression tests for gist shortcode parsing.

These tests prevent regression of the critical bug discovered in HARD-001
where mixed-format shortcodes (unquoted owner/ID, quoted filename) were
not being parsed correctly.

Run with: pytest tests/test_gist_parsing.py
"""

import sys
from pathlib import Path

# Add src and tests to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from gist_service import GistService
from fixtures.gist_fixtures import (
    MIXED_FORMAT_SHORTCODE,
    QUOTED_FORMAT_SHORTCODE,
    MIXED_NO_FILENAME,
    QUOTED_NO_FILENAME,
    COMPACT_MIXED,
    COMPACT_QUOTED,
    UNQUOTED_FORMAT,
    MALFORMED_SHORTCODES,
    EXPECTED_PARSE_RESULT,
    EXPECTED_PARSE_NO_FILE,
    REAL_GIST_OWNER,
    REAL_GIST_ID,
    REAL_GIST_FILE,
)


class TestGistShortcodeParsing:
    """Test gist shortcode parsing for all discovered formats."""

    def setup_method(self):
        """Create GistService instance for testing."""
        # Create minimal service for parsing-only tests (no database needed for parsing)
        from database import Database
        import tempfile

        temp_dir = Path(tempfile.mkdtemp())
        temp_db = temp_dir / "test.db"

        self.db = Database(temp_db)
        self.service = GistService(
            cache_dir=temp_dir / "cache",
            db=self.db
        )

    def test_mixed_format_with_filename(self):
        """Test mixed format: unquoted owner/ID, quoted filename (HARD-001 regression test)."""
        result = self.service.parse_gist_shortcode(MIXED_FORMAT_SHORTCODE)

        assert result is not None, "Mixed format shortcode should parse successfully"
        assert result == EXPECTED_PARSE_RESULT, \
            f"Expected {EXPECTED_PARSE_RESULT}, got {result}"

        owner, gist_id, filename = result
        assert owner == REAL_GIST_OWNER
        assert gist_id == REAL_GIST_ID
        assert filename == REAL_GIST_FILE

    def test_quoted_format_with_filename(self):
        """Test fully quoted format (legacy compatibility)."""
        result = self.service.parse_gist_shortcode(QUOTED_FORMAT_SHORTCODE)

        assert result is not None, "Quoted format shortcode should parse successfully"
        assert result == EXPECTED_PARSE_RESULT

    def test_mixed_format_no_filename(self):
        """Test mixed format without filename."""
        result = self.service.parse_gist_shortcode(MIXED_NO_FILENAME)

        assert result is not None, "Mixed format without filename should parse"
        assert result == EXPECTED_PARSE_NO_FILE

        owner, gist_id, filename = result
        assert owner == REAL_GIST_OWNER
        assert gist_id == REAL_GIST_ID
        assert filename is None, "Filename should be None when not provided"

    def test_quoted_format_no_filename(self):
        """Test quoted format without filename."""
        result = self.service.parse_gist_shortcode(QUOTED_NO_FILENAME)

        assert result is not None, "Quoted format without filename should parse"
        assert result == EXPECTED_PARSE_NO_FILE

    def test_compact_mixed_format(self):
        """Test mixed format without space after {{<."""
        result = self.service.parse_gist_shortcode(COMPACT_MIXED)

        assert result is not None, "Compact mixed format should parse"
        owner, gist_id, filename = result
        assert owner == REAL_GIST_OWNER
        assert gist_id == REAL_GIST_ID
        assert filename == "Example.cs"

    def test_compact_quoted_format(self):
        """Test quoted format without space after {{<."""
        result = self.service.parse_gist_shortcode(COMPACT_QUOTED)

        assert result is not None, "Compact quoted format should parse"
        owner, gist_id, filename = result
        assert owner == REAL_GIST_OWNER
        assert gist_id == REAL_GIST_ID
        assert filename == "Example.cs"

    def test_unquoted_format(self):
        """Test fully unquoted format (edge case)."""
        result = self.service.parse_gist_shortcode(UNQUOTED_FORMAT)

        # This might match the fully unquoted pattern
        assert result is not None, "Unquoted format should parse"
        owner, gist_id, filename = result
        assert owner == REAL_GIST_OWNER
        assert gist_id == REAL_GIST_ID
        # Filename might be "Example.cs" or None depending on pattern priority

    def test_malformed_shortcodes_return_none(self):
        """Test that malformed shortcodes return None."""
        for malformed in MALFORMED_SHORTCODES:
            result = self.service.parse_gist_shortcode(malformed)
            assert result is None, \
                f"Malformed shortcode should return None: {malformed}"

    def test_empty_string_returns_none(self):
        """Test that empty string returns None."""
        result = self.service.parse_gist_shortcode("")
        assert result is None

    def test_non_gist_shortcode_returns_none(self):
        """Test that non-gist Hugo shortcodes return None."""
        other_shortcodes = [
            '{{< figure src="image.jpg" >}}',
            '{{< youtube "abc123" >}}',
            '{{< code >}}',
        ]

        for shortcode in other_shortcodes:
            result = self.service.parse_gist_shortcode(shortcode)
            assert result is None, \
                f"Non-gist shortcode should return None: {shortcode}"


class TestGistShortcodeEdgeCases:
    """Test edge cases and boundary conditions."""

    def setup_method(self):
        """Create GistService instance for testing."""
        from database import Database
        import tempfile

        temp_dir = Path(tempfile.mkdtemp())
        temp_db = temp_dir / "test.db"

        self.db = Database(temp_db)
        self.service = GistService(
            cache_dir=temp_dir / "cache",
            db=self.db
        )

    def test_whitespace_variations(self):
        """Test various whitespace patterns."""
        variations = [
            '{{<  gist  aspose-com-gists  123  "file.cs"  >}}',  # Extra spaces
            '{{<gist aspose-com-gists 123 "file.cs">}}',  # No spaces
            '{{< gist\taspose-com-gists\t123\t"file.cs" >}}',  # Tabs
        ]

        for shortcode in variations:
            result = self.service.parse_gist_shortcode(shortcode)
            assert result is not None, \
                f"Should parse with whitespace variations: {shortcode}"

    def test_case_sensitivity(self):
        """Test that 'gist' keyword is case-sensitive (lowercase only)."""
        uppercase_shortcodes = [
            '{{< GIST owner id "file" >}}',
            '{{< Gist owner id "file" >}}',
        ]

        for shortcode in uppercase_shortcodes:
            result = self.service.parse_gist_shortcode(shortcode)
            # Hugo is case-sensitive for shortcodes
            assert result is None, \
                f"Uppercase 'gist' should not parse: {shortcode}"

    def test_special_characters_in_parameters(self):
        """Test gist IDs and filenames with special characters."""
        special_cases = [
            '{{< gist owner 123-abc-456 "file.cs" >}}',  # Dashes in ID
            '{{< gist owner_name 123 "file-name.cs" >}}',  # Underscores
            '{{< gist owner.name 123 "File.Name.cs" >}}',  # Dots
        ]

        for shortcode in special_cases:
            result = self.service.parse_gist_shortcode(shortcode)
            # Should parse as long as format is correct
            assert result is not None, \
                f"Should parse with special characters: {shortcode}"


if __name__ == "__main__":
    # Allow running tests directly
    import pytest
    pytest.main([__file__, "-v"])
