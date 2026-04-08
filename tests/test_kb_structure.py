"""
Structural and contract tests for the Family KB subsystem.

Tests in this file use a mix of:
- Real production files (config/families/words_*.json) for structural assurance
- Temporary fixture files (tmp_path) for negative/contract tests

Test IDs map to the plan:
  T-KB-01  words_review_hints.json   structural validity
  T-KB-02  words_behavioral_patterns.json  structural validity
  T-KB-AUTO  auto-discovery: all KB files in config/families/ load without error
  T-KB-03  File not found → []
  T-KB-04  Malformed JSON → KBLoadError
  T-KB-05  Invalid regex → KBLoadError
  T-KB-06  Missing required field → KBLoadError
  T-KB-07  Unknown field → KBLoadError  (extra="forbid")
  T-KB-08  words review hints count >= 9  (regression guard)
  T-KB-09  words behavioral patterns count >= 10  (regression guard)
  T-KB-11  Invalid severity value → KBLoadError
"""
from __future__ import annotations

import glob
import json
from pathlib import Path

import pytest

from src.services.kb import KBLoadError, KnowledgeBaseLoader
from src.services.kb.models import BehavioralPattern, ReviewHint

# ---------------------------------------------------------------------------
# Paths to real production files
# ---------------------------------------------------------------------------
_REAL_CONFIG_DIR = "config/families"
_WORDS_FAMILY = "words"


# ===========================================================================
# T-KB-01  words_review_hints.json — structural validity
# ===========================================================================

class TestWordsReviewHintsStructure:
    """T-KB-01: Real production file loads successfully and is well-formed."""

    def setup_method(self):
        self.hints = KnowledgeBaseLoader.load_review_hints(
            _WORDS_FAMILY, config_dir=_REAL_CONFIG_DIR
        )

    def test_loads_without_error(self):
        assert isinstance(self.hints, list)

    def test_all_items_are_review_hint_instances(self):
        for item in self.hints:
            assert isinstance(item, ReviewHint), f"Expected ReviewHint, got {type(item)}"

    def test_all_items_have_required_id(self):
        for item in self.hints:
            assert item.id and isinstance(item.id, str), f"Missing/empty id on hint: {item!r}"

    def test_all_items_have_required_hint(self):
        for item in self.hints:
            assert item.hint and isinstance(item.hint, str), f"Missing/empty hint on hint {item.id!r}"


# ===========================================================================
# T-KB-02  words_behavioral_patterns.json — structural validity
# ===========================================================================

class TestWordsBehavioralPatternsStructure:
    """T-KB-02: Real production file loads and all regex fields compile."""

    def setup_method(self):
        self.patterns = KnowledgeBaseLoader.load_behavioral_patterns(
            _WORDS_FAMILY, config_dir=_REAL_CONFIG_DIR
        )

    def test_loads_without_error(self):
        assert isinstance(self.patterns, list)

    def test_all_items_are_behavioral_pattern_instances(self):
        for p in self.patterns:
            assert isinstance(p, BehavioralPattern), f"Expected BehavioralPattern, got {type(p)}"

    def test_all_items_have_required_id(self):
        for p in self.patterns:
            assert p.id and isinstance(p.id, str), f"Missing/empty id: {p!r}"

    def test_all_items_have_valid_severity(self):
        for p in self.patterns:
            assert p.severity in {"error", "warning", "critical"}, (
                f"Pattern {p.id!r} has unexpected severity {p.severity!r}"
            )

    def test_all_items_have_required_description(self):
        for p in self.patterns:
            assert p.description and isinstance(p.description, str), (
                f"Missing/empty description on pattern {p.id!r}"
            )

    def test_all_items_have_at_least_one_regex(self):
        for p in self.patterns:
            assert p.code_regex or p.required_regex, (
                f"Pattern {p.id!r} has neither code_regex nor required_regex"
            )


# ===========================================================================
# T-KB-03  File not found → returns []
# ===========================================================================

class TestLoaderFileNotFound:
    """T-KB-03: Missing file returns empty list (valid; family may have no KB yet)."""

    def test_review_hints_missing_file_returns_empty(self, tmp_path):
        result = KnowledgeBaseLoader.load_review_hints("nosuchfamily", config_dir=str(tmp_path))
        assert result == []

    def test_behavioral_patterns_missing_file_returns_empty(self, tmp_path):
        result = KnowledgeBaseLoader.load_behavioral_patterns("nosuchfamily", config_dir=str(tmp_path))
        assert result == []


