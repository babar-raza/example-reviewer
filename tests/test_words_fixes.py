"""
Unit tests for src/services/family_fixes/words_fixes.py

Covers:
- fix_commentrange_node_insertion (existing)
- fix_comment_text_setter (G1 addition)
- fix_comment_text_setter idempotency and negative cases
"""
import pytest
from src.services.family_fixes.words_fixes import (
    fix_comment_anchor_with_ranges,
    fix_commentrange_node_insertion,
    fix_comment_manual_paragraph_workaround,
    fix_comment_text_setter,
    fix_stop_track_revisions_before_save,
    get_synthesis_harness,
    CATALOG_VERIFIED,
)


class TestCatalogVerified:
    def test_all_required_keys_present(self):
        required = {'CommentRangeStart', 'CommentRangeEnd', 'InsertBefore', 'InsertAfter',
                    'Comment', 'Run', 'FirstParagraph', 'StartTrackRevisions', 'StopTrackRevisions'}
        assert required.issubset(CATALOG_VERIFIED.keys())

    def test_all_values_true(self):
        assert all(CATALOG_VERIFIED.values()), "All CATALOG_VERIFIED entries must be True"


class TestWordsSynthesisHarness:
    def test_strips_framework_wrapper_artifacts_from_watermark_controller(self):
        body = """
namespace WatermarkAPI.Controllers
    public class WatermarkController : ControllerBase
        public async Task<IActionResult> AddWatermark(IFormFile file, [FromQuery] string watermarkText)
                Document doc = new Document(tempFilePath);
                AddTextWatermark(doc, watermarkText);
                doc.Save(outputStream, SaveFormat.Docx);
        private void AddTextWatermark(Document doc, string text)
            foreach (Section section in doc.Sections)
                var watermark = new Shape(doc, ShapeType.TextPlainText)
                    TextPath = { Text = text, FontFamily = "Arial" },
                    WrapType = WrapType.None,
                    RelativeHorizontalPosition = RelativeHorizontalPosition.Page,
                    RelativeVerticalPosition = RelativeVerticalPosition.Page,
                section.HeadersFooters[HeaderFooterType.HeaderPrimary]?.AppendChild(watermark);
""".strip()

        harness = get_synthesis_harness(body)

        assert "ControllerBase" not in harness
        assert "IActionResult" not in harness
        assert 'Document doc = new Document("Blank.docx");' in harness
        assert 'string watermarkText = "Watermark";' in harness
        assert 'doc.Save("output.docx");' in harness
        assert 'TextPath = { Text = watermarkText, FontFamily = "Arial" },' in harness
        assert "using Aspose.Words.Drawing;" in harness

    def test_preserves_simple_body_without_wrapper_noise(self):
        body = """
Document doc = new Document("Blank.docx");
doc.Save("output.docx");
""".strip()

        harness = get_synthesis_harness(body)

        assert 'Document doc = new Document("Blank.docx");' in harness
        assert 'doc.Save("output.docx");' in harness


