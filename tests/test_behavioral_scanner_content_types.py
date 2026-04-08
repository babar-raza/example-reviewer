"""Tests for the content_type filtering feature of BehavioralPatternScanner (T9)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from src.services.behavioral_pattern_scanner import BehavioralFinding, BehavioralPatternScanner
from src.services.kb.models import BehavioralPattern


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_kb_only_pattern() -> BehavioralPattern:
    """A minimal pattern that is restricted to the 'kb' content type."""
    return BehavioralPattern(
        id="test_kb_only_pattern",
        issue_type="documentation_gap",
        severity="warning",
        code_regex=r"SetPassword\s*\(",
        description="KB-only: password call detected.",
        suggestion="Review password handling for KB articles.",
        content_types=["kb"],
    )


def _make_blog_and_docs_pattern() -> BehavioralPattern:
    """A pattern restricted to blog and docs content types."""
    return BehavioralPattern(
        id="test_blog_docs_pattern",
        issue_type="api_mismatch",
        severity="error",
        code_regex=r"SetPassword\s*\(",
        description="Blog/docs: password call detected.",
        suggestion="Consider alternative approach for blog/docs.",
        content_types=["blog", "docs"],
    )


def _make_unrestricted_pattern() -> BehavioralPattern:
    """A pattern with no content_types restriction — fires everywhere."""
    return BehavioralPattern(
        id="test_unrestricted_pattern",
        issue_type="other",
        severity="warning",
        code_regex=r"SetPassword\s*\(",
        description="Unrestricted: password call detected.",
    )


CODE_WITH_SETPASSWORD = 'doc.WriteProtection.SetPassword("secret");'


# ---------------------------------------------------------------------------
# content_types filter: kb-only pattern
# ---------------------------------------------------------------------------


def test_kb_only_pattern_fires_for_kb(monkeypatch):
    """A pattern with content_types=['kb'] must fire when content_type='kb'."""
    scanner = BehavioralPatternScanner()
    monkeypatch.setattr(scanner, "_load_patterns", lambda family: [_make_kb_only_pattern()])

    findings = scanner.scan_example(
        "words",
        CODE_WITH_SETPASSWORD,
        content_type="kb",
    )

    assert any(f.pattern_id == "test_kb_only_pattern" for f in findings), (
        "KB-only pattern must fire when content_type='kb'"
    )


def test_kb_only_pattern_skipped_for_blog(monkeypatch):
    """A pattern with content_types=['kb'] must NOT fire when content_type='blog'."""
    scanner = BehavioralPatternScanner()
    monkeypatch.setattr(scanner, "_load_patterns", lambda family: [_make_kb_only_pattern()])

    findings = scanner.scan_example(
        "words",
        CODE_WITH_SETPASSWORD,
        content_type="blog",
    )

    assert not any(f.pattern_id == "test_kb_only_pattern" for f in findings), (
        "KB-only pattern must be skipped when content_type='blog'"
    )


def test_kb_only_pattern_skipped_for_docs(monkeypatch):
    """A pattern with content_types=['kb'] must NOT fire when content_type='docs'."""
    scanner = BehavioralPatternScanner()
    monkeypatch.setattr(scanner, "_load_patterns", lambda family: [_make_kb_only_pattern()])

    findings = scanner.scan_example(
        "words",
        CODE_WITH_SETPASSWORD,
        content_type="docs",
    )

    assert not any(f.pattern_id == "test_kb_only_pattern" for f in findings), (
        "KB-only pattern must be skipped when content_type='docs'"
    )


def test_kb_only_pattern_fires_when_no_content_type(monkeypatch):
    """A pattern with content_types=['kb'] must fire when content_type='' (no filter applied)."""
    scanner = BehavioralPatternScanner()
    monkeypatch.setattr(scanner, "_load_patterns", lambda family: [_make_kb_only_pattern()])

    findings = scanner.scan_example(
        "words",
        CODE_WITH_SETPASSWORD,
        content_type="",  # explicit empty — backwards-compatible default
    )

    assert any(f.pattern_id == "test_kb_only_pattern" for f in findings), (
        "KB-only pattern must fire when content_type='' (filter disabled)"
    )


def test_kb_only_pattern_fires_when_content_type_omitted(monkeypatch):
    """content_type defaults to '' so filter is never applied — full backwards compat."""
    scanner = BehavioralPatternScanner()
    monkeypatch.setattr(scanner, "_load_patterns", lambda family: [_make_kb_only_pattern()])

    findings = scanner.scan_example(
        "words",
        CODE_WITH_SETPASSWORD,
        # content_type not passed
    )

    assert any(f.pattern_id == "test_kb_only_pattern" for f in findings), (
        "KB-only pattern must fire when content_type is not passed (default='')"
    )


# ---------------------------------------------------------------------------
# content_types filter: multi-type pattern (blog + docs)
# ---------------------------------------------------------------------------


def test_blog_docs_pattern_fires_for_blog(monkeypatch):
    scanner = BehavioralPatternScanner()
    monkeypatch.setattr(scanner, "_load_patterns", lambda family: [_make_blog_and_docs_pattern()])

    findings = scanner.scan_example(
        "words",
        CODE_WITH_SETPASSWORD,
        content_type="blog",
    )

    assert any(f.pattern_id == "test_blog_docs_pattern" for f in findings)


def test_blog_docs_pattern_fires_for_docs(monkeypatch):
    scanner = BehavioralPatternScanner()
    monkeypatch.setattr(scanner, "_load_patterns", lambda family: [_make_blog_and_docs_pattern()])

    findings = scanner.scan_example(
        "words",
        CODE_WITH_SETPASSWORD,
        content_type="docs",
    )

    assert any(f.pattern_id == "test_blog_docs_pattern" for f in findings)


def test_blog_docs_pattern_skipped_for_kb(monkeypatch):
    scanner = BehavioralPatternScanner()
    monkeypatch.setattr(scanner, "_load_patterns", lambda family: [_make_blog_and_docs_pattern()])

    findings = scanner.scan_example(
        "words",
        CODE_WITH_SETPASSWORD,
        content_type="kb",
    )

    assert not any(f.pattern_id == "test_blog_docs_pattern" for f in findings)


# ---------------------------------------------------------------------------
# Unrestricted pattern (no content_types field)
# ---------------------------------------------------------------------------


def test_unrestricted_pattern_fires_for_all_content_types(monkeypatch):
    """Patterns without content_types must fire regardless of content_type."""
    scanner = BehavioralPatternScanner()
    monkeypatch.setattr(scanner, "_load_patterns", lambda family: [_make_unrestricted_pattern()])

    for ct in ("blog", "docs", "kb", "", "unknown_type"):
        findings = scanner.scan_example(
            "words",
            CODE_WITH_SETPASSWORD,
            content_type=ct,
        )
        assert any(f.pattern_id == "test_unrestricted_pattern" for f in findings), (
            f"Unrestricted pattern must fire for content_type={ct!r}"
        )


# ---------------------------------------------------------------------------
# Mixed pattern list: selective firing
# ---------------------------------------------------------------------------


def test_only_matching_patterns_fire_in_mixed_list(monkeypatch):
    """In a mixed list, only patterns whose content_types match (or are absent) fire."""
    scanner = BehavioralPatternScanner()
    patterns = [
        _make_kb_only_pattern(),
        _make_blog_and_docs_pattern(),
        _make_unrestricted_pattern(),
    ]
    monkeypatch.setattr(scanner, "_load_patterns", lambda family: patterns)

    # For content_type='kb': kb-only fires, blog+docs is skipped, unrestricted fires
    findings_kb = scanner.scan_example("words", CODE_WITH_SETPASSWORD, content_type="kb")
    ids_kb = {f.pattern_id for f in findings_kb}
    assert "test_kb_only_pattern" in ids_kb
    assert "test_blog_docs_pattern" not in ids_kb
    assert "test_unrestricted_pattern" in ids_kb

    # For content_type='blog': kb-only skipped, blog+docs fires, unrestricted fires
    findings_blog = scanner.scan_example("words", CODE_WITH_SETPASSWORD, content_type="blog")
    ids_blog = {f.pattern_id for f in findings_blog}
    assert "test_kb_only_pattern" not in ids_blog
    assert "test_blog_docs_pattern" in ids_blog
    assert "test_unrestricted_pattern" in ids_blog

    # For content_type='': no filter — all three fire
    findings_all = scanner.scan_example("words", CODE_WITH_SETPASSWORD, content_type="")
    ids_all = {f.pattern_id for f in findings_all}
    assert "test_kb_only_pattern" in ids_all
    assert "test_blog_docs_pattern" in ids_all
    assert "test_unrestricted_pattern" in ids_all


# ---------------------------------------------------------------------------
# Integration: real words patterns (no content_types) still fire
# ---------------------------------------------------------------------------


def test_real_words_pattern_fires_with_kb_content_type():
    """Real words patterns (no content_types field) must still fire for any content_type."""
    scanner = BehavioralPatternScanner()
    code = 'doc.WriteProtection.SetPassword("pw");'

    findings = scanner.scan_example(
        "words",
        code,
        article_intent="encrypt the document",
        content_type="kb",
    )
    assert any(f.pattern_id == "words_write_protection_not_encryption" for f in findings), (
        "WriteProtection pattern (no content_types) must fire for content_type='kb'"
    )


def test_real_words_pattern_fires_with_blog_content_type():
    """Real words patterns (no content_types field) must still fire for content_type='blog'."""
    scanner = BehavioralPatternScanner()
    code = 'doc.WriteProtection.SetPassword("pw");'

    findings = scanner.scan_example(
        "words",
        code,
        article_intent="encrypt the document",
        content_type="blog",
    )
    assert any(f.pattern_id == "words_write_protection_not_encryption" for f in findings), (
        "WriteProtection pattern (no content_types) must fire for content_type='blog'"
    )
