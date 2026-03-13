"""
Aspose.Words family-specific runtime fix functions.

P1 compliance: All API types and methods used in fixes must be verified
in words_api_catalog.json before encoding. See catalog_verified dict below.

P2 compliance: This module only contains Words-specific logic.
Registration: calls register_runtime_fix('words', fn) for each fix.
"""
from __future__ import annotations
import re
import logging
from typing import Optional, Tuple

from src.services.family_fix_registry import register_runtime_fix, register_synthesis_harness, register_behavioral_fix

logger = logging.getLogger(__name__)

# Catalog-verified types and methods (confirmed in words_api_catalog.json).
# Verification date: 2026-03-12 via extract_assembly_catalog.py --full (Aspose.Words 26.1.0)
#   CommentRangeStart : True  (present in catalog['types'])
#   CommentRangeEnd   : True  (present in catalog['types'])
#   InsertBefore      : True  (confirmed: CompositeNode.key_methods after adding "InsertBefore"/"InsertAfter"
#                              to keyMethodNames in Program.cs and regenerating catalog)
#   InsertAfter       : True  (same)
#   StartTrackRevisions: True (confirmed: Document.key_methods in regenerated catalog)
#   StopTrackRevisions : True (confirmed: Document.key_methods in regenerated catalog)
CATALOG_VERIFIED = {
    # Key: type/method name, Value: confirmed present in catalog (True) or not confirmed (False)
    'CommentRangeStart': True,   # confirmed: words_api_catalog.json types dict
    'CommentRangeEnd': True,     # confirmed: words_api_catalog.json types dict
    'InsertBefore': True,        # confirmed: CompositeNode key_methods in regenerated catalog
    'InsertAfter': True,         # confirmed: CompositeNode key_methods in regenerated catalog
    'Comment': True,             # confirmed: words_api_catalog.json types dict
    'Run': True,                 # confirmed: words_api_catalog.json types dict
    'FirstParagraph': True,      # confirmed: Comment.FirstParagraph property in catalog
    'StartTrackRevisions': True, # confirmed: Document key_methods in regenerated catalog
    'StopTrackRevisions': True,  # confirmed: Document key_methods in regenerated catalog
}

# Gate: InsertBefore/InsertAfter must be catalog-verified before the fix is active.
_INSERTBEFORE_AFTER_VERIFIED = CATALOG_VERIFIED['InsertBefore'] and CATALOG_VERIFIED['InsertAfter']


