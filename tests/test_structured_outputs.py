"""
Tests for LLM structured outputs with Pydantic contracts.

Validates:
- ReviewResponse schema compliance
- CodeFixResponse with prose rejection
- Consensus review logic
"""

import pytest
from pydantic import ValidationError
from unittest.mock import Mock, patch, MagicMock

from src.services.llm_contracts import (
    ReviewResponse, ReviewIssue, CodeFixResponse,
    IssueType, Severity, ErrorAnalysis, CompilationHint
)


class TestReviewResponseContract:
    """Tests for ReviewResponse Pydantic model."""

    def test_valid_approved_response(self):
        """Approved response with no issues should be valid."""
        response = ReviewResponse(approved=True, issues=[])
        assert response.approved is True
        assert len(response.issues) == 0

    def test_valid_rejected_response(self):
        """Rejected response with issues should be valid."""
        response = ReviewResponse(
            approved=False,
            issues=[
                ReviewIssue(
                    snippet_index=0,
                    issue_type=IssueType.SYNTAX_ERROR,
                    description="Missing semicolon at end of line",
                    severity=Severity.ERROR,
                )
            ]
        )
        assert response.approved is False
        assert len(response.issues) == 1
        assert response.issues[0].issue_type == IssueType.SYNTAX_ERROR

    def test_invalid_snippet_index_rejected(self):
        """Negative snippet index should fail validation."""
        with pytest.raises(ValidationError):
            ReviewResponse(
                approved=False,
                issues=[
                    ReviewIssue(
                        snippet_index=-1,  # Invalid: must be >= 0
                        issue_type=IssueType.SYNTAX_ERROR,
                        description="Test issue description",
                        severity=Severity.ERROR,
                    )
                ]
            )

    def test_short_description_rejected(self):
        """Description under 10 chars should fail validation."""
        with pytest.raises(ValidationError):
            ReviewResponse(
                approved=False,
                issues=[
                    ReviewIssue(
                        snippet_index=0,
                        issue_type=IssueType.SYNTAX_ERROR,
                        description="Short",  # Too short
                        severity=Severity.ERROR,
                    )
                ]
            )

    def test_optional_suggestion(self):
        """Suggestion field should be optional."""
        issue = ReviewIssue(
            snippet_index=0,
            issue_type=IssueType.API_MISMATCH,
            description="API usage doesn't match the documented signature",
            severity=Severity.WARNING,
            suggestion=None,
        )
        assert issue.suggestion is None

        issue_with_suggestion = ReviewIssue(
            snippet_index=0,
            issue_type=IssueType.API_MISMATCH,
            description="API usage doesn't match the documented signature",
            severity=Severity.WARNING,
            suggestion="Use the correct method overload",
        )
        assert issue_with_suggestion.suggestion == "Use the correct method overload"

    def test_all_issue_types(self):
        """All IssueType enum values should be valid."""
        for issue_type in IssueType:
            issue = ReviewIssue(
                snippet_index=0,
                issue_type=issue_type,
                description="Test description for this issue type",
                severity=Severity.INFO,
            )
            assert issue.issue_type == issue_type

    def test_all_severity_levels(self):
        """All Severity enum values should be valid."""
        for severity in Severity:
            issue = ReviewIssue(
                snippet_index=0,
                issue_type=IssueType.OTHER,
                description="Test description for this severity level",
                severity=severity,
            )
            assert issue.severity == severity


