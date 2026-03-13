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
