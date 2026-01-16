"""
Tests for ID-03: Original-Anchored Fix Prompts

This test suite verifies that LLM fix prompts are properly anchored to
the original code to reduce drift generation at the source.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.services.llm_service import LLMService, LLMResponse


class TestPromptStructure:
    """Test that prompts include all required sections."""

    @pytest.fixture
    def llm_service(self):
        """Create LLM service with mocked client."""
        service = LLMService(provider="openai", model="gpt-4o", api_key="test-key")
        # Mock the client to avoid actual API calls
        service._client = Mock()
        return service

    def test_fix_code_accepts_original_code_parameter(self, llm_service):
        """Test that fix_code() accepts original_code parameter."""
        with patch.object(llm_service, 'complete') as mock_complete:
            mock_complete.return_value = LLMResponse(
                content="fixed code",
                model="gpt-4o",
                usage={},
                finish_reason="stop",
                latency_ms=100,
                success=True
            )

            # Should not raise TypeError
            llm_service.fix_code(
                code="var x = 1;",
                error_logs="CS1002: ; expected",
                context_type="compile",
                original_code="var x = 1"  # NEW parameter
            )

    def test_fix_prompt_includes_original_code_section_when_different(self, llm_service):
        """Test that original code section is included when original differs from current."""
        with patch.object(llm_service, 'complete') as mock_complete:
            mock_complete.return_value = LLMResponse(
                content="fixed code",
                model="gpt-4o",
                usage={},
                finish_reason="stop",
                latency_ms=100,
                success=True
            )

            llm_service.fix_code(
                code="using System;\nvar x = 1;",  # Current code (different)
                error_logs="CS1002: ; expected",
                context_type="compile",
                original_code="var x = 1"  # Original code (no using)
            )

            # Get the prompt that was passed to complete()
            call_args = mock_complete.call_args
            prompt = call_args[1]['prompt']

            # Verify original code section exists
            assert "## Original Code (teaching intent reference):" in prompt
            assert "**CRITICAL**: The original code demonstrates a specific concept/feature." in prompt
            assert "Your fix MUST preserve this teaching intent." in prompt
            assert "Do NOT add features, error handling, or complexity" in prompt

            # Verify original code is in prompt
            assert "var x = 1" in prompt

            # Verify there's also a "Current Code" section
            assert "## Current Code (to be fixed):" in prompt

    def test_fix_prompt_includes_minimal_change_instruction(self, llm_service):
        """Test that prompts include minimal change instructions."""
        with patch.object(llm_service, 'complete') as mock_complete:
            mock_complete.return_value = LLMResponse(
                content="fixed code",
                model="gpt-4o",
                usage={},
                finish_reason="stop",
                latency_ms=100,
                success=True
            )

            llm_service.fix_code(
                code="var x = 1;",
                error_logs="CS1002: ; expected",
                context_type="compile"
            )

            prompt = mock_complete.call_args[1]['prompt']

            # Verify Fix Instructions section
            assert "## Fix Instructions:" in prompt
            assert "1. **Minimal Changes**: Make ONLY the changes needed to fix the errors" in prompt
            assert "2. **Preserve Intent**: The fixed code must demonstrate the SAME concept" in prompt
            assert "3. **No Scope Creep**: Do NOT add error handling, validation, or features" in prompt
            assert "4. **Teaching Clarity**: A reader should understand the same lesson" in prompt

    def test_fix_prompt_includes_intent_preservation_emphasis(self, llm_service):
        """Test that prompts emphasize intent preservation."""
        with patch.object(llm_service, 'complete') as mock_complete:
            mock_complete.return_value = LLMResponse(
                content="fixed code",
                model="gpt-4o",
                usage={},
                finish_reason="stop",
                latency_ms=100,
                success=True
            )

            llm_service.fix_code(
                code="var x = 1;",
                error_logs="CS1002: ; expected",
                context_type="compile",
                original_code="var x = 1"
            )

            prompt = mock_complete.call_args[1]['prompt']

            # Check for intent preservation language
            assert "preserve this teaching intent" in prompt.lower()
            assert "preserve intent" in prompt.lower() or "preserving intent" in prompt.lower()

    def test_fix_prompt_includes_scope_creep_examples(self, llm_service):
        """Test that prompts include examples of BAD fixes (scope creep)."""
        with patch.object(llm_service, 'complete') as mock_complete:
            mock_complete.return_value = LLMResponse(
                content="fixed code",
                model="gpt-4o",
                usage={},
                finish_reason="stop",
                latency_ms=100,
                success=True
            )

            llm_service.fix_code(
                code="var x = 1;",
                error_logs="CS1002: ; expected",
                context_type="compile"
            )

            prompt = mock_complete.call_args[1]['prompt']

            # Verify BAD fixes section
            assert "## Examples of BAD fixes (scope creep):" in prompt
            assert "❌ Adding try-catch blocks when original had none" in prompt
            assert "❌ Adding File.Exists() checks when original assumed file exists" in prompt
            assert "❌ Adding complex error messages when original used simple code" in prompt
            assert "❌ Restructuring code into methods when original was inline" in prompt

    def test_fix_prompt_includes_good_fix_examples(self, llm_service):
        """Test that prompts include examples of GOOD fixes (minimal)."""
        with patch.object(llm_service, 'complete') as mock_complete:
            mock_complete.return_value = LLMResponse(
                content="fixed code",
                model="gpt-4o",
                usage={},
                finish_reason="stop",
                latency_ms=100,
                success=True
            )

            llm_service.fix_code(
                code="var x = 1;",
                error_logs="CS1002: ; expected",
                context_type="compile"
            )

            prompt = mock_complete.call_args[1]['prompt']

            # Verify GOOD fixes section
            assert "## Examples of GOOD fixes (minimal):" in prompt
            assert "✅ Adding missing using statement" in prompt
            assert "✅ Fixing typo in variable name" in prompt
            assert "✅ Correcting API method signature" in prompt
            assert "✅ Adding namespace qualification" in prompt


class TestConditionalLogic:
    """Test conditional logic for original code inclusion."""

    @pytest.fixture
    def llm_service(self):
        """Create LLM service with mocked client."""
        service = LLMService(provider="openai", model="gpt-4o", api_key="test-key")
        service._client = Mock()
        return service

    def test_original_code_not_included_if_identical(self, llm_service):
        """Test that original code section is NOT included when identical to current code."""
        with patch.object(llm_service, 'complete') as mock_complete:
            mock_complete.return_value = LLMResponse(
                content="fixed code",
                model="gpt-4o",
                usage={},
                finish_reason="stop",
                latency_ms=100,
                success=True
            )

            same_code = "using System;\nvar x = 1;"

            llm_service.fix_code(
                code=same_code,
                error_logs="CS1002: ; expected",
                context_type="compile",
                original_code=same_code  # Identical
            )

            prompt = mock_complete.call_args[1]['prompt']

            # Original code section should NOT be present
            assert "## Original Code (teaching intent reference):" not in prompt
            # But current code section should still be there
            assert "## Current Code (to be fixed):" in prompt

    def test_original_code_not_included_if_none(self, llm_service):
        """Test that original code section is NOT included when original_code is None."""
        with patch.object(llm_service, 'complete') as mock_complete:
            mock_complete.return_value = LLMResponse(
                content="fixed code",
                model="gpt-4o",
                usage={},
                finish_reason="stop",
                latency_ms=100,
                success=True
            )

            llm_service.fix_code(
                code="using System;\nvar x = 1;",
                error_logs="CS1002: ; expected",
                context_type="compile",
                original_code=None  # Not provided
            )

            prompt = mock_complete.call_args[1]['prompt']

            # Original code section should NOT be present
            assert "## Original Code (teaching intent reference):" not in prompt

    def test_original_code_included_if_different(self, llm_service):
        """Test that original code section IS included when different from current."""
        with patch.object(llm_service, 'complete') as mock_complete:
            mock_complete.return_value = LLMResponse(
                content="fixed code",
                model="gpt-4o",
                usage={},
                finish_reason="stop",
                latency_ms=100,
                success=True
            )

            llm_service.fix_code(
                code="using System;\nusing Aspose.Zip;\nvar x = 1;",  # Has extra using
                error_logs="CS1002: ; expected",
                context_type="compile",
                original_code="var x = 1;"  # Original without usings
            )

            prompt = mock_complete.call_args[1]['prompt']

            # Original code section SHOULD be present
            assert "## Original Code (teaching intent reference):" in prompt
            assert "## Current Code (to be fixed):" in prompt


class TestBackwardCompatibility:
    """Test backward compatibility without original_code parameter."""

    @pytest.fixture
    def llm_service(self):
        """Create LLM service with mocked client."""
        service = LLMService(provider="openai", model="gpt-4o", api_key="test-key")
        service._client = Mock()
        return service

    def test_backward_compatibility_without_original_code(self, llm_service):
        """Test that fix_code works without original_code parameter (backward compatible)."""
        with patch.object(llm_service, 'complete') as mock_complete:
            mock_complete.return_value = LLMResponse(
                content="fixed code",
                model="gpt-4o",
                usage={},
                finish_reason="stop",
                latency_ms=100,
                success=True
            )

            # Should work without original_code parameter
            llm_service.fix_code(
                code="var x = 1;",
                error_logs="CS1002: ; expected",
                context_type="compile"
                # No original_code parameter
            )

            prompt = mock_complete.call_args[1]['prompt']

            # Should still have all the new sections except original code
            assert "## Fix Instructions:" in prompt
            assert "## Examples of BAD fixes (scope creep):" in prompt
            assert "## Examples of GOOD fixes (minimal):" in prompt
            # But no original code section
            assert "## Original Code (teaching intent reference):" not in prompt


class TestRuntimePrompts:
    """Test runtime fix prompts have same enhancements."""

    @pytest.fixture
    def llm_service(self):
        """Create LLM service with mocked client."""
        service = LLMService(provider="openai", model="gpt-4o", api_key="test-key")
        service._client = Mock()
        return service

    def test_runtime_prompts_include_original_code(self, llm_service):
        """Test that runtime prompts also include original code section."""
        with patch.object(llm_service, 'complete') as mock_complete:
            mock_complete.return_value = LLMResponse(
                content="fixed code",
                model="gpt-4o",
                usage={},
                finish_reason="stop",
                latency_ms=100,
                success=True
            )

            llm_service.fix_code(
                code="using System;\nFile.ReadAllText(\"missing.txt\");",
                error_logs="System.IO.FileNotFoundException",
                context_type="runtime",
                original_code="File.ReadAllText(\"data.txt\");"
            )

            prompt = mock_complete.call_args[1]['prompt']

            # Verify original code section
            assert "## Original Code (teaching intent reference):" in prompt
            assert "## Fix Instructions:" in prompt
            assert "## Examples of BAD fixes (scope creep):" in prompt
            assert "## Examples of GOOD fixes (minimal):" in prompt

    def test_runtime_prompts_include_minimal_change_instructions(self, llm_service):
        """Test that runtime prompts include minimal change instructions."""
        with patch.object(llm_service, 'complete') as mock_complete:
            mock_complete.return_value = LLMResponse(
                content="fixed code",
                model="gpt-4o",
                usage={},
                finish_reason="stop",
                latency_ms=100,
                success=True
            )

            llm_service.fix_code(
                code="File.ReadAllText(\"missing.txt\");",
                error_logs="System.IO.FileNotFoundException",
                context_type="runtime"
            )

            prompt = mock_complete.call_args[1]['prompt']

            # Verify instructions
            assert "## Fix Instructions:" in prompt
            assert "Minimal Changes" in prompt


class TestPromptValidation:
    """Test prompt structure validation."""

    @pytest.fixture
    def llm_service(self):
        """Create LLM service with mocked client."""
        service = LLMService(provider="openai", model="gpt-4o", api_key="test-key")
        service._client = Mock()
        return service

    def test_prompt_structure_valid(self, llm_service):
        """Test that generated prompts have valid structure."""
        with patch.object(llm_service, 'complete') as mock_complete:
            mock_complete.return_value = LLMResponse(
                content="fixed code",
                model="gpt-4o",
                usage={},
                finish_reason="stop",
                latency_ms=100,
                success=True
            )

            llm_service.fix_code(
                code="var x = 1;",
                error_logs="CS1002: ; expected",
                context_type="compile",
                original_code="var x = 1"
            )

            prompt = mock_complete.call_args[1]['prompt']

            # Check that sections appear in logical order
            original_idx = prompt.find("## Original Code (teaching intent reference):")
            current_idx = prompt.find("## Current Code (to be fixed):")
            errors_idx = prompt.find("## Compilation Errors:")
            instructions_idx = prompt.find("## Fix Instructions:")
            bad_idx = prompt.find("## Examples of BAD fixes")
            good_idx = prompt.find("## Examples of GOOD fixes")

            # Original should come before current
            assert original_idx < current_idx
            # Current should come before errors
            assert current_idx < errors_idx
            # Instructions should exist
            assert instructions_idx > 0
            # BAD examples should come before GOOD examples
            assert bad_idx < good_idx

    def test_csharp_code_blocks_properly_formatted(self, llm_service):
        """Test that C# code blocks are properly formatted with language tags."""
        with patch.object(llm_service, 'complete') as mock_complete:
            mock_complete.return_value = LLMResponse(
                content="fixed code",
                model="gpt-4o",
                usage={},
                finish_reason="stop",
                latency_ms=100,
                success=True
            )

            original = "var x = 1;"
            current = "using System;\nvar x = 1;"

            llm_service.fix_code(
                code=current,
                error_logs="CS1002: ; expected",
                context_type="compile",
                original_code=original
            )

            prompt = mock_complete.call_args[1]['prompt']

            # Check for proper code block formatting
            assert "```csharp" in prompt
            # Should have at least 2 code blocks (original and current)
            assert prompt.count("```csharp") >= 2
            # Each opening should have a closing
            assert prompt.count("```") % 2 == 0  # Even number of ``` (open + close)