def fix_commentrange_node_insertion(code: str, error_text: str) -> Optional[Tuple[str, str]]:
    """
    Fix: CommentRangeStart/End nodes inserted at wrong DOM level via AppendChild.

    Aspose.Words DOM rule: CommentRangeStart and CommentRangeEnd are inline nodes;
    they must be inserted relative to Run nodes within a Paragraph using
    InsertBefore/InsertAfter, not AppendChild on a block-level parent.

    Error trigger: "Cannot insert a node of this type at this location"
    Catalog dependency: CommentRangeStart (verified), CommentRangeEnd (verified),
                        InsertBefore (verified 2026-03-12, CompositeNode.key_methods),
                        InsertAfter  (verified 2026-03-12, CompositeNode.key_methods)
    """
    # Gate: only apply when error matches
    if 'Cannot insert a node of this type' not in error_text:
        return None

    # Gate: only if CommentRange pattern is in the code (case-insensitive: handles both
    # 'CommentRangeStart' type references and 'commentRangeStart' variable references)
    if 'ommentRange' not in code:
        return None

    # Idempotency: already fixed
    if 'InsertBefore(commentRange' in code or 'InsertAfter(commentRange' in code:
        return None

    # Pattern: detect .AppendChild(<commentRange arg>)
    # Handles two forms:
    #   1. Variable: para.AppendChild(commentRangeStart)  -- lowercase variable name
    #   2. New:      para.AppendChild(new CommentRangeStart(...))  -- inline construction
    # Group 1: parent var, Group 2: 'Start' or 'End' (case-insensitive suffix)
    append_pattern = re.compile(
        r'(\w+)\.AppendChild\(\s*'
        r'(?:'
        r'(?:new\s+)?[Cc]ommentRange(Start|End)\b'  # both forms; capture Start/End
        r')'
    )
    if not append_pattern.search(code):
        return None

    lines = code.split('\n')
    changed = False
    new_lines = []

    for line in lines:
        m = append_pattern.search(line)
        if m:
            parent_var = m.group(1)
            kind = m.group(2)  # 'Start' or 'End'
            # Extract the full argument being appended (variable or new-expression)
            arg_match = re.search(
                r'\.AppendChild\((\s*(?:new\s+)?[Cc]ommentRange(?:Start|End)[^)]*)\)',
                line
            )
            if arg_match:
                arg = arg_match.group(1).strip()
                old_call = f'{parent_var}.AppendChild({arg_match.group(1)})'
                if kind == 'Start':
                    # Insert before the first run in the paragraph
                    new_call = f'{parent_var}.InsertBefore({arg}, {parent_var}.Runs[0])'
                else:
                    # Insert after the last child in the paragraph
                    new_call = f'{parent_var}.InsertAfter({arg}, {parent_var}.LastChild)'
                new_line = line.replace(old_call, new_call, 1)
                new_lines.append(new_line)
                changed = True
                continue
        new_lines.append(line)

    if not changed:
        return None

    return (
        '\n'.join(new_lines),
        "CommentRange: rewrote AppendChild to InsertBefore/InsertAfter (inline node DOM fix)",
    )


# Words harness template for synthesized examples extracted from framework wrappers
WORDS_HARNESS_TEMPLATE = """\
using System;
using System.IO;
using Aspose.Words;
{extra_usings}

class Program
{{
    static void Main()
    {{
        // Synthesized from framework wrapper -- extracted product logic
        string dataDir = "{data_dir}";
{body}
    }}
}}
"""


def _build_extra_usings(body: str, extra_usings: str = "") -> str:
    """Add required usings for extracted Words snippets while preserving caller input."""
    using_lines = [line for line in extra_usings.splitlines() if line.strip()]
    if (
        any(token in body for token in ("Shape(", "ShapeType.", "WrapType.", "RelativeHorizontalPosition.", "RelativeVerticalPosition."))
        and "using Aspose.Words.Drawing;" not in using_lines
    ):
        using_lines.append("using Aspose.Words.Drawing;")
    return "\n".join(using_lines)


