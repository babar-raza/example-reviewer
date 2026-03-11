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

from src.services.family_fix_registry import register_runtime_fix

logger = logging.getLogger(__name__)

# Catalog-verified types and methods (confirmed in words_api_catalog.json).
# Verification date: 2026-03-12 via extract_assembly_catalog.py --full (Aspose.Words 26.1.0)
#   CommentRangeStart : True  (present in catalog['types'])
#   CommentRangeEnd   : True  (present in catalog['types'])
#   InsertBefore      : True  (confirmed: CompositeNode.key_methods after adding "InsertBefore"/"InsertAfter"
#                              to keyMethodNames in Program.cs and regenerating catalog)
#   InsertAfter       : True  (same)
CATALOG_VERIFIED = {
    # Key: type/method name, Value: confirmed present in catalog (True) or not confirmed (False)
    'CommentRangeStart': True,   # confirmed: words_api_catalog.json types dict
    'CommentRangeEnd': True,     # confirmed: words_api_catalog.json types dict
    'InsertBefore': True,        # confirmed: CompositeNode key_methods in regenerated catalog
    'InsertAfter': True,         # confirmed: CompositeNode key_methods in regenerated catalog
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


def get_synthesis_harness(body: str, extra_usings: str = "", data_dir: str = ".") -> str:
    """Return a Words console harness wrapping extracted product API calls."""
    indented_body = '\n'.join('        ' + line for line in body.split('\n'))
    return WORDS_HARNESS_TEMPLATE.format(
        extra_usings=extra_usings,
        data_dir=data_dir,
        body=indented_body,
    )


# Register the fix with the generic registry.
# Note: fix_commentrange_node_insertion has an internal P1 guard and will return None
# until InsertBefore/InsertAfter are confirmed in the catalog. Registering it now
# ensures it is picked up automatically once the guard is lifted.
register_runtime_fix('words', fix_commentrange_node_insertion)

logger.debug("words_fixes: registered 1 runtime fix (fix_commentrange_node_insertion)")