# ===========================================================================
# T-KB-04  Malformed JSON → KBLoadError
# ===========================================================================

class TestLoaderMalformedJson:
    """T-KB-04: Malformed JSON in file raises KBLoadError."""

    def test_review_hints_malformed_json_raises(self, tmp_path):
        (tmp_path / "badfam_review_hints.json").write_text("{not valid json", encoding="utf-8")
        with pytest.raises(KBLoadError, match="Failed to parse"):
            KnowledgeBaseLoader.load_review_hints("badfam", config_dir=str(tmp_path))

    def test_behavioral_patterns_malformed_json_raises(self, tmp_path):
        (tmp_path / "badfam_behavioral_patterns.json").write_text("{not valid json", encoding="utf-8")
        with pytest.raises(KBLoadError, match="Failed to parse"):
            KnowledgeBaseLoader.load_behavioral_patterns("badfam", config_dir=str(tmp_path))

    def test_review_hints_non_array_root_raises(self, tmp_path):
        (tmp_path / "badfam_review_hints.json").write_text(
            json.dumps({"id": "x", "hint": "y"}), encoding="utf-8"
        )
        with pytest.raises(KBLoadError, match="root element must be a JSON array"):
            KnowledgeBaseLoader.load_review_hints("badfam", config_dir=str(tmp_path))

    def test_behavioral_patterns_non_array_root_raises(self, tmp_path):
        (tmp_path / "badfam_behavioral_patterns.json").write_text(
            json.dumps({"id": "x"}), encoding="utf-8"
        )
        with pytest.raises(KBLoadError, match="root element must be a JSON array"):
            KnowledgeBaseLoader.load_behavioral_patterns("badfam", config_dir=str(tmp_path))


# ===========================================================================
# T-KB-05  Invalid regex → KBLoadError
# ===========================================================================

class TestLoaderInvalidRegex:
    """T-KB-05: A pattern with an invalid regex field raises KBLoadError at load time."""

    def test_invalid_code_regex_raises(self, tmp_path):
        bad_pattern = [
            {
                "id": "bad-regex",
                "severity": "error",
                "description": "A pattern with a broken regex",
                "code_regex": "[invalid",  # unclosed bracket
            }
        ]
        (tmp_path / "testfam_behavioral_patterns.json").write_text(
            json.dumps(bad_pattern), encoding="utf-8"
        )
        with pytest.raises(KBLoadError, match="Schema validation failed"):
            KnowledgeBaseLoader.load_behavioral_patterns("testfam", config_dir=str(tmp_path))

    def test_invalid_required_regex_raises(self, tmp_path):
        bad_pattern = [
            {
                "id": "bad-required",
                "severity": "warning",
                "description": "A pattern with a broken required_regex",
                "required_regex": "(?P<name>[)",  # invalid group
            }
        ]
        (tmp_path / "testfam_behavioral_patterns.json").write_text(
            json.dumps(bad_pattern), encoding="utf-8"
        )
        with pytest.raises(KBLoadError, match="Schema validation failed"):
            KnowledgeBaseLoader.load_behavioral_patterns("testfam", config_dir=str(tmp_path))


# ===========================================================================
# T-KB-06  Missing required field → KBLoadError
# ===========================================================================