def _sanitize_synthesized_body(body: str) -> str:
    """
    Strip framework-wrapper scaffolding from extracted product lines and normalize the
    remaining code into a runnable console snippet.
    """
    lines = [line.rstrip() for line in body.splitlines() if line.strip()]
    cleaned: list[str] = []
    helper_lines: list[str] = []
    in_helper = False

    skip_patterns = (
        r'^\s*namespace\b',
        r'^\s*\[.*\]\s*$',
        r'^\s*(?:public|private|protected|internal)\s+class\b',
        r'^\s*(?:public|private|protected|internal)\s+async\s+Task<.*IActionResult.*$',
    )

    for line in lines:
        if any(re.match(pattern, line) for pattern in skip_patterns):
            continue
        if re.match(r'^\s*private\s+void\s+AddTextWatermark\s*\(', line):
            in_helper = True
            continue
        if re.match(r'^\s*(?:try|catch)\b', line):
            continue

        if in_helper:
            helper_lines.append(line)
        else:
            cleaned.append(line)

    def _build_watermark_block(lines: list[str]) -> list[str]:
        shape_line = next((ln.strip() for ln in lines if "new Shape(" in ln), "")
        append_line = next((ln.strip() for ln in lines if "AppendChild(watermark)" in ln), "")
        property_lines = [
            ln.strip().replace(" text", " watermarkText").replace("(text)", "(watermarkText)")
            for ln in lines
            if ln.strip()
            and "new Shape(" not in ln
            and "AppendChild(watermark)" not in ln
            and not ln.strip().startswith("foreach")
        ]
        if not shape_line or not append_line:
            return []
        return [
            "foreach (Section section in doc.Sections)",
            "{",
            f"    {shape_line}",
            "    {",
            *[f"        {ln}" for ln in property_lines],
            "    };",
            f"    {append_line}",
            "}",
        ]

    normalized: list[str] = []
    inserted_watermark_text = False
    for line in cleaned:
        stripped = line.strip()
        if not stripped or stripped in {"{", "}"}:
            continue
        if "tempFilePath" in line and "new Document(" in line:
            line = line.replace("tempFilePath", '"Blank.docx"')
        if "doc.Save(" in line and "outputStream" in line:
            line = re.sub(r'doc\.Save\(\s*outputStream\s*,\s*SaveFormat\.Docx\s*\);', 'doc.Save("output.docx");', line)
        stripped = line.strip()
        if re.search(r'\bAddTextWatermark\s*\(\s*doc\s*,\s*watermarkText\s*\)\s*;', line):
            if not inserted_watermark_text:
                normalized.append('string watermarkText = "Watermark";')
                inserted_watermark_text = True
            watermark_block = _build_watermark_block(helper_lines)
            if watermark_block:
                normalized.extend(watermark_block)
            else:
                for helper_line in helper_lines:
                    helper_stripped = helper_line.strip()
                    if not helper_stripped or helper_stripped in {"{", "}"}:
                        continue
                    normalized.append(helper_stripped.replace(" text", " watermarkText").replace("(text)", "(watermarkText)"))
            continue
        if any(token in line for token in ("ControllerBase", "IActionResult", "IFormFile", "[FromQuery]")):
            continue
        normalized.append(stripped)

    if helper_lines and not any("watermarkText" in line and line.startswith("string ") for line in normalized):
        for idx, line in enumerate(normalized):
            if "new Document(" in line:
                normalized.insert(idx, 'string watermarkText = "Watermark";')
                break

    return "\n".join(normalized)


def get_synthesis_harness(body: str, extra_usings: str = "", data_dir: str = ".") -> str:
    """Return a Words console harness wrapping extracted product API calls."""
    sanitized_body = _sanitize_synthesized_body(body)
    merged_usings = _build_extra_usings(sanitized_body, extra_usings=extra_usings)
    indented_body = '\n'.join('        ' + line for line in sanitized_body.split('\n'))
    return WORDS_HARNESS_TEMPLATE.format(
        extra_usings=merged_usings,
        data_dir=data_dir,
        body=indented_body,
    )


