import json

import pytest

from src.services.behavioral_pattern_scanner import BehavioralPatternScanner
from src.services.kb import KBLoadError


def test_detects_write_protection_used_for_encryption_article():
    scanner = BehavioralPatternScanner()
    code = """
var doc = new Document();
doc.WriteProtection.SetPassword("secret");
doc.Save("protected.docx");
""".strip()

    findings = scanner.scan_example(
        "words",
        code,
        article_intent="Encrypt a Word file with a password before saving it.",
    )

    assert any(f.pattern_id == "words_write_protection_not_encryption" for f in findings)


def test_detects_mail_merge_without_non_merge_fields_flag():
    scanner = BehavioralPatternScanner()
    code = """
var doc = new Document("template.docx");
doc.MailMerge.Execute(new[] { "Name" }, new object[] { "Alice" });
doc.Save("out.docx");
""".strip()

    findings = scanner.scan_example(
        "words",
        code,
        article_intent="Populate mustache tags in a template with mail merge data.",
    )

    assert any(f.pattern_id == "words_mailmerge_use_non_merge_fields" for f in findings)


def test_detects_manual_text_plain_text_watermark():
    scanner = BehavioralPatternScanner()
    code = """
var watermark = new Shape(doc, ShapeType.TextPlainText);
watermark.TextPath.Text = "Demo";
""".strip()

    findings = scanner.scan_example(
        "words",
        code,
        article_intent="Add a text watermark to a Word document.",
    )

    assert any(f.pattern_id == "words_shape_watermark_outdated" for f in findings)


def test_no_finding_without_matching_context():
    scanner = BehavioralPatternScanner()
    code = """
var doc = new Document();
doc.WriteProtection.SetPassword("secret");
""".strip()

    findings = scanner.scan_example(
        "words",
        code,
        article_intent="Protect a document from editing changes.",
    )

    assert findings == []


def test_words_patterns_all_compile():
    """T-KB-10: All words behavioral patterns load and compile without error.

    This test uses the real production file (config/families/words_behavioral_patterns.json).
    If a pattern's regex becomes invalid, this test will fail immediately — before
    the error is discovered silently at scan time.
    """
    scanner = BehavioralPatternScanner()
    patterns = scanner._load_patterns("words")
    assert len(patterns) > 0, (
        "Expected at least one pattern to load from words_behavioral_patterns.json. "
        "If the file was intentionally removed, this test needs updating."
    )


# --- Absence detection (required_regex) tests ---


def test_absence_detection_blank_pages_missing_builtin():
    """Article about removing blank pages that doesn't use RemoveBlankPages()."""
    scanner = BehavioralPatternScanner()
    code = """
var doc = new Document("input.docx");
for (int i = doc.PageCount - 1; i >= 0; i--)
{
    var page = doc.ExtractPages(i, 1);
    if (string.IsNullOrEmpty(page.GetText().Trim()))
        continue;
    result.AppendDocument(page, ImportFormatMode.KeepSourceFormatting);
}
result.Save("output.docx");
""".strip()

    findings = scanner.scan_example(
        "words",
        code,
        article_intent="How to remove blank pages from a Word document",
        content_type="kb",
    )

    assert any(f.pattern_id == "words_blank_pages_missing_builtin" for f in findings)


def test_absence_detection_no_false_positive_when_api_present():
    """Article about removing blank pages that DOES use RemoveBlankPages()."""
    scanner = BehavioralPatternScanner()
    code = """
var doc = new Document("input.docx");
doc.RemoveBlankPages();
doc.Save("output.docx");
""".strip()

    findings = scanner.scan_example(
        "words",
        code,
        article_intent="How to remove blank pages from a Word document",
        content_type="kb",
    )

    assert not any(f.pattern_id == "words_blank_pages_missing_builtin" for f in findings)


def test_absence_detection_no_false_positive_wrong_intent():
    """Article NOT about blank pages shouldn't trigger the absence pattern."""
    scanner = BehavioralPatternScanner()
    code = """
var doc = new Document("input.docx");
doc.Save("output.pdf", SaveFormat.Pdf);
""".strip()

    findings = scanner.scan_example(
        "words",
        code,
        article_intent="Convert a Word document to PDF format",
        content_type="kb",
    )

    assert not any(f.pattern_id == "words_blank_pages_missing_builtin" for f in findings)


