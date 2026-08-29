"""
Unit tests for Article Quality Detection parameters:
  T3 — _build_family_review_hints() framing and empty-guard
  T4 — review_prose_against_code() family_hints param
  T5 — MarkdownUpdateService family_hints_str constructor storage
  T9_llm — content_types filter in _build_family_review_hints()
"""
import inspect
import json
import types
from pathlib import Path

import pytest

from src.services.llm_service import LLMService
from src.services.markdown_service import MarkdownUpdateService
from tests.conftest import make_pdp


# ---------------------------------------------------------------------------
# T3: _build_family_review_hints() framing
# ---------------------------------------------------------------------------

def _make_hints_file(tmp_path, hints):
    hints_dir = tmp_path / "config" / "families"
    hints_dir.mkdir(parents=True, exist_ok=True)
    hints_file = hints_dir / "testfam_review_hints.json"
    hints_file.write_text(json.dumps(hints), encoding="utf-8")
    return hints_file


def test_T3_hints_header_present_when_match(tmp_path, monkeypatch):
    """T3: returned string contains mandatory 'Flag These Regardless' header and preamble."""
    hints = [
        {
            "id": "t3-01",
            "pattern": "WriteProtection",
            "context": "",
            "issue_type": "api_mismatch",
            "hint": "WriteProtection is NOT encryption.",
        }
    ]
    _make_hints_file(tmp_path, hints)
    monkeypatch.chdir(tmp_path)

    svc = LLMService.__new__(LLMService)
    result = svc._build_family_review_hints(
        family="testfam",
        code_snippets=[{"code": "doc.Protect(ProtectionType.AllowOnlyFormFields); // WriteProtection"}],
        article_intent="encrypt the document",
        markdown_content="use WriteProtection to protect",
    )

    assert "Flag These Regardless of Article Intent" in result
    assert "IMPORTANT" in result
    assert "WriteProtection is NOT encryption" in result


def test_T3_empty_hints_returns_empty_string(tmp_path, monkeypatch):
    """T3: when no hints match the code, returns empty string (no orphan header)."""
    hints = [
        {
            "id": "t3-02",
            "pattern": "SomeNonexistentToken",
            "context": "",
            "issue_type": "api_mismatch",
            "hint": "Should never appear.",
        }
    ]
    _make_hints_file(tmp_path, hints)
    monkeypatch.chdir(tmp_path)

    svc = LLMService.__new__(LLMService)
    result = svc._build_family_review_hints(
        family="testfam",
        code_snippets=[{"code": "var doc = new Document();"}],
        article_intent="",
        markdown_content="",
    )

    assert result == ""


def test_T3_no_hints_file_returns_empty_string(tmp_path, monkeypatch):
    """T3: missing hints file returns empty string gracefully."""
    monkeypatch.chdir(tmp_path)
    svc = LLMService.__new__(LLMService)
    result = svc._build_family_review_hints(
        family="nonexistentfam",
        code_snippets=[],
        article_intent="",
        markdown_content="",
    )
    assert result == ""


# ---------------------------------------------------------------------------
# T4: review_prose_against_code() family_hints param
# ---------------------------------------------------------------------------

def test_T4_signature_has_family_hints_with_default():
    """T4: review_prose_against_code must have family_hints param with default ''."""
    sig = inspect.signature(LLMService.review_prose_against_code)
    assert "family_hints" in sig.parameters
    assert sig.parameters["family_hints"].default == ""


def test_T4_nonempty_family_hints_appears_in_prompt(monkeypatch):
    """T4: non-empty family_hints causes 'Family Knowledge Constraints' to appear in the LLM prompt."""
    svc = LLMService.__new__(LLMService)
    svc._client = True  # make truthy so early-return guard is skipped

    captured = {}

    def mock_complete(prompt, system_prompt="", **kwargs):
        captured["prompt"] = prompt
        # Return a minimal valid-looking response to avoid further errors
        resp = types.SimpleNamespace(
            success=True,
            content='{"accurate": true, "issues": "", "corrected_prose": null}',
        )
        return resp

    svc.complete = mock_complete

    svc.review_prose_against_code(
        prose_text="This saves memory.",
        code_text="foreach (Section sec in doc.Sections) { }",
        family_hints="Section iteration does NOT reduce peak memory.",
    )

    assert "Family Knowledge Constraints" in captured.get("prompt", "")
    assert "Section iteration does NOT reduce peak memory" in captured.get("prompt", "")


# ---------------------------------------------------------------------------
# T5: MarkdownUpdateService family_hints_str
# ---------------------------------------------------------------------------