def fix_comment_text_setter(code: str, error_text: str) -> Optional[Tuple[str, str]]:
    """
    Fix: comment.Text property setter removed in Aspose.Words v26.1.0.

    Code like `comment.Text = "some text";` or a `new Comment(...) { Text = "..." }`
    initializer no longer compiles/runs. Rewrite to a catalog-backed form:
      comment.AppendChild(new Paragraph(doc));
      comment.FirstParagraph.AppendChild(new Run(doc, text));

    Error trigger: Comment.Text compile/runtime failures
    Catalog dependency: Comment (verified), Run (verified), FirstParagraph (verified),
                        Paragraph (verified), AppendChild (verified — CompositeNode.key_methods)
    """
    error_mentions_missing_text = (
        "does not contain a definition for 'Text'" in error_text
        or "NullReferenceException" in error_text
        or "System.NullReferenceException" in error_text
    )
    if not error_mentions_missing_text:
        return None

    if ' Text =' not in code and '.Text =' not in code and '.Text=' not in code:
        return None

    comment_var_pattern = re.compile(
        r'(?:var\s+(\w+)\s*=\s*new\s+Comment\b|Comment\s+(\w+)\s*=\s*new\s+Comment\b)'
    )
    comment_vars: set = set()
    for m in comment_var_pattern.finditer(code):
        comment_vars.update(v for v in m.groups() if v)

    if not comment_vars:
        return None

    if 'AppendChild(new Paragraph(' in code and 'FirstParagraph.AppendChild(new Run(' in code:
        return None

    fixed = code
    changed = False

    # Pattern A: object initializer on new Comment(...){ Text = "..." };
    initializer_pattern = re.compile(
        r'(?P<indent>^[ \t]*)'
        r'(?P<decl>(?:var|Comment)\s+(?P<var>\w+)\s*=\s*new\s+Comment\((?P<args>[^)]*)\))\s*'
        r'\{\s*Text\s*=\s*(?P<text>"(?:[^"\\]|\\.)*")\s*\}\s*;',
        re.MULTILINE | re.DOTALL,
    )

    def _replace_initializer(match: re.Match[str]) -> str:
        nonlocal changed
        var_name = match.group('var')
        if var_name not in comment_vars:
            return match.group(0)
        args = match.group('args')
        doc_match = re.match(r'\s*(\w+)', args)
        doc_var = doc_match.group(1) if doc_match else 'doc'
        text_val = match.group('text')
        indent = match.group('indent')
        changed = True
        return (
            f"{indent}{match.group('decl')};\n"
            f"{indent}{var_name}.AppendChild(new Paragraph({doc_var}));\n"
            f"{indent}{var_name}.FirstParagraph.AppendChild(new Run({doc_var}, {text_val}));"
        )

    fixed = initializer_pattern.sub(_replace_initializer, fixed)

    # Pattern B: <var>.Text = "<string-literal>";
    text_setter_pattern = re.compile(
        r'(?P<indent>^[ \t]*)(?P<var>\w+)\.Text\s*=\s*(?P<text>"(?:[^"\\]|\\.)*")\s*;',
        re.MULTILINE,
    )

    def _replace_assignment(match: re.Match[str]) -> str:
        nonlocal changed
        var_name = match.group('var')
        if var_name not in comment_vars:
            return match.group(0)
        doc_match = re.search(rf'new\s+Comment\s*\(\s*(\w+)[^)]*\)\s*;?', fixed)
        doc_var = doc_match.group(1) if doc_match else 'doc'
        text_val = match.group('text')
        indent = match.group('indent')
        changed = True
        return (
            f"{indent}{var_name}.AppendChild(new Paragraph({doc_var}));\n"
            f"{indent}{var_name}.FirstParagraph.AppendChild(new Run({doc_var}, {text_val}));"
        )

    fixed = text_setter_pattern.sub(_replace_assignment, fixed)

    if not changed:
        return None

    return (
        fixed,
        "Comment.Text setter: rewrote to Comment.AppendChild(new Paragraph(doc)) + FirstParagraph.AppendChild(new Run(...))",
    )


