"""
SR-01 / SR-02 — Unit tests for:
  - MarkdownUpdateService.update_prose_only()
  - MarkdownUpdateService._audit_and_update_adjacent_prose(force_audit_all=True)
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, call
from typing import List, Dict, Any


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _make_service(
    llm_service=None,
    audit_prose: bool = True,
    family_hints_str: str = "hint: check memory usage",
    allow_markdown_write: bool = True,
):
    """Build a MarkdownUpdateService with a minimal stub DB and optional LLM mock."""
    from src.services.markdown_service import MarkdownUpdateService
    from tests.conftest import make_pdp

    db = MagicMock()
    return MarkdownUpdateService(
        db=db,
        pdp=make_pdp(allow_writes=allow_markdown_write),
        llm_service=llm_service,
        audit_prose=audit_prose,
        family_hints_str=family_hints_str,
    )


def _make_llm(accurate: bool = True, corrected: str = ""):
    """Return an LLM mock whose review_prose_against_code() returns the given values."""
    llm = MagicMock()
    llm.review_prose_against_code.return_value = {
        "accurate": accurate,
        "corrected_prose": corrected,
    }
    return llm


CONTENT_WITH_TWO_BLOCKS = """\
## Memory Usage

This approach loads the entire file into memory and writes bytes.

```csharp
var ms = new MemoryStream();
doc.Save(ms, SaveFormat.Docx);
File.WriteAllBytes("out.docx", ms.ToArray());
```

## Signature

Sign the document before saving.

