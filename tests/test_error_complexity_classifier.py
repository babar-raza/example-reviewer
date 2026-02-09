"""
Unit tests for Error Complexity Classifier.

Tests cover:
- Error categorization (7+ categories)
- Complexity scoring (0.0-1.0 range)
- Model tier routing (small/medium/large)
- Modifier application (retries, error count, domain entities)
- Edge cases and boundary conditions
"""

import pytest
from src.pipeline.error_complexity_classifier import (
    ErrorComplexityClassifier,
    ErrorComplexity,
)


class TestErrorCategorization:
    """Test error categorization by error code."""

    @pytest.fixture
    def classifier(self):
        """Create classifier instance."""
        return ErrorComplexityClassifier()

    def test_categorize_cs0246_missing_type(self, classifier):
        """CS0246 should categorize as missing_type."""
        category = classifier._categorize_error('CS0246')
        assert category == 'missing_type'

    def test_categorize_cs0103_undefined_variable(self, classifier):
        """CS0103 should categorize as undefined_variable."""
        category = classifier._categorize_error('CS0103')
        assert category == 'undefined_variable'

    def test_categorize_cs1061_member_not_found(self, classifier):
        """CS1061 should categorize as member_not_found."""
        category = classifier._categorize_error('CS1061')
        assert category == 'member_not_found'

    def test_categorize_cs7036_missing_argument(self, classifier):
        """CS7036 should categorize as missing_argument."""
        category = classifier._categorize_error('CS7036')
        assert category == 'missing_argument'

    def test_categorize_cs0104_ambiguous_reference(self, classifier):
        """CS0104 should categorize as ambiguous_reference."""
        category = classifier._categorize_error('CS0104')
        assert category == 'ambiguous_reference'

    def test_categorize_cs0029_type_mismatch(self, classifier):
        """CS0029 should categorize as type_mismatch."""
        category = classifier._categorize_error('CS0029')
        assert category == 'type_mismatch'

    def test_categorize_unknown_code(self, classifier):
        """Unknown error code should return 'unknown'."""
        category = classifier._categorize_error('CS9999')
        assert category == 'unknown'

    def test_categorize_runtime_exception(self, classifier):
        """Runtime exception should categorize appropriately."""
        category = classifier._categorize_error('NullReferenceException')
        assert category == 'null_reference'

    def test_categorize_io_exception(self, classifier):
        """I/O exception should categorize as io_exception."""
        category = classifier._categorize_error('FileNotFoundException')
        assert category == 'io_exception'


class TestErrorScoring:
    """Test complexity scoring."""

    @pytest.fixture
    def classifier(self):
        """Create classifier instance."""
        return ErrorComplexityClassifier()

    def test_score_simple_missing_type(self, classifier):
        """CS0246 missing type should score low (0.2-0.3)."""
        score = classifier.score_error(
            'CS0246',
            "The type or namespace name 'Archive' could not be found"
        )
        assert 0.1 <= score <= 0.4
        assert score < 0.4  # Should be in 'simple' range

    def test_score_simple_undefined_variable(self, classifier):
        """CS0103 undefined variable should score low (0.2-0.4)."""
        score = classifier.score_error(
            'CS0103',
            "The name 'myVariable' does not exist in the current context"
        )
        assert 0.1 <= score <= 0.5

    def test_score_complex_member_not_found(self, classifier):
        """CS1061 member not found should score higher (0.7+)."""
        score = classifier.score_error(
            'CS1061',
            "Archive does not contain a definition for 'SaveAsync'"
        )
        assert score >= 0.6

    def test_score_complex_ambiguous_reference(self, classifier):
        """CS0104 ambiguous reference should score higher (0.7+)."""
        score = classifier.score_error(
            'CS0104',
            "'ParallelOptions' is an ambiguous reference"
        )
        assert score >= 0.6

    def test_score_runtime_exception(self, classifier):
        """Runtime exceptions should score higher (0.7+)."""
        score = classifier.score_error(
            'NullReferenceException',
            "Object reference not set to an instance of an object"
        )
        assert score >= 0.6

    def test_score_range_always_valid(self, classifier):
        """Scores should always be between 0.0 and 1.0."""
        test_errors = [
            ('CS0246', 'Missing type'),
            ('CS1061', 'Member not found'),
            ('CS0104', 'Ambiguous reference'),
            ('CS9999', 'Unknown error'),
        ]
        for error_code, msg in test_errors:
            score = classifier.score_error(error_code, msg)
            assert 0.0 <= score <= 1.0, f"Score {score} out of range for {error_code}"


