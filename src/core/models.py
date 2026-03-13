"""
Core data models for Example Reviewer Pipeline.
Uses Pydantic for validation and serialization.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, computed_field, field_validator
import hashlib
import socket
import uuid

# Import AppContext for application architecture classification
try:
    from .app_context import AppContext
except ImportError:
    # Fallback for cases where app_context module is not yet available
    AppContext = None


class ExampleStatus(str, Enum):
    """Status state machine for examples."""
    DISCOVERED = "DISCOVERED"
    COMPILE_FAILED = "COMPILE_FAILED"
    COMPILABLE = "COMPILABLE"
    RUNTIME_FAILED = "RUNTIME_FAILED"
    VERIFIED = "VERIFIED"
    MD_UPDATED = "MD_UPDATED"
    FINAL_REVIEW_PASSED = "FINAL_REVIEW_PASSED"
    FINAL_REVIEW_FAILED = "FINAL_REVIEW_FAILED"
    NEEDS_REVIEW = "NEEDS_REVIEW"  # Track 2: Risk routing escalation state
    INFRA_BLOCKED = "INFRA_BLOCKED"  # Phase-2: Infrastructure blocker (missing fixtures, etc.)
    COMMITTED = "COMMITTED"


class ErrorRisk(str, Enum):
    """Risk level for error routing (Track 2: D.4)."""
    LOW = "LOW"  # Auto-fix with limited retries
    MEDIUM = "MEDIUM"  # Auto-fix with drift + validation gates
    HIGH = "HIGH"  # One attempt then NEEDS_REVIEW
    CRITICAL = "CRITICAL"  # Immediate NEEDS_REVIEW


class SourceType(str, Enum):
    """Source type for code examples."""
    INLINE = "inline"
    GIST = "gist"
    CS_FILE = "cs_file"
    EXTRACTED_FROM_WRAPPER = "extracted_from_wrapper"


class EditType(str, Enum):
    """Type of edit operation."""
    INLINE_REPLACE = "inline_replace"
    GIST_REPLACE = "gist_replace"
    CS_FILE_REPLACE = "cs_file_replace"


class ScanMode(str, Enum):
    """Scan mode for discovery."""
    DIRECTORY = "directory"
    FAMILY = "family"


class ScanScope(BaseModel):
    """Scan scope configuration for discovery."""
    mode: ScanMode = ScanMode.FAMILY
    directory_path: Optional[str] = None
    family: Optional[str] = None
    


class Location(BaseModel):
    """Location metadata for code blocks."""
    block_index: int = 0
    start_line: int = 0
    end_line: int = 0
    anchor: str = ""


class GistInfo(BaseModel):
    """Gist reference information."""
    owner: str = ""
    gist_id: str = ""
    filename: str = ""


class ExampleRecord(BaseModel):
    """
    A code example extracted from markdown.
    Represents one discoverable unit throughout the pipeline.
    """
    example_id: str = Field(default="", description="Stable hash ID")
    family: str = Field(..., description="Product family identifier")
    file_path: str = Field(..., description="Source markdown file")
    source_type: SourceType = Field(default=SourceType.INLINE)
    language: str = Field(default="csharp")
    location: Location = Field(default_factory=Location)
    gist: Optional[GistInfo] = None
    original_code: Optional[str] = Field(default="", description="Code as discovered")
    compilable_code: Optional[str] = Field(default=None, description="Code after compile fixes")
    verified_code: Optional[str] = Field(default=None, description="Code after runtime verification")
    status: ExampleStatus = Field(default=ExampleStatus.DISCOVERED)
    failure_reason: Optional[str] = None
    escalation_reason: Optional[str] = Field(default=None, description="Reason for NEEDS_REVIEW escalation")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Content context fields for LLM relevance preservation
    section_heading: Optional[str] = Field(default=None, description="Markdown heading above code block")
    description_context: Optional[str] = Field(default=None, description="Paragraphs before code block")
    topic: Optional[str] = Field(default=None, description="Topic inferred from file path")
    article_intent: Optional[str] = Field(default=None, description="Compact article intent from YAML frontmatter (title + description + steps)")

    # Application context classification (Phase-2 Gate B: prevent cross-context substitution)
    app_context: Optional[str] = Field(default=None, description="Application architecture type (console, aspnet_core_minimal, mvc, webapi, library)")

    # Code block location metadata for safe md_update targeting (Migration 011)
    code_block_signature: Optional[str] = Field(default=None, description="SHA256 hash of normalized original code content")
    extraction_warning: Optional[str] = Field(default=None, description="Warning if block index is ambiguous during extraction")

    # Deterministic key for stable ordering (Track 1 requirement)
    example_key: str = Field(default="", description="Deterministic hash for stable ordering")
    
    @computed_field
    @property
    def current_code(self) -> str:
        """Get the most recent version of the code."""
        return self.verified_code or self.compilable_code or self.original_code
    
    def generate_id(self) -> str:
        """Generate stable ID from content hash."""
        content = f"{self.family}:{self.file_path}:{self.location.block_index}:{self.original_code or ''}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def generate_example_key(self) -> str:
        """
        Generate deterministic example_key for stable ordering.

        Formula: sha256(f"{norm_path}:{block_index}:{lang}:{kind}").hexdigest()[:16]

        Where:
        - norm_path: normalized file path (lowercase, forward slashes)
        - block_index: location.block_index
        - lang: language
        - kind: source_type (inline/gist)

        Returns:
            16-character hex hash for deterministic ordering
        """
        # Normalize path for cross-platform determinism
        norm_path = self.file_path.replace("\\", "/").lower()

        # Build deterministic key from stable components
        content = f"{norm_path}:{self.location.block_index}:{self.language}:{self.source_type.value}"

        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def model_post_init(self, __context) -> None:
        """Generate ID and example_key if not provided."""
        if not self.example_id:
            self.example_id = self.generate_id()
        if not self.example_key:
            self.example_key = self.generate_example_key()

    @field_validator("original_code", mode="before")
    @classmethod
    def _normalize_original_code(cls, value: Optional[str]) -> str:
        if value is None:
            return ""
        return value
    
    def can_transition_to(self, new_status: ExampleStatus) -> bool:
        """Check if transition to new status is valid."""
        valid_transitions = {
            ExampleStatus.DISCOVERED: [ExampleStatus.COMPILE_FAILED, ExampleStatus.COMPILABLE, ExampleStatus.NEEDS_REVIEW, ExampleStatus.INFRA_BLOCKED],
            ExampleStatus.COMPILE_FAILED: [ExampleStatus.COMPILABLE, ExampleStatus.NEEDS_REVIEW, ExampleStatus.INFRA_BLOCKED],
            ExampleStatus.COMPILABLE: [ExampleStatus.RUNTIME_FAILED, ExampleStatus.VERIFIED, ExampleStatus.NEEDS_REVIEW, ExampleStatus.INFRA_BLOCKED],
            ExampleStatus.RUNTIME_FAILED: [ExampleStatus.VERIFIED, ExampleStatus.NEEDS_REVIEW, ExampleStatus.INFRA_BLOCKED],
            ExampleStatus.VERIFIED: [ExampleStatus.MD_UPDATED],
            ExampleStatus.MD_UPDATED: [ExampleStatus.FINAL_REVIEW_PASSED, ExampleStatus.FINAL_REVIEW_FAILED],
            ExampleStatus.FINAL_REVIEW_PASSED: [ExampleStatus.COMMITTED],
            ExampleStatus.FINAL_REVIEW_FAILED: [],
            ExampleStatus.NEEDS_REVIEW: [],  # Terminal state - requires human review
            ExampleStatus.INFRA_BLOCKED: [],  # Terminal state - requires infrastructure fix
            ExampleStatus.COMMITTED: [],
        }
        return new_status in valid_transitions.get(self.status, [])
    
    def transition_to(self, new_status: ExampleStatus, reason: Optional[str] = None) -> bool:
        """Attempt to transition to new status."""
        if not self.can_transition_to(new_status):
            return False
        self.status = new_status
        self.updated_at = datetime.now(timezone.utc)
        if reason:
            self.failure_reason = reason
        return True


class CompileAttempt(BaseModel):
    """Record of a compilation attempt."""
    attempt_id: str = Field(default="", description="Unique attempt ID")
    example_id: str = Field(..., description="Reference to example")
    family: str = Field(..., description="Product family")
    dll_version: str = Field(default="", description="NuGet package version used")
    success: bool = Field(default=False)
    compiler_log_ref: str = Field(default="", description="Artifact reference")
    input_code_ref: str = Field(default="", description="Input code artifact")
    output_code_ref: str = Field(default="", description="Output code artifact")
    llm_request_ref: str = Field(default="", description="LLM request artifact")
    llm_response_ref: str = Field(default="", description="LLM response artifact")
    error_messages: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    def model_post_init(self, __context) -> None:
        if not self.attempt_id:
            content = f"{self.example_id}:{self.timestamp.isoformat()}"
            self.attempt_id = hashlib.sha256(content.encode()).hexdigest()[:16]


class RuntimeAttempt(BaseModel):
    """Record of a runtime execution attempt."""
    attempt_id: str = Field(default="", description="Unique attempt ID")
    example_id: str = Field(..., description="Reference to example")
    family: str = Field(..., description="Product family")
    sample_ref: str = Field(default="", description="Test data reference")
    scenario: str = Field(default="", description="Execution scenario")
    success: bool = Field(default=False)
    runtime_log_ref: str = Field(default="", description="Runtime log artifact")
    exit_code: int = Field(default=-1)
    stdout: str = Field(default="")
    stderr: str = Field(default="")
    exception_type: Optional[str] = None
    exception_message: Optional[str] = None
    output_files: List[str] = Field(default_factory=list)
    environment: Dict[str, str] = Field(default_factory=dict)
    retrieved_examples_refs: List[str] = Field(default_factory=list)
    llm_request_ref: str = Field(default="")
    llm_response_ref: str = Field(default="")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    def model_post_init(self, __context) -> None:
        if not self.attempt_id:
            content = f"{self.example_id}:{self.timestamp.isoformat()}"
            self.attempt_id = hashlib.sha256(content.encode()).hexdigest()[:16]


class MarkdownEdit(BaseModel):
    """Record of a markdown file edit."""
    edit_id: str = Field(default="", description="Unique edit ID")
    file_path: str = Field(..., description="Markdown file path")
    example_id: str = Field(..., description="Reference to example")
    family: str = Field(..., description="Product family")
    edit_type: EditType = Field(default=EditType.INLINE_REPLACE)
    diff_ref: str = Field(default="", description="Diff artifact reference")
    old_code: str = Field(default="")
    new_code: str = Field(default="")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    def model_post_init(self, __context) -> None:
        if not self.edit_id:
            content = f"{self.example_id}:{self.file_path}:{self.timestamp.isoformat()}"
            self.edit_id = hashlib.sha256(content.encode()).hexdigest()[:16]


class CommitRecord(BaseModel):
    """Record of a git commit."""
    commit_id: str = Field(default="", description="Internal commit ID")
    run_id: str = Field(..., description="Pipeline run ID")
    family: str = Field(..., description="Product family")
    hash: str = Field(default="", description="Git commit hash")
    message: str = Field(default="")
    description: str = Field(default="")
    touched_files: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    def model_post_init(self, __context) -> None:
        if not self.commit_id:
            content = f"{self.run_id}:{self.family}:{self.timestamp.isoformat()}"
            self.commit_id = hashlib.sha256(content.encode()).hexdigest()[:16]


class RunRecord(BaseModel):
    """Record of a pipeline run."""
    run_id: str = Field(default="", description="Unique run ID")
    family: str = Field(..., description="Product family")
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    status: str = Field(default="running")
    phases_completed: List[str] = Field(default_factory=list)
    current_phase: str = Field(default="")
    examples_processed: int = Field(default=0)
    examples_successful: int = Field(default=0)
    examples_failed: int = Field(default=0)
    error: Optional[str] = None
    
    def model_post_init(self, __context) -> None:
        if not self.run_id:
            content = f"{self.family}:{self.started_at.isoformat()}"
            self.run_id = hashlib.sha256(content.encode()).hexdigest()[:16]


class LLMFixPayload(BaseModel):
    """Payload for LLM code fixing requests."""
    code: str = Field(..., description="Code to fix")
    errors: List[str] = Field(default_factory=list, description="Error messages")
    context_type: str = Field(default="compile", description="compile or runtime")
    api_references: List[str] = Field(default_factory=list)
    similar_examples: List[str] = Field(default_factory=list)
    scaffolding_hints: List[str] = Field(default_factory=list)
    family: str = Field(default="")
    nuget_package: str = Field(default="")
    default_usings: List[str] = Field(default_factory=list)

    def to_prompt(self) -> str:
        """Generate a text representation of the payload for logging."""
        parts = [f"Context: {self.context_type}"]
        if self.family:
            parts.append(f"Family: {self.family}")
        if self.errors:
            parts.append(f"Errors:\n" + "\n".join(self.errors[:5]))
        if self.scaffolding_hints:
            parts.append(f"Hints:\n" + "\n".join(self.scaffolding_hints[:3]))
        parts.append(f"Code:\n{self.code[:500]}{'...' if len(self.code) > 500 else ''}")
        return "\n\n".join(parts)


class TelemetryEvent(BaseModel):
    """Telemetry event record."""
    event_id: str = Field(default="", description="Unique event ID")
    run_id: str = Field(..., description="Pipeline run ID")
    family: str = Field(..., description="Product family")
    event_type: str = Field(..., description="Event type")
    phase: str = Field(default="")
    example_id: Optional[str] = None
    duration_ms: Optional[int] = None
    success: bool = Field(default=True)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def model_post_init(self, __context) -> None:
        if not self.event_id:
            content = f"{self.run_id}:{self.event_type}:{self.timestamp.isoformat()}"
            self.event_id = hashlib.sha256(content.encode()).hexdigest()[:16]


class FailureCategory(str, Enum):
    """Categories of failures tracked in the pipeline."""
    TIMEOUT = "timeout"
    DRIFT_EXCEEDED = "drift_exceeded"
    API_CONTEXT_MISSING = "api_context_missing"
    LLM_RESPONSE_REJECTED = "llm_response_rejected"
    ESCALATED_TO_REVIEW = "escalated_to_review"
    COMPILE_ERROR = "compile_error"
    RUNTIME_ERROR = "runtime_error"
    REVIEW_FAILED = "review_failed"
    INFRA_MISSING_TEST_DATA = "infra_missing_test_data"  # Infrastructure: test data files missing
    INFRA_BLOCKED_RAR_FIXTURE = "infra_blocked_rar_fixture"  # Phase-2: RAR fixture unavailable
    INFRA_BLOCKED_7Z_FIXTURE = "infra_blocked_7z_fixture"  # Phase-2: 7z fixture incompatible
    INFRA_BLOCKED_PASSWORD = "infra_blocked_password"  # Phase-2: Password/secret required
    INFRA_BLOCKED_FORMAT = "infra_blocked_format"  # Phase-2: Unsupported archive format
    INFRA_BLOCKED_EXTERNAL = "infra_blocked_external"  # Phase-2: External dependency missing
    PRECHECK_ONLY = "precheck_only"  # Phase-2: Pre-compilation check failed (empty/incomplete)
    OTHER = "other"


class FailureResolution(str, Enum):
    """Resolution status for tracked failures."""
    FIXED = "fixed"
    NEEDS_REVIEW = "needs_review"
    ABANDONED = "abandoned"
    PENDING = "pending"


class FailureDetail(BaseModel):
    """Record of a failure for analytics tracking."""
    failure_id: str = Field(default="", description="Unique failure ID")
    run_id: str = Field(..., description="Pipeline run ID")
    example_id: Optional[str] = Field(default=None, description="Example that failed")
    phase: str = Field(..., description="Phase where failure occurred")
    failure_category: FailureCategory = Field(..., description="Category of failure")
    error_category: Optional[str] = Field(default=None, description="Specific error type")
    error_message: Optional[str] = Field(default=None, description="Error message text")
    resolution: FailureResolution = Field(default=FailureResolution.PENDING)
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def model_post_init(self, __context) -> None:
        if not self.failure_id:
            content = f"{self.run_id}:{self.phase}:{self.failure_category.value}:{self.timestamp.isoformat()}"
            self.failure_id = hashlib.sha256(content.encode()).hexdigest()[:16]


class TelemetryRun(BaseModel):
    """
    Full telemetry run record matching local-telemetry HTTP API schema.
    Supports ~40 fields for comprehensive run tracking.
    """
    # Required identifiers
    event_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique event ID (UUID)"
    )
    run_id: str = Field(..., description="Pipeline run ID")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Record creation timestamp"
    )
    start_time: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Run start timestamp"
    )
    agent_name: str = Field(default="example-reviewer", description="Agent identifier")
    job_type: str = Field(..., description="Type of job (e.g., 'validation', 'discovery')")

    # Status fields
    end_time: Optional[datetime] = Field(default=None, description="Run end timestamp")
    status: str = Field(
        default="running",
        pattern="^(running|success|failure|partial|timeout|cancelled)$",
        description="Run status"
    )

    # Product context
    product: str = Field(default="", description="Product display name (e.g., 'Aspose.Zip for .NET')")
    product_family: str = Field(default="", description="Product family identifier")
    platform: str = Field(default="dotnet", description="Target platform")
    subdomain: str = Field(default="", description="Subdomain from content roots")
    website: str = Field(default="", description="Website/repo URL")
    website_section: str = Field(default="", description="Website section (blog/docs/kb)")
    item_name: str = Field(default="", description="Item/file being processed")

    # Item counts
    items_discovered: int = Field(default=0, ge=0, description="Total items discovered")
    items_succeeded: int = Field(default=0, ge=0, description="Items successfully processed")
    items_failed: int = Field(default=0, ge=0, description="Items that failed")
    items_skipped: int = Field(default=0, ge=0, description="Items skipped")
    duration_ms: int = Field(default=0, ge=0, description="Total duration in milliseconds")

    # Summary fields
    input_summary: str = Field(default="", description="Summary of input/scope")
    output_summary: str = Field(default="", description="Summary of outputs/results")
    source_ref: str = Field(default="", description="Source reference (path/URL)")
    target_ref: str = Field(default="", description="Target reference (path/URL)")
    error_summary: Optional[str] = Field(default=None, description="Error summary if failed")
    error_details: Optional[str] = Field(default=None, description="Detailed error info")

    # Git information
    git_repo: str = Field(default="", description="Git repository URL")
    git_branch: str = Field(default="", description="Git branch name")
    git_commit_hash: str = Field(default="", description="Git commit SHA")
    git_run_tag: str = Field(default="", description="Run-specific tag")
    git_commit_source: str = Field(default="llm", description="Commit source (llm/manual)")
    git_commit_author: str = Field(
        default="Example Reviewer <example-reviewer@aspose.net>",
        description="Commit author identity"
    )
    git_commit_timestamp: Optional[datetime] = Field(
        default=None,
        description="Timestamp of associated commit"
    )

    # Environment
    host: str = Field(
        default_factory=lambda: socket.gethostname(),
        description="Host machine name"
    )
    environment: str = Field(default="dev", description="Environment (dev/staging/prod)")
    trigger_type: str = Field(default="manual", description="Trigger type (manual/scheduled/ci)")

    # JSON metadata fields
    metrics_json: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metrics as JSON"
    )
    context_json: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context as JSON"
    )

    # API posting status
    api_posted: bool = Field(default=False, description="Whether posted to HTTP API")
    api_posted_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when posted to API"
    )
    api_retry_count: int = Field(default=0, ge=0, description="Number of API post retries")

    # Relations
    insight_id: Optional[str] = Field(default=None, description="Related insight ID")
    parent_run_id: Optional[str] = Field(default=None, description="Parent run ID for nested runs")

    def to_api_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for HTTP API posting."""
        data = self.model_dump(mode='json')
        # Convert datetime objects to ISO strings
        for key in ['created_at', 'start_time', 'end_time', 'git_commit_timestamp', 'api_posted_at']:
            if data.get(key):
                if isinstance(data[key], str):
                    pass  # Already string
                else:
                    data[key] = data[key].isoformat()
        return data

    def calculate_duration(self) -> int:
        """Calculate duration from start to end time."""
        if self.end_time and self.start_time:
            delta = self.end_time - self.start_time
            return int(delta.total_seconds() * 1000)
        return self.duration_ms


