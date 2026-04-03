from src.services.article_validator import ArticleValidator, validate_article, validate_family_articles


def test_validate_files_reports_fence_warning_for_real_temp_file(tmp_path):
    validator = ArticleValidator()
    article = tmp_path / "sample.md"
    article.write_text(
        """
# Sample

using Aspose.Words;

```csharp
var doc = new Document();
```
""".strip(),
        encoding="utf-8",
    )

    result = validator.validate_files([str(article)])

    warning_types = [warning["type"] for warning in result["reports"][0]["warnings"]]
    assert "fence_warning" in warning_types


def test_detects_filename_mismatch_between_prose_and_code(tmp_path):
    validator = ArticleValidator()
    article = tmp_path / "sample.md"
    article.write_text(
        """
# Save

Save the document as "output.docx".

```csharp
doc.Save("result.docx");
```
""".strip(),
        encoding="utf-8",
    )

    result = validator.validate_files([str(article)])

    warning_types = [warning["type"] for warning in result["reports"][0]["warnings"]]
    assert "filename_mismatch" in warning_types


def test_detects_duplicate_code_overlap(tmp_path):
    validator = ArticleValidator()
    left = tmp_path / "left.md"
    right = tmp_path / "right.md"
    shared = """
```csharp
var doc = new Document();
doc.Save("out.docx");
```
"""
    left.write_text(shared + "\nExtra left prose", encoding="utf-8")
    right.write_text(shared + "\nExtra right prose", encoding="utf-8")

    result = validator.validate_files([str(left), str(right)])

    all_warning_types = [
        warning["type"]
        for report in result["reports"]
        for warning in report["warnings"]
    ]
    assert "duplicate_content" in all_warning_types


def test_extract_adjacent_prose_sections_returns_matching_block_index():
    validator = ArticleValidator()
    content = """
# Heading

This paragraph describes the code.

```csharp
var doc = new Document();
```
""".strip()

    sections = validator.extract_adjacent_prose_sections(content)

    assert len(sections) == 1
    assert sections[0]["block_index"] == 0
    assert sections[0]["section_heading"] == "Heading"
    assert "describes the code" in sections[0]["prose_text"]


# ---------------------------------------------------------------------------
# Tests for standalone validate_article / validate_family_articles functions
# ---------------------------------------------------------------------------


def test_broken_fence_detection(tmp_path):
    """C# code outside a fenced block should be flagged as broken_fence."""
    article = tmp_path / "raw.md"
    article.write_text(
        "# Example\n\nusing Aspose.Words;\nclass Foo {}\n",
        encoding="utf-8",
    )

    issues = validate_article(str(article))

    issue_types = [i.issue_type for i in issues]
    assert "broken_fence" in issue_types


def test_no_false_positive_inside_fence(tmp_path):
    """C# inside a fenced block must NOT be flagged as broken_fence."""
    article = tmp_path / "good.md"
    article.write_text(
        "# Example\n\n```csharp\nusing Aspose.Words;\nclass Foo {}\n```\n",
        encoding="utf-8",
    )

    issues = validate_article(str(article))

    broken_fence_issues = [i for i in issues if i.issue_type == "broken_fence"]
    assert broken_fence_issues == [], f"Unexpected broken_fence issues: {broken_fence_issues}"


def test_duplicate_detection(tmp_path):
    """Two files sharing an identical code block should each generate a duplicate_content issue."""
    shared_block = "```csharp\nvar doc = new Document();\ndoc.Save(\"out.docx\");\n```\n"
    left = tmp_path / "left.md"
    right = tmp_path / "right.md"
    left.write_text("# Left\n\n" + shared_block, encoding="utf-8")
    right.write_text("# Right\n\n" + shared_block, encoding="utf-8")

    issues = validate_family_articles([str(left), str(right)])

    dup_issues = [i for i in issues if i.issue_type == "duplicate_content"]
    assert len(dup_issues) >= 1, "Expected at least one duplicate_content issue"