class TestFixCommentTextSetter:
    """Tests for fix_comment_text_setter (G1 — Comment.Text setter removed in v26.1.0)."""

    NULLREF_ERROR = "System.NullReferenceException: Object reference not set to an instance of an object."
    COMPILE_ERROR = "error CS0117: 'Comment' does not contain a definition for 'Text'"

    def _make_code(self, comment_var="comment", doc_var="doc", text='"Hello"'):
        return f"""
var {comment_var} = new Comment({doc_var}, "Author", "AuthorId", DateTime.Now);
{comment_var}.Text = {text};
para.AppendChild({comment_var});
""".strip()

    def test_happy_path_rewrites_text_setter(self):
        code = self._make_code()
        result = fix_comment_text_setter(code, self.NULLREF_ERROR)
        assert result is not None, "Expected fix to apply"
        fixed_code, desc = result
        assert "comment.AppendChild(new Paragraph(doc));" in fixed_code
        assert "comment.FirstParagraph.AppendChild(new Run(doc, \"Hello\"));" in fixed_code
        assert "comment.Text =" not in fixed_code
        assert "Comment.Text setter" in desc

    def test_idempotency_does_not_apply_twice(self):
        code = self._make_code()
        result1 = fix_comment_text_setter(code, self.NULLREF_ERROR)
        assert result1 is not None
        fixed_code, _ = result1
        # Second application should return None (already fixed)
        result2 = fix_comment_text_setter(fixed_code, self.NULLREF_ERROR)
        assert result2 is None, "Fix must be idempotent: second application should return None"

    def test_no_match_if_no_nullref_in_error(self):
        code = self._make_code()
        result = fix_comment_text_setter(code, "CS0246: Type 'Comment' could not be found")
        assert result is None, "Must not apply without a Comment.Text-related error"

    def test_no_match_if_no_text_setter(self):
        code = """
var comment = new Comment(doc, "Author", "AuthorId", DateTime.Now);
para.AppendChild(comment);
""".strip()
        result = fix_comment_text_setter(code, self.NULLREF_ERROR)
        assert result is None, "Must not apply if no .Text = assignment"

    def test_no_match_if_not_comment_variable(self):
        # .Text = is present but on a non-Comment variable
        code = """
var shape = new Shape(doc, ShapeType.TextBox);
shape.Text = "Watermark";
""".strip()
        result = fix_comment_text_setter(code, self.NULLREF_ERROR)
        assert result is None, "Must not rewrite .Text = on non-Comment variables"

    def test_preserves_doc_variable_name(self):
        code = """
var myDoc = new Document();
var c = new Comment(myDoc, "A", "B", DateTime.Now);
c.Text = "test text";
""".strip()
        result = fix_comment_text_setter(code, self.NULLREF_ERROR)
        assert result is not None
        fixed, _ = result
        assert "new Run(myDoc," in fixed, "Should use the correct doc variable from new Comment(...)"

    def test_system_nullref_variant_matches(self):
        code = self._make_code()
        result = fix_comment_text_setter(code, "System.NullReferenceException: ...")
        assert result is not None, "Should match 'System.NullReferenceException' prefix variant"

    def test_compile_error_variant_matches(self):
        code = self._make_code()
        result = fix_comment_text_setter(code, self.COMPILE_ERROR)
        assert result is not None, "Should match compile-time Comment.Text errors"

    def test_object_initializer_variant_rewritten(self):
        code = """
Comment comment = new Comment(doc, "Reviewer Name", "RN", DateTime.Now)
{
    Text = "This section needs additional explanation."
};
""".strip()
        result = fix_comment_text_setter(code, self.COMPILE_ERROR)
        assert result is not None
        fixed, _ = result
        assert 'Comment comment = new Comment(doc, "Reviewer Name", "RN", DateTime.Now);' in fixed
        assert "comment.AppendChild(new Paragraph(doc));" in fixed
        assert 'comment.FirstParagraph.AppendChild(new Run(doc, "This section needs additional explanation."));' in fixed
        assert "Text =" not in fixed


class TestFixCommentrangeNodeInsertion:
    """Regression tests for the existing fix (must still work after refactor)."""

    CANNOT_INSERT_ERROR = "Cannot insert a node of this type at this location."

    def test_rewrite_appendchild_to_insertbefore(self):
        code = """
var commentRangeStart = new CommentRangeStart(doc, commentId);
para.AppendChild(commentRangeStart);
""".strip()
        result = fix_commentrange_node_insertion(code, self.CANNOT_INSERT_ERROR)
        assert result is not None
        fixed, desc = result
        assert "InsertBefore" in fixed or "InsertAfter" in fixed
        assert "AppendChild" not in fixed

    def test_no_match_without_error_keyword(self):
        code = "para.AppendChild(commentRangeStart);"
        result = fix_commentrange_node_insertion(code, "CS0246: type not found")
        assert result is None

    def test_idempotent_when_already_fixed(self):
        code = """
para.InsertBefore(commentRangeStart, para.Runs[0]);
""".strip()
        result = fix_commentrange_node_insertion(code, self.CANNOT_INSERT_ERROR)
        assert result is None, "Must not reapply if InsertBefore already present"