def fix_comment_manual_paragraph_workaround(code: str, error_text: str) -> Optional[Tuple[str, str]]:
    """
    Normalize brittle manual comment-text workarounds to a catalog-backed form.

    Accepted target shape:
      comment.AppendChild(new Paragraph(doc));
      comment.FirstParagraph.AppendChild(new Run(doc, "..."));
    """
    if 'Cannot insert a node of this type' not in error_text:
        return None

    if 'new Comment(' not in code:
        return None

    comment_var_pattern = re.compile(
        r'(?:var\s+(\w+)\s*=\s*new\s+Comment\b|Comment\s+(\w+)\s*=\s*new\s+Comment\b)'
    )
    comment_vars: set[str] = set()
    for match in comment_var_pattern.finditer(code):
        comment_vars.update(v for v in match.groups() if v)

    if not comment_vars:
        return None

    fixed = code
    changed = False

    for comment_var in comment_vars:
        constructor_match = re.search(rf'new\s+Comment\s*\(\s*(\w+)[^)]*\)', fixed)
        doc_var = constructor_match.group(1) if constructor_match else 'doc'

        # Variant A: comment.Paragraphs.Add(new Paragraph(doc));
        paragraphs_add_pattern = re.compile(
            rf'^\s*{re.escape(comment_var)}\.Paragraphs\.Add\(new Paragraph\(\w+\)\);\s*$',
            re.MULTILINE,
        )
        if paragraphs_add_pattern.search(fixed):
            fixed, subs = paragraphs_add_pattern.subn(
                f'{comment_var}.AppendChild(new Paragraph({doc_var}));',
                fixed,
                count=1,
            )
            if subs:
                changed = True

        # Variant B: separate paragraph variable appended into the comment.
        comment_append_pattern = re.compile(
            rf'^\s*{re.escape(comment_var)}\.AppendChild\((\w+)\);\s*$',
            re.MULTILINE,
        )
        append_match = comment_append_pattern.search(fixed)
        if append_match:
            paragraph_var = append_match.group(1)
            paragraph_decl_pattern = re.compile(
                rf'^\s*Paragraph\s+{re.escape(paragraph_var)}\s*=\s*new Paragraph\(\w+\);\s*$',
                re.MULTILINE,
            )
            paragraph_run_pattern = re.compile(
                rf'^\s*{re.escape(paragraph_var)}\.AppendChild\(new Run\(\w+,\s*("(?:[^"\\]|\\.)*")\)\);\s*$',
                re.MULTILINE,
            )
            paragraph_run_match = paragraph_run_pattern.search(fixed)
            if paragraph_run_match:
                text_literal = paragraph_run_match.group(1)
                fixed, decl_subs = paragraph_decl_pattern.subn('', fixed, count=1)
                fixed, run_subs = paragraph_run_pattern.subn('', fixed, count=1)
                fixed, append_subs = comment_append_pattern.subn(
                    f'{comment_var}.AppendChild(new Paragraph({doc_var}));\n'
                    f'{comment_var}.FirstParagraph.AppendChild(new Run({doc_var}, {text_literal}));',
                    fixed,
                    count=1,
                )
                if decl_subs or run_subs or append_subs:
                    changed = True

        first_paragraph_pattern = re.compile(
            rf'{re.escape(comment_var)}\.FirstParagraph\.AppendChild\(new Run\('
        )
        append_paragraph_pattern = re.compile(
            rf'{re.escape(comment_var)}\.AppendChild\(new Paragraph\('
        )
        if append_paragraph_pattern.search(fixed) and first_paragraph_pattern.search(fixed):
            continue

    if not changed:
        return None

    return (
        fixed,
        "Comment text workaround: normalized to Comment.AppendChild(new Paragraph(doc)) + FirstParagraph.AppendChild(new Run(...))",
    )