class TestLoaderMissingRequiredField:
    """T-KB-06: Hints or patterns missing required fields raise KBLoadError."""

    def test_review_hint_missing_id_raises(self, tmp_path):
        (tmp_path / "testfam_review_hints.json").write_text(
            json.dumps([{"hint": "Some hint text"}]), encoding="utf-8"
        )
        with pytest.raises(KBLoadError, match="Schema validation failed"):
            KnowledgeBaseLoader.load_review_hints("testfam", config_dir=str(tmp_path))

    def test_review_hint_missing_hint_raises(self, tmp_path):
        (tmp_path / "testfam_review_hints.json").write_text(
            json.dumps([{"id": "x"}]), encoding="utf-8"
        )
        with pytest.raises(KBLoadError, match="Schema validation failed"):
            KnowledgeBaseLoader.load_review_hints("testfam", config_dir=str(tmp_path))

    def test_behavioral_pattern_missing_id_raises(self, tmp_path):
        (tmp_path / "testfam_behavioral_patterns.json").write_text(
            json.dumps([{"severity": "error", "description": "desc", "code_regex": "foo"}]),
            encoding="utf-8",
        )
        with pytest.raises(KBLoadError, match="Schema validation failed"):
            KnowledgeBaseLoader.load_behavioral_patterns("testfam", config_dir=str(tmp_path))

    def test_behavioral_pattern_missing_severity_raises(self, tmp_path):
        (tmp_path / "testfam_behavioral_patterns.json").write_text(
            json.dumps([{"id": "x", "description": "desc", "code_regex": "foo"}]),
            encoding="utf-8",
        )
        with pytest.raises(KBLoadError, match="Schema validation failed"):
            KnowledgeBaseLoader.load_behavioral_patterns("testfam", config_dir=str(tmp_path))

    def test_behavioral_pattern_missing_both_regex_raises(self, tmp_path):
        """Pattern with neither code_regex nor required_regex must raise."""
        (tmp_path / "testfam_behavioral_patterns.json").write_text(
            json.dumps([{"id": "x", "severity": "error", "description": "desc"}]),
            encoding="utf-8",
        )
        with pytest.raises(KBLoadError, match="Schema validation failed"):
            KnowledgeBaseLoader.load_behavioral_patterns("testfam", config_dir=str(tmp_path))


# ===========================================================================
# T-KB-07  Unknown field → KBLoadError  (extra="forbid")
# ===========================================================================

class TestLoaderUnknownField:
    """T-KB-07: Unknown fields raise KBLoadError (extra='forbid' enforced)."""

    def test_review_hint_unknown_field_raises(self, tmp_path):
        (tmp_path / "testfam_review_hints.json").write_text(
            json.dumps([{"id": "x", "hint": "h", "totally_unknown_field": "oops"}]),
            encoding="utf-8",
        )
        with pytest.raises(KBLoadError, match="Schema validation failed"):
            KnowledgeBaseLoader.load_review_hints("testfam", config_dir=str(tmp_path))

    def test_behavioral_pattern_unknown_field_raises(self, tmp_path):
        (tmp_path / "testfam_behavioral_patterns.json").write_text(
            json.dumps([{
                "id": "x", "severity": "error", "description": "d",
                "code_regex": "foo", "random_extra_field": 42,
            }]),
            encoding="utf-8",
        )
        with pytest.raises(KBLoadError, match="Schema validation failed"):
            KnowledgeBaseLoader.load_behavioral_patterns("testfam", config_dir=str(tmp_path))


# ===========================================================================
# T-KB-08  words review hints count >= 9  (regression guard)
# ===========================================================================

def test_words_review_hints_minimum_count():
    """T-KB-08: words_review_hints.json must have at least 9 entries (regression guard)."""
    hints = KnowledgeBaseLoader.load_review_hints(_WORDS_FAMILY, config_dir=_REAL_CONFIG_DIR)
    assert len(hints) >= 9, (
        f"Expected at least 9 review hints for 'words', got {len(hints)}. "
        "If hints were intentionally removed, update this lower bound."
    )


# ===========================================================================
# T-KB-09  words behavioral patterns count >= 10  (regression guard)
# ===========================================================================

def test_words_behavioral_patterns_minimum_count():
    """T-KB-09: words_behavioral_patterns.json must have at least 10 entries (regression guard)."""
    patterns = KnowledgeBaseLoader.load_behavioral_patterns(_WORDS_FAMILY, config_dir=_REAL_CONFIG_DIR)
    assert len(patterns) >= 10, (
        f"Expected at least 10 behavioral patterns for 'words', got {len(patterns)}. "
        "If patterns were intentionally removed, update this lower bound."
    )


# ===========================================================================
# T-KB-11  Invalid severity value → KBLoadError
# ===========================================================================

