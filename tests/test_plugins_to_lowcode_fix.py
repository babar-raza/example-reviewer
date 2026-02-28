"""
Tests for fix_plugins_to_lowcode() family-gated namespace rename fix.

Regression tests for the bug where Aspose.TeX.Plugins was incorrectly renamed
to Aspose.TeX.LowCode (which does not exist), causing the CS0234 fix to then
strip the using directive entirely from published markdown examples.
"""

from src.services.semantic_microfixes import (
    _PLUGINS_TO_LOWCODE_FAMILIES,
    fix_plugins_to_lowcode,
)


# ---------------------------------------------------------------------------
# Allowlist membership
# ---------------------------------------------------------------------------

class TestPluginsToLowCodeAllowlist:
    def test_allowlist_contains_expected_families(self):
        assert "words" in _PLUGINS_TO_LOWCODE_FAMILIES
        assert "cells" in _PLUGINS_TO_LOWCODE_FAMILIES
        assert "slides" in _PLUGINS_TO_LOWCODE_FAMILIES

    def test_allowlist_excludes_pdf(self):
        """PDF still ships Plugins; LowCode rewrite must remain disabled."""
        assert "pdf" not in _PLUGINS_TO_LOWCODE_FAMILIES

    def test_allowlist_excludes_tex(self):
        """TeX uses .Plugins as its current valid namespace and must stay excluded."""
        assert "tex" not in _PLUGINS_TO_LOWCODE_FAMILIES

    def test_allowlist_excludes_zip(self):
        assert "zip" not in _PLUGINS_TO_LOWCODE_FAMILIES


# ---------------------------------------------------------------------------
# TeX family - must be a no-op (the original bug)
# ---------------------------------------------------------------------------

class TestPluginsToLowCodeTex:
    def test_tex_using_directive_unchanged(self):
        """Regression: using Aspose.TeX.Plugins must NOT be renamed."""
        code = "using Aspose.TeX.Plugins;\nusing System.IO;\n"
        result, desc = fix_plugins_to_lowcode(code, family="tex")
        assert result == code
        assert desc == ""

    def test_tex_type_references_unchanged(self):
        """Inline type references must not change for TeX."""
        code = "var r = new Aspose.TeX.Plugins.FigureRendererPlugin();\n"
        result, desc = fix_plugins_to_lowcode(code, family="tex")
        assert result == code
        assert desc == ""

    def test_tex_full_example_unchanged(self):
        code = (
            "using System.Drawing;\n"
            "using System.IO;\n"
            "using Aspose.TeX.Plugins;\n"
            "\n"
            "var renderer = new FigureRendererPlugin();\n"
            "var opts = new PngFigureRendererPluginOptions();\n"
        )
        result, desc = fix_plugins_to_lowcode(code, family="tex")
        assert "Aspose.TeX.Plugins" in result
        assert "Aspose.TeX.LowCode" not in result
        assert desc == ""


# ---------------------------------------------------------------------------
# Known-valid families - rename should apply
# ---------------------------------------------------------------------------

class TestPluginsToLowCodeValidFamilies:
    def test_words_plugins_renamed(self):
        code = "using Aspose.Words.Plugins;\n"
        result, desc = fix_plugins_to_lowcode(code, family="words")
        assert "Aspose.Words.LowCode" in result
        assert "Aspose.Words.Plugins" not in result
        assert desc != ""

    def test_pdf_plugins_unchanged(self):
        code = "using Aspose.Pdf.Plugins;\n"
        result, desc = fix_plugins_to_lowcode(code, family="pdf")
        assert result == code
        assert desc == ""

    def test_cells_plugins_renamed(self):
        code = "using Aspose.Cells.Plugins;\n"
        result, desc = fix_plugins_to_lowcode(code, family="cells")
        assert "Aspose.Cells.LowCode" in result
        assert desc != ""

    def test_slides_plugins_renamed(self):
        code = "using Aspose.Slides.Plugins;\n"
        result, desc = fix_plugins_to_lowcode(code, family="slides")
        assert "Aspose.Slides.LowCode" in result
        assert desc != ""

    def test_family_matching_is_case_insensitive(self):
        code = "using Aspose.Words.Plugins;\n"
        result, desc = fix_plugins_to_lowcode(code, family="Words")
        assert "Aspose.Words.LowCode" in result
        assert desc != ""

    def test_fix_description_string(self):
        code = "using Aspose.Words.Plugins;\n"
        _, desc = fix_plugins_to_lowcode(code, family="words")
        assert "LowCode" in desc


# ---------------------------------------------------------------------------
# family=None - unknown family, must be a no-op (safe default)
# ---------------------------------------------------------------------------

class TestPluginsToLowCodeNoFamily:
    def test_none_family_is_noop(self):
        """When family is not specified, skip the rename; safer than a wrong rename."""
        code = "using Aspose.Words.Plugins;\n"
        result, desc = fix_plugins_to_lowcode(code, family=None)
        assert result == code
        assert desc == ""

    def test_missing_family_arg_is_noop(self):
        """Calling without family kwarg should also be a no-op."""
        code = "using Aspose.Pdf.Plugins;\n"
        result, desc = fix_plugins_to_lowcode(code)
        assert result == code
        assert desc == ""


# ---------------------------------------------------------------------------
# Early-exit when no .Plugins present
# ---------------------------------------------------------------------------

class TestPluginsToLowCodeEarlyExit:
    def test_no_plugins_in_code_is_noop_for_valid_family(self):
        code = "using System;\nusing Aspose.Words;\n"
        result, desc = fix_plugins_to_lowcode(code, family="words")
        assert result == code
        assert desc == ""

    def test_no_plugins_in_code_is_noop_for_tex(self):
        code = "using System;\nusing Aspose.TeX.IO;\n"
        result, desc = fix_plugins_to_lowcode(code, family="tex")
        assert result == code
        assert desc == ""
