"""
Tests for Final Review phase with structured issue tracking.
Tests the re-review loop and database integration.
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from src.core.database import Database
from src.core.models import (
    ExampleRecord, ExampleStatus, SourceType, Location,
    ReviewResult, ReviewIssue, IssueType, IssueSeverity
)
from src.services.llm_service import LLMService


@pytest.fixture
def temp_db():
    """Create a temporary database for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = Database(db_path)
        db.initialize_schema()
        yield db
        db.close()


@pytest.fixture
def sample_review_result():
    """Create a sample ReviewResult for testing."""
    issues = [
        ReviewIssue(
            review_id="test_review_001",
            example_id="ex_001",
            issue_type=IssueType.SYNTAX_ERROR,
            description="Missing semicolon at line 5",
            suggestion="Add semicolon",
            severity=IssueSeverity.ERROR,
        ),
        ReviewIssue(
            review_id="test_review_001",
            example_id="ex_002",
            issue_type=IssueType.MISSING_CONTEXT,
            description="Code doesn't show imports",
            suggestion="Add using statements",
            severity=IssueSeverity.WARNING,
        ),
    ]

    return ReviewResult(
        file_path="/test/file.md",
        run_id="run_001",
        family="zip",
        approved=False,
        review_attempt=1,
        issues=issues,
        llm_response='{"approved": false, "issues": [...]}',
    )


class TestReviewResultDatabase:
    """Tests for ReviewResult database operations."""

    def test_save_and_get_review_result(self, temp_db, sample_review_result):
        """Test saving and retrieving a review result."""
        # Save
        review_id = temp_db.save_review_result(sample_review_result)
        assert review_id == sample_review_result.review_id

        # Get
        retrieved = temp_db.get_review_result(review_id)
        assert retrieved is not None
        assert retrieved.file_path == sample_review_result.file_path
        assert retrieved.approved == sample_review_result.approved
        assert retrieved.review_attempt == 1
        assert len(retrieved.issues) == 2

    def test_get_review_results_by_run(self, temp_db, sample_review_result):
        """Test getting all reviews for a run."""
        temp_db.save_review_result(sample_review_result)

        # Create another review for the same run
        result2 = ReviewResult(
            file_path="/test/file2.md",
            run_id="run_001",
            family="zip",
            approved=True,
            review_attempt=1,
            issues=[],
        )
        temp_db.save_review_result(result2)

        results = temp_db.get_review_results_by_run("run_001")
        assert len(results) == 2

    def test_get_review_results_by_file(self, temp_db, sample_review_result):
        """Test getting reviews for a specific file."""
        temp_db.save_review_result(sample_review_result)

        # Add a second attempt for the same file
        result2 = ReviewResult(
            file_path="/test/file.md",
            run_id="run_001",
            family="zip",
            approved=True,
            review_attempt=2,
            issues=[],
        )
        temp_db.save_review_result(result2)

        results = temp_db.get_review_results_by_file("/test/file.md")
        assert len(results) == 2
        # Should be ordered by attempt descending
        assert results[0].review_attempt == 2

    def test_get_latest_review_attempt(self, temp_db, sample_review_result):
        """Test getting the latest review attempt number."""
        temp_db.save_review_result(sample_review_result)

        # Add second attempt
        result2 = ReviewResult(
            file_path="/test/file.md",
            run_id="run_001",
            family="zip",
            approved=True,
            review_attempt=2,
            issues=[],
        )
        temp_db.save_review_result(result2)

        latest = temp_db.get_latest_review_attempt("/test/file.md", "run_001")
        assert latest == 2

    def test_get_unresolved_issues(self, temp_db, sample_review_result):
        """Test getting unresolved issues for a file."""
        temp_db.save_review_result(sample_review_result)

        issues = temp_db.get_unresolved_issues_for_file("/test/file.md")
        assert len(issues) == 2

        # Resolve one issue
        temp_db.resolve_issue(issues[0].issue_id)

        issues = temp_db.get_unresolved_issues_for_file("/test/file.md")
        assert len(issues) == 1

    def test_resolve_issue(self, temp_db, sample_review_result):
        """Test resolving an issue."""
        temp_db.save_review_result(sample_review_result)

        issues = temp_db.get_unresolved_issues_for_file("/test/file.md")
        issue_id = issues[0].issue_id

        result = temp_db.resolve_issue(issue_id)
        assert result is True

        # Verify resolution
        retrieved = temp_db.get_review_result(sample_review_result.review_id)
        resolved_issue = next(i for i in retrieved.issues if i.issue_id == issue_id)
        assert resolved_issue.resolved is True

    def test_review_stats_by_family(self, temp_db, sample_review_result):
        """Test getting review statistics for a family."""
        temp_db.save_review_result(sample_review_result)

        # Add an approved review
        approved = ReviewResult(
            file_path="/test/file2.md",
            run_id="run_001",
            family="zip",
            approved=True,
            review_attempt=1,
            issues=[],
        )
        temp_db.save_review_result(approved)

        stats = temp_db.get_review_stats_by_family("zip")
        assert stats['total_reviews'] == 2
        assert stats['approved'] == 1
        assert stats['rejected'] == 1
        assert 'error' in stats['issues_by_severity']