def test_T5_family_hints_str_stored_on_instance(tmp_path):
    """T5: MarkdownUpdateService(family_hints_str='test') stores it on self.family_hints_str."""
    svc = MarkdownUpdateService(
        db=None,
        pdp=make_pdp(allow_writes=False),
        artifacts_dir=tmp_path,
        family_hints_str="test-hint",
    )
    assert svc.family_hints_str == "test-hint"


def test_T5_family_hints_str_defaults_to_empty(tmp_path):
    """T5: MarkdownUpdateService without family_hints_str defaults to ''."""
    svc = MarkdownUpdateService(
        db=None,
        pdp=make_pdp(allow_writes=False),
        artifacts_dir=tmp_path,
    )
    assert svc.family_hints_str == ""


# ---------------------------------------------------------------------------
# T9_llm: content_types filter in _build_family_review_hints()
# ---------------------------------------------------------------------------

def test_T9_hint_skipped_for_wrong_content_type(tmp_path, monkeypatch):
    """T9: hint with content_types=['kb'] is skipped when content_type='blog'."""
    hints = [
        {
            "id": "t9-01",
            "pattern": "WriteProtection",
            "context": "",
            "issue_type": "api_mismatch",
            "content_types": ["kb"],
            "hint": "KB-only hint about WriteProtection.",
        }
    ]
    _make_hints_file(tmp_path, hints)
    monkeypatch.chdir(tmp_path)

    svc = LLMService.__new__(LLMService)
    result = svc._build_family_review_hints(
        family="testfam",
        code_snippets=[{"code": "doc.Protect(ProtectionType.AllowOnlyFormFields); // WriteProtection"}],
        article_intent="",
        markdown_content="WriteProtection",
        content_type="blog",
    )

    assert result == ""


def test_T9_hint_fires_for_matching_content_type(tmp_path, monkeypatch):
    """T9: hint with content_types=['kb'] fires when content_type='kb'."""
    hints = [
        {
            "id": "t9-02",
            "pattern": "WriteProtection",
            "context": "",
            "issue_type": "api_mismatch",
            "content_types": ["kb"],
            "hint": "KB-only hint about WriteProtection.",
        }
    ]
    _make_hints_file(tmp_path, hints)
    monkeypatch.chdir(tmp_path)

    svc = LLMService.__new__(LLMService)
    result = svc._build_family_review_hints(
        family="testfam",
        code_snippets=[{"code": "doc.Protect(ProtectionType.AllowOnlyFormFields); // WriteProtection"}],
        article_intent="",
        markdown_content="WriteProtection",
        content_type="kb",
    )

    assert "KB-only hint about WriteProtection" in result


def test_T9_hint_fires_when_content_type_empty(tmp_path, monkeypatch):
    """T9: hint with content_types=['kb'] fires when content_type='' (unknown, don't filter)."""
    hints = [
        {
            "id": "t9-03",
            "pattern": "WriteProtection",
            "context": "",
            "issue_type": "api_mismatch",
            "content_types": ["kb"],
            "hint": "KB-only hint about WriteProtection.",
        }
    ]
    _make_hints_file(tmp_path, hints)
    monkeypatch.chdir(tmp_path)

    svc = LLMService.__new__(LLMService)
    result = svc._build_family_review_hints(
        family="testfam",
        code_snippets=[{"code": "doc.Protect(ProtectionType.AllowOnlyFormFields); // WriteProtection"}],
        article_intent="",
        markdown_content="WriteProtection",
        content_type="",
    )

    assert "KB-only hint about WriteProtection" in result


def test_T9_hint_without_content_types_applies_to_all(tmp_path, monkeypatch):
    """T9: hint without content_types field applies to all content types."""
    hints = [
        {
            "id": "t9-04",
            "pattern": "WriteProtection",
            "context": "",
            "issue_type": "api_mismatch",
            "hint": "Global hint about WriteProtection.",
        }
    ]
    _make_hints_file(tmp_path, hints)
    monkeypatch.chdir(tmp_path)

    svc = LLMService.__new__(LLMService)
    for ct in ("blog", "docs", "kb", ""):
        result = svc._build_family_review_hints(
            family="testfam",
            code_snippets=[{"code": "doc.Protect(ProtectionType.AllowOnlyFormFields); // WriteProtection"}],
            article_intent="",
            markdown_content="WriteProtection",
            content_type=ct,
        )
        assert "Global hint about WriteProtection" in result, f"Should fire for content_type={ct!r}"
