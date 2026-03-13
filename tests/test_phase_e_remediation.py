"""
Unit tests for Phase E auto-remediation methods.

Covers:
- LLMService.generate_semantic_fix() — 4 tests
- Orchestrator._build_semantic_fix_context() — 3 tests
"""
import json
import types
import unittest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_llm_service():
    """Return an LLMService instance with minimal real initialisation."""
    from src.services.llm_service import LLMService

    svc = LLMService.__new__(LLMService)
    # Attributes accessed by generate_semantic_fix via self.complete()
    # are satisfied by patching self.complete in each test, so no
    # further initialisation is needed here.
    return svc


def _make_llm_response(success: bool, content: str = "", error: str = ""):
    """Return a minimal LLMResponse-like object."""
    r = MagicMock()
    r.success = success
    r.content = content
    r.error = error
    return r


def _make_orchestrator_with_catalog(catalog):
    """Return a PipelineOrchestrator instance whose registry returns *catalog*."""
    from src.pipeline.orchestrator import PipelineOrchestrator as Orchestrator

    orch = Orchestrator.__new__(Orchestrator)
    registry = MagicMock()
    registry.get_api_catalog.return_value = catalog
    orch.registry = registry
    return orch


def _make_catalog(has_type_result: bool = True, has_hierarchy_result: bool = True):
    """Return a mock APICatalogService."""
    cat = MagicMock()
    cat.is_loaded = True
    cat.has_type.return_value = has_type_result
    cat.has_hierarchy.return_value = has_hierarchy_result
    cat.get_namespace_for_type.return_value = "Aspose.Zip.Saving"
    cat.get_type_kind.return_value = "sealed class"
    cat.get_sibling_types.return_value = [
        "Bzip2CompressionSettings",
        "LzmaCompressionSettings",
        "StoreCompressionSettings",
    ]
    cat.get_type_group.return_value = [
        "Bzip2CompressionSettings",
        "DeflateCompressionSettings",
        "LzmaCompressionSettings",
        "StoreCompressionSettings",
    ]
    cat.get_constructor_signatures.return_value = [{"params": ""}]
    return cat


# ===========================================================================
# Tests for LLMService.generate_semantic_fix()
# ===========================================================================


class TestGenerateSemanticFix(unittest.TestCase):

    CODE = "var x = new DeflateCompressionSettings();"

    # ------------------------------------------------------------------
    # Test 1: happy path — LLM returns valid JSON with changed=true
    # ------------------------------------------------------------------
    def test_happy_path_changed_true(self):
        """LLM returns valid JSON with changed=true; result reflects the fix."""
        svc = _make_llm_service()

        fixed = "var x = new Bzip2CompressionSettings();"
        payload = json.dumps({
            "fixed_code": fixed,
            "explanation": "Replaced Deflate with Bzip2 for better ratio.",
            "changed": True,
        })
        mock_response = _make_llm_response(success=True, content=payload)

        with patch.object(svc, "complete", return_value=mock_response):
            result = svc.generate_semantic_fix(
                code=self.CODE,
                issue_type="intent_mismatch",
                issue_description="All three objects are identical DeflateCompressionSettings.",
                issue_suggestion="Use distinct compression algorithm classes.",
            )

        self.assertTrue(result["success"])
        self.assertTrue(result["changed"])
        self.assertEqual(result["fixed_code"], fixed)
        self.assertIn("Bzip2", result["explanation"])
        self.assertIsNone(result["error"])

    # ------------------------------------------------------------------
    # Test 2: LLM returns changed=false (no modification)
    # ------------------------------------------------------------------
    def test_changed_false_returns_original(self):
        """LLM returns changed=false; fixed_code equals original, changed=False."""
        svc = _make_llm_service()

        payload = json.dumps({
            "fixed_code": self.CODE,
            "explanation": "Cannot determine correct fix with confidence.",
            "changed": False,
        })
        mock_response = _make_llm_response(success=True, content=payload)

        with patch.object(svc, "complete", return_value=mock_response):
            result = svc.generate_semantic_fix(
                code=self.CODE,
                issue_type="intent_mismatch",
                issue_description="Some issue.",
                issue_suggestion="",
            )

        self.assertTrue(result["success"])
        self.assertFalse(result["changed"])
        self.assertEqual(result["fixed_code"], self.CODE)

    # ------------------------------------------------------------------
    # Test 3: LLM call fails (error in LLMResponse)
    # ------------------------------------------------------------------
    def test_llm_call_failure_returns_error(self):
        """LLM response has success=False; result propagates error, success=False."""
        svc = _make_llm_service()

        mock_response = _make_llm_response(
            success=False,
            error="Connection timeout",
        )

        with patch.object(svc, "complete", return_value=mock_response):
            result = svc.generate_semantic_fix(
                code=self.CODE,
                issue_type="api_mismatch",
                issue_description="Wrong type used.",
                issue_suggestion="Use correct type.",
            )

        self.assertFalse(result["success"])
        self.assertFalse(result["changed"])
        self.assertEqual(result["fixed_code"], self.CODE)
        self.assertEqual(result["error"], "Connection timeout")

    # ------------------------------------------------------------------
    # Test 4: LLM returns unparseable JSON (graceful fallback)
    # ------------------------------------------------------------------
    def test_unparseable_json_graceful_fallback(self):
        """LLM returns non-JSON content; result has success=False, original code."""
        svc = _make_llm_service()

        mock_response = _make_llm_response(
            success=True,
            content="Sorry, I cannot fix this code.",  # not JSON
        )

        with patch.object(svc, "complete", return_value=mock_response):
            result = svc.generate_semantic_fix(
                code=self.CODE,
                issue_type="intent_mismatch",
                issue_description="Some issue.",
                issue_suggestion="",
            )

        self.assertFalse(result["success"])
        self.assertFalse(result["changed"])
        self.assertEqual(result["fixed_code"], self.CODE)
        self.assertIsNotNone(result["error"])
        self.assertIn("JSON", result["error"])