class TestFixCommentManualParagraphWorkaround:
    CANNOT_INSERT_ERROR = "Cannot insert a node of this type at this location."

    def test_normalizes_paragraphs_add_variant(self):
        code = """
Comment comment = new Comment(doc, "Reviewer Name", "RN", DateTime.Now);
comment.Paragraphs.Add(new Paragraph(doc));
comment.FirstParagraph.AppendChild(new Run(doc, "This section needs additional explanation."));
Paragraph para = doc.FirstSection.Body.FirstParagraph;
para.AppendChild(comment);
""".strip()

        result = fix_comment_manual_paragraph_workaround(code, self.CANNOT_INSERT_ERROR)

        assert result is not None, "Expected workaround fix to apply"
        fixed, desc = result
        assert 'comment.AppendChild(new Paragraph(doc));' in fixed
        assert 'comment.Paragraphs.Add(new Paragraph(doc));' not in fixed
        assert 'comment.FirstParagraph.AppendChild(new Run(doc, "This section needs additional explanation."));' in fixed
        assert "normalized" in desc

    def test_no_match_without_runtime_error(self):
        code = """
Comment comment = new Comment(doc, "Reviewer Name", "RN", DateTime.Now);
comment.Paragraphs.Add(new Paragraph(doc));
comment.FirstParagraph.AppendChild(new Run(doc, "This section needs additional explanation."));
""".strip()

        result = fix_comment_manual_paragraph_workaround(code, "CS1061: member not found")

        assert result is None

    def test_rewrites_comment_para_variant_to_catalog_shape(self):
        code = """
Comment comment = new Comment(doc, "Reviewer Name", "RN", DateTime.Now);
Paragraph commentPara = new Paragraph(doc);
commentPara.AppendChild(new Run(doc, "This section needs additional explanation."));
comment.AppendChild(commentPara);
Paragraph para = doc.FirstSection.Body.FirstParagraph;
para.AppendChild(comment);
""".strip()

        result = fix_comment_manual_paragraph_workaround(code, self.CANNOT_INSERT_ERROR)

        assert result is not None
        fixed, _ = result
        assert 'comment.AppendChild(new Paragraph(doc));' in fixed
        assert 'comment.FirstParagraph.AppendChild(new Run(doc, "This section needs additional explanation."));' in fixed
        assert "Paragraph commentPara = new Paragraph(doc);" not in fixed
        assert 'comment.AppendChild(commentPara);' not in fixed