def test_absence_detection_pdf_digital_signature_missing():
    """Article about signed PDF that doesn't use DigitalSignatureDetails."""
    scanner = BehavioralPatternScanner()
    code = """
DigitalSignatureUtil.Sign(filePath, signedPath, CertificateHolder.Create("cert.pfx", "pw"));
var doc = new Document(signedPath);
doc.Save("output.pdf", SaveFormat.Pdf);
""".strip()

    findings = scanner.scan_example(
        "words",
        code,
        article_intent="Create a digitally signed PDF document",
        content_type="kb",
    )

    assert any(f.pattern_id == "words_pdf_digital_signature_missing" for f in findings)


def test_absence_detection_content_type_scoping():
    """Absence patterns scoped to kb should not fire for blog content."""
    scanner = BehavioralPatternScanner()
    code = """
var doc = new Document("input.docx");
for (int i = 0; i < doc.PageCount; i++) { }
""".strip()

    findings = scanner.scan_example(
        "words",
        code,
        article_intent="How to remove blank pages from a Word document",
        content_type="blog",
    )

    assert not any(f.pattern_id == "words_blank_pages_missing_builtin" for f in findings)


# --- New presence-based pattern tests ---


def test_detects_pdf_form_flattening_warning():
    """Article about interactive forms that saves to PDF should warn about flattening."""
    scanner = BehavioralPatternScanner()
    code = """
doc.Save("InteractiveForm.pdf", SaveFormat.Pdf);
""".strip()

    findings = scanner.scan_example(
        "words",
        code,
        article_intent="Design fillable interactive forms and convert to PDF",
    )

    assert any(f.pattern_id == "words_pdf_form_flattening" for f in findings)


def test_detects_comment_text_setter():
    """Code using comment.Text = should be flagged as removed API."""
    scanner = BehavioralPatternScanner()
    code = """
var comment = new Comment(doc, "Author", "A", DateTime.Now);
comment.Text = "Review this section";
doc.FirstSection.Body.FirstParagraph.AppendChild(comment);
""".strip()

    findings = scanner.scan_example(
        "words",
        code,
        article_intent="Add comments to a Word document",
    )

    assert any(f.pattern_id == "words_comment_text_removed" for f in findings)


# ---------------------------------------------------------------------------
# TASK-023: KBLoadError propagation and cache behaviour
# ---------------------------------------------------------------------------

def test_load_patterns_raises_kb_load_error_on_broken_file(tmp_path):
    """_load_patterns raises KBLoadError when the patterns file is structurally broken.

    Proves the error is not swallowed at the scanner level, so callers
    (e.g. the orchestrator pre-flight check) can catch it explicitly.
    """
    broken_file = tmp_path / "testfam_behavioral_patterns.json"
    broken_file.write_text("{not valid json", encoding="utf-8")

    scanner = BehavioralPatternScanner(config_dir=str(tmp_path))
    with pytest.raises(KBLoadError):
        scanner._load_patterns("testfam")


def test_load_patterns_does_not_cache_on_kb_load_error(tmp_path):
    """After a KBLoadError, the family is NOT in the pattern cache.

    This ensures a subsequent call (e.g. after the file is fixed) will
    retry the load rather than serving a stale empty result.
    """
    broken_file = tmp_path / "testfam_behavioral_patterns.json"
    broken_file.write_text("{not valid json", encoding="utf-8")

    scanner = BehavioralPatternScanner(config_dir=str(tmp_path))
    with pytest.raises(KBLoadError):
        scanner._load_patterns("testfam")

    assert "testfam" not in scanner._pattern_cache


def test_scan_example_propagates_kb_load_error(tmp_path):
    """scan_example propagates KBLoadError when the patterns file is broken.

    The orchestrator pre-flight check calls _load_patterns directly and
    catches KBLoadError. This test proves the error is not silently absorbed
    inside scan_example, so the pre-flight mechanism works as designed.
    """
    broken_file = tmp_path / "testfam_behavioral_patterns.json"
    broken_file.write_text(
        json.dumps([{"id": "x", "severity": "error", "description": "d",
                     "code_regex": "[invalid"}]),
        encoding="utf-8",
    )

    scanner = BehavioralPatternScanner(config_dir=str(tmp_path))
    with pytest.raises(KBLoadError):
        scanner.scan_example("testfam", "some code here")