class TestCodeFixContract:
    """Tests for CodeFixResponse Pydantic model with prose rejection."""

    def test_valid_code_response(self):
        """Valid C# code should pass validation."""
        response = CodeFixResponse(
            fixed_code="using System;\n\nclass Program { static void Main() { } }",
            changes_made=["Added using statement", "Added Main method"]
        )
        assert "using System" in response.fixed_code
        assert len(response.changes_made) == 2

    def test_prose_starting_with_I_rejected(self):
        """Response starting with 'I ' should be rejected (either as prose or lacking code indicators)."""
        with pytest.raises(ValidationError):
            CodeFixResponse(
                fixed_code="I cannot fix this code because it has too many issues.",
                changes_made=[]
            )
        # ValidationError is raised - either for prose pattern or lack of code indicators

    def test_prose_starting_with_sorry_rejected(self):
        """Response starting with 'Sorry' should be rejected (either as prose or lacking code indicators)."""
        with pytest.raises(ValidationError):
            CodeFixResponse(
                fixed_code="Sorry, I'm unable to provide a fix for this code.",
                changes_made=[]
            )
        # ValidationError is raised - either for prose pattern or lack of code indicators

    def test_prose_starting_with_unfortunately_rejected(self):
        """Response starting with 'Unfortunately' should be rejected (either as prose or lacking code indicators)."""
        with pytest.raises(ValidationError):
            CodeFixResponse(
                fixed_code="Unfortunately, the code cannot be fixed without more context.",
                changes_made=[]
            )
        # ValidationError is raised - either for prose pattern or lack of code indicators

    def test_prose_with_code_indicators_rejected(self):
        """Prose that happens to contain code indicators should still be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            CodeFixResponse(
                fixed_code="I apologize, but the 'using System;' and 'class' keywords are not enough to make this valid code.",
                changes_made=[]
            )
        # Should be rejected for starting with prose pattern
        assert "prose" in str(exc_info.value).lower()

    def test_empty_code_rejected(self):
        """Empty code should fail min_length validation."""
        with pytest.raises(ValidationError):
            CodeFixResponse(fixed_code="", changes_made=[])

    def test_too_short_code_rejected(self):
        """Code under 10 chars should fail min_length validation."""
        with pytest.raises(ValidationError):
            CodeFixResponse(fixed_code="x = 1;", changes_made=[])

    def test_insufficient_code_indicators_rejected(self):
        """Code with fewer than 2 indicators should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            CodeFixResponse(
                fixed_code="some random text without code indicators",
                changes_made=[]
            )
        assert "code" in str(exc_info.value).lower()

    def test_minimal_valid_code(self):
        """Code with minimal indicators should pass."""
        response = CodeFixResponse(
            fixed_code="class Test { }",
            changes_made=["Created minimal class"]
        )
        assert response.fixed_code == "class Test { }"

    def test_full_csharp_example(self):
        """Complete C# example should pass validation."""
        code = '''using System;
using System.IO;

public class FileHandler
{
    private string _path;

    public void Process()
    {
        var content = File.ReadAllText(_path);
        Console.WriteLine(content);
    }
}'''
        response = CodeFixResponse(
            fixed_code=code,
            changes_made=[
                "Added System.IO using",
                "Created FileHandler class",
                "Added Process method"
            ]
        )
        assert "using System" in response.fixed_code
        assert len(response.changes_made) == 3


class TestErrorAnalysisContract:
    """Tests for ErrorAnalysis Pydantic model."""

    def test_valid_error_analysis(self):
        """Valid error analysis should pass."""
        analysis = ErrorAnalysis(
            primary_error="CS0246: The type 'ZipFile' could not be found",
            error_category="missing_type",
            suggested_fixes=[
                CompilationHint(
                    hint_type="add_using",
                    detail="Add: using System.IO.Compression;"
                )
            ]
        )
        assert "CS0246" in analysis.primary_error
        assert analysis.error_category == "missing_type"
        assert len(analysis.suggested_fixes) == 1

    def test_empty_suggested_fixes(self):
        """Empty suggested_fixes list should be valid."""
        analysis = ErrorAnalysis(
            primary_error="Unknown error",
            error_category="unknown",
            suggested_fixes=[]
        )
        assert len(analysis.suggested_fixes) == 0