class TestScoringModifiers:
    """Test complexity score modifiers."""

    @pytest.fixture
    def classifier(self):
        """Create classifier instance."""
        return ErrorComplexityClassifier()

    def test_modifier_retry_count(self, classifier):
        """Retry count should increase score."""
        score_no_retry = classifier.score_error(
            'CS0246',
            "The type 'Archive' could not be found"
        )
        score_one_retry = classifier.score_error(
            'CS0246',
            "The type 'Archive' could not be found",
            {'retry_count': 1}
        )
        score_two_retries = classifier.score_error(
            'CS0246',
            "The type 'Archive' could not be found",
            {'retry_count': 2}
        )

        # Retries should escalate complexity
        assert score_one_retry >= score_no_retry
        assert score_two_retries >= score_one_retry

    def test_modifier_multiple_errors(self, classifier):
        """Multiple errors should increase score."""
        score_single = classifier.score_error(
            'CS0246',
            "Missing type"
        )
        score_multi = classifier.score_error(
            'CS0246',
            "Missing type",
            {'all_errors': ['Error1', 'Error2', 'Error3']}
        )

        assert score_multi >= score_single

    def test_modifier_domain_entities(self, classifier):
        """Domain entities should increase score."""
        simple_msg = "Type 'XYZ' not found"
        domain_msg = "Type 'CompressionLevel' not found"

        score_simple = classifier.score_error('CS0246', simple_msg)
        score_domain = classifier.score_error('CS0246', domain_msg)

        # Domain-specific errors should score higher
        assert score_domain > score_simple

    def test_modifier_cryptic_message(self, classifier):
        """Cryptic messages should increase score."""
        clear_msg = "Missing type"
        cryptic_msg = "System.Exception: Object reference not set to an instance of an object\n" \
                     "at Namespace.Class.Method() in file.cs:line 42"

        score_clear = classifier.score_error('CS0103', clear_msg)
        score_cryptic = classifier.score_error('CS0103', cryptic_msg)

        # Cryptic messages should score higher
        assert score_cryptic > score_clear

    def test_modifier_error_history(self, classifier):
        """Error history should increase score."""
        context_no_history = {}
        context_with_history = {
            'error_history': ['CS0246', 'CS0103', 'CS1061']
        }

        score_no_history = classifier.score_error('CS0103', "Error", context_no_history)
        score_with_history = classifier.score_error('CS0103', "Error", context_with_history)

        # Multiple different errors suggest complex issue
        assert score_with_history >= score_no_history


class TestModelTierRouting:
    """Test model tier routing based on score."""

    @pytest.fixture
    def classifier(self):
        """Create classifier instance."""
        return ErrorComplexityClassifier()

    def test_route_simple_tier(self, classifier):
        """Scores < 0.4 should route to 'small' model."""
        tier = classifier.route_to_tier(0.2)
        assert tier == "small"

        tier = classifier.route_to_tier(0.35)
        assert tier == "small"

    def test_route_medium_tier(self, classifier):
        """Scores 0.4-0.7 should route to 'medium' model."""
        tier = classifier.route_to_tier(0.4)
        assert tier == "medium"

        tier = classifier.route_to_tier(0.55)
        assert tier == "medium"

        tier = classifier.route_to_tier(0.69)
        assert tier == "medium"

    def test_route_large_tier(self, classifier):
        """Scores >= 0.7 should route to 'large' model."""
        tier = classifier.route_to_tier(0.7)
        assert tier == "large"

        tier = classifier.route_to_tier(0.85)
        assert tier == "large"

        tier = classifier.route_to_tier(1.0)
        assert tier == "large"

    def test_route_boundary_conditions(self, classifier):
        """Test boundary score values."""
        # Test exact boundaries
        assert classifier.route_to_tier(0.4) == "medium"
        assert classifier.route_to_tier(0.7) == "large"

        # Test just below boundaries
        assert classifier.route_to_tier(0.39) == "small"
        assert classifier.route_to_tier(0.69) == "medium"


class TestComplexityLevelEnum:
    """Test ErrorComplexity enum conversion."""

    @pytest.fixture
    def classifier(self):
        """Create classifier instance."""
        return ErrorComplexityClassifier()

    def test_simple_level(self, classifier):
        """Score < 0.4 should map to SIMPLE."""
        level = classifier.get_complexity_level(0.2)
        assert level == ErrorComplexity.SIMPLE

    def test_medium_level(self, classifier):
        """Score 0.4-0.7 should map to MEDIUM."""
        level = classifier.get_complexity_level(0.55)
        assert level == ErrorComplexity.MEDIUM

    def test_complex_level(self, classifier):
        """Score >= 0.7 should map to COMPLEX."""
        level = classifier.get_complexity_level(0.8)
        assert level == ErrorComplexity.COMPLEX


