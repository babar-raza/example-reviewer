"""
Integration tests for executable pattern generation (SR-02-B).

Tests LLMPatternExtractor's ability to generate executable fix_code patterns
instead of template-only patterns.
"""

import json
import pytest
import sys
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock, MagicMock

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.auto_learn import LLMPatternExtractor


class MockLLMService:
    """Mock LLM service for testing pattern extraction."""

    def __init__(self, response_content: str = ""):
        self.response_content = response_content
        self.calls = []

    def complete(self, prompt: str, system_prompt: str = "", temperature: float = 0.2):
        """Mock LLM completion."""
        self.calls.append({
            "prompt": prompt,
            "system_prompt": system_prompt,
            "temperature": temperature,
        })

        # Return mock response
        response = Mock()
        response.success = True
        response.content = self.response_content
        response.error = None
        return response


class MockCatalog:
    """Mock API catalog for testing."""

    def __init__(self, namespaces=None):
        self.is_loaded = True
        self.namespaces = namespaces or [
            "Aspose.Zip",
            "Aspose.Zip.Saving",
            "Aspose.Words",
            "Aspose.Words.Drawing",
        ]
        self.types_map = {
            "Aspose.Zip": ["Archive", "ArchiveEntry"],
            "Aspose.Zip.Saving": ["ParallelOptions", "ArchiveSaveOptions"],
            "Aspose.Words": ["Document", "Node"],
            "Aspose.Words.Drawing": ["Shape", "ShapeBase"],
        }

    def get_all_namespaces(self):
        """Return all namespaces."""
        return self.namespaces

    def get_types_in_namespace(self, namespace: str):
        """Return types in namespace."""
        return self.types_map.get(namespace, [])