class TestLoaderInvalidSeverity:
    """T-KB-11: A pattern with an unrecognised severity value raises KBLoadError."""

    def test_unrecognised_severity_raises(self, tmp_path):
        (tmp_path / "testfam_behavioral_patterns.json").write_text(
            json.dumps([{
                "id": "x", "severity": "critical_error", "description": "d",
                "code_regex": "foo",
            }]),
            encoding="utf-8",
        )
        with pytest.raises(KBLoadError, match="Schema validation failed"):
            KnowledgeBaseLoader.load_behavioral_patterns("testfam", config_dir=str(tmp_path))

    def test_severity_critical_is_valid(self, tmp_path):
        """'critical' IS an accepted severity value (alongside 'error' and 'warning')."""
        (tmp_path / "testfam_behavioral_patterns.json").write_text(
            json.dumps([{
                "id": "x", "severity": "critical", "description": "d",
                "code_regex": "foo",
            }]),
            encoding="utf-8",
        )
        patterns = KnowledgeBaseLoader.load_behavioral_patterns("testfam", config_dir=str(tmp_path))
        assert len(patterns) == 1
        assert patterns[0].severity == "critical"


# ===========================================================================
# T-KB-AUTO  Auto-discovery: every KB file in config/families/ loads cleanly
# ===========================================================================

def test_all_kb_families_load_without_error():
    """T-KB-AUTO: every *_review_hints.json and *_behavioral_patterns.json found in
    config/families/ must load through KnowledgeBaseLoader without raising KBLoadError.

    This test auto-discovers files so that adding a new family KB file is
    automatically validated in CI without requiring a new named test.
    T-KB-01 and T-KB-02 provide deeper structural assertions for the 'words'
    files specifically; this test is the safety net for all other families.
    """
    config_dir = _REAL_CONFIG_DIR
    errors: list[str] = []

    for path in sorted(glob.glob(f"{config_dir}/*_review_hints.json")):
        family = Path(path).stem.removesuffix("_review_hints")
        try:
            KnowledgeBaseLoader.load_review_hints(family, config_dir=config_dir)
        except KBLoadError as exc:
            errors.append(f"{path}: {exc}")

    for path in sorted(glob.glob(f"{config_dir}/*_behavioral_patterns.json")):
        family = Path(path).stem.removesuffix("_behavioral_patterns")
        try:
            KnowledgeBaseLoader.load_behavioral_patterns(family, config_dir=config_dir)
        except KBLoadError as exc:
            errors.append(f"{path}: {exc}")

    assert not errors, "KB load errors:\n" + "\n".join(errors)


# ===========================================================================
# TASK-024  config_dir threading in _build_family_review_hints
# ===========================================================================

def test_build_family_review_hints_uses_custom_config_dir(tmp_path):
    """_build_family_review_hints must load hints from the config_dir it is given,
    not from the hardcoded default 'config/families'.

    This test creates a custom hints file in tmp_path and verifies that the
    hint text appears in the output when config_dir points to that directory.
    The hint must NOT appear when config_dir points to an empty directory.
    """
    from unittest.mock import MagicMock
    from src.services.llm_service import LLMService

    hint_id = "test_hint_for_config_dir"
    hint_text = "Use the preferred API instead of the legacy one"
    hints_data = [{"id": hint_id, "hint": hint_text}]
    (tmp_path / "testfam_review_hints.json").write_text(
        json.dumps(hints_data), encoding="utf-8"
    )

    # Instantiate LLMService without a real client
    svc = LLMService.__new__(LLMService)
    svc._client = MagicMock()

    # With custom config_dir pointing to the tmp_path directory — hint must appear
    result_with = svc._build_family_review_hints(
        family="testfam",
        code_snippets=[],
        article_intent="",
        markdown_content="",
        config_dir=str(tmp_path),
    )
    assert hint_text in result_with, (
        f"Expected hint text '{hint_text}' in result when config_dir={tmp_path!r}, "
        f"but got: {result_with!r}"
    )

    # With default config_dir (no testfam file there) — hint must NOT appear
    result_without = svc._build_family_review_hints(
        family="testfam",
        code_snippets=[],
        article_intent="",
        markdown_content="",
        # config_dir defaults to "config/families" which has no testfam file
    )
    assert hint_text not in result_without, (
        f"Did not expect hint text in result when config_dir='config/families', "
        f"but it appeared: {result_without!r}"
    )


# ===========================================================================
# TASK-030  Regression: content_type NameError fix in _review_with_instructor
# ===========================================================================

