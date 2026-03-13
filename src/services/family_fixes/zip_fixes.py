"""
Aspose.ZIP family-specific runtime fix functions.

P1 compliance: All API types used in fixes must be verified in
zip_api_catalog.json before encoding. See CATALOG_VERIFIED dict below.

P2 compliance: This module only contains ZIP-specific logic.
Registration: calls register_runtime_fix('zip', fn) for each fix.
"""
from __future__ import annotations
import re
import logging
from collections import Counter
from typing import Optional, Tuple

from src.services.family_fix_registry import register_runtime_fix, register_synthesis_harness

logger = logging.getLogger(__name__)

# Catalog-verified types (confirmed in zip_api_catalog.json).
# Verification date: 2026-03-12 via extract_assembly_catalog.py --full (Aspose.ZIP 26.1.0)
CATALOG_VERIFIED = {
    'DeflateCompressionSettings': True,   # confirmed: zip_api_catalog.json types dict
    'Bzip2CompressionSettings': True,     # confirmed: zip_api_catalog.json types dict
    'LzmaCompressionSettings': True,      # confirmed: zip_api_catalog.json types dict
    'StoreCompressionSettings': True,     # confirmed: zip_api_catalog.json types dict
    'EnhancedDeflateCompressionSettings': True,  # confirmed: zip_api_catalog.json types dict
    'ArchiveEntrySettings': True,         # confirmed: zip_api_catalog.json types dict
    'Archive': True,                      # confirmed: zip_api_catalog.json types dict
}

# All known concrete subclasses of CompressionSettings in the ZIP catalog.
# NOTE: Once T2 (catalog hierarchy enrichment) is complete, this set should be
# derived from get_type_group('CompressionSettings') instead of being hardcoded.
COMPRESSION_SETTINGS_TYPES: frozenset = frozenset([
    'DeflateCompressionSettings',
    'EnhancedDeflateCompressionSettings',
    'Bzip2CompressionSettings',
    'LzmaCompressionSettings',
    'StoreCompressionSettings',
    'XzCompressionSettings',
])


def detect_identical_default_constructed_objects(code: str, error_text: str) -> Optional[Tuple[str, str]]:
    """
    Detector: N >= 2 variables of the same CompressionSettings subtype, all
    default-constructed (no args) — pattern of misleading placeholder code where
    variables are labelled "fastest"/"balanced"/"smallest" but are identical.

    This is a DETECTOR, not a fixer: Phase E (final review) handles the semantic
    correction with full intent context. This detector surfaces the issue earlier
    in pipeline logs and is the scaffolding for a catalog-grounded fixer once T2
    (catalog hierarchy enrichment) is complete.

    NOTE: Returns None always (no code mutation). The registry continues to the
    next fix if this detector runs.

    Catalog dependency: COMPRESSION_SETTINGS_TYPES (all catalog-verified above).
    """
    # Pattern: new TypeName() with no constructor arguments
    new_default_pattern = re.compile(r'\bnew\s+(\w+)\s*\(\s*\)')

    type_counts: Counter = Counter()
    for m in new_default_pattern.finditer(code):
        type_name = m.group(1)
        if type_name in COMPRESSION_SETTINGS_TYPES:
            type_counts[type_name] += 1

    # Only flag when 2+ variables use the same default constructor
    duplicates = {t: n for t, n in type_counts.items() if n >= 2}
    if not duplicates:
        return None

    for type_name, count in duplicates.items():
        alternatives = sorted(COMPRESSION_SETTINGS_TYPES - {type_name})
        logger.warning(
            "[zip_fixes] IDENTICAL-OBJECT PATTERN detected: '%s()' appears %d times "
            "with default constructor -- likely placeholder code with misleading variable names. "
            "Phase E will flag this as intent_mismatch. "
            "Available alternatives (catalog-verified): %s",
            type_name, count, alternatives,
        )

    # Return None -- no code mutation; Phase E review handles the semantic fix.
    # TODO (T2): once catalog hierarchy is available, build a catalog-grounded
    # replacement that substitutes sibling CompressionSettings types.
    return None


# ZIP harness template for synthesized examples extracted from framework wrappers
ZIP_HARNESS_TEMPLATE = """\
using System;
using System.IO;
using Aspose.Zip;
using Aspose.Zip.Saving;
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
    """Return a ZIP console harness wrapping extracted product API calls."""
    indented_body = '\n'.join('        ' + line for line in body.split('\n'))
    return ZIP_HARNESS_TEMPLATE.format(
        extra_usings=extra_usings,
        data_dir=data_dir,
        body=indented_body,
    )


# Register with the generic registry (detector before any future fixers).
register_runtime_fix('zip', detect_identical_default_constructed_objects)

register_synthesis_harness('zip', get_synthesis_harness)

logger.debug("zip_fixes: registered 1 runtime fix (detector) + 1 synthesis harness")
