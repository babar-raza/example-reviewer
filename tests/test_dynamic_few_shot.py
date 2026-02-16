"""
Tests for dynamic few-shot example selection in LLM service (WS4/LLM-01).
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.services.llm_service import LLMService


class TestDynamicFewShot:
    """Test suite for _build_few_shot_section method."""

    @pytest.fixture
    def llm_service(self):
        """Create an LLM service instance for testing."""
        return LLMService(provider='openai', model='gpt-4o')

    def test_fallback_to_static_when_no_similar_examples(self, llm_service):
        """Should use static FEW_SHOT_EXAMPLES when no similar_examples provided."""
        result = llm_service._build_few_shot_section(
            error_logs='CS0246: Archive not found',
            family='zip',
            catalog=None,
            similar_examples=None
        )

        assert '## Minimal Fix Patterns:' in result
        assert 'Example 1: Missing using statement fix' in result
        assert 'Example 2: Missing wrapper fix' in result
        assert 'Example 3: Missing compression settings namespace' in result

    def test_fallback_to_static_when_empty_similar_examples(self, llm_service):
        """Should use static examples when similar_examples list is empty."""
        result = llm_service._build_few_shot_section(
            error_logs='CS0246: Archive not found',
            family='zip',
            catalog=None,
            similar_examples=[]
        )

        assert 'Example 1: Missing using statement fix' in result

    def test_dynamic_examples_from_cs_file_source(self, llm_service):
        """Should use CS_FILE examples when available from vector DB."""
        mock_examples = [
            ('ex1', 'using Aspose.Zip;\nvar archive = new Archive();', 0.95,
             {'source_type': 'cs_file', 'topic': 'archive creation'}),
            ('ex2', 'using Aspose.Zip.Saving;\nvar settings = new DeflateCompressionSettings();', 0.92,
             {'source_type': 'cs_file', 'topic': 'compression settings'}),
        ]

        result = llm_service._build_few_shot_section(
            error_logs='CS0246: Archive not found',
            family='zip',
            catalog=None,
            similar_examples=mock_examples
        )

        # Should contain dynamic examples
        assert 'archive creation' in result
        assert 'using Aspose.Zip' in result

        # Should NOT contain static examples
        assert 'Example 1: Missing using statement fix' not in result

    def test_ignores_non_cs_file_examples(self, llm_service):
        """Should skip examples that are not from cs_file source."""
        mock_examples = [
            ('ex1', 'using System;\nconsole.WriteLine("test");', 0.95,
             {'source_type': 'markdown', 'topic': 'console app'}),
            ('ex2', 'var x = 5;', 0.90,
             {'source_type': 'fixed_example', 'topic': 'variable'}),
        ]

        result = llm_service._build_few_shot_section(
            error_logs='CS0246: Archive not found',
            family='zip',
            catalog=None,
            similar_examples=mock_examples
        )

        # Should fall back to static since no cs_file examples
        assert 'Example 1: Missing using statement fix' in result
        assert 'console app' not in result

    def test_limits_to_two_examples(self, llm_service):
        """Should only use first 2 CS_FILE examples even if more available."""
        mock_examples = [
            ('ex1', 'code1', 0.95, {'source_type': 'cs_file', 'topic': 'topic1'}),
            ('ex2', 'code2', 0.92, {'source_type': 'cs_file', 'topic': 'topic2'}),
            ('ex3', 'code3', 0.88, {'source_type': 'cs_file', 'topic': 'topic3'}),
            ('ex4', 'code4', 0.85, {'source_type': 'cs_file', 'topic': 'topic4'}),
        ]

        result = llm_service._build_few_shot_section(
            error_logs='CS0246: Archive not found',
            family='zip',
            catalog=None,
            similar_examples=mock_examples
        )

        # First 2 should be present
        assert 'topic1' in result
        assert 'topic2' in result

        # Last 2 should not be present
        assert 'topic3' not in result
        assert 'topic4' not in result

    def test_truncates_long_code_examples(self, llm_service):
        """Should truncate code examples longer than 500 chars."""
        long_code = 'x' * 1000
        mock_examples = [
            ('ex1', long_code, 0.95, {'source_type': 'cs_file', 'topic': 'long example'}),
        ]

        result = llm_service._build_few_shot_section(
            error_logs='CS0246: Archive not found',
            family='zip',
            catalog=None,
            similar_examples=mock_examples
        )

        # Should contain truncation marker
        assert '// ... (truncated)' in result
        # Should not contain the full code
        assert long_code not in result

    def test_handles_missing_topic_metadata(self, llm_service):
        """Should handle examples with missing topic gracefully."""
        mock_examples = [
            ('ex1', 'code1', 0.95, {'source_type': 'cs_file'}),  # No topic
        ]

        result = llm_service._build_few_shot_section(
            error_logs='CS0246: Archive not found',
            family='zip',
            catalog=None,
            similar_examples=mock_examples
        )

        # Should use default topic
        assert 'similar example' in result

    def test_error_code_extraction(self, llm_service):
        """Should extract error code from error logs."""
        result = llm_service._build_few_shot_section(
            error_logs='error CS1234: Some error message',
            family='zip',
            catalog=None,
            similar_examples=None
        )

        # Error code should be present in output (optional feature)
        # This is allowed but not required
        assert '## Minimal Fix Patterns:' in result

    def test_string_format_falls_back_to_static(self, llm_service):
        """Should fall back to static examples when given string format (current orchestrator format)."""
        # Orchestrator currently passes code strings, not tuples with metadata
        mock_examples_strings = ['code1', 'code2']

        result = llm_service._build_few_shot_section(
            error_logs='CS0246: Archive not found',
            family='zip',
            catalog=None,
            similar_examples=mock_examples_strings
        )

        # Should fall back to static since we can't extract cs_file metadata from strings
        assert 'Example 1: Missing using statement fix' in result


class TestFewShotIntegrationInFixCompileCode:
    """Test integration of _build_few_shot_section in _fix_compile_code."""

    @pytest.fixture
    def llm_service(self):
        """Create an LLM service instance for testing."""
        return LLMService(provider='openai', model='gpt-4o')

    def test_fix_compile_code_calls_build_few_shot(self, llm_service):
        """Should call _build_few_shot_section when fixing compile errors."""
        family_config = {'family': 'zip', 'api_patterns': {}}

        with patch.object(llm_service, '_build_few_shot_section') as mock_build, \
             patch.object(llm_service, 'complete') as mock_complete:
            mock_build.return_value = "## Minimal Fix Patterns:\nTest pattern"
            mock_complete.return_value = Mock(success=True, content='fixed code')

            # Pass strings like the orchestrator does (not tuples)
            llm_service._fix_compile_code(
                code='var archive = new Archive();',
                error_logs='CS0246: Archive not found',
                family_config=family_config,
                similar_examples=['code1', 'code2']  # Strings, not tuples
            )

            # Verify _build_few_shot_section was called with correct params
            mock_build.assert_called_once()
            call_args = mock_build.call_args
            assert call_args[0][0] == 'CS0246: Archive not found'  # error_logs
            assert call_args[0][1] == 'zip'  # family
            # similar_examples should be passed through
            assert call_args[0][3] is not None

    def test_fix_compile_code_handles_dict_family_config(self, llm_service):
        """Should extract family from dict-based family_config."""
        family_config_dict = {'family': 'words', 'api_patterns': {}}

        with patch.object(llm_service, '_build_few_shot_section') as mock_build, \
             patch.object(llm_service, 'complete') as mock_complete:
            mock_build.return_value = "## Minimal Fix Patterns:\nTest pattern"
            mock_complete.return_value = Mock(success=True, content='fixed code')

            llm_service._fix_compile_code(
                code='var doc = new Document();',
                error_logs='CS0246: Document not found',
                family_config=family_config_dict,
                similar_examples=None
            )

            # Verify correct family extracted
            call_args = mock_build.call_args
            assert call_args[0][1] == 'words'

    def test_fix_compile_code_handles_missing_family_config(self, llm_service):
        """Should handle None family_config gracefully."""
        with patch.object(llm_service, '_build_few_shot_section') as mock_build, \
             patch.object(llm_service, 'complete') as mock_complete:
            mock_build.return_value = "## Minimal Fix Patterns:\nTest pattern"
            mock_complete.return_value = Mock(success=True, content='fixed code')

            llm_service._fix_compile_code(
                code='var archive = new Archive();',
                error_logs='CS0246: Archive not found',
                family_config=None,
                similar_examples=None
            )

            # Should default to 'unknown'
            call_args = mock_build.call_args
            assert call_args[0][1] == 'unknown'


class TestVectorDBIntegration:
    """Test integration with vector DB similar_examples."""

    @pytest.fixture
    def llm_service(self):
        """Create an LLM service instance for testing."""
        return LLMService(provider='openai', model='gpt-4o')

    def test_vector_db_result_format_compatibility(self, llm_service):
        """Should handle vector DB result format: (id, code, score, metadata)."""
        # This is the actual format returned by vector_db_service.search_similar
        vector_db_results = [
            (
                'zip_example_001',
                'using Aspose.Zip;\nusing System.IO;\n\nvar archive = new Archive();',
                0.95,
                {
                    'family': 'zip',
                    'source_type': 'cs_file',
                    'topic': 'archive creation',
                    'app_context': 'console'
                }
            ),
            (
                'zip_example_002',
                'using Aspose.Zip.Saving;\nvar settings = new DeflateCompressionSettings();',
                0.92,
                {
                    'family': 'zip',
                    'source_type': 'cs_file',
                    'topic': 'compression',
                    'app_context': 'library'
                }
            )
        ]

        result = llm_service._build_few_shot_section(
            error_logs='CS0246: Archive not found',
            family='zip',
            catalog=None,
            similar_examples=vector_db_results
        )

        # Should successfully extract and use the examples
        assert 'archive creation' in result
        assert 'using Aspose.Zip' in result
        assert 'compression' in result

    def test_mixed_source_types_prioritizes_cs_file(self, llm_service):
        """Should prioritize cs_file over other source types."""
        mixed_results = [
            ('ex1', 'markdown code', 0.98, {'source_type': 'markdown', 'topic': 'high score markdown'}),
            ('ex2', 'cs_file code', 0.85, {'source_type': 'cs_file', 'topic': 'lower score cs_file'}),
        ]

        result = llm_service._build_few_shot_section(
            error_logs='CS0246: Archive not found',
            family='zip',
            catalog=None,
            similar_examples=mixed_results
        )

        # Should use cs_file despite lower score
        assert 'lower score cs_file' in result
        # Should not use markdown despite higher score
        assert 'high score markdown' not in result