class TestFixCommentAnchorWithRanges:
    CANNOT_INSERT_ERROR = "Cannot insert a node of this type at this location."

    def test_rewrites_para_append_comment_to_range_anchor_pattern(self):
        code = """
Comment comment = new Comment(doc, "Reviewer Name", "RN", DateTime.Now);
comment.AppendChild(new Paragraph(doc));
comment.FirstParagraph.AppendChild(new Run(doc, "This section needs additional explanation."));
Paragraph para = doc.FirstSection.Body.FirstParagraph;
para.AppendChild(comment);
""".strip()

        result = fix_comment_anchor_with_ranges(code, self.CANNOT_INSERT_ERROR)

        assert result is not None
        fixed, desc = result
        assert 'CommentRangeStart commentRangeStart = new CommentRangeStart(doc, comment.Id);' in fixed
        assert 'CommentRangeEnd commentRangeEnd = new CommentRangeEnd(doc, comment.Id);' in fixed
        assert 'para.InsertBefore(commentRangeStart, commentAnchorStart);' in fixed
        assert 'para.InsertAfter(commentRangeEnd, commentAnchorEnd);' in fixed
        assert 'para.InsertAfter(comment, commentRangeEnd);' in fixed
        assert 'para.AppendChild(comment);' not in fixed
        assert "Comment anchor" in desc

    def test_also_inserts_stop_track_before_save_when_tracking_is_enabled(self):
        code = """
Comment comment = new Comment(doc, "Reviewer Name", "RN", DateTime.Now);
comment.AppendChild(new Paragraph(doc));
comment.FirstParagraph.AppendChild(new Run(doc, "This section needs additional explanation."));
Paragraph para = doc.FirstSection.Body.FirstParagraph;
para.AppendChild(comment);
doc.StartTrackRevisions("Reviewer Name");
doc.Save("ReviewedDocument.docx");
""".strip()

        result = fix_comment_anchor_with_ranges(code, self.CANNOT_INSERT_ERROR)

        assert result is not None
        fixed, _ = result
        assert 'doc.StopTrackRevisions();' in fixed
        assert fixed.index('doc.StopTrackRevisions();') < fixed.index('doc.Save("ReviewedDocument.docx");')

    def test_idempotent_when_ranges_already_present(self):
        code = """
Comment comment = new Comment(doc, "Reviewer Name", "RN", DateTime.Now);
CommentRangeStart commentRangeStart = new CommentRangeStart(doc, comment.Id);
CommentRangeEnd commentRangeEnd = new CommentRangeEnd(doc, comment.Id);
para.InsertAfter(comment, commentRangeEnd);
""".strip()

        result = fix_comment_anchor_with_ranges(code, self.CANNOT_INSERT_ERROR)

        assert result is None


class TestFixStopTrackRevisionsBeforeSave:
    CANNOT_INSERT_ERROR = "Cannot insert a node of this type at this location."

    def test_inserts_stop_before_save_for_started_document(self):
        code = """
Document doc = new Document();
doc.StartTrackRevisions("Reviewer Name");
doc.Save("output.docx");
""".strip()

        result = fix_stop_track_revisions_before_save(code, self.CANNOT_INSERT_ERROR)

        assert result is not None
        fixed, desc = result
        assert 'doc.StopTrackRevisions();' in fixed
        assert fixed.index('doc.StopTrackRevisions();') < fixed.index('doc.Save("output.docx");')
        assert "Track revisions" in desc

    def test_preserves_custom_document_variable(self):
        code = """
var sourceDoc = new Document();
sourceDoc.StartTrackRevisions("Reviewer Name", DateTime.Now);
sourceDoc.Save("tracked.docx");
""".strip()

        result = fix_stop_track_revisions_before_save(code, self.CANNOT_INSERT_ERROR)

        assert result is not None
        fixed, _ = result
        assert 'sourceDoc.StopTrackRevisions();' in fixed
        assert fixed.index('sourceDoc.StopTrackRevisions();') < fixed.index('sourceDoc.Save("tracked.docx");')

    def test_idempotent_when_stop_already_present(self):
        code = """
Document doc = new Document();
doc.StartTrackRevisions("Reviewer Name");
doc.StopTrackRevisions();
doc.Save("output.docx");
""".strip()

        result = fix_stop_track_revisions_before_save(code, self.CANNOT_INSERT_ERROR)

        assert result is None

    def test_no_match_without_runtime_error(self):
        code = """
Document doc = new Document();
doc.StartTrackRevisions("Reviewer Name");
doc.Save("output.docx");
""".strip()

        result = fix_stop_track_revisions_before_save(code, "CS1061: member not found")

        assert result is None

    def test_no_match_without_track_revisions(self):
        code = """
Document doc = new Document();
doc.Save("output.docx");
""".strip()

        result = fix_stop_track_revisions_before_save(code, self.CANNOT_INSERT_ERROR)

        assert result is None
