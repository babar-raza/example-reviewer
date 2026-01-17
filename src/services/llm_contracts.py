"""
Pydantic contracts for LLM structured outputs.

This module defines Pydantic models that enforce schema compliance
for all LLM responses, eliminating JSON parsing errors and ensuring
type safety throughout the pipeline.

Uses the Instructor library for automatic schema enforcement with retry.
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from enum import Enum


class IssueType(str, Enum):
    """Types of issues that can be identified during code review."""
    SYNTAX_ERROR = "syntax_error"
    MISSING_CONTEXT = "missing_context"
    INCOMPLETE_CODE = "incomplete_code"
    API_MISMATCH = "api_mismatch"
    SECURITY_CONCERN = "security_concern"
    FORMATTING_ISSUE = "formatting_issue"
    DOCUMENTATION_GAP = "documentation_gap"
    OTHER = "other"


class Severity(str, Enum):
    """Severity levels for review issues."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ReviewIssue(BaseModel):
    """A single issue found during code review."""
    snippet_index: int = Field(
        ge=0,
        description="Index of the code snippet with the issue (0-based)"
    )
    issue_type: IssueType = Field(
        description="Category of the issue"
    )
    description: str = Field(
        min_length=10,
        description="Clear description of the issue found"
    )
    suggestion: Optional[str] = Field(
        default=None,
        description="Optional suggestion for fixing the issue"
    )
    severity: Severity = Field(
        description="Severity level of the issue"
    )


class ReviewResponse(BaseModel):
    """
    Structured response from code review.

    Guarantees:
    - approved is always a boolean (never null or missing)
    - issues is always a list (never null)
    - Each issue has validated types and constraints
    """
    approved: bool = Field(
        description="Whether all code snippets pass review"
    )
    issues: List[ReviewIssue] = Field(
        default_factory=list,
        description="List of issues found during review (empty if approved)"
    )


class CodeFixResponse(BaseModel):
    """
    Structured response from code fix request.

    Includes validation to ensure the response is actual code,
    not prose explanation or apology.
    """
    fixed_code: str = Field(
        min_length=10,
        description="The corrected C# code"
    )
    changes_made: List[str] = Field(
        default_factory=list,
        description="Summary of changes made to fix the code"
    )

    @field_validator('fixed_code')
    @classmethod
    def validate_csharp_code(cls, v: str) -> str:
        """
        Ensure response is actual C# code, not prose explanation.

        Raises:
            ValueError: If the response appears to be prose instead of code
        """
        # Code indicators that should be present
        code_indicators = [
            'using ', 'class ', 'void ', 'public ', 'private ',
            'static ', 'new ', ';', '{', '}', 'var ', 'string ',
            'int ', 'bool ', 'return '
        ]

        # Count how many indicators are present
        indicator_count = sum(1 for ind in code_indicators if ind in v)

        # Require at least 2 code indicators
        if indicator_count < 2:
            raise ValueError(
                "Response does not appear to be valid C# code. "
                f"Found only {indicator_count} code indicators."
            )

        # Reject if it starts with prose patterns
        prose_patterns = [
            'I ', "I'm ", 'Sorry', 'Unfortunately', 'Note:',
            'The ', 'This ', 'Here ', 'To ', 'You '
        ]

        stripped = v.strip()
        if any(stripped.startswith(p) for p in prose_patterns):
            raise ValueError(
                "Response appears to be prose explanation, not code. "
                f"Starts with: {stripped[:50]}..."
            )

        return v


class CompilationHint(BaseModel):
    """A hint for fixing compilation errors."""
    hint_type: str = Field(description="Type of fix needed (e.g., 'add_using', 'wrap_main')")
    detail: str = Field(description="Specific fix to apply")


class ErrorAnalysis(BaseModel):
    """Analysis of compilation or runtime errors."""
    primary_error: str = Field(description="The main error that needs to be fixed")
    error_category: str = Field(description="Category: syntax, missing_type, runtime, etc.")
    suggested_fixes: List[CompilationHint] = Field(
        default_factory=list,
        description="Ordered list of suggested fixes to try"
    )