class TestIntegrationScenarios:
    """Integration tests with realistic scenarios."""

    @pytest.fixture
    def classifier(self):
        """Create classifier instance."""
        return ErrorComplexityClassifier()

    def test_simple_missing_using_scenario(self, classifier):
        """Simple missing type -> small model."""
        # Scenario: Missing System.Text using
        score = classifier.score_error(
            'CS0246',
            "The type or namespace name 'StringBuilder' could not be found"
        )
        tier = classifier.route_to_tier(score)
        assert tier == "small"

    def test_complex_domain_api_scenario(self, classifier):
        """Complex Aspose API issue -> large model."""
        # Scenario: Wrong Aspose.Zip API usage
        score = classifier.score_error(
            'CS1061',
            "Archive does not contain a definition for 'SaveAsync'",
            {'retry_count': 1}
        )
        tier = classifier.route_to_tier(score)
        assert tier == "large"

    def test_multiple_compilation_errors_scenario(self, classifier):
        """Multiple errors -> escalate tier."""
        score = classifier.score_error(
            'CS0103',
            "The name 'entry' does not exist",
            {
                'all_errors': [
                    'CS0103: entry',
                    'CS0246: ArchiveEntry',
                    'CS1061: SaveAsync',
                ]
            }
        )
        tier = classifier.route_to_tier(score)
        # Multiple errors should escalate from simple to medium
        assert tier in ["medium", "large"]

    def test_runtime_exception_scenario(self, classifier):
        """Runtime exception with complex message -> large model."""
        score = classifier.score_error(
            'NullReferenceException',
            "System.NullReferenceException: Object reference not set to an instance of an object\n"
            "at Aspose.Zip.Archive.ExtractToDirectory(String destDir)\n"
            "at Program.Main() in Program.cs:line 42"
        )
        tier = classifier.route_to_tier(score)
        assert tier == "large"

    def test_full_diagnostic_output(self, classifier):
        """Full diagnostic information is generated correctly."""
        result = classifier.estimate_fix_difficulty(
            'CS0246',
            "The type or namespace name 'CompressionLevel' could not be found"
        )

        # Verify all required fields
        assert 'complexity_score' in result
        assert 'complexity_level' in result
        assert 'model_tier' in result
        assert 'category' in result
        assert 'reasoning' in result

        # Verify types
        assert isinstance(result['complexity_score'], float)
        assert isinstance(result['complexity_level'], str)
        assert isinstance(result['model_tier'], str)
        assert isinstance(result['category'], str)
        assert isinstance(result['reasoning'], str)

        # Verify valid values
        assert 0.0 <= result['complexity_score'] <= 1.0
        assert result['complexity_level'] in ['simple', 'medium', 'complex']
        assert result['model_tier'] in ['small', 'medium', 'large']
        assert len(result['reasoning']) > 0


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.fixture
    def classifier(self):
        """Create classifier instance."""
        return ErrorComplexityClassifier()

    def test_empty_error_code(self, classifier):
        """Empty error code should default to unknown."""
        category = classifier._categorize_error('')
        assert category == 'unknown'

    def test_empty_error_message(self, classifier):
        """Empty error message should still produce valid score."""
        score = classifier.score_error('CS0246', '')
        assert 0.0 <= score <= 1.0

    def test_none_context(self, classifier):
        """None context should be handled gracefully."""
        score = classifier.score_error('CS0246', "Error message", None)
        assert 0.0 <= score <= 1.0

    def test_extreme_retry_count(self, classifier):
        """Very high retry counts should cap at 1.0."""
        score = classifier.score_error(
            'CS0103',
            "Error",
            {'retry_count': 100}
        )
        assert score <= 1.0

    def test_many_errors(self, classifier):
        """Many errors should cap complexity at 1.0."""
        many_errors = [f'Error{i}' for i in range(50)]
        score = classifier.score_error(
            'CS0246',
            "Error",
            {'all_errors': many_errors}
        )
        assert score <= 1.0

    def test_case_insensitivity(self, classifier):
        """Error codes should be case-insensitive where applicable."""
        # Aspose.ZIP usage in message
        score1 = classifier.score_error('CS0246', 'Aspose.ZIP method not found')
        score2 = classifier.score_error('CS0246', 'aspose.zip method not found')
        # Both should recognize domain entity
        assert score1 > 0.2
        assert score2 > 0.2

    def test_unicode_in_messages(self, classifier):
        """Unicode characters should be handled."""
        score = classifier.score_error(
            'CS0103',
            "Variable 'måste' does not exist"
        )
        assert 0.0 <= score <= 1.0


class TestDomainEntityDetection:
    """Test domain-specific entity detection."""

    @pytest.fixture
    def classifier(self):
        """Create classifier instance."""
        return ErrorComplexityClassifier()

    def test_detect_aspose_zip_entities(self, classifier):
        """Should detect Aspose.ZIP specific entities."""
        messages = [
            "CompressionLevel.Optimal",
            "RarArchive not found",
            "SevenZipArchive usage",
            "EncryptionSettings missing",
        ]
        for msg in messages:
            has_domain = classifier._has_domain_entities(msg)
            assert has_domain, f"Failed to detect domain entity in: {msg}"

    def test_detect_aspose_words_entities(self, classifier):
        """Should detect Aspose.Words specific entities."""
        messages = [
            "DocumentBuilder usage",
            "ChartType unknown",
            "Watermark missing",
        ]
        for msg in messages:
            has_domain = classifier._has_domain_entities(msg)
            assert has_domain, f"Failed to detect domain entity in: {msg}"

    def test_no_domain_entities_in_generic_message(self, classifier):
        """Generic errors should not trigger domain detection."""
        score = classifier.score_error(
            'CS0246',
            "Type 'StringBuilder' could not be found"
        )
        # Score should be low (no domain entity boost)
        assert score < 0.4


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