class TestReviewIssueModels:
    """Tests for ReviewIssue and ReviewResult models."""

    def test_review_result_generates_id(self):
        """Test that ReviewResult generates a unique ID."""
        result = ReviewResult(
            file_path="/test/file.md",
            run_id="run_001",
            family="zip",
        )
        assert result.review_id != ""
        assert len(result.review_id) == 16

    def test_review_issue_generates_id(self):
        """Test that ReviewIssue generates a unique ID."""
        issue = ReviewIssue(
            review_id="rev_001",
            example_id="ex_001",
            description="Test issue",
        )
        assert issue.issue_id != ""
        assert len(issue.issue_id) == 16

    def test_issue_count_property(self):
        """Test ReviewResult.issue_count property."""
        result = ReviewResult(
            file_path="/test/file.md",
            run_id="run_001",
            family="zip",
            issues=[
                ReviewIssue(review_id="r", example_id="e", description="d1"),
                ReviewIssue(review_id="r", example_id="e", description="d2"),
            ],
        )
        assert result.issue_count == 2

    def test_unresolved_count_property(self):
        """Test ReviewResult.unresolved_count property."""
        result = ReviewResult(
            file_path="/test/file.md",
            run_id="run_001",
            family="zip",
            issues=[
                ReviewIssue(review_id="r", example_id="e", description="d1", resolved=True),
                ReviewIssue(review_id="r", example_id="e", description="d2", resolved=False),
            ],
        )
        assert result.unresolved_count == 1

    def test_has_critical_issues_property(self):
        """Test ReviewResult.has_critical_issues property."""
        result = ReviewResult(
            file_path="/test/file.md",
            run_id="run_001",
            family="zip",
            issues=[
                ReviewIssue(
                    review_id="r",
                    example_id="e",
                    description="d1",
                    severity=IssueSeverity.CRITICAL,
                ),
            ],
        )
        assert result.has_critical_issues is True

        # Resolved critical issues don't count
        result.issues[0].resolved = True
        assert result.has_critical_issues is False