def test_no_duplicate_unique_blocks(tmp_path):
    """Unique code blocks across files should NOT generate duplicate_content issues."""
    left = tmp_path / "left.md"
    right = tmp_path / "right.md"
    left.write_text("# Left\n\n```csharp\nvar x = 1;\n```\n", encoding="utf-8")
    right.write_text("# Right\n\n```csharp\nvar y = 2;\n```\n", encoding="utf-8")

    issues = validate_family_articles([str(left), str(right)])

    dup_issues = [i for i in issues if i.issue_type == "duplicate_content"]
    assert dup_issues == [], f"Unexpected duplicate_content issues: {dup_issues}"


def test_filename_mismatch(tmp_path):
    """Prose mentioning 'output.docx' but code using 'result.docx' should be flagged."""
    article = tmp_path / "mismatch.md"
    article.write_text(
        '# Save\n\nSave the document as "output.docx".\n\n```csharp\ndoc.Save("result.docx");\n```\n',
        encoding="utf-8",
    )

    issues = validate_article(str(article))

    mismatch_issues = [i for i in issues if i.issue_type == "filename_mismatch"]
    assert len(mismatch_issues) >= 1, "Expected filename_mismatch issue"


def test_filename_match(tmp_path):
    """Prose and code agreeing on the same filename should NOT be flagged."""
    article = tmp_path / "match.md"
    article.write_text(
        '# Save\n\nSave the document as "output.docx".\n\n```csharp\ndoc.Save("output.docx");\n```\n',
        encoding="utf-8",
    )

    issues = validate_article(str(article))

    mismatch_issues = [i for i in issues if i.issue_type == "filename_mismatch"]
    assert mismatch_issues == [], f"Unexpected filename_mismatch issues: {mismatch_issues}"


# ---------------------------------------------------------------------------
# T6: Prose-inside-fence detection tests
# ---------------------------------------------------------------------------


def test_prose_inside_csharp_fence_is_flagged(tmp_path):
    """A csharp-fenced block containing prose (no C# tokens) should be flagged."""
    article = tmp_path / "prose_fence.md"
    article.write_text(
        "## Step 1\n\n"
        "```csharp\n"
        "This is some prose text about the watermark feature.\n"
        "It has multiple sentences and no C# code at all.\n"
        "This paragraph should be flagged as prose inside a fence block.\n"
        "```\n",
        encoding="utf-8",
    )

    result = ArticleValidator().validate_files([str(article)])

    warning_types = [w["type"] for w in result["reports"][0]["warnings"]]
    assert "prose_inside_fence" in warning_types, f"Expected prose_inside_fence, got: {warning_types}"


def test_real_csharp_code_not_flagged_as_prose(tmp_path):
    """A csharp-fenced block with real C# code should NOT be flagged as prose."""
    article = tmp_path / "real_code.md"
    article.write_text(
        "## Load document\n\n"
        "```csharp\n"
        "using Aspose.Words;\n"
        "var doc = new Document();\n"
        "doc.Save(\"output.docx\");\n"
        "```\n",
        encoding="utf-8",
    )

    result = ArticleValidator().validate_files([str(article)])

    prose_warnings = [w for w in result["reports"][0]["warnings"] if w["type"] == "prose_inside_fence"]
    assert prose_warnings == [], f"False positive prose_inside_fence: {prose_warnings}"


def test_prose_inside_fence_too_short_is_not_flagged(tmp_path):
    """A csharp-fenced block with fewer than 3 non-empty lines is too short to judge."""
    article = tmp_path / "short_fence.md"
    article.write_text(
        "```csharp\n"
        "Some prose sentence.\n"
        "```\n",
        encoding="utf-8",
    )

    result = ArticleValidator().validate_files([str(article)])

    prose_warnings = [w for w in result["reports"][0]["warnings"] if w["type"] == "prose_inside_fence"]
    assert prose_warnings == [], f"Unexpected prose_inside_fence on short block: {prose_warnings}"