def fix_comment_anchor_with_ranges(code: str, error_text: str) -> Optional[Tuple[str, str]]:
    """
    Fix: anchor Comment nodes using CommentRangeStart/End + InsertAfter, not para.AppendChild(comment).

    Local evidence (2026-03-13):
    - `para.AppendChild(comment);` fails for the track-comments example fixture.
    - The shipped Words example corpus uses:
        para.InsertBefore(commentRangeStart, anchorRun);
        para.InsertAfter(commentRangeEnd, endAnchor);
        para.InsertAfter(comment, commentRangeEnd);
    - With StartTrackRevisions present, stopping tracking before Save() is also required.

    Catalog dependency: CommentRangeStart, CommentRangeEnd, InsertBefore, InsertAfter,
                        StartTrackRevisions, StopTrackRevisions
    """
    if 'Cannot insert a node of this type' not in error_text:
        return None

    if 'new Comment(' not in code or '.AppendChild(comment' not in code:
        return None

    if 'CommentRangeStart' in code or 'CommentRangeEnd' in code:
        return None

    comment_var_pattern = re.compile(
        r'(?:var\s+(\w+)\s*=\s*new\s+Comment\b|Comment\s+(\w+)\s*=\s*new\s+Comment\b)'
    )
    comment_vars: set[str] = set()
    for match in comment_var_pattern.finditer(code):
        comment_vars.update(v for v in match.groups() if v)

    if not comment_vars:
        return None

    if not _INSERTBEFORE_AFTER_VERIFIED:
        return None

    fixed = code
    changed = False

    for comment_var in comment_vars:
        constructor_match = re.search(
            rf'(?:var|Comment)\s+{re.escape(comment_var)}\s*=\s*new\s+Comment\s*\(\s*(\w+)[^)]*\)',
            fixed,
        )
        doc_var = constructor_match.group(1) if constructor_match else 'doc'

        append_pattern = re.compile(
            rf'(?P<indent>^[ \t]*)(?P<para>\w+)\.AppendChild\(\s*{re.escape(comment_var)}\s*\)\s*;',
            re.MULTILINE,
        )
        append_match = append_pattern.search(fixed)
        if not append_match:
            continue

        indent = append_match.group('indent')
        para_var = append_match.group('para')
        anchor_start_var = f"{comment_var}AnchorStart"
        anchor_end_var = f"{comment_var}AnchorEnd"
        range_start_var = f"{comment_var}RangeStart"
        range_end_var = f"{comment_var}RangeEnd"
        replacement = (
            f"{indent}Run {anchor_start_var} = {para_var}.Runs.Count > 0 ? {para_var}.Runs[0] : {para_var}.AppendChild(new Run({doc_var}, \"Annotated text\"));\n"
            f"{indent}Run {anchor_end_var} = {para_var}.AppendChild(new Run({doc_var}, \"Annotated text\"));\n"
            f"{indent}CommentRangeStart {range_start_var} = new CommentRangeStart({doc_var}, {comment_var}.Id);\n"
            f"{indent}CommentRangeEnd {range_end_var} = new CommentRangeEnd({doc_var}, {comment_var}.Id);\n"
            f"{indent}{para_var}.InsertBefore({range_start_var}, {anchor_start_var});\n"
            f"{indent}{para_var}.InsertAfter({range_end_var}, {anchor_end_var});\n"
            f"{indent}{para_var}.InsertAfter({comment_var}, {range_end_var});"
        )
        fixed = append_pattern.sub(replacement, fixed, count=1)
        changed = True

    if not changed:
        return None

    stop_track_fix = fix_stop_track_revisions_before_save(fixed, error_text)
    if stop_track_fix is not None:
        fixed = stop_track_fix[0]

    return (
        fixed,
        "Comment anchor: rewrote para.AppendChild(comment) to CommentRangeStart/End + InsertAfter(comment, rangeEnd) and stopped tracking before Save() when needed",
    )


def fix_stop_track_revisions_before_save(code: str, error_text: str) -> Optional[Tuple[str, str]]:
    """
    Fix: tracked-revision examples must stop tracking before Save() in the current fixture/runtime path.

    Runtime evidence (2026-03-13):
    - StartTrackRevisions(...); Save(...) fails with "Cannot insert a node of this type at this location."
    - StartTrackRevisions(...); StopTrackRevisions(); Save(...) passes.

    Catalog dependency: Document.StartTrackRevisions (verified), Document.StopTrackRevisions (verified),
                        Document.Save (verified)
    """
    if 'Cannot insert a node of this type' not in error_text:
        return None

    if 'StartTrackRevisions(' not in code or '.Save(' not in code:
        return None

    if 'StopTrackRevisions()' in code:
        return None

    if not (CATALOG_VERIFIED['StartTrackRevisions'] and CATALOG_VERIFIED['StopTrackRevisions']):
        return None

    started_vars: set[str] = set()
    for match in re.finditer(r'(?P<var>\w+)\.StartTrackRevisions\(', code):
        started_vars.add(match.group('var'))

    if not started_vars:
        return None

    fixed = code
    changed = False

    for doc_var in started_vars:
        save_pattern = re.compile(rf'(?P<indent>^[ \t]*)(?P<call>{re.escape(doc_var)}\.Save\()', re.MULTILINE)

        def _insert_stop(match: re.Match[str]) -> str:
            nonlocal changed
            changed = True
            indent = match.group('indent')
            return f"{indent}{doc_var}.StopTrackRevisions();\n{indent}{match.group('call')}"

        fixed, subs = save_pattern.subn(_insert_stop, fixed, count=1)
        if subs:
            continue

    if not changed:
        return None

    return (
        fixed,
        "Track revisions: inserted StopTrackRevisions() before Save() for tracked-document runtime stability",
    )


