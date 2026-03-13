from src.services.behavioral_pattern_scanner import BehavioralPatternScanner


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