class TestLLMPatternExtractor:
    """Test suite for LLMPatternExtractor executable pattern generation."""

    def test_using_directive_pattern_extraction(self):
        """Test: LLM generates valid using_directive pattern."""
        # Mock LLM response for CS0246 error
        llm_response = json.dumps({
            "fix_type": "using_directive",
            "fix_code": {
                "directive": "using Aspose.Zip.Saving;",
                "trigger_type": "ParallelOptions"
            },
            "confidence": 0.9,
            "fix_template": "Add using directive for Aspose.Zip.Saving namespace",
            "example_before": "var opts = new ParallelOptions();",
            "example_after": "using Aspose.Zip.Saving;\\nvar opts = new ParallelOptions();"
        })

        llm_service = MockLLMService(llm_response)
        catalog = MockCatalog()
        extractor = LLMPatternExtractor(llm_service, catalog)

        # Extract pattern from CS0246 failure cluster
        cluster = {
            "signature": "CS0246",
            "examples": [{
                "compilable_code": "var opts = new ParallelOptions();",
                "failure_reason": "error CS0246: The type or namespace name 'ParallelOptions' could not be found",
            }]
        }

        patterns = extractor.extract_patterns_with_llm(cluster, "zip")

        # Verify
        assert len(patterns) == 1
        pattern = patterns[0]
        assert pattern["fix_type"] == "using_directive"
        assert pattern["fix_code"]["directive"] == "using Aspose.Zip.Saving;"
        assert pattern["fix_code"]["trigger_type"] == "ParallelOptions"
        assert pattern["confidence"] == 0.9
        assert pattern["auto_approved"] is True  # High confidence + executable type

    def test_regex_replace_pattern_extraction(self):
        """Test: LLM generates valid regex_replace pattern."""
        llm_response = json.dumps({
            "fix_type": "regex_replace",
            "fix_code": {
                "pattern": r"CompressionLevel\.Normal",
                "replacement": "CompressionLevel.Optimal"
            },
            "confidence": 0.85,
            "fix_template": "Replace CompressionLevel.Normal with CompressionLevel.Optimal",
            "example_before": "var level = CompressionLevel.Normal;",
            "example_after": "var level = CompressionLevel.Optimal;"
        })

        llm_service = MockLLMService(llm_response)
        extractor = LLMPatternExtractor(llm_service, catalog=None)

        cluster = {
            "signature": "CS0117",
            "examples": [{
                "compilable_code": "var level = CompressionLevel.Normal;",
                "failure_reason": "error CS0117: 'CompressionLevel' does not contain 'Normal'",
            }]
        }

        patterns = extractor.extract_patterns_with_llm(cluster, "zip")

        assert len(patterns) == 1
        pattern = patterns[0]
        assert pattern["fix_type"] == "regex_replace"
        assert pattern["fix_code"]["pattern"] == r"CompressionLevel\.Normal"
        assert pattern["fix_code"]["replacement"] == "CompressionLevel.Optimal"
        assert pattern["confidence"] == 0.85
        assert pattern["auto_approved"] is True

    def test_code_transform_pattern_extraction(self):
        """Test: LLM generates valid code_transform pattern."""
        llm_response = json.dumps({
            "fix_type": "code_transform",
            "fix_code": {
                "transformer": "fix_stream_disposal",
                "params": {}
            },
            "confidence": 0.9,
            "fix_template": "Wrap stream in using statement",
            "example_before": "var ms = new MemoryStream();",
            "example_after": "using (var ms = new MemoryStream()) { ... }"
        })

        llm_service = MockLLMService(llm_response)
        extractor = LLMPatternExtractor(llm_service, catalog=None)

        cluster = {
            "signature": "ObjectDisposedException",
            "examples": [{
                "compilable_code": "var ms = new MemoryStream(); ms.Dispose(); ms.WriteByte(0);",
                "failure_reason": "ObjectDisposedException: Cannot access a disposed object",
            }]
        }

        patterns = extractor.extract_patterns_with_llm(cluster, "zip")

        assert len(patterns) == 1
        pattern = patterns[0]
        assert pattern["fix_type"] == "code_transform"
        assert pattern["fix_code"]["transformer"] == "fix_stream_disposal"
        assert pattern["confidence"] == 0.9
        assert pattern["auto_approved"] is True

    def test_llm_prompt_pattern_extraction(self):
        """Test: LLM generates valid llm_prompt pattern for complex fixes."""
        llm_response = json.dumps({
            "fix_type": "llm_prompt",
            "fix_code": {
                "prompt": "Fix the null reference error in: {code}\\nError: {error}",
                "system_prompt": "Fix C# code. Return ONLY fixed code."
            },
            "confidence": 0.5,
            "fix_template": "Fix null reference by adding null check",
            "example_before": "var x = obj.Property;",
            "example_after": "var x = obj?.Property ?? default;"
        })

        llm_service = MockLLMService(llm_response)
        extractor = LLMPatternExtractor(llm_service, catalog=None)

        cluster = {
            "signature": "NullReferenceException",
            "examples": [{
                "compilable_code": "var x = obj.Property;",
                "failure_reason": "NullReferenceException: Object reference not set to an instance",
            }]
        }

        patterns = extractor.extract_patterns_with_llm(cluster, "zip")

        assert len(patterns) == 1
        pattern = patterns[0]
        assert pattern["fix_type"] == "llm_prompt"
        assert pattern["fix_code"]["prompt"]
        assert pattern["fix_code"]["system_prompt"]
        assert pattern["confidence"] == 0.5
        assert pattern["auto_approved"] is False  # Low confidence
        assert pattern["requires_llm"] is True

    def test_fallback_on_missing_directive(self):
        """Test: Falls back to llm_prompt when using_directive missing directive field."""
        # Invalid using_directive (missing directive)
        llm_response = json.dumps({
            "fix_type": "using_directive",
            "fix_code": {
                "trigger_type": "Archive"  # Missing 'directive' field!
            },
            "confidence": 0.9,
            "fix_template": "Add using directive for Aspose.Zip"
        })

        llm_service = MockLLMService(llm_response)
        extractor = LLMPatternExtractor(llm_service, catalog=None)

        cluster = {
            "signature": "CS0246",
            "examples": [{
                "compilable_code": "var archive = new Archive();",
                "failure_reason": "error CS0246: The type 'Archive' could not be found",
            }]
        }

        patterns = extractor.extract_patterns_with_llm(cluster, "zip")

        # Should fall back to llm_prompt
        assert len(patterns) == 1
        pattern = patterns[0]
        assert pattern["fix_type"] == "llm_prompt"
        assert pattern["fix_code"]["prompt"]  # Fallback prompt generated

    def test_fallback_on_invalid_regex(self):
        """Test: Falls back to llm_prompt when regex pattern is invalid."""
        # Invalid regex pattern
        llm_response = json.dumps({
            "fix_type": "regex_replace",
            "fix_code": {
                "pattern": r"[invalid(regex",  # Unclosed bracket!
                "replacement": "Fixed"
            },
            "confidence": 0.8,
            "fix_template": "Replace invalid pattern"
        })

        llm_service = MockLLMService(llm_response)
        extractor = LLMPatternExtractor(llm_service, catalog=None)

        cluster = {
            "signature": "CS0117",
            "examples": [{
                "compilable_code": "var x = Something.Invalid;",
                "failure_reason": "error CS0117: Something does not contain Invalid",
            }]
        }

        patterns = extractor.extract_patterns_with_llm(cluster, "zip")

        # Should fall back to llm_prompt
        assert len(patterns) == 1
        pattern = patterns[0]
        assert pattern["fix_type"] == "llm_prompt"

    def test_fallback_on_unknown_transformer(self):
        """Test: Falls back to llm_prompt when transformer is unknown."""
        llm_response = json.dumps({
            "fix_type": "code_transform",
            "fix_code": {
                "transformer": "fix_nonexistent_transformer",  # Not in KNOWN_TRANSFORMERS!
                "params": {}
            },
            "confidence": 0.9,
            "fix_template": "Apply unknown transformer"
        })

        llm_service = MockLLMService(llm_response)
        extractor = LLMPatternExtractor(llm_service, catalog=None)

        cluster = {
            "signature": "RUNTIME_ERROR",
            "examples": [{
                "compilable_code": "var x = 1;",
                "failure_reason": "Some runtime error",
            }]
        }

        patterns = extractor.extract_patterns_with_llm(cluster, "zip")

        # Should fall back to llm_prompt
        assert len(patterns) == 1
        pattern = patterns[0]
        assert pattern["fix_type"] == "llm_prompt"

    def test_catalog_context_included_for_cs0246(self):
        """Test: Catalog context is included in prompt for CS0246 errors."""
        llm_response = json.dumps({
            "fix_type": "using_directive",
            "fix_code": {
                "directive": "using Aspose.Words.Drawing;",
                "trigger_type": "Shape"
            },
            "confidence": 0.9,
            "fix_template": "Add using directive"
        })

        llm_service = MockLLMService(llm_response)
        catalog = MockCatalog()
        extractor = LLMPatternExtractor(llm_service, catalog)

        cluster = {
            "signature": "CS0246",
            "examples": [{
                "compilable_code": "var shape = new Shape();",
                "failure_reason": "error CS0246: The type 'Shape' could not be found",
            }]
        }

        patterns = extractor.extract_patterns_with_llm(cluster, "words")

        # Verify catalog context was included in prompt
        assert len(llm_service.calls) == 1
        prompt = llm_service.calls[0]["prompt"]
        assert "Available API Namespaces" in prompt
        assert "Aspose.Words.Drawing" in prompt
        assert "Shape" in prompt

    def test_prompt_includes_decision_tree(self):
        """Test: Enhanced prompt includes fix type decision tree."""
        llm_service = MockLLMService(json.dumps({
            "fix_type": "llm_prompt",
            "fix_code": {"prompt": "Fix it", "system_prompt": "Fix code"},
            "confidence": 0.5,
            "fix_template": "Fix"
        }))
        extractor = LLMPatternExtractor(llm_service, catalog=None)

        cluster = {
            "signature": "RUNTIME_ERROR",
            "examples": [{"compilable_code": "var x = 1;", "failure_reason": "Error"}]
        }

        extractor.extract_patterns_with_llm(cluster, "zip")

        # Verify prompt structure
        prompt = llm_service.calls[0]["prompt"]
        assert "Fix Type Decision Tree" in prompt
        assert "using_directive" in prompt
        assert "regex_replace" in prompt
        assert "code_transform" in prompt
        assert "llm_prompt" in prompt

    def test_prompt_includes_examples(self):
        """Test: Enhanced prompt includes concrete examples for each fix_type."""
        llm_service = MockLLMService(json.dumps({
            "fix_type": "llm_prompt",
            "fix_code": {"prompt": "Fix it", "system_prompt": "Fix code"},
            "confidence": 0.5,
            "fix_template": "Fix"
        }))
        extractor = LLMPatternExtractor(llm_service, catalog=None)

        cluster = {
            "signature": "RUNTIME_ERROR",
            "examples": [{"compilable_code": "var x = 1;", "failure_reason": "Error"}]
        }

        extractor.extract_patterns_with_llm(cluster, "zip")

        # Verify examples are in prompt
        prompt = llm_service.calls[0]["prompt"]
        assert "Example 1: using_directive" in prompt
        assert "Example 2: regex_replace" in prompt
        assert "Example 3: code_transform" in prompt
        assert "Example 4: llm_prompt" in prompt
        assert "CompressionLevel.Optimal" in prompt  # From regex example

    def test_confidence_clamping(self):
        """Test: Confidence values are clamped to 0.1-0.9 range."""
        # Test high confidence (above 1.0)
        llm_response = json.dumps({
            "fix_type": "using_directive",
            "fix_code": {"directive": "using Aspose.Zip;", "trigger_type": "Archive"},
            "confidence": 1.5,  # Too high!
            "fix_template": "Add directive"
        })

        llm_service = MockLLMService(llm_response)
        extractor = LLMPatternExtractor(llm_service, catalog=None)

        cluster = {
            "signature": "CS0246",
            "examples": [{"compilable_code": "var a = new Archive();", "failure_reason": "CS0246"}]
        }

        patterns = extractor.extract_patterns_with_llm(cluster, "zip")
        assert patterns[0]["confidence"] == 0.9  # Clamped to max

        # Test low confidence (below 0.0)
        llm_response = json.dumps({
            "fix_type": "llm_prompt",
            "fix_code": {"prompt": "Fix", "system_prompt": "Fix"},
            "confidence": -0.5,  # Too low!
            "fix_template": "Fix"
        })

        llm_service = MockLLMService(llm_response)
        extractor = LLMPatternExtractor(llm_service, catalog=None)

        patterns = extractor.extract_patterns_with_llm(cluster, "zip")
        assert patterns[0]["confidence"] == 0.1  # Clamped to min

    def test_auto_approved_threshold_differs_by_type(self):
        """Test: auto_approved threshold is 0.8 for executable, 0.85 for llm_prompt."""
        # Executable pattern with confidence 0.8 should be auto_approved
        llm_response = json.dumps({
            "fix_type": "using_directive",
            "fix_code": {"directive": "using Aspose.Zip;", "trigger_type": "Archive"},
            "confidence": 0.8,
            "fix_template": "Add directive"
        })

        llm_service = MockLLMService(llm_response)
        extractor = LLMPatternExtractor(llm_service, catalog=None)

        cluster = {
            "signature": "CS0246",
            "examples": [{"compilable_code": "var a = new Archive();", "failure_reason": "CS0246"}]
        }

        patterns = extractor.extract_patterns_with_llm(cluster, "zip")
        assert patterns[0]["auto_approved"] is True  # 0.8 is enough for executable

        # llm_prompt pattern with confidence 0.8 should NOT be auto_approved
        llm_response = json.dumps({
            "fix_type": "llm_prompt",
            "fix_code": {"prompt": "Fix", "system_prompt": "Fix"},
            "confidence": 0.8,
            "fix_template": "Fix"
        })

        llm_service = MockLLMService(llm_response)
        extractor = LLMPatternExtractor(llm_service, catalog=None)

        patterns = extractor.extract_patterns_with_llm(cluster, "zip")
        assert patterns[0]["auto_approved"] is False  # 0.8 is NOT enough for llm_prompt (needs 0.85)

    def test_known_transformers_registry(self):
        """Test: KNOWN_TRANSFORMERS constant is defined and contains expected transformers."""
        assert hasattr(LLMPatternExtractor, "KNOWN_TRANSFORMERS")
        transformers = LLMPatternExtractor.KNOWN_TRANSFORMERS

        # Should contain transformers from semantic_microfixes.py
        assert "fix_stream_disposal" in transformers
        assert "fix_rar_password" in transformers
        assert "fix_entries_string_index" in transformers
        assert isinstance(transformers, set)

    def test_invalid_json_returns_none(self):
        """Test: Invalid JSON response returns None (graceful failure)."""
        llm_service = MockLLMService("This is not valid JSON {{{")
        extractor = LLMPatternExtractor(llm_service, catalog=None)

        cluster = {
            "signature": "CS0246",
            "examples": [{"compilable_code": "var x = 1;", "failure_reason": "Error"}]
        }

        patterns = extractor.extract_patterns_with_llm(cluster, "zip")
        assert len(patterns) == 0  # No patterns extracted (graceful failure)

    def test_markdown_fence_removal(self):
        """Test: Markdown code fences are removed from LLM response."""
        llm_response_with_fence = """```json
{
    "fix_type": "using_directive",
    "fix_code": {
        "directive": "using Aspose.Zip;",
        "trigger_type": "Archive"
    },
    "confidence": 0.9,
    "fix_template": "Add directive"
}
```"""

        llm_service = MockLLMService(llm_response_with_fence)
        extractor = LLMPatternExtractor(llm_service, catalog=None)

        cluster = {
            "signature": "CS0246",
            "examples": [{"compilable_code": "var a = new Archive();", "failure_reason": "CS0246"}]
        }

        patterns = extractor.extract_patterns_with_llm(cluster, "zip")
        assert len(patterns) == 1
        assert patterns[0]["fix_type"] == "using_directive"


if __name__ == "__main__":
    # Run tests directly for quick validation
    sys.stdout.reconfigure(encoding="utf-8")

    print("=" * 60)
    print("Auto-Learn Executable Patterns Tests (SR-02-B)")
    print("=" * 60)

    pytest.main([__file__, "-v", "--tb=short"])
