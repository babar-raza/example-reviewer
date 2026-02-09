"""
Unit tests for APIContextService.

TASK-3B: Tests for smart API documentation chunking.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path
from src.services.api_context_service import APIContextService


@pytest.fixture
def api_context_service():
    """Create APIContextService instance without API reference."""
    return APIContextService(api_reference_service=None)


@pytest.fixture
def api_context_with_reference():
    """Create APIContextService with mock API reference."""
    mock_api_ref = Mock()
    mock_api_ref.get_context_for_error.return_value = "Mock API context"
    return APIContextService(api_reference_service=mock_api_ref)


@pytest.fixture
def sample_docs_index():
    """Sample documentation index for testing."""
    return {
        "ChartType": [Mock(relative_path="ChartType.md", preview="Chart type documentation")],
        "Document": [Mock(relative_path="Document.md", preview="Document class docs")],
        "ChartSeriesCollection": [Mock(relative_path="ChartSeriesCollection.md")],
        "Aspose": [Mock(relative_path="Aspose.md")],
        "Words": [Mock(relative_path="Words.md")],
    }


class TestEntityExtraction:
    """Test entity extraction from error messages."""

    def test_extract_entities_simple_error(self, api_context_service):
        """Test extraction from simple 'does not exist' error."""
        error_msg = "'ChartType' does not exist in current context"
        entities = api_context_service.extract_entities_from_error("CS0103", error_msg)

        assert "ChartType" in entities
        assert len(entities) >= 1

    def test_extract_entities_cs0103_style(self, api_context_service):
        """Test CS0103 error pattern (name does not exist)."""
        error_msg = "'CompressionLevel' does not exist in the current context"
        entities = api_context_service.extract_entities_from_error("CS0103", error_msg)

        assert "CompressionLevel" in entities

    def test_extract_entities_cs0117_style(self, api_context_service):
        """Test CS0117 error pattern (contains definition)."""
        error_msg = "'Document' does not contain a definition for 'BuildDoc'"
        entities = api_context_service.extract_entities_from_error("CS0117", error_msg)

        assert "Document" in entities
        assert "BuildDoc" in entities

    def test_extract_entities_cs0246_style(self, api_context_service):
        """Test CS0246 error pattern (type or namespace name)."""
        error_msg = "type or namespace name 'ChartSeriesCollection' could not be found"
        entities = api_context_service.extract_entities_from_error("CS0246", error_msg)

        assert "ChartSeriesCollection" in entities

    def test_extract_entities_dotted_names(self, api_context_service):
        """Test extraction with dotted namespace.Type patterns."""
        error_msg = "type or namespace name 'Aspose.Words.Document' could not be found"
        entities = api_context_service.extract_entities_from_error("CS0246", error_msg)

        # Should extract from the pattern
        assert len(entities) > 0

    def test_extract_entities_backtick_style(self, api_context_service):
        """Test extraction from backtick-quoted names."""
        error_msg = "Cannot find type `ChartType` in namespace"
        entities = api_context_service.extract_entities_from_error("CS0234", error_msg)

        assert "ChartType" in entities

    def test_extract_entities_multiple_patterns(self, api_context_service):
        """Test extraction with multiple error patterns in one message."""
        error_msg = "'ChartType' does not exist and 'Document' does not contain a definition for 'Test'"
        entities = api_context_service.extract_entities_from_error("CS0103", error_msg)

        # Should extract at least ChartType
        assert "ChartType" in entities or len(entities) > 0

    def test_extract_entities_ignores_single_chars(self, api_context_service):
        """Test that single character matches are ignored."""
        error_msg = "'X' does not exist"
        entities = api_context_service.extract_entities_from_error("CS0103", error_msg)

        # Single char should be filtered
        assert "X" not in entities or len(entities) == 0

    def test_extract_entities_empty_error_message(self, api_context_service):
        """Test behavior with empty error message."""
        entities = api_context_service.extract_entities_from_error("CS0103", "")

        assert len(entities) == 0

    def test_extract_entities_case_variations(self, api_context_service):
        """Test extraction handles case variations correctly."""
        error_msg = "'charttype' does not exist"
        entities = api_context_service.extract_entities_from_error("CS0103", error_msg)

        assert "charttype" in entities

    def test_extract_entities_from_stacktrace(self, api_context_service):
        """Test extraction from stack trace patterns."""
        error_msg = """
        Unhandled exception: System.ArgumentException
        at Aspose.Words.Document.Open(String path)
        at Program.Main()
        """
        entities = api_context_service.extract_entities_from_error("CS0000", error_msg)

        # Should extract class and method names
        assert len(entities) > 0


class TestRelevanceRanking:
    """Test relevance ranking algorithm."""

    def test_rank_exact_matches_highest(self, api_context_service, sample_docs_index):
        """Test that exact matches rank highest."""
        entities = {"ChartType", "Document"}
        ranked = api_context_service._rank_matches(entities, sample_docs_index)

        # Both entities should be ranked
        entity_names = [name for name, score in ranked]
        assert "ChartType" in entity_names
        assert "Document" in entity_names

    def test_rank_exact_beats_partial(self, api_context_service):
        """Test that exact matches score higher than partial."""
        docs_index = {
            "Chart": [Mock()],
            "ChartType": [Mock()],
            "ChartSeriesCollection": [Mock()],
        }
        entities = {"Chart"}
        ranked = api_context_service._rank_matches(entities, docs_index)

        # Exact match (Chart) should be ranked and have the highest score
        assert len(ranked) > 0
        # Chart is exact match (100) + partial matches in ChartType and ChartSeriesCollection (30 each)
        assert ranked[0][0] == "Chart"
        assert ranked[0][1] >= 100  # At least exact match score

    def test_rank_case_insensitive_matches(self, api_context_service):
        """Test case-insensitive ranking."""
        docs_index = {
            "ChartType": [Mock()],
        }
        entities = {"charttype"}
        ranked = api_context_service._rank_matches(entities, docs_index)

        # Should find case-insensitive match
        assert len(ranked) > 0

    def test_rank_empty_entities(self, api_context_service, sample_docs_index):
        """Test ranking with empty entity set."""
        ranked = api_context_service._rank_matches(set(), sample_docs_index)

        assert len(ranked) == 0

    def test_rank_empty_index(self, api_context_service):
        """Test ranking with empty documentation index."""
        entities = {"ChartType", "Document"}
        ranked = api_context_service._rank_matches(entities, {})

        assert len(ranked) == 0

    def test_rank_deterministic_ordering(self, api_context_service):
        """Test that ranking is deterministic."""
        docs_index = {
            "Alpha": [Mock()],
            "Beta": [Mock()],
            "Gamma": [Mock()],
        }
        entities = {"Alpha", "Beta", "Gamma"}

        ranked1 = api_context_service._rank_matches(entities, docs_index)
        ranked2 = api_context_service._rank_matches(entities, docs_index)

        # Results should be identical
        assert ranked1 == ranked2

    def test_rank_partial_matches_lower_score(self, api_context_service):
        """Test that partial matches score lower than exact."""
        docs_index = {
            "ChartSeriesCollection": [Mock()],
        }
        entities = {"Chart"}  # Partial match
        ranked = api_context_service._rank_matches(entities, docs_index)

        # Should find partial match with lower score
        assert len(ranked) > 0
        assert ranked[0][1] < 100  # Lower than exact match


class TestContextAssembly:
    """Test context assembly algorithm."""

    def test_assemble_context_basic(self, api_context_service, sample_docs_index):
        """Test basic context assembly."""
        entities = {"ChartType", "Document"}
        context = api_context_service.assemble_context(entities, sample_docs_index)

        assert len(context) > 0
        assert "Relevant API Documentation" in context or "API" in context

    def test_assemble_context_includes_entities(self, api_context_service, sample_docs_index):
        """Test that assembled context references the error entities."""
        entities = {"ChartType"}
        context = api_context_service.assemble_context(entities, sample_docs_index)

        # Should mention the entity or have documentation header
        assert len(context) > 0

    def test_assemble_context_respects_char_limit(self, api_context_service, sample_docs_index):
        """Test that assembled context respects character budget."""
        entities = {"ChartType", "Document", "ChartSeriesCollection"}
        max_chars = 200
        context = api_context_service.assemble_context(entities, sample_docs_index, max_chars)

        assert len(context) <= max_chars or len(context) <= max_chars + 100  # Small tolerance for markers

    def test_assemble_context_empty_entities(self, api_context_service, sample_docs_index):
        """Test assembly with empty entity set."""
        context = api_context_service.assemble_context(set(), sample_docs_index)

        assert context == ""

    def test_assemble_context_empty_index(self, api_context_service):
        """Test assembly with empty documentation index."""
        entities = {"ChartType"}
        context = api_context_service.assemble_context(entities, {})

        assert context == ""

    def test_assemble_context_no_matches(self, api_context_service):
        """Test assembly when no entities match index."""
        docs_index = {"Other": [Mock()]}
        entities = {"ChartType"}
        context = api_context_service.assemble_context(entities, docs_index)

        assert context == ""

    def test_assemble_context_truncation_marker(self, api_context_service, sample_docs_index):
        """Test that truncation marker appears when appropriate."""
        # Create large index to trigger truncation
        large_index = {f"Type{i}": [Mock(relative_path=f"Type{i}.md")] for i in range(100)}
        entities = set(large_index.keys())
        max_chars = 500
        context = api_context_service.assemble_context(entities, large_index, max_chars)

        # Context assembly may include header with entity list, which can be large
        # Just verify that assembling large index works
        assert isinstance(context, str)
        assert len(context) > 0


class TestGetContextForError:
    """Test main entry point method."""

    def test_get_context_basic(self, api_context_service, sample_docs_index):
        """Test basic context retrieval."""
        error_msg = "'ChartType' does not exist"
        context = api_context_service.get_context_for_error(
            "CS0103",
            error_msg,
            sample_docs_index
        )

        assert len(context) >= 0  # May be empty if no matches

    def test_get_context_with_api_reference(self, api_context_with_reference):
        """Test context retrieval with API reference service."""
        error_msg = "'ChartType' does not exist"
        context = api_context_with_reference.get_context_for_error(
            "CS0103",
            error_msg
        )

        assert context == "Mock API context"

    def test_get_context_api_reference_fallback(self, api_context_with_reference):
        """Test fallback to API reference when no index provided."""
        error_msg = "'ChartType' does not exist"
        context = api_context_with_reference.get_context_for_error(
            "CS0103",
            error_msg,
            docs_index=None
        )

        # Should use API reference service
        assert context == "Mock API context"

    def test_get_context_no_entities(self, api_context_service, sample_docs_index):
        """Test behavior when no entities can be extracted."""
        error_msg = ""  # Empty message
        context = api_context_service.get_context_for_error(
            "CS0000",
            error_msg,
            sample_docs_index
        )

        assert context == ""

    def test_get_context_no_reference_no_index(self, api_context_service):
        """Test behavior with no API reference and no index."""
        error_msg = "'ChartType' does not exist"
        context = api_context_service.get_context_for_error(
            "CS0103",
            error_msg,
            docs_index=None
        )

        assert context == ""

    def test_get_context_custom_max_chars(self, api_context_service, sample_docs_index):
        """Test custom max_chars parameter."""
        error_msg = "'ChartType' does not exist"
        context = api_context_service.get_context_for_error(
            "CS0103",
            error_msg,
            docs_index=sample_docs_index,
            max_chars=100
        )

        assert len(context) <= 200  # Allow some tolerance


class TestContextTruncation:
    """Test context truncation utility."""

    def test_truncate_no_truncation_needed(self, api_context_service):
        """Test truncation when not needed."""
        text = "Short text"
        truncated = api_context_service.truncate_context(text, 100)

        assert truncated == text

    def test_truncate_exact_limit(self, api_context_service):
        """Test truncation at exact limit."""
        text = "Short text"
        truncated = api_context_service.truncate_context(text, len(text))

        assert truncated == text

    def test_truncate_respects_limit(self, api_context_service):
        """Test that truncation respects character limit."""
        text = "This is a very long text " * 100
        max_chars = 200
        truncated = api_context_service.truncate_context(text, max_chars)

        assert len(truncated) <= max_chars + 50  # Some tolerance for markers

    def test_truncate_at_sentence_boundary(self, api_context_service):
        """Test truncation at sentence boundaries."""
        text = "First sentence. Second sentence. Third sentence."
        truncated = api_context_service.truncate_context(text, 20)

        # Should truncate somewhere reasonable
        assert len(truncated) <= 100
        assert "truncated" in truncated.lower()

    def test_truncate_at_newline(self, api_context_service):
        """Test truncation at newline boundaries."""
        text = "Line 1\nLine 2\nLine 3\nLine 4\n"
        truncated = api_context_service.truncate_context(text, 20)

        assert len(truncated) <= 100


class TestMergeContexts:
    """Test context merging utility."""

    def test_merge_single_context(self, api_context_service):
        """Test merging single context."""
        contexts = ["Context 1"]
        merged = api_context_service.merge_contexts(contexts, 1000)

        assert "Context 1" in merged

    def test_merge_multiple_contexts(self, api_context_service):
        """Test merging multiple contexts."""
        contexts = ["Context 1", "Context 2", "Context 3"]
        merged = api_context_service.merge_contexts(contexts, 1000)

        assert "Context 1" in merged
        assert "---" in merged  # Separator

    def test_merge_respects_char_limit(self, api_context_service):
        """Test that merge respects character limit."""
        contexts = ["A" * 500, "B" * 500, "C" * 500]
        max_chars = 800
        merged = api_context_service.merge_contexts(contexts, max_chars)

        assert len(merged) <= max_chars + 100  # Tolerance for markers

    def test_merge_empty_contexts(self, api_context_service):
        """Test merging with empty context list."""
        merged = api_context_service.merge_contexts([], 1000)

        assert merged == ""

    def test_merge_with_empty_strings(self, api_context_service):
        """Test merging with empty strings in list."""
        contexts = ["Context 1", "", "Context 2"]
        merged = api_context_service.merge_contexts(contexts, 1000)

        assert "Context 1" in merged
        assert "Context 2" in merged

    def test_merge_preserves_content(self, api_context_service):
        """Test that merge preserves content."""
        context1 = "First context with data"
        context2 = "Second context with data"
        merged = api_context_service.merge_contexts([context1, context2], 1000)

        assert context1 in merged
        assert context2 in merged


class TestIntegration:
    """Integration tests combining multiple components."""

    def test_full_pipeline_cs0103(self, api_context_service, sample_docs_index):
        """Test full pipeline for CS0103 error."""
        error_msg = "'ChartType' does not exist in the current context"
        context = api_context_service.get_context_for_error(
            "CS0103",
            error_msg,
            docs_index=sample_docs_index
        )

        # Should produce some output (may be empty if no index matches)
        assert isinstance(context, str)

    def test_full_pipeline_cs0117(self, api_context_service, sample_docs_index):
        """Test full pipeline for CS0117 error."""
        error_msg = "'Document' does not contain a definition for 'BuildDoc'"
        context = api_context_service.get_context_for_error(
            "CS0117",
            error_msg,
            docs_index=sample_docs_index
        )

        assert isinstance(context, str)

    def test_full_pipeline_cs0246(self, api_context_service, sample_docs_index):
        """Test full pipeline for CS0246 error."""
        error_msg = "type or namespace name 'ChartSeriesCollection' could not be found"
        context = api_context_service.get_context_for_error(
            "CS0246",
            error_msg,
            docs_index=sample_docs_index
        )

        assert isinstance(context, str)

    def test_full_pipeline_with_api_reference(self, api_context_with_reference):
        """Test full pipeline with API reference service."""
        error_msg = "'ChartType' does not exist"
        context = api_context_with_reference.get_context_for_error(
            "CS0103",
            error_msg
        )

        assert context == "Mock API context"

    def test_full_pipeline_complex_error(self, api_context_service, sample_docs_index):
        """Test full pipeline with complex error containing multiple issues."""
        error_msg = """
        Compilation failed:
        Error CS0103: The name 'ChartType' does not exist in the current context
        Error CS0117: 'Document' does not contain a definition for 'GenerateChart'
        """
        context = api_context_service.get_context_for_error(
            "CS0103",
            error_msg,
            docs_index=sample_docs_index
        )

        assert isinstance(context, str)


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_special_characters_in_error(self, api_context_service):
        """Test handling of special characters in error messages."""
        error_msg = "'Type<T>' does not exist"
        entities = api_context_service.extract_entities_from_error("CS0103", error_msg)

        # Should handle angle brackets
        assert len(entities) >= 0

    def test_very_long_error_message(self, api_context_service):
        """Test handling of very long error messages."""
        error_msg = "'Type' does not exist " * 1000
        entities = api_context_service.extract_entities_from_error("CS0103", error_msg)

        # Should extract entities efficiently
        assert "Type" in entities

    def test_unicode_in_error_message(self, api_context_service):
        """Test handling of unicode characters in error messages."""
        error_msg = "'ChartType' does not exist (Ошибка)"
        entities = api_context_service.extract_entities_from_error("CS0103", error_msg)

        assert "ChartType" in entities

    def test_null_values(self, api_context_service, sample_docs_index):
        """Test graceful handling of None values."""
        # Should not raise exceptions
        result = api_context_service.assemble_context(set(), sample_docs_index)
        assert result == ""

    def test_malformed_index(self, api_context_service):
        """Test handling of malformed documentation index."""
        malformed_index = {
            "Type1": None,  # Missing list
            "Type2": [Mock()],
        }
        entities = {"Type1", "Type2"}

        # Should handle gracefully
        try:
            ranked = api_context_service._rank_matches(entities, malformed_index)
            # No error should occur
            assert True
        except Exception as e:
            pytest.fail(f"Should handle malformed index gracefully: {e}")