def fix_comment_node_appendchild(code: str, error_text: str) -> Optional[Tuple[str, str]]:
    """
    Fix: Comment node appended to Paragraph — must be appended to Body instead.

    In Aspose.Words, Comment is a block-level node; it cannot be a child of Paragraph.
    Code like `para.AppendChild(comment);` throws:
      "Cannot insert a node of this type at this location."
    Rewrite to: `para.ParentNode.AppendChild(comment);`

    Error trigger: "Cannot insert a node of this type at this location"
    Catalog dependency: Comment (verified)
    """
    if 'Cannot insert a node of this type' not in error_text:
        return None

    # Must have a Comment variable in the code
    if 'new Comment(' not in code:
        return None

    # Find variables declared as Comment instances
    comment_var_pattern = re.compile(
        r'(?:var\s+(\w+)\s*=\s*new\s+Comment\b|Comment\s+(\w+)\s*=\s*new\s+Comment\b)'
    )
    comment_vars: set = set()
    for m in comment_var_pattern.finditer(code):
        comment_vars.update(v for v in m.groups() if v)

    if not comment_vars:
        return None

    # Idempotency guard
    if 'ParentNode.AppendChild' in code:
        return None

    fixed = code
    changed = False
    for cv in comment_vars:
        # Match <parent>.AppendChild(<comment_var>) where parent is not itself a comment var
        pattern = re.compile(rf'(\w+)\.AppendChild\(\s*{re.escape(cv)}\s*\)')

        def _replace(m, _cv=cv):
            nonlocal changed
            parent = m.group(1)
            if parent in comment_vars:
                # comment.AppendChild(paragraph) is valid — don't touch
                return m.group(0)
            changed = True
            return f'{parent}.ParentNode.AppendChild({_cv})'

        fixed = pattern.sub(_replace, fixed)

    if not changed:
        return None

    return (
        fixed,
        "Comment: rewrote para.AppendChild(comment) to para.ParentNode.AppendChild(comment) (block-level node fix)",
    )


# Known correct password for certificate.pfx (identical to morzal.pfx from Aspose.Words examples repo).
# Verified: X509Certificate2("certificate.pfx", "aw") → Subject=CN=Morzal.Me  (2026-03-12)
_CERTIFICATE_PFX_PASSWORD = "aw"


