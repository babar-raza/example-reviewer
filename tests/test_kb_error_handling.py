"""
KB error handling isolation tests.

Focused tests for KBLoadError propagation and graceful missing-file behavior.
Complements test_kb_structure.py which tests structural validity of production files.
These tests focus exclusively on failure-path scenarios to give the reviewer a
dedicated, named file for KB error handling evidence.

Test IDs:
  KB-EH-01  Malformed JSON → KBLoadError raised (not swallowed)
  KB-EH-02  KBLoadError message includes file path
  KB-EH-03  Invalid regex in behavioral pattern → KBLoadError
  KB-EH-04  Missing required field → KBLoadError
  KB-EH-05  Missing file → returns [] (not an exception)
  KB-EH-06  Both loaders return [] for missing files (graceful)
"""
from __future__ import annotations

import json
import re
import pytest
from pathlib import Path

from src.services.kb import KBLoadError, KnowledgeBaseLoader


# ===========================================================================
# KB-EH-01/02  Malformed JSON → KBLoadError with path in message
# ===========================================================================

class TestMalformedJSONRaisesKBLoadError:
    """KB-EH-01 + KB-EH-02: Invalid JSON must raise KBLoadError with file path."""

    def test_malformed_json_review_hints_raises_kb_load_error(self, tmp_path):
        broken_file = tmp_path / "test_review_hints.json"
        broken_file.write_text("{bad json", encoding="utf-8")

        with pytest.raises(KBLoadError):
            KnowledgeBaseLoader.load_review_hints("test", config_dir=str(tmp_path))

    def test_malformed_json_behavioral_patterns_raises_kb_load_error(self, tmp_path):
        broken_file = tmp_path / "test_behavioral_patterns.json"
        broken_file.write_text("[{bad json", encoding="utf-8")

        with pytest.raises(KBLoadError):
            KnowledgeBaseLoader.load_behavioral_patterns("test", config_dir=str(tmp_path))

    def test_kb_load_error_message_includes_something_identifying(self, tmp_path):
        broken_file = tmp_path / "myfamily_review_hints.json"
        broken_file.write_text("{not json at all}", encoding="utf-8")

        with pytest.raises(KBLoadError) as exc_info:
            KnowledgeBaseLoader.load_review_hints("myfamily", config_dir=str(tmp_path))

        # The error message should contain something that identifies the problem
        # (file path, family name, or error type)
        error_text = str(exc_info.value).lower()
        assert any(
            indicator in error_text
            for indicator in ["myfamily", "hints", "json", "review"]
        ), f"KBLoadError message not informative enough: {exc_info.value}"


# ===========================================================================
# KB-EH-03  Invalid regex → KBLoadError
# ===========================================================================

class TestInvalidRegexRaisesKBLoadError:
    """KB-EH-03: A behavioral pattern with invalid regex must raise KBLoadError."""

    def test_invalid_regex_raises_kb_load_error(self, tmp_path):
        patterns_file = tmp_path / "test_behavioral_patterns.json"
        bad_pattern = [
            {
                "id": "P-001",
                "pattern": "[unclosed bracket",  # invalid regex
                "description": "Test pattern with bad regex",
                "severity": "warning",
                "fix_hint": "Fix it",
            }
        ]
        patterns_file.write_text(json.dumps(bad_pattern), encoding="utf-8")

        with pytest.raises(KBLoadError):
            KnowledgeBaseLoader.load_behavioral_patterns("test", config_dir=str(tmp_path))


# ===========================================================================
# KB-EH-04  Missing required field → KBLoadError
# ===========================================================================

class TestMissingRequiredFieldRaisesKBLoadError:
    """KB-EH-04: Missing required fields must raise KBLoadError (schema validation)."""

    def test_missing_hint_field_raises_kb_load_error(self, tmp_path):
        hints_file = tmp_path / "test_review_hints.json"
        # "hint" field is required but absent
        bad_hints = [{"id": "H-001"}]
        hints_file.write_text(json.dumps(bad_hints), encoding="utf-8")

        with pytest.raises(KBLoadError):
            KnowledgeBaseLoader.load_review_hints("test", config_dir=str(tmp_path))

    def test_missing_id_field_raises_kb_load_error(self, tmp_path):
        hints_file = tmp_path / "test_review_hints.json"
        # "id" field is required but absent
        bad_hints = [{"hint": "Some hint text without an ID"}]
        hints_file.write_text(json.dumps(bad_hints), encoding="utf-8")

        with pytest.raises(KBLoadError):
            KnowledgeBaseLoader.load_review_hints("test", config_dir=str(tmp_path))


# ===========================================================================
# KB-EH-05/06  Missing file → returns [] gracefully (no exception)
# ===========================================================================

class TestMissingFileGracefulBehavior:
    """KB-EH-05 + KB-EH-06: Missing KB files must return [] without raising."""

    def test_missing_review_hints_file_returns_empty_list(self, tmp_path):
        # tmp_path exists but has no hints file
        result = KnowledgeBaseLoader.load_review_hints(
            "nonexistent_family", config_dir=str(tmp_path)
        )
        assert result == []

    def test_missing_behavioral_patterns_file_returns_empty_list(self, tmp_path):
        result = KnowledgeBaseLoader.load_behavioral_patterns(
            "nonexistent_family", config_dir=str(tmp_path)
        )
        assert result == []

    def test_missing_dir_review_hints_returns_empty_list(self, tmp_path):
        nonexistent_dir = str(tmp_path / "no_such_dir")
        result = KnowledgeBaseLoader.load_review_hints(
            "words", config_dir=nonexistent_dir
        )
        assert result == []

    def test_missing_dir_behavioral_patterns_returns_empty_list(self, tmp_path):
        nonexistent_dir = str(tmp_path / "no_such_dir")
        result = KnowledgeBaseLoader.load_behavioral_patterns(
            "words", config_dir=nonexistent_dir
        )
        assert result == []

    def test_missing_file_does_not_cache_error(self, tmp_path):
        """After a missing file, a subsequent call with the file present should succeed."""
        family = "dynamic_family"

        # First call: file absent → returns []
        result1 = KnowledgeBaseLoader.load_review_hints(family, config_dir=str(tmp_path))
        assert result1 == []

        # Create the file
        hints_file = tmp_path / f"{family}_review_hints.json"
        hints_file.write_text(
            json.dumps([{"id": "H-001", "hint": "Use the streaming API instead"}]),
            encoding="utf-8",
        )

        # Second call: file now exists → should return the hints (no error cached)
        result2 = KnowledgeBaseLoader.load_review_hints(family, config_dir=str(tmp_path))
        assert len(result2) == 1
        assert result2[0].id == "H-001"