```csharp
DigitalSignatureUtil.Sign("input.docx", "signed.docx", cert);
```
"""


# ---------------------------------------------------------------------------
# SR-01: update_prose_only()
# ---------------------------------------------------------------------------

class TestUpdateProseOnly:
    def test_returns_false_empty_when_audit_prose_disabled(self, tmp_path):
        """No-op when audit_prose=False."""
        svc = _make_service(llm_service=_make_llm(), audit_prose=False)
        f = tmp_path / "article.md"
        f.write_text(CONTENT_WITH_TWO_BLOCKS, encoding="utf-8")
        changed, changes = svc.update_prose_only(str(f))
        assert changed is False
        assert changes == []

    def test_returns_false_empty_when_no_llm(self, tmp_path):
        """No-op when llm_service is None."""
        svc = _make_service(llm_service=None, audit_prose=True)
        f = tmp_path / "article.md"
        f.write_text(CONTENT_WITH_TWO_BLOCKS, encoding="utf-8")
        changed, changes = svc.update_prose_only(str(f))
        assert changed is False
        assert changes == []

    def test_returns_false_when_file_missing(self):
        """Missing file: returns (False, []) without crashing."""
        svc = _make_service(llm_service=_make_llm())
        changed, changes = svc.update_prose_only("/nonexistent/file.md")
        assert changed is False
        assert changes == []

    def test_no_corrections_when_llm_says_accurate(self, tmp_path):
        """When LLM says accurate=True, no prose_changes returned."""
        llm = _make_llm(accurate=True, corrected="")
        svc = _make_service(llm_service=llm)
        f = tmp_path / "article.md"
        f.write_text(CONTENT_WITH_TWO_BLOCKS, encoding="utf-8")
        changed, changes = svc.update_prose_only(str(f))
        assert changed is False
        assert changes == []
        # File content should be untouched
        assert f.read_text(encoding="utf-8") == CONTENT_WITH_TWO_BLOCKS

    def test_prose_corrected_and_written_when_inaccurate(self, tmp_path):
        """When LLM returns a correction, file is written and (True, [..]) returned."""
        corrected = "Use FileStream directly for large documents instead of MemoryStream."
        llm = MagicMock()
        call_count = [0]
        def side_effect(**kwargs):
            call_count[0] += 1
            # Only correct the first section
            if call_count[0] == 1:
                return {"accurate": False, "corrected_prose": corrected}
            return {"accurate": True, "corrected_prose": ""}
        llm.review_prose_against_code.side_effect = side_effect

        svc = _make_service(llm_service=llm)
        f = tmp_path / "article.md"
        f.write_text(CONTENT_WITH_TWO_BLOCKS, encoding="utf-8")

        changed, changes = svc.update_prose_only(str(f))
        assert changed is True
        assert len(changes) >= 1
        written = f.read_text(encoding="utf-8")
        assert corrected in written

    def test_dry_run_does_not_write_file(self, tmp_path):
        """dry_run=True: corrections computed but file NOT written."""
        corrected = "Use FileStream for large documents."
        llm = MagicMock()
        llm.review_prose_against_code.return_value = {
            "accurate": False,
            "corrected_prose": corrected,
        }
        svc = _make_service(llm_service=llm)
        f = tmp_path / "article.md"
        f.write_text(CONTENT_WITH_TWO_BLOCKS, encoding="utf-8")
        original = f.read_text(encoding="utf-8")

        changed, changes = svc.update_prose_only(str(f), dry_run=True)
        # Returns True (corrections exist) but file unchanged
        assert changed is True
        assert f.read_text(encoding="utf-8") == original

    def test_extra_hints_appended_and_restored(self, tmp_path):
        """extra_hints is temporarily merged into family_hints_str, then restored."""
        llm = _make_llm(accurate=True, corrected="")
        svc = _make_service(llm_service=llm, family_hints_str="base-hint")
        f = tmp_path / "article.md"
        f.write_text(CONTENT_WITH_TWO_BLOCKS, encoding="utf-8")

        svc.update_prose_only(str(f), extra_hints="extra-hint")
        # After the call, family_hints_str is restored to the original value
        assert svc.family_hints_str == "base-hint"

    def test_extra_hints_visible_during_llm_call(self, tmp_path):
        """family_hints_str passed to LLM review call includes extra_hints content."""
        captured_hints = []
        def capture(**kwargs):
            captured_hints.append(kwargs.get("family_hints", ""))
            return {"accurate": True, "corrected_prose": ""}
        llm = MagicMock()
        llm.review_prose_against_code.side_effect = capture

        svc = _make_service(llm_service=llm, family_hints_str="base")
        f = tmp_path / "article.md"
        f.write_text(CONTENT_WITH_TWO_BLOCKS, encoding="utf-8")

        svc.update_prose_only(str(f), extra_hints="extra")
        assert any("extra" in h for h in captured_hints)


# ---------------------------------------------------------------------------
# SR-02: _audit_and_update_adjacent_prose(force_audit_all=True)
# ---------------------------------------------------------------------------

class TestForceAuditAll:
    def test_force_audit_all_audits_all_sections(self, tmp_path):
        """force_audit_all=True: LLM called for every prose section, not just changed blocks."""
        llm = _make_llm(accurate=True, corrected="")
        svc = _make_service(llm_service=llm)

        # No code_changes — without force_audit_all this would return immediately
        updated, changes = svc._audit_and_update_adjacent_prose(
            content=CONTENT_WITH_TWO_BLOCKS,
            file_path="fake.md",
            file_examples=[],
            code_changes=[],
            force_audit_all=True,
        )
        # LLM must have been called at least once (for each code-adjacent prose section)
        assert llm.review_prose_against_code.call_count >= 1

    def test_without_force_audit_all_no_llm_call_when_no_changes(self, tmp_path):
        """Without force_audit_all, no LLM call when code_changes is empty."""
        llm = _make_llm(accurate=True, corrected="")
        svc = _make_service(llm_service=llm)

        updated, changes = svc._audit_and_update_adjacent_prose(
            content=CONTENT_WITH_TWO_BLOCKS,
            file_path="fake.md",
            file_examples=[],
            code_changes=[],
            force_audit_all=False,
        )
        assert llm.review_prose_against_code.call_count == 0
        assert changes == []

    def test_extract_called_once_when_force_audit_all(self, tmp_path):
        """extract_adjacent_prose_sections() called exactly once (not twice) with force_audit_all."""
        llm = _make_llm(accurate=True, corrected="")
        svc = _make_service(llm_service=llm)

        with patch.object(
            svc.article_validator,
            "extract_adjacent_prose_sections",
            wraps=svc.article_validator.extract_adjacent_prose_sections,
        ) as mock_extract:
            svc._audit_and_update_adjacent_prose(
                content=CONTENT_WITH_TWO_BLOCKS,
                file_path="fake.md",
                file_examples=[],
                code_changes=[],
                force_audit_all=True,
            )
        assert mock_extract.call_count == 1, (
            f"extract_adjacent_prose_sections called {mock_extract.call_count} times; expected 1"
        )