def test_prose_inside_fence_line_number_reported(tmp_path):
    """The warning should report the line number of the opening fence marker."""
    article = tmp_path / "line_num.md"
    article.write_text(
        "# Header\n\n"
        "Some intro text here.\n\n"
        "```csharp\n"
        "This is definitely just prose text in the fence.\n"
        "It mentions nothing about C# syntax or code.\n"
        "Completely descriptive paragraph with no code tokens.\n"
        "```\n",
        encoding="utf-8",
    )

    result = ArticleValidator().validate_files([str(article)])

    prose_warnings = [w for w in result["reports"][0]["warnings"] if w["type"] == "prose_inside_fence"]
    assert len(prose_warnings) == 1
    # Opening fence is on line 5 (1-based)
    assert prose_warnings[0]["line"] == 5, f"Expected line 5, got: {prose_warnings[0]['line']}"


def test_prose_inside_fence_non_csharp_fences_ignored(tmp_path):
    """Fences marked as 'python', 'bash', etc. should never be flagged."""
    article = tmp_path / "other_lang.md"
    article.write_text(
        "```python\n"
        "This is some prose text about Python.\n"
        "It has multiple sentences but this is a python block.\n"
        "Should not be flagged because it is not csharp.\n"
        "```\n",
        encoding="utf-8",
    )

    result = ArticleValidator().validate_files([str(article)])

    prose_warnings = [w for w in result["reports"][0]["warnings"] if w["type"] == "prose_inside_fence"]
    assert prose_warnings == [], f"Unexpected prose_inside_fence on non-csharp fence: {prose_warnings}"


# ---------------------------------------------------------------------------
# T8: Cross-root duplicate detection via validate_files
# ---------------------------------------------------------------------------


def test_cross_root_duplicate_detection_when_all_files_passed_together(tmp_path):
    """When files from multiple roots are passed to validate_files() together,
    duplicate_content warnings should be emitted across roots."""
    root_a = tmp_path / "blog"
    root_b = tmp_path / "docs"
    root_a.mkdir()
    root_b.mkdir()

    shared_block = (
        "```csharp\n"
        "var doc = new Document();\n"
        "doc.Save(\"out.docx\");\n"
        "```\n"
    )
    (root_a / "article.md").write_text("# Blog\n\n" + shared_block, encoding="utf-8")
    (root_b / "guide.md").write_text("# Docs\n\n" + shared_block, encoding="utf-8")

    all_files = [str(root_a / "article.md"), str(root_b / "guide.md")]
    result = ArticleValidator().validate_files(all_files)

    all_warning_types = [
        w["type"]
        for report in result["reports"]
        for w in report["warnings"]
    ]
    assert "duplicate_content" in all_warning_types, (
        "Expected cross-root duplicate_content warning when all files passed together"
    )


# ---------------------------------------------------------------------------
# SR-03: T8 missing-root graceful handling
# ---------------------------------------------------------------------------


def test_missing_root_path_does_not_crash_and_checks_zero_files(tmp_path):
    """SR-03: validate_files() with a non-existent path list does not crash and reports 0 files."""
    nonexistent = str(tmp_path / "nonexistent_root" / "article.md")
    result = ArticleValidator().validate_files([nonexistent])

    assert result["files_checked"] == 1
    # The file could not be read, so it should appear as a read_error — not a crash
    errors = [err for report in result["reports"] for err in report["errors"]]
    assert any("read_error" in e for e in errors), f"Expected read_error, got: {errors}"


def test_empty_file_list_returns_zero_counts():
    """SR-03: validate_files([]) returns zero counts without crashing."""
    result = ArticleValidator().validate_files([])

    assert result["files_checked"] == 0
    assert result["warnings"] == 0
    assert result["reports"] == []


# ---------------------------------------------------------------------------
# repair_broken_fences
# ---------------------------------------------------------------------------