class TestEdgeCases:
    """Test edge cases for original code handling."""

    @pytest.fixture
    def llm_service(self):
        """Create LLM service with mocked client."""
        service = LLMService(provider="openai", model="gpt-4o", api_key="test-key")
        service._client = Mock()
        return service

    def test_empty_original_code(self, llm_service):
        """Test handling of empty original_code string."""
        with patch.object(llm_service, 'complete') as mock_complete:
            mock_complete.return_value = LLMResponse(
                content="fixed code",
                model="gpt-4o",
                usage={},
                finish_reason="stop",
                latency_ms=100,
                success=True
            )

            llm_service.fix_code(
                code="var x = 1;",
                error_logs="CS1002: ; expected",
                context_type="compile",
                original_code=""  # Empty string
            )

            prompt = mock_complete.call_args[1]['prompt']

            # Empty original should be treated as None (not included)
            assert "## Original Code (teaching intent reference):" not in prompt

    def test_very_long_original_code(self, llm_service):
        """Test handling of very long original code."""
        with patch.object(llm_service, 'complete') as mock_complete:
            mock_complete.return_value = LLMResponse(
                content="fixed code",
                model="gpt-4o",
                usage={},
                finish_reason="stop",
                latency_ms=100,
                success=True
            )

            # Create a long original code
            long_code = "var x = 1;\n" * 1000
            current_code = "using System;\n" + long_code

            llm_service.fix_code(
                code=current_code,
                error_logs="CS1002: ; expected",
                context_type="compile",
                original_code=long_code
            )

            prompt = mock_complete.call_args[1]['prompt']

            # Should still include original code section
            assert "## Original Code (teaching intent reference):" in prompt
            # And should include the long code
            assert long_code in prompt

    def test_whitespace_only_difference(self, llm_service):
        """Test that whitespace-only differences are considered identical."""
        with patch.object(llm_service, 'complete') as mock_complete:
            mock_complete.return_value = LLMResponse(
                content="fixed code",
                model="gpt-4o",
                usage={},
                finish_reason="stop",
                latency_ms=100,
                success=True
            )

            llm_service.fix_code(
                code="var x = 1;",  # No leading/trailing whitespace
                error_logs="CS1002: ; expected",
                context_type="compile",
                original_code="  var x = 1;  "  # With whitespace
            )

            prompt = mock_complete.call_args[1]['prompt']

            # Whitespace-only difference should be ignored (strip() comparison)
            # So original code section should NOT be present
            assert "## Original Code (teaching intent reference):" not in prompt


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