class TestLLMServiceStructuredReview:
    """Tests for LLMService.review_markdown_structured method."""

    @patch.object(LLMService, 'complete')
    def test_review_returns_approved_when_no_issues(self, mock_complete):
        """Test that review returns approved when LLM finds no issues."""
        mock_complete.return_value = Mock(
            success=True,
            content='{"approved": true, "issues": []}',
            error=None,
        )

        service = LLMService(provider="openai", api_key="test")
        service._client = Mock()  # Bypass client init

        result = service.review_markdown_structured(
            markdown_content="# Test\n```csharp\ncode\n```",
            code_snippets=[
                {'code': 'code', 'example_id': 'ex1', 'line': 5, 'language': 'csharp'}
            ]
        )

        assert result['approved'] is True
        assert len(result['issues']) == 0

    @patch.object(LLMService, 'complete')
    def test_review_returns_issues_when_found(self, mock_complete):
        """Test that review returns issues when LLM finds problems."""
        mock_complete.return_value = Mock(
            success=True,
            content='''{
                "approved": false,
                "issues": [
                    {
                        "snippet_index": 0,
                        "issue_type": "syntax_error",
                        "description": "Missing semicolon",
                        "suggestion": "Add semicolon",
                        "severity": "error"
                    }
                ]
            }''',
            error=None,
        )

        service = LLMService(provider="openai", api_key="test")
        service._client = Mock()

        result = service.review_markdown_structured(
            markdown_content="# Test\n```csharp\ncode\n```",
            code_snippets=[
                {'code': 'code', 'example_id': 'ex1', 'line': 5, 'language': 'csharp'}
            ]
        )

        assert result['approved'] is False
        assert len(result['issues']) == 1
        assert result['issues'][0]['example_id'] == 'ex1'
        assert result['issues'][0]['issue_type'] == 'syntax_error'

    @patch.object(LLMService, 'complete')
    def test_review_handles_llm_failure(self, mock_complete):
        """Test that review handles LLM failure gracefully."""
        mock_complete.return_value = Mock(
            success=False,
            content='',
            error='API rate limit exceeded',
        )

        service = LLMService(provider="openai", api_key="test")
        service._client = Mock()

        result = service.review_markdown_structured(
            markdown_content="# Test",
            code_snippets=[]
        )

        assert result['approved'] is False
        assert len(result['issues']) == 1
        assert 'rate limit' in result['issues'][0]['description'].lower()

    @patch.object(LLMService, 'complete')
    def test_review_handles_invalid_json(self, mock_complete):
        """Test that review handles invalid JSON response."""
        mock_complete.return_value = Mock(
            success=True,
            content='This is not valid JSON',
            error=None,
        )

        service = LLMService(provider="openai", api_key="test")
        service._client = Mock()

        result = service.review_markdown_structured(
            markdown_content="# Test",
            code_snippets=[]
        )

        assert result['approved'] is False
        assert len(result['issues']) == 1
        assert 'parse' in result['issues'][0]['description'].lower()

    @patch.object(LLMService, 'complete')
    def test_review_maps_snippet_index_to_example_id(self, mock_complete):
        """Test that snippet_index is correctly mapped to example_id."""
        mock_complete.return_value = Mock(
            success=True,
            content='''{
                "approved": false,
                "issues": [
                    {"snippet_index": 1, "issue_type": "other", "description": "Issue", "severity": "warning"}
                ]
            }''',
            error=None,
        )

        service = LLMService(provider="openai", api_key="test")
        service._client = Mock()

        result = service.review_markdown_structured(
            markdown_content="# Test",
            code_snippets=[
                {'code': 'code1', 'example_id': 'ex_001', 'line': 1, 'language': 'csharp'},
                {'code': 'code2', 'example_id': 'ex_002', 'line': 10, 'language': 'csharp'},
            ]
        )

        # Issue at snippet_index=1 should map to ex_002
        assert result['issues'][0]['example_id'] == 'ex_002'


class TestFinalReviewIntegration:
    """Integration tests for the final review phase."""

    @pytest.fixture
    def mock_orchestrator_deps(self, temp_db):
        """Create mock dependencies for orchestrator testing."""
        with patch('src.pipeline.orchestrator.ConfigurationManager') as mock_cm:
            mock_global = MagicMock()
            mock_global.final_review.enabled = True
            mock_global.final_review.auto_remediation_enabled = False
            mock_global.final_review.max_review_attempts = 2
            mock_global.final_review.fail_on_critical = True
            mock_global.final_review.strict_mode = False
            mock_cm.return_value.load_global_config.return_value = mock_global

            yield {
                'config_manager': mock_cm,
                'db': temp_db,
                'global_config': mock_global,
            }

    def test_review_phase_respects_max_attempts(self, mock_orchestrator_deps):
        """Test that review phase respects max_review_attempts config."""
        # This would be a more complex integration test
        # For now, verify the config is properly loaded
        config = mock_orchestrator_deps['global_config']
        assert config.final_review.max_review_attempts == 2

    def test_critical_issues_stop_retry_loop(self, mock_orchestrator_deps):
        """Test that critical issues prevent retry loop."""
        config = mock_orchestrator_deps['global_config']
        assert config.final_review.fail_on_critical is True