def fix_certificate_pfx_password(code: str, error_text: str) -> Optional[Tuple[str, str]]:
    """
    Fix: certificate.pfx password normalized to the known test-fixture value.

    The fixture certificate.pfx (from Aspose.Words-for-.NET Examples/Data/) uses "password".
    After generic placeholder substitution it may become "p@s$" or retain an article-specific
    value like "certpassword". This fix restores the correct password.

    Error trigger: any (called proactively with empty error_text; also after invalid_password)
    Catalog dependency: none (fixture, not API type)
    """
    if 'certificate.pfx' not in code:
        return None

    fixed = code
    changed = False

    # Pattern A: string-literal password in CertificateHolder.Create / CertificateHolder
    cert_literal_pat = re.compile(
        r'(CertificateHolder(?:\.Create)?)\s*\(\s*"certificate\.pfx"\s*,\s*"([^"]+)"\s*\)'
    )
    for m in cert_literal_pat.finditer(code):
        current_pw = m.group(2)
        if current_pw != _CERTIFICATE_PFX_PASSWORD:
            old_call = m.group(0)
            new_call = old_call.replace(f'"{current_pw}"', f'"{_CERTIFICATE_PFX_PASSWORD}"', 1)
            fixed = fixed.replace(old_call, new_call, 1)
            changed = True

    if changed:
        return (fixed, f"certificate.pfx: normalized literal password to '{_CERTIFICATE_PFX_PASSWORD}'")

    # Pattern B: variable-based password — CertificateHolder.Create("certificate.pfx", someVar)
    cert_var_pat = re.compile(
        r'CertificateHolder(?:\.Create)?\s*\(\s*"certificate\.pfx"\s*,\s*(\w+)\s*\)'
    )
    for m in cert_var_pat.finditer(code):
        var_name = m.group(1)
        # Replace the variable's string-literal assignment
        assign_pat = re.compile(
            rf'(?:string\s+{re.escape(var_name)}\s*=\s*|{re.escape(var_name)}\s*=\s*)"([^"]+)"'
        )
        for a in assign_pat.finditer(fixed):
            current_pw = a.group(1)
            if current_pw != _CERTIFICATE_PFX_PASSWORD:
                old_assign = a.group(0)
                new_assign = old_assign.replace(f'"{current_pw}"', f'"{_CERTIFICATE_PFX_PASSWORD}"', 1)
                fixed = fixed.replace(old_assign, new_assign, 1)
                changed = True
        if changed:
            break

    if not changed:
        return None

    return (fixed, f"certificate.pfx: normalized variable password to '{_CERTIFICATE_PFX_PASSWORD}'")


# Register fixes with the generic registry (order matters: more specific first).
register_runtime_fix('words', fix_commentrange_node_insertion)
register_runtime_fix('words', fix_comment_text_setter)
register_runtime_fix('words', fix_comment_anchor_with_ranges)
register_runtime_fix('words', fix_stop_track_revisions_before_save)
register_runtime_fix('words', fix_comment_manual_paragraph_workaround)
register_runtime_fix('words', fix_certificate_pfx_password)

register_synthesis_harness('words', get_synthesis_harness)


def fix_mailmerge_use_non_merge_fields(code: str) -> Optional[Tuple[str, str]]:
    """
    Behavioral fix: insert doc.MailMerge.UseNonMergeFields = true before Execute().

    When a template uses mustache-style {{field}} placeholders, Aspose.Words requires
    UseNonMergeFields = true set on the MailMerge object before Execute() or
    ExecuteWithRegions() is called. Without it, placeholders are treated as plain text.

    Catalog dependency: MailMerge.UseNonMergeFields (confirmed in words_api_catalog.json)
    """
    # Gate: must have a MailMerge.Execute call
    execute_pattern = re.compile(r'\.MailMerge\.Execute(?:WithRegions)?\s*\(')
    if not execute_pattern.search(code):
        return None

    # Idempotency: already set
    if 'UseNonMergeFields' in code:
        return None

    # Find the doc variable used for MailMerge
    doc_var_match = re.search(r'(\w+)\.MailMerge\.Execute', code)
    if not doc_var_match:
        return None
    doc_var = doc_var_match.group(1)

    # Insert UseNonMergeFields = true before the first Execute call
    def _insert_before_execute(m: re.Match) -> str:
        # Capture leading whitespace from the line
        line_start = code.rfind('\n', 0, m.start()) + 1
        indent = ''
        for ch in code[line_start:m.start()]:
            if ch in (' ', '\t'):
                indent += ch
            else:
                break
        return f"{doc_var}.MailMerge.UseNonMergeFields = true;\n{indent}{m.group(0)}"

    fixed = execute_pattern.sub(_insert_before_execute, code, count=1)
    if fixed == code:
        return None

    return (
        fixed,
        f"MailMerge: inserted {doc_var}.MailMerge.UseNonMergeFields = true before Execute() "
        "(required for mustache {{...}} placeholders)",
    )


register_behavioral_fix('words', fix_mailmerge_use_non_merge_fields)

logger.debug("words_fixes: registered 6 runtime fixes + 1 synthesis harness + 1 behavioral fix")