# ===========================================================================
# Tests for Orchestrator._build_semantic_fix_context()
# ===========================================================================


class TestBuildSemanticFixContext(unittest.TestCase):

    DESCRIPTION_WITH_TYPE = (
        "The code uses three identical DeflateCompressionSettings objects "
        "labelled fastest/balanced/smallest — they are all the same."
    )

    # ------------------------------------------------------------------
    # Test 5: known type → sibling list returned in context
    # ------------------------------------------------------------------
    def test_known_type_returns_sibling_context(self):
        """Catalog has DeflateCompressionSettings with siblings; context is non-empty."""
        catalog = _make_catalog(has_type_result=True, has_hierarchy_result=True)
        orch = _make_orchestrator_with_catalog(catalog)

        ctx = orch._build_semantic_fix_context(
            family="zip",
            issue_type="intent_mismatch",
            issue_description=self.DESCRIPTION_WITH_TYPE,
        )

        self.assertIsInstance(ctx, str)
        self.assertGreater(len(ctx), 0)
        # Sibling types should appear in the context
        self.assertIn("Bzip2CompressionSettings", ctx)

    # ------------------------------------------------------------------
    # Test 6: unknown family (catalog not loaded) → empty string
    # ------------------------------------------------------------------
    def test_unknown_family_returns_empty_string(self):
        """Registry returns None for the family; context must be empty string."""
        from src.pipeline.orchestrator import PipelineOrchestrator as Orchestrator

        orch = Orchestrator.__new__(Orchestrator)
        registry = MagicMock()
        registry.get_api_catalog.return_value = None
        orch.registry = registry

        ctx = orch._build_semantic_fix_context(
            family="nonexistent_family",
            issue_type="intent_mismatch",
            issue_description=self.DESCRIPTION_WITH_TYPE,
        )

        self.assertEqual(ctx, "")

    # ------------------------------------------------------------------
    # Test 7: catalog loaded but no hierarchy → empty string
    # ------------------------------------------------------------------
    def test_no_hierarchy_in_catalog_returns_empty_string(self):
        """Catalog is loaded but has no known types matching description → empty string."""
        catalog = _make_catalog(has_type_result=False, has_hierarchy_result=False)
        orch = _make_orchestrator_with_catalog(catalog)

        ctx = orch._build_semantic_fix_context(
            family="zip",
            issue_type="intent_mismatch",
            issue_description=self.DESCRIPTION_WITH_TYPE,
        )

        # has_type returns False for all candidates → candidate_types is empty → ""
        self.assertEqual(ctx, "")


if __name__ == "__main__":
    unittest.main()