class IssueSeverity(str, Enum):
    """Severity level for review issues."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class IssueType(str, Enum):
    """Type of review issue."""
    SYNTAX_ERROR = "syntax_error"
    MISSING_CONTEXT = "missing_context"
    INCOMPLETE_CODE = "incomplete_code"
    API_MISMATCH = "api_mismatch"
    SECURITY_CONCERN = "security_concern"
    FORMATTING_ISSUE = "formatting_issue"
    DOCUMENTATION_GAP = "documentation_gap"
    INTENT_MISMATCH = "intent_mismatch"
    OUTDATED_API = "outdated_api"
    OTHER = "other"


class ReviewIssue(BaseModel):
    """An issue found during final LLM review."""
    issue_id: str = Field(default="", description="Unique issue ID")
    review_id: str = Field(..., description="Parent review ID")
    example_id: str = Field(..., description="Example this issue relates to")
    issue_type: IssueType = Field(default=IssueType.OTHER)
    description: str = Field(..., description="Description of the issue")
    suggestion: Optional[str] = Field(default=None, description="Suggested fix")
    severity: IssueSeverity = Field(default=IssueSeverity.WARNING)
    resolved: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def model_post_init(self, __context) -> None:
        if not self.issue_id:
            content = f"{self.review_id}:{self.example_id}:{self.description[:50]}:{self.created_at.isoformat()}"
            self.issue_id = hashlib.sha256(content.encode()).hexdigest()[:16]


class ReviewResult(BaseModel):
    """Result of a final LLM review for a file."""
    review_id: str = Field(default="", description="Unique review ID")
    file_path: str = Field(..., description="Reviewed file path")
    run_id: str = Field(..., description="Pipeline run ID")
    family: str = Field(..., description="Product family")
    approved: bool = Field(default=False)
    review_attempt: int = Field(default=1, description="Which review attempt this is")
    issues: List[ReviewIssue] = Field(default_factory=list)
    llm_response: Optional[str] = Field(default=None, description="Raw LLM response")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def model_post_init(self, __context) -> None:
        if not self.review_id:
            content = f"{self.run_id}:{self.file_path}:{self.review_attempt}:{self.timestamp.isoformat()}"
            self.review_id = hashlib.sha256(content.encode()).hexdigest()[:16]

    @property
    def issue_count(self) -> int:
        """Get count of issues found."""
        return len(self.issues)

    @property
    def unresolved_count(self) -> int:
        """Get count of unresolved issues."""
        return sum(1 for issue in self.issues if not issue.resolved)

    @property
    def has_critical_issues(self) -> bool:
        """Check if any critical issues exist."""
        return any(
            issue.severity == IssueSeverity.CRITICAL and not issue.resolved
            for issue in self.issues
        )