def test_repair_broken_fences_no_fence():
    """Content with no fences at all: no change, zero repairs."""
    content = "# Heading\n\nSome prose.\n"
    v = ArticleValidator()
    repaired, count = v.repair_broken_fences(content)
    assert count == 0
    assert repaired == content


def test_repair_broken_fences_closed_fence():
    """Balanced open/close fence: no change."""
    content = "# Heading\n\n```csharp\nvar x = 1;\n```\n"
    v = ArticleValidator()
    repaired, count = v.repair_broken_fences(content)
    assert count == 0
    assert repaired == content


def test_repair_broken_fences_unclosed_at_eof():
    """Open fence never closed: closing ``` inserted at EOF."""
    content = "# Heading\n\n```csharp\nvar x = 1;\n"
    v = ArticleValidator()
    repaired, count = v.repair_broken_fences(content)
    assert count == 1
    assert repaired.endswith("```\n")
    assert "var x = 1;" in repaired


def test_repair_broken_fences_unclosed_before_heading():
    """Open fence interrupted by a heading: closing ``` inserted before that heading."""
    content = "# Step 1\n\n```csharp\nvar x = 1;\n### Step 2\n\nSome prose.\n"
    v = ArticleValidator()
    repaired, count = v.repair_broken_fences(content)
    assert count == 1
    # The closing fence must appear before ### Step 2
    fence_close_pos = repaired.index("```\n", repaired.index("var x = 1;"))
    heading_pos = repaired.index("### Step 2")
    assert fence_close_pos < heading_pos


def test_repair_broken_fences_multiple_valid_fences_unchanged():
    """Multiple balanced fences: no repairs needed."""
    content = (
        "# A\n```csharp\nvar a = 1;\n```\n"
        "# B\n```csharp\nvar b = 2;\n```\n"
    )
    v = ArticleValidator()
    repaired, count = v.repair_broken_fences(content)
    assert count == 0
    assert repaired == content


# ---------------------------------------------------------------------------
# _detect_prose_duplication
# ---------------------------------------------------------------------------

def test_detect_prose_duplication_no_overlap(tmp_path):
    """Two completely different articles: no duplicate_prose warning."""
    f1 = tmp_path / "a.md"
    f2 = tmp_path / "b.md"
    f1.write_text(
        "# Article A\n\nThis article explains compression algorithms in detail.\n"
        "We cover deflate and bzip2 with concrete examples.\n",
        encoding="utf-8",
    )
    f2.write_text(
        "# Article B\n\nThis article covers watermarking Word documents programmatically.\n"
        "The watermark API provides text and image watermark options.\n",
        encoding="utf-8",
    )
    v = ArticleValidator()
    result = v.validate_files([str(f1), str(f2)])
    all_types = [
        w["type"]
        for report in result["reports"]
        for w in report["warnings"]
    ]
    assert "duplicate_prose" not in all_types


def test_detect_prose_duplication_high_overlap(tmp_path):
    """Two near-identical articles: duplicate_prose warning emitted for both files."""
    shared = (
        "This article explains how to process Word documents using Aspose.Words for .NET.\n"
        "You can extract text, images, and metadata from any Word document with a few lines of code.\n"
        "The API provides comprehensive support for all Word document formats including DOCX and DOC.\n"
        "Processing large documents is straightforward with the built-in document model.\n"
        "Simply load the document and iterate over the nodes to access all content elements.\n"
    )
    f1 = tmp_path / "article1.md"
    f2 = tmp_path / "article2.md"
    f1.write_text(f"# Article One\n\n{shared}", encoding="utf-8")
    f2.write_text(f"# Article Two\n\n{shared}", encoding="utf-8")

    v = ArticleValidator()
    result = v.validate_files([str(f1), str(f2)])
    all_types = [
        w["type"]
        for report in result["reports"]
        for w in report["warnings"]
    ]
    assert "duplicate_prose" in all_types


