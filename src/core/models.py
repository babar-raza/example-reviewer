"""
Core data models for Example Reviewer Pipeline.
Uses Pydantic for validation and serialization.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, computed_field
import hashlib


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
    COMMITTED = "COMMITTED"


class SourceType(str, Enum):
    """Source type for code examples."""
    INLINE = "inline"
    GIST = "gist"


class EditType(str, Enum):
    """Type of markdown edit."""
    INLINE_REPLACE = "inline_replace"
    GIST_REPLACE = "gist_replace"


class ScanMode(str, Enum):
    """Scan mode for discovery."""
    DIRECTORY = "directory"
    FAMILY = "family"


class ScanScope(BaseModel):
    """Scan scope configuration for discovery."""
    mode: ScanMode = ScanMode.FAMILY
    directory_path: Optional[str] = None
    family: Optional[str] = None
    
    def validate_scope(self) -> bool:
        """Validate that scope is properly configured."""
        if self.mode == ScanMode.DIRECTORY:
            return self.directory_path is not None
        return self.family is not None


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
    original_code: str = Field(default="", description="Code as discovered")
    compilable_code: Optional[str] = Field(default=None, description="Code after compile fixes")
    verified_code: Optional[str] = Field(default=None, description="Code after runtime verification")
    status: ExampleStatus = Field(default=ExampleStatus.DISCOVERED)
    failure_reason: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @computed_field
    @property
    def current_code(self) -> str:
        """Get the most recent version of the code."""
        return self.verified_code or self.compilable_code or self.original_code
    
    def generate_id(self) -> str:
        """Generate stable ID from content hash."""
        content = f"{self.family}:{self.file_path}:{self.location.block_index}:{self.original_code}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def model_post_init(self, __context) -> None:
        """Generate ID if not provided."""
        if not self.example_id:
            self.example_id = self.generate_id()
    
    def can_transition_to(self, new_status: ExampleStatus) -> bool:
        """Check if transition to new status is valid."""
        valid_transitions = {
            ExampleStatus.DISCOVERED: [ExampleStatus.COMPILE_FAILED, ExampleStatus.COMPILABLE],
            ExampleStatus.COMPILE_FAILED: [ExampleStatus.COMPILABLE],
            ExampleStatus.COMPILABLE: [ExampleStatus.RUNTIME_FAILED, ExampleStatus.VERIFIED],
            ExampleStatus.RUNTIME_FAILED: [ExampleStatus.VERIFIED],
            ExampleStatus.VERIFIED: [ExampleStatus.MD_UPDATED],
            ExampleStatus.MD_UPDATED: [ExampleStatus.FINAL_REVIEW_PASSED, ExampleStatus.FINAL_REVIEW_FAILED],
            ExampleStatus.FINAL_REVIEW_PASSED: [ExampleStatus.COMMITTED],
            ExampleStatus.FINAL_REVIEW_FAILED: [],
            ExampleStatus.COMMITTED: [],
        }
        return new_status in valid_transitions.get(self.status, [])
    
    def transition_to(self, new_status: ExampleStatus, reason: Optional[str] = None) -> bool:
        """Attempt to transition to new status."""
        if not self.can_transition_to(new_status):
            return False
        self.status = new_status
        self.updated_at = datetime.utcnow()
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
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
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
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
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
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
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
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    def model_post_init(self, __context) -> None:
        if not self.commit_id:
            content = f"{self.run_id}:{self.family}:{self.timestamp.isoformat()}"
            self.commit_id = hashlib.sha256(content.encode()).hexdigest()[:16]


class RunRecord(BaseModel):
    """Record of a pipeline run."""
    run_id: str = Field(default="", description="Unique run ID")
    family: str = Field(..., description="Product family")
    started_at: datetime = Field(default_factory=datetime.utcnow)
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
        """Convert the payload to a prompt string for LLM."""
        prompt_parts = [f"# Code to Fix\n```csharp\n{self.code}\n```\n"]

        if self.errors:
            prompt_parts.append(f"\n# Errors\n" + "\n".join(f"- {err}" for err in self.errors))

        if self.default_usings:
            prompt_parts.append(f"\n# Available Namespaces\n" + "\n".join(f"- {ns}" for ns in self.default_usings))

        if self.api_references:
            prompt_parts.append(f"\n# API References\n" + "\n".join(f"- {ref}" for ref in self.api_references))

        if self.scaffolding_hints:
            prompt_parts.append(f"\n# Hints\n" + "\n".join(f"- {hint}" for hint in self.scaffolding_hints))

        return "\n".join(prompt_parts)


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
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    def model_post_init(self, __context) -> None:
        if not self.event_id:
            content = f"{self.run_id}:{self.event_type}:{self.timestamp.isoformat()}"
            self.event_id = hashlib.sha256(content.encode()).hexdigest()[:16]