def test_review_with_instructor_accepts_content_type_and_config_dir(tmp_path):
    """Regression: _review_with_instructor must accept content_type and config_dir
    without raising TypeError (before the fix, content_type was used inside the
    method body but absent from the function signature, causing NameError).

    Does NOT make a live LLM call — patches _build_family_review_hints to a mock
    so we can assert the parameters were forwarded correctly.  Any failure before
    the mock is reached (NameError / TypeError on the function call itself) means
    the fix is incomplete.
    """
    from unittest.mock import MagicMock, patch
    from src.services.llm_service import LLMService

    svc = LLMService.__new__(LLMService)
    svc._client = MagicMock()
    svc._last_response = None

    with patch.object(svc, "_build_family_review_hints", return_value="") as mock_bhf:
        try:
            svc._review_with_instructor(
                markdown_content="# Test",
                code_snippets=[],
                family="words",
                content_type="tutorial",
                config_dir=str(tmp_path),
            )
        except TypeError as exc:
            raise AssertionError(
                f"_review_with_instructor raised TypeError before reaching "
                f"_build_family_review_hints — the content_type/config_dir fix is incomplete: {exc}"
            ) from exc
        except Exception:
            pass  # Internal errors (UnboundLocalError, missing client, etc.) are acceptable;
                  # we only care that the function accepted the parameters without TypeError

    mock_bhf.assert_called_once()
    call_kwargs = mock_bhf.call_args[1]
    assert call_kwargs.get("content_type") == "tutorial", (
        f"content_type='tutorial' was not forwarded to _build_family_review_hints: {call_kwargs}"
    )
    assert call_kwargs.get("config_dir") == str(tmp_path), (
        f"config_dir was not forwarded to _build_family_review_hints: {call_kwargs}"
    )


# ===========================================================================
# TASK-031  E2E: config_dir flows from review_markdown_structured to hint file
# ===========================================================================

def test_review_markdown_structured_routes_config_dir_to_hints(tmp_path, monkeypatch):
    """Integration: config_dir flows from review_markdown_structured all the way
    to the on-disk hint file read by KnowledgeBaseLoader.

    Uses monkeypatch to:
    - disable Instructor so _review_with_manual_parsing is the active path
    - intercept self.complete to capture the prompt without a live LLM call

    Asserts:
    - The sentinel hint text from the custom config_dir appears in the prompt
    - The sentinel does NOT appear when using the default config_dir
      (so we know it came from tmp_path, not from config/families)
    """
    import json
    from unittest.mock import MagicMock
    from src.services.llm_service import LLMService

    # Unique sentinel text that will NOT appear in the real config/families/words_review_hints.json
    sentinel = "SENTINEL_HINT_E2E_TEST_DO_NOT_USE"
    (tmp_path / "words_review_hints.json").write_text(
        json.dumps([{"id": "sentinel", "hint": sentinel}]), encoding="utf-8"
    )

    svc = LLMService.__new__(LLMService)
    svc._client = MagicMock()
    svc._last_response = None

    captured_prompts = []

    def fake_complete(prompt, **kwargs):
        captured_prompts.append(prompt)
        r = MagicMock()
        r.success = False
        r.error = "mocked"
        r.content = ""
        return r

    monkeypatch.setattr(svc, "complete", fake_complete)
    monkeypatch.setattr("src.services.llm_service.INSTRUCTOR_AVAILABLE", False)

    # Call with custom config_dir — sentinel must appear in prompt
    svc.review_markdown_structured(
        markdown_content="# Test article",
        code_snippets=[{"code": "var doc = new Document();", "language": "csharp",
                        "example_id": "e1", "line": 1}],
        family="words",
        config_dir=str(tmp_path),
    )

    assert captured_prompts, "_review_with_manual_parsing never called complete()"
    assert sentinel in captured_prompts[0], (
        f"Sentinel hint not found in LLM prompt — config_dir={tmp_path!r} was not threaded "
        f"through to KnowledgeBaseLoader.\nPrompt excerpt: {captured_prompts[0][:600]}"
    )

    # Call with default config_dir — sentinel must NOT appear
    captured_prompts.clear()
    svc.review_markdown_structured(
        markdown_content="# Test article",
        code_snippets=[{"code": "var doc = new Document();", "language": "csharp",
                        "example_id": "e1", "line": 1}],
        family="words",
        # config_dir defaults to "config/families" — no sentinel file there
    )

    assert captured_prompts, "complete() was not called in second invocation"
    assert sentinel not in captured_prompts[0], (
        f"Sentinel found in default config_dir prompt — unexpected. "
        f"The sentinel text may accidentally match something in the real hints file."
    )
