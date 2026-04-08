"""
Tests for src/services/proactive_llm_audit.py

Covers:
- load_family_hints: missing file, valid file, malformed JSON
- _filter_hints: pattern filter, context filter, no filters
- run_proactive_audit: empty hints, empty code, LLM returns [], LLM returns
  valid issues, LLM returns malformed JSON, LLM raises exception,
  severity filtering (only "error" issues are actionable), multiple issues
"""
from __future__ import annotations

import json
import textwrap
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest

from src.services.kb.models import ReviewHint
from src.services.proactive_llm_audit import (
    ProactiveAuditIssue,
    _filter_hints,
    load_family_hints,
    run_proactive_audit,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

# SAMPLE_HINTS as valid dicts (must satisfy ReviewHint schema: id + hint required)
_SAMPLE_HINTS_DICTS: List[Dict[str, Any]] = [
    {
        "id": "words-01",
        "hint": "WriteProtection.SetPassword only restricts editing, it does NOT encrypt.",
        "detection_keywords": ["WriteProtection", "SetPassword"],
        "correction": "Use OoxmlSaveOptions.Password",
        "pattern": "WriteProtection.SetPassword",
        "context": "encrypt",
    },
    {
        "id": "words-02",
        "hint": "Mustache placeholders require UseNonMergeFields = true before Execute().",
        "detection_keywords": ["MailMerge.Execute"],
        "correction": "Add UseNonMergeFields = true",
        "pattern": "MailMerge.Execute",
        "context": "",  # no context filter
    },
]
SAMPLE_HINTS: List[ReviewHint] = [ReviewHint.model_validate(h) for h in _SAMPLE_HINTS_DICTS]

CODE_WITH_WRITE_PROTECTION = textwrap.dedent("""\
    var doc = new Document();
    doc.WriteProtection.SetPassword("secret");
    doc.Save("out.docx");
""")

CODE_WITH_MAIL_MERGE = textwrap.dedent("""\
    var doc = new Document("Template.docx");
    doc.MailMerge.Execute(fieldNames, fieldValues);
    doc.Save("output.docx");
""")

CODE_CLEAN = textwrap.dedent("""\
    var doc = new Document("test.docx");
    doc.Save("result.docx");
""")


def _make_llm(content: str) -> MagicMock:
    """Return a mock LLM service whose .complete() returns a SimpleNamespace with .content."""
    mock = MagicMock()
    mock.complete.return_value = SimpleNamespace(content=content)
    return mock


# ---------------------------------------------------------------------------
# load_family_hints
# ---------------------------------------------------------------------------

class TestLoadFamilyHints:
    def test_missing_file_returns_empty(self, tmp_path):
        result = load_family_hints("nonexistent_family", config_dir=str(tmp_path))
        assert result == []

    def test_valid_file_loaded(self, tmp_path):
        hints_file = tmp_path / "myfamily_review_hints.json"
        hints_file.write_text(json.dumps(_SAMPLE_HINTS_DICTS), encoding="utf-8")
        result = load_family_hints("myfamily", config_dir=str(tmp_path))
        assert len(result) == 2
        assert result[0].id == "words-01"

    def test_malformed_json_returns_empty(self, tmp_path):
        # KBLoadError is caught internally; soft-fail for optional proactive-audit phase
        hints_file = tmp_path / "badfamily_review_hints.json"
        hints_file.write_text("{not valid json", encoding="utf-8")
        result = load_family_hints("badfamily", config_dir=str(tmp_path))
        assert result == []

    def test_empty_array_file_returns_empty_list(self, tmp_path):
        hints_file = tmp_path / "emptyfamily_review_hints.json"
        hints_file.write_text("[]", encoding="utf-8")
        result = load_family_hints("emptyfamily", config_dir=str(tmp_path))
        assert result == []

    def test_override_config_dir(self, tmp_path):
        """Verify config_dir can be overridden."""
        hints_file = tmp_path / "words_review_hints.json"
        hints_file.write_text(json.dumps([{"id": "w1", "hint": "Some hint"}]), encoding="utf-8")
        result = load_family_hints("words", config_dir=str(tmp_path))
        assert result[0].id == "w1"


# ---------------------------------------------------------------------------
# _filter_hints
# ---------------------------------------------------------------------------

class TestFilterHints:
    def test_pattern_must_be_in_code(self):
        matched = _filter_hints(SAMPLE_HINTS, CODE_CLEAN, "", "")
        assert matched == []

    def test_pattern_match_without_context(self):
        # words-02 has no context requirement, just pattern
        matched = _filter_hints(SAMPLE_HINTS, CODE_WITH_MAIL_MERGE, "", "")
        ids = [h.id for h in matched]
        assert "words-02" in ids
        assert "words-01" not in ids

    def test_pattern_and_context_both_required(self):
        # words-01 needs "encrypt" in context; without it, excluded
        matched = _filter_hints(SAMPLE_HINTS, CODE_WITH_WRITE_PROTECTION, "", "")
        ids = [h.id for h in matched]
        assert "words-01" not in ids

    def test_pattern_and_context_both_present(self):
        matched = _filter_hints(
            SAMPLE_HINTS, CODE_WITH_WRITE_PROTECTION,
            article_intent="We want to encrypt the document",
            markdown_snippet="",
        )
        ids = [h.id for h in matched]
        assert "words-01" in ids

    def test_hint_without_pattern_key_always_passes_pattern_check(self):
        hint_no_pattern = ReviewHint(id="x", hint="some hint")
        matched = _filter_hints([hint_no_pattern], CODE_CLEAN, "", "")
        assert len(matched) == 1
        assert matched[0].id == "x"

    def test_context_check_is_case_insensitive(self):
        matched = _filter_hints(
            SAMPLE_HINTS, CODE_WITH_WRITE_PROTECTION,
            article_intent="ENCRYPT the document",
            markdown_snippet="",
        )
        ids = [h.id for h in matched]
        assert "words-01" in ids


# ---------------------------------------------------------------------------
# run_proactive_audit
# ---------------------------------------------------------------------------

class TestRunProactiveAudit:
    def test_empty_hints_returns_empty(self):
        mock_llm = _make_llm("[]")
        result = run_proactive_audit(CODE_WITH_WRITE_PROTECTION, "intent", "heading", [], mock_llm)
        assert result == []
        mock_llm.complete.assert_not_called()

    def test_empty_code_returns_empty(self):
        mock_llm = _make_llm("[]")
        result = run_proactive_audit("   ", "intent", "heading", SAMPLE_HINTS, mock_llm)
        assert result == []
        mock_llm.complete.assert_not_called()

    def test_llm_returns_empty_array(self):
        mock_llm = _make_llm("[]")
        result = run_proactive_audit(CODE_WITH_MAIL_MERGE, "intent", "heading", SAMPLE_HINTS, mock_llm)
        assert result == []

    def test_llm_returns_valid_issue(self):
        payload = json.dumps([{
            "hint_id": "words-02",
            "issue_type": "missing_required_property",
            "description": "UseNonMergeFields not set",
            "correction": "Add doc.MailMerge.UseNonMergeFields = true",
            "severity": "error",
        }])
        mock_llm = _make_llm(payload)
        result = run_proactive_audit(CODE_WITH_MAIL_MERGE, "intent", "heading", SAMPLE_HINTS, mock_llm)
        assert len(result) == 1
        issue = result[0]
        assert isinstance(issue, ProactiveAuditIssue)
        assert issue.hint_id == "words-02"
        assert issue.severity == "error"
        assert issue.issue_type == "missing_required_property"

    def test_llm_returns_multiple_issues(self):
        payload = json.dumps([
            {"hint_id": "words-01", "issue_type": "semantic_misuse",
             "description": "WP misuse", "correction": "Fix", "severity": "error"},
            {"hint_id": "words-02", "issue_type": "missing_required_property",
             "description": "NMF missing", "correction": "Fix2", "severity": "warning"},
        ])
        mock_llm = _make_llm(payload)
        result = run_proactive_audit(CODE_WITH_WRITE_PROTECTION, "intent", "heading", SAMPLE_HINTS, mock_llm)
        assert len(result) == 2
        severities = {i.severity for i in result}
        assert severities == {"error", "warning"}

    def test_llm_returns_malformed_json_returns_empty(self):
        mock_llm = _make_llm("This is not JSON at all.")
        result = run_proactive_audit(CODE_WITH_MAIL_MERGE, "intent", "heading", SAMPLE_HINTS, mock_llm)
        assert result == []

    def test_llm_returns_json_with_non_dict_items(self):
        mock_llm = _make_llm('["string_item", null, 42]')
        result = run_proactive_audit(CODE_WITH_MAIL_MERGE, "intent", "heading", SAMPLE_HINTS, mock_llm)
        assert result == []

    def test_llm_raises_exception_returns_empty(self):
        mock_llm = MagicMock()
        mock_llm.complete.side_effect = RuntimeError("LLM is down")
        result = run_proactive_audit(CODE_WITH_MAIL_MERGE, "intent", "heading", SAMPLE_HINTS, mock_llm)
        assert result == []

    def test_llm_returns_json_embedded_in_prose(self):
        # LLM sometimes wraps JSON in prose; regex should still extract it
        payload = (
            'Here are the issues I found:\n'
            '[{"hint_id": "words-02", "issue_type": "missing_required_property", '
            '"description": "desc", "correction": "fix", "severity": "error"}]\n'
            'Hope that helps!'
        )
        mock_llm = _make_llm(payload)
        result = run_proactive_audit(CODE_WITH_MAIL_MERGE, "intent", "heading", SAMPLE_HINTS, mock_llm)
        assert len(result) == 1
        assert result[0].hint_id == "words-02"

    def test_missing_optional_fields_default_gracefully(self):
        # hint_id and correction missing from LLM response
        payload = json.dumps([{
            "issue_type": "semantic_misuse",
            "description": "Some issue",
            "severity": "error",
        }])
        mock_llm = _make_llm(payload)
        result = run_proactive_audit(CODE_WITH_MAIL_MERGE, "intent", "heading", SAMPLE_HINTS, mock_llm)
        assert len(result) == 1
        assert result[0].hint_id == ""
        assert result[0].correction == ""

    def test_issue_type_defaults_to_semantic_misuse_when_missing(self):
        payload = json.dumps([{
            "hint_id": "x",
            "description": "desc",
            "correction": "fix",
            "severity": "warning",
        }])
        mock_llm = _make_llm(payload)
        result = run_proactive_audit(CODE_WITH_MAIL_MERGE, "intent", "heading", SAMPLE_HINTS, mock_llm)
        assert result[0].issue_type == "semantic_misuse"

    def test_llm_called_with_code_in_prompt(self):
        mock_llm = _make_llm("[]")
        run_proactive_audit(CODE_WITH_MAIL_MERGE, "my intent", "Section X", SAMPLE_HINTS, mock_llm)
        assert mock_llm.complete.called
        call_kwargs = mock_llm.complete.call_args
        prompt = call_kwargs.kwargs.get("prompt") or call_kwargs.args[0]
        assert "MailMerge.Execute" in prompt
        assert "my intent" in prompt