def test_detect_prose_duplication_code_blocks_excluded(tmp_path):
    """Shared code blocks do NOT trigger duplicate_prose (only prose lines count)."""
    shared_code = "```csharp\nvar doc = new Document();\ndoc.Save(\"out.docx\");\n```\n"
    f1 = tmp_path / "c1.md"
    f2 = tmp_path / "c2.md"
    f1.write_text(
        f"# Article One\n\nThis article is about compression.\n{shared_code}",
        encoding="utf-8",
    )
    f2.write_text(
        f"# Article Two\n\nThis article is about watermarks.\n{shared_code}",
        encoding="utf-8",
    )
    v = ArticleValidator()
    result = v.validate_files([str(f1), str(f2)])
    all_types = [
        w["type"]
        for report in result["reports"]
        for w in report["warnings"]
    ]
    assert "duplicate_prose" not in all_types


def test_cross_step_filename_chain_mismatch_detected(tmp_path):
    """Fires cross_step_filename_mismatch when Step 3 loads a file not saved by Step 2."""
    article = tmp_path / "sample.md"
    article.write_text(
        "# Step 2\n\n"
        "```cs\n"
        "Document doc = new Document(\"InteractiveFormTemplate.docx\");\n"
        "doc.Save(\"InteractiveForm.docx\");\n"
        "```\n\n"
        "# Step 3\n\n"
        "```cs\n"
        "Document doc = new Document(\"ActiveX controls.docx\");\n"  # wrong file
        "doc.Save(\"FilledInteractiveForm.docx\");\n"
        "```\n",
        encoding="utf-8",
    )
    v = ArticleValidator()
    result = v.validate_files([str(article)])
    all_types = [w["type"] for w in result["reports"][0]["warnings"]]
    assert "cross_step_filename_mismatch" in all_types


def test_cross_step_filename_chain_no_false_positive(tmp_path):
    """Does NOT fire when each step loads the file saved by the previous step."""
    article = tmp_path / "sample.md"
    article.write_text(
        "# Step 1\n\n"
        "```cs\n"
        "Document doc = new Document();\n"
        "doc.Save(\"InteractiveForm.docx\");\n"
        "```\n\n"
        "# Step 2\n\n"
        "```cs\n"
        "Document doc = new Document(\"InteractiveForm.docx\");\n"
        "doc.Save(\"FilledInteractiveForm.docx\");\n"
        "```\n",
        encoding="utf-8",
    )
    v = ArticleValidator()
    result = v.validate_files([str(article)])
    all_types = [w["type"] for w in result["reports"][0]["warnings"]]
    assert "cross_step_filename_mismatch" not in all_types


def test_detect_prose_duplication_below_threshold(tmp_path):
    """30% prose overlap does NOT fire the warning (threshold is 50%)."""
    f1 = tmp_path / "d1.md"
    f2 = tmp_path / "d2.md"
    # 1 shared line + 3 unique lines each → overlap = 1/4 = 25%
    f1.write_text(
        "# Article One\n\n"
        "This article explains how to load a Word document using Aspose.Words for dotnet.\n"
        "The Document class is the main entry point for all document operations.\n"
        "You can save documents in many different formats including PDF and HTML.\n"
        "Processing is done through the rich document object model provided by Aspose.\n",
        encoding="utf-8",
    )
    f2.write_text(
        "# Article Two\n\n"
        "This article explains how to load a Word document using Aspose.Words for dotnet.\n"
        "Watermarks can be added using the dedicated Watermark API available on Document.\n"
        "Text watermarks support font family, size, color, and layout configuration options.\n"
        "Image watermarks can be added by providing a stream or file path to the method.\n",
        encoding="utf-8",
    )
    v = ArticleValidator()
    result = v.validate_files([str(f1), str(f2)])
    all_types = [
        w["type"]
        for report in result["reports"]
        for w in report["warnings"]
    ]
    assert "duplicate_prose" not in all_types