class TestConsensusReviewLogic:
    """Tests for consensus review behavior in orchestrator."""

    @pytest.fixture
    def mock_orchestrator(self):
        """Create a mock orchestrator with consensus review method."""
        from src.pipeline.orchestrator import PipelineOrchestrator

        with patch.object(PipelineOrchestrator, '__init__', lambda x: None):
            orchestrator = PipelineOrchestrator()
            # Mock the internal _llm_service attribute (not the property)
            orchestrator._llm_service = Mock()
            return orchestrator

    def test_consensus_both_approve(self, mock_orchestrator):
        """Both reviews approving should result in high confidence approval."""
        mock_orchestrator._llm_service.review_markdown_structured.side_effect = [
            {'approved': True, 'issues': [], 'raw_response': '{}'},
            {'approved': True, 'issues': [], 'raw_response': '{}'},
        ]

        result = mock_orchestrator._consensus_review("content", [])

        assert result['approved'] is True
        assert result['confidence'] == 'high'
        assert len(result['issues']) == 0
        assert mock_orchestrator._llm_service.review_markdown_structured.call_count == 2

    def test_consensus_both_reject(self, mock_orchestrator):
        """Both reviews rejecting should result in high confidence rejection."""
        issue1 = {'description': 'Issue 1', 'example_id': 'ex1'}
        issue2 = {'description': 'Issue 2', 'example_id': 'ex2'}

        mock_orchestrator._llm_service.review_markdown_structured.side_effect = [
            {'approved': False, 'issues': [issue1], 'raw_response': '{}'},
            {'approved': False, 'issues': [issue2], 'raw_response': '{}'},
        ]

        result = mock_orchestrator._consensus_review("content", [])

        assert result['approved'] is False
        assert result['confidence'] == 'high'
        # Should have both issues (deduplicated)
        assert len(result['issues']) == 2

    def test_consensus_split_decision_tiebreaker_approves(self, mock_orchestrator):
        """Split decision with tiebreaker approving should result in medium confidence approval."""
        mock_orchestrator._llm_service.review_markdown_structured.side_effect = [
            {'approved': True, 'issues': [], 'raw_response': '{}'},
            {'approved': False, 'issues': [{'description': 'Minor issue'}], 'raw_response': '{}'},
            {'approved': True, 'issues': [], 'raw_response': '{}'},  # Tiebreaker
        ]

        result = mock_orchestrator._consensus_review("content", [])

        assert result['approved'] is True
        assert result['confidence'] == 'medium'
        assert mock_orchestrator._llm_service.review_markdown_structured.call_count == 3

    def test_consensus_split_decision_tiebreaker_rejects(self, mock_orchestrator):
        """Split decision with tiebreaker rejecting should result in medium confidence rejection."""
        mock_orchestrator._llm_service.review_markdown_structured.side_effect = [
            {'approved': False, 'issues': [{'description': 'Issue found'}], 'raw_response': '{}'},
            {'approved': True, 'issues': [], 'raw_response': '{}'},
            {'approved': False, 'issues': [{'description': 'Issue confirmed'}], 'raw_response': '{}'},
        ]

        result = mock_orchestrator._consensus_review("content", [])

        assert result['approved'] is False
        assert result['confidence'] == 'medium'
        assert mock_orchestrator._llm_service.review_markdown_structured.call_count == 3

    def test_consensus_deduplicates_issues(self, mock_orchestrator):
        """Same issue from multiple reviews should be deduplicated."""
        same_issue = {'description': 'Duplicate issue', 'example_id': 'ex1'}

        mock_orchestrator._llm_service.review_markdown_structured.side_effect = [
            {'approved': False, 'issues': [same_issue], 'raw_response': '{}'},
            {'approved': False, 'issues': [same_issue], 'raw_response': '{}'},
        ]

        result = mock_orchestrator._consensus_review("content", [])

        assert result['approved'] is False
        # Should have only 1 issue after deduplication
        assert len(result['issues']) == 1


class TestInstructorIntegration:
    """Tests for Instructor library integration."""

    def test_instructor_availability_check(self):
        """Instructor availability should be properly detected."""
        from src.services import llm_service
        # Just verify the flag exists and is boolean
        assert hasattr(llm_service, 'INSTRUCTOR_AVAILABLE')
        assert isinstance(llm_service.INSTRUCTOR_AVAILABLE, bool)

    def test_contracts_importable(self):
        """All contracts should be importable."""
        from src.services.llm_contracts import (
            ReviewResponse, ReviewIssue, CodeFixResponse,
            IssueType, Severity, ErrorAnalysis, CompilationHint
        )
        # Verify all are available
        assert ReviewResponse is not None
        assert ReviewIssue is not None
        assert CodeFixResponse is not None
        assert IssueType is not None
        assert Severity is not None
        assert ErrorAnalysis is not None
        assert CompilationHint is not None
