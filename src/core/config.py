"""
Configuration system for Example Reviewer Pipeline.
Uses Pydantic for validation and supports multi-family configurations.
"""

import os
import json
import hashlib
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple, Set
from pydantic import BaseModel, Field, ConfigDict
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class ConfigAccessTracker:
    """
    Tracks which config fields are accessed at runtime.

    Usage:
        tracker = ConfigAccessTracker()
        tracker.record_access('llm.seed')
        tracker.record_access('vector_db.enabled')
        tracker.export_to_file('runs/run_id/config_access.json')
    """

    def __init__(self):
        """Initialize config access tracker."""
        self._accesses: Set[str] = set()
        self._enabled: bool = True

    def record_access(self, field_path: str) -> None:
        """
        Record access to a config field.

        Args:
            field_path: Dot-separated path to config field (e.g., 'llm.seed')
        """
        if self._enabled:
            self._accesses.add(field_path)

    def get_accesses(self) -> List[str]:
        """
        Get list of all accessed config fields.

        Returns:
            Sorted list of field paths
        """
        return sorted(self._accesses)

    def export_to_file(self, file_path: Path) -> None:
        """
        Export config access log to JSON file.

        Args:
            file_path: Path to output JSON file
        """
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            'total_accesses': len(self._accesses),
            'accessed_fields': self.get_accesses(),
        }

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def clear(self) -> None:
        """Clear all recorded accesses."""
        self._accesses.clear()

    def disable(self) -> None:
        """Disable tracking (for performance)."""
        self._enabled = False

    def enable(self) -> None:
        """Enable tracking."""
        self._enabled = True


class LLMConfig(BaseModel):
    """LLM provider configuration."""
    model_config = ConfigDict(extra="forbid")

    provider: str = Field(default="company", description="LLM provider (openai, ollama, azure, company)")
    model: str = Field(default="gpt-oss-120b", description="Model name")
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_retries: int = Field(default=3, ge=1)
    retry_backoff_seconds: int = Field(default=5, ge=1)
    api_key_env_var: str = Field(default="litellm_key", description="Environment variable containing API key")
    base_url: Optional[str] = Field(default="https://llm.professionalize.com/v1", description="Custom API base URL")
    timeout_seconds: int = Field(default=120)
    seed: Optional[int] = Field(default=None, description="Random seed for deterministic mode")
    deterministic_mode: bool = Field(default=False, description="Enable deterministic mode")
    enforce_timeout: bool = Field(default=True, description="Enforce timeout strictly")


class LimitsConfig(BaseModel):
    """Resource limit configuration."""
    model_config = ConfigDict(extra="forbid")

    cpu_max_percent: int = Field(default=90, ge=0, le=100)
    ram_max_mb: int = Field(default=0, description="0 = no limit")
    vram_max_mb: int = Field(default=0, description="0 = no limit")


class ResourceDetectionConfig(BaseModel):
    """Resource detection settings."""
    model_config = ConfigDict(extra="forbid")

    auto_detect_vram: bool = True
    prefer_gpu_when_available: bool = True
    fallback_to_cpu: bool = True
    telemetry_log_resource_decisions: bool = True


class GitConfig(BaseModel):
    """Git integration configuration."""
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    commit_format: str = "compact"  # "minimal" | "compact" | "detailed" | "structured"
    commit_message_template: str = "chore({family}): verify {count} examples"
    commit_description_template: str = "Automated verification of {count} examples.\n\nRunId: {run_id}\nFamily: {family}"
    only_commit_touched_files: bool = True


class DatabaseConfig(BaseModel):
    """Database configuration for dev and production."""
    model_config = ConfigDict(extra="forbid")

    # Development database (always active)
    path: str = Field(
        default="./data/example_reviewer.db",
        description="Primary development database"
    )

    # Production database (optional, enables dual-DB mode)
    production_path: Optional[str] = Field(
        default=None,
        description="Production database path. If set, enables dual-database mode."
    )

    # How to identify production runs
    production_criteria: str = Field(
        default="git_commit",
        pattern="^(git_commit)$",
        description="Criteria for production runs (currently only git_commit supported)"
    )


class GistConfig(BaseModel):
    """GitHub Gist configuration."""
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    target_account: str = ""
    auth_method: str = Field(default="none", pattern="^(pat|oauth|none)$")
    pat_env_var: str = "GIST_PAT"
    upload_mode: str = Field(
        default="inline-only",
        pattern="^(upload-on-change|upload-always|inline-only)$",
        description="Gist handling: upload-on-change, upload-always, or inline-only"
    )
    is_public: bool = Field(default=True, description="Create public or secret gists")
    description_template: str = Field(
        default="Verified example from {family} - {file_path}",
        description="Template for gist descriptions"
    )
    readme_generation: bool = Field(
        default=True,
        description="Generate README.md for gists using LLM (with template fallback)"
    )


class APICatalogConfig(BaseModel):
    """API catalog configuration (HEAL-05)."""
    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    storage_type: str = Field(default="json", pattern="^(json|database)$")
    path: str = ""
    lazy_loading: bool = False
    assembly_verified: bool = Field(default=False, description="Whether catalog was validated against assembly")
    assembly_version: str = Field(default="", description="Version of assembly used for validation")


class FixtureResolverConfig(BaseModel):
    """Fixture resolver configuration for self-healing runtime environment."""
    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    max_generations_per_run: int = Field(default=50, ge=0)
    registry_path: str = ""
    skip_output_patterns: List[str] = Field(
        default_factory=lambda: ["output*", "result*", "*.out"],
        description="Glob patterns for filenames that should NOT be generated (look like outputs)"
    )


class TelemetryConfig(BaseModel):
    """Telemetry configuration."""
    model_config = ConfigDict(extra="forbid")

    internal_enabled: bool = True
    local_telemetry_enabled: bool = True
    local_telemetry_path: str = "./local-telemetry"
    http_api_enabled: bool = True
    http_api_url: str = "http://localhost:8765"
    http_api_timeout_seconds: int = 10
    http_api_retry_count: int = 3


class VectorDBConfig(BaseModel):
    """Vector database configuration for similarity search."""
    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(default=False, description="Enable vector DB features")
    provider: str = Field(default="chromadb", description="Vector DB provider")
    embedding_model: str = Field(
        default="all-MiniLM-L6-v2",
        description="Sentence-transformers model for embeddings"
    )
    persist_directory: str = Field(default="./data/chroma", description="ChromaDB persist directory")
    search_k: int = Field(default=3, ge=1, le=10, description="Number of similar examples to retrieve")
    min_similarity_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score (0.0-1.0)"
    )
    require_on_startup: bool = Field(
        default=False,
        description="Require vector DB to be available on startup (fail-fast if disabled)"
    )
    deterministic_search: bool = Field(
        default=True,
        description="Enable deterministic ordering for vector search results"
    )
    embedding_device: str = Field(
        default="cpu",
        description="Device for embeddings (cpu or cuda)"
    )
    drift_tolerance: float = Field(
        default=0.02,
        ge=0.0,
        le=1.0,
        description="Tolerance for drift in embedding comparisons"
    )


class BackfillConfig(BaseModel):
    """Backfill configuration for auto-downloading missing data."""
    model_config = ConfigDict(extra="forbid")

    auto_enabled: bool = Field(default=False, description="Enable automatic backfill")
    targets: List[str] = Field(
        default_factory=lambda: ["test_data", "examples", "gist_source_code"],
        description="Backfill targets (test_data, examples, gist_source_code)"
    )
    github_timeout_seconds: int = Field(default=120, ge=10)
    retry_on_failure: bool = Field(default=True)


class ContextExtractionConfig(BaseModel):
    """Configuration for context extraction around code snippets."""
    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(
        default=True,
        description="Enable/disable context extraction"
    )
    max_paragraphs: int = Field(
        default=2,
        ge=0,
        description="Maximum paragraphs of context before code"
    )
    max_heading_distance: int = Field(
        default=50,
        ge=1,
        description="Max lines to look back for headings"
    )
    include_file_header: bool = Field(
        default=False,
        description="Include file-level header (first heading)"
    )
    context_window_lines: int = Field(
        default=20,
        ge=1,
        description="Lines of context to capture before code"
    )
    min_context_length: int = Field(
        default=10,
        ge=0,
        description="Minimum characters for context (filter too-short)"
    )


class GistPatternsConfig(BaseModel):
    """Configuration for gist detection patterns."""
    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(
        default=True,
        description="Enable/disable gist extraction"
    )
    shortcode_patterns: List[str] = Field(
        default_factory=lambda: [
            r'\{\{<\s*gist\s+([^\s]+)\s+([^\s]+)(?:\s+["\']?([^"\'>\s]+)["\']?)?\s*>\}\}',
        ],
        description="Regex patterns for gist shortcodes"
    )
    script_patterns: List[str] = Field(
        default_factory=lambda: [
            r'<script\s+src=["\']https://gist\.github\.com/([^/]+)/([^.]+)\.js(?:\?file=([^"\']+))?["\']',
        ],
        description="Regex patterns for gist script tags"
    )
    allowed_owners: List[str] = Field(
        default_factory=list,
        description="Whitelist of gist owners (empty = all allowed)"
    )
    blocked_owners: List[str] = Field(
        default_factory=list,
        description="Blacklist of gist owners"
    )

    def compile_shortcode_patterns(self) -> List[Any]:
        """Compile shortcode patterns with error handling."""
        import re
        import logging
        logger = logging.getLogger(__name__)

        patterns = []
        for pattern_str in self.shortcode_patterns:
            try:
                patterns.append(re.compile(pattern_str, re.IGNORECASE))
            except re.error as e:
                logger.warning(f"Failed to compile gist shortcode pattern '{pattern_str}': {e}")
        return patterns

    def compile_script_patterns(self) -> List[Any]:
        """Compile script tag patterns with error handling."""
        import re
        import logging
        logger = logging.getLogger(__name__)

        patterns = []
        for pattern_str in self.script_patterns:
            try:
                patterns.append(re.compile(pattern_str, re.IGNORECASE))
            except re.error as e:
                logger.warning(f"Failed to compile gist script pattern '{pattern_str}': {e}")
        return patterns

    def should_include_owner(self, owner: str) -> Tuple[bool, Optional[str]]:
        """Check if gist owner should be included.

        Args:
            owner: Gist owner username

        Returns:
            Tuple of (should_include: bool, reason: Optional[str])
        """
        # Check blocked first
        if owner in self.blocked_owners:
            return False, f"blocked_owner:{owner}"

        # Check allowed (empty = all allowed)
        if self.allowed_owners and owner not in self.allowed_owners:
            return False, "not_in_allowed_owners"

        return True, None


class DiscoveryPatternsConfig(BaseModel):
    """Discovery pattern configuration for code extraction."""
    model_config = ConfigDict(extra="forbid")

    fence_patterns: List[str] = Field(
        default=["^```(\\w+|c#)\\s*\\n(.*?)^```"],
        description="Regex patterns for code fence detection"
    )
    validatable_languages: List[str] = Field(
        default=["cs", "csharp", "c#"],
        description="Languages that should be validated"
    )
    language_aliases: Dict[str, List[str]] = Field(
        default={
            "csharp": ["cs", "c#", "C#", "csharp", "CSharp"],
            "python": ["py", "python", "python3"]
        },
        description="Language normalization mapping"
    )
    normalize_to_canonical: bool = Field(
        default=True,
        description="Normalize language tags to canonical form"
    )
    regex_timeout_seconds: float = Field(
        default=5.0,
        ge=0.1,
        le=30.0,
        description="Regex execution timeout for safety"
    )

    # CD-02: Line count and content-based filtering
    min_line_count: int = Field(
        default=1,
        ge=1,
        description="Minimum lines to consider as code snippet"
    )
    max_line_count: int = Field(
        default=500,
        ge=1,
        description="Maximum lines to consider as code snippet"
    )
    content_exclude_patterns: List[str] = Field(
        default_factory=lambda: [
            r"^[\s\n]*\{[\s\n]*[\"']",  # JSON object (starts with { followed by quote)
            r"^\s*<\?xml",  # Starts with <?xml
            r"^\s*Output:",  # Command output
            r"^\s*\$\s+(dotnet|npm|node|python|pip|git|cd|ls|mkdir)",  # Shell commands
        ],
        description="Regex patterns for excluding non-code content"
    )
    require_code_indicators: List[str] = Field(
        default_factory=lambda: [
            r"\bclass\b",
            r"\bpublic\b",
            r"\bvoid\b",
            r"\busing\b",
            r"\bnamespace\b",
            r"\bvar\b"
        ],
        description="Patterns indicating actual C# code (at least one must match)"
    )

    # CD-04: Context extraction configuration
    context_extraction: ContextExtractionConfig = Field(
        default_factory=ContextExtractionConfig,
        description="Context extraction settings for code snippets"
    )

    # CD-03: Gist pattern detection configuration
    gist_extraction: GistPatternsConfig = Field(
        default_factory=GistPatternsConfig,
        description="Gist pattern detection and filtering settings"
    )


class FinalReviewConfig(BaseModel):
    """Final review phase configuration."""
    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(default=True, description="Enable final LLM review phase")
    provider: str = Field(default="anthropic", description="LLM provider for final review")
    model: str = Field(default="claude-3-5-sonnet-latest", description="Model for final review")
    timeout_seconds: int = Field(default=30, ge=1, description="Timeout for final review calls")
    confidence_threshold: float = Field(default=0.85, ge=0.0, le=1.0, description="Confidence threshold for intent drift rejection")
    auto_remediation_enabled: bool = Field(
        default=False,
        description="Enable automatic remediation of review issues (future feature)"
    )
    max_review_attempts: int = Field(
        default=2,
        ge=1,
        le=5,
        description="Maximum re-review attempts per file"
    )
    strict_mode: bool = Field(
        default=False,
        description="In strict mode, any unresolved issue fails the review"
    )
    fail_on_critical: bool = Field(
        default=True,
        description="Fail review if critical issues are found"
    )
    only_review_llm_fixed: bool = Field(
        default=True,
        description="Only review examples that were fixed by LLM"
    )
    enable_signature_validation: bool = Field(
        default=True,
        description="Enable API signature-based drift detection (Gate 1: semantic signatures)"
    )
    enable_family_drift_validation: bool = Field(
        default=True,
        description="Enable family-specific drift validation (Gate 2: barcode type/mode/property checks)"
    )
    reject_critical_enum_changes: bool = Field(
        default=True,
        description="Auto-reject changes to critical enum values (DecodeType, EncodeTypes, etc.)"
    )
    base_url: Optional[str] = Field(
        default=None,
        description="Base URL for final review LLM provider (if None, inherits from main LLM config)"
    )
    api_key_env_var: Optional[str] = Field(
        default=None,
        description="Env var name holding API key for final review (if None, inherits from main LLM config)"
    )


class DriftConfig(BaseModel):
    """Configuration for drift detection during LLM fix iterations."""
    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(
        default=True,
        description="Enable drift detection in compilation and runtime fix loops"
    )
    threshold: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Maximum allowed drift score (0.0=identical, 1.0=completely different)"
    )
    fail_on_exceed: bool = Field(
        default=True,
        description="Abort fix loop when drift exceeds threshold"
    )
    log_all_drift_scores: bool = Field(
        default=True,
        description="Log drift scores for all fix attempts (debug visibility)"
    )


class MarkdownWriteConfig(BaseModel):
    """
    Markdown write safety configuration.

    SAFETY: This enforces write guards to prevent accidental manual edits.
    Default is False (dry-run) to ensure operator must explicitly enable writes.
    """
    model_config = ConfigDict(extra="forbid")

    allow_markdown_write: bool = Field(
        default=False,
        description="Allow markdown file writes. Default is False for safety. Use --allow-md-write CLI flag."
    )


class TimeoutsConfig(BaseModel):
    """Timeout configuration for various operations."""
    model_config = ConfigDict(extra="forbid")

    llm_call_seconds: int = Field(default=120, ge=1, description="Timeout for LLM API calls")
    code_execution_seconds: int = Field(default=30, ge=1, description="Timeout for code execution")
    per_example_seconds: int = Field(default=300, ge=1, description="Timeout per example processing")
    per_phase_seconds: int = Field(default=1800, ge=1, description="Timeout per pipeline phase")
    hard_run_timeout_seconds: int = Field(default=2400, ge=1, description="Hard timeout for entire run")



class SubstitutionConfig(BaseModel):
    """
    Example substitution configuration.

    Phase-2 Gate B: Controls automatic substitution of failing examples
    with verified examples from the example repository.
    """
    model_config = ConfigDict(extra="forbid")

    same_context_only: bool = Field(
        default=False,
        description="Only substitute with examples from the same app_context (console, aspnet, mvc, etc.). Default False for backward compatibility."
    )


class ContextEnforcementConfig(BaseModel):
    """
    Context enforcement configuration for LLM fixes.

    Phase-2 Gate B: Prevents LLM from changing app_context type during fixes
    (e.g., console → ASP.NET, ASP.NET → console).
    """
    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(
        default=False,
        description="Reject LLM fixes that change app_context type. Default False for backward compatibility."
    )


class ContextHarnessConfig(BaseModel):
    """
    Context-specific build harness configuration.

    Phase-2 Gate B: Compiles examples in their native app context
    (ASP.NET as ASP.NET projects, not console apps).
    """
    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(
        default=False,
        description="Use context-specific project templates (ASP.NET SDK for ASP.NET code, etc.). Default False for backward compatibility."
    )


class AutoLearnConfig(BaseModel):
    """Auto-learn configuration for pattern extraction from failures."""
    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(default=False, description="Enable automatic pattern extraction after each pipeline run")
    use_llm: bool = Field(default=False, description="Use LLM for pattern extraction (vs regex-only)")
    timeout_seconds: int = Field(default=300, ge=30, le=600, description="Timeout for auto-learn subprocess")


class RetirementPolicyConfig(BaseModel):
    """Pattern retirement policy configuration."""
    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(default=False, description="Enable automatic pattern retirement")
    min_attempts: int = Field(default=10, ge=1, description="Minimum attempts before considering retirement")
    max_success_rate: float = Field(default=0.1, ge=0.0, le=1.0, description="Retire if success rate <= this threshold")
    max_age_days: int = Field(default=90, ge=1, description="Retire if older than N days")
    dry_run: bool = Field(default=True, description="Log retirements without deleting (safety mode)")


class ProviderConfig(BaseModel):
    """Configuration for a single LLM provider."""
    model_config = ConfigDict(extra="forbid")
    base_url: str
    api_key_env: Optional[str] = None
    model: str = "gpt-oss"
    fallback_to: Optional[str] = None
    timeout_seconds: int = 120
    # Ollama auto-start settings (only meaningful for ollama provider)
    auto_start: bool = True
    startup_timeout_seconds: int = 30
    auto_pull_model: bool = True
    pull_timeout_seconds: int = 600


class CircuitBreakerConfig(BaseModel):
    """Circuit breaker configuration for LLM provider health monitoring.

    Monitors primary LLM endpoint (professionalize.LLM) health across calls
    and proactively routes to fallback (Ollama) when primary is detected flaky.

    Thresholds are calibrated for LLM workloads (expensive calls, clustered failures).
    """
    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(default=True, description="Enable circuit breaker (auto-enabled when fallback configured)")
    failure_threshold: int = Field(default=3, ge=1, description="Consecutive primary failures before opening circuit")
    error_rate_threshold: float = Field(default=0.5, ge=0.0, le=1.0, description=">50% error rate in rolling window opens circuit")
    window_size: int = Field(default=10, ge=2, description="Rolling window size for error rate evaluation")
    latency_threshold_s: float = Field(default=30.0, gt=0, description="Average latency (seconds) above this opens circuit")
    recovery_timeout_s: float = Field(default=60.0, gt=0, description="Seconds in OPEN state before probing primary (HALF_OPEN)")


class ModelRoutingConfig(BaseModel):
    """Model routing and fallback configuration."""
    model_config = ConfigDict(extra="forbid")
    enabled: bool = False
    providers: Dict[str, ProviderConfig] = Field(default_factory=dict)
    model_tiers: Dict[str, str] = Field(default_factory=dict)
    routing_rules: Dict[str, str] = Field(default_factory=dict)
    fallback_enabled: bool = True
    track_cost: bool = False
    fallback_on_timeout: bool = True
    fallback_on_error: bool = True
    circuit_breaker: CircuitBreakerConfig = Field(
        default_factory=CircuitBreakerConfig,
        description="Passive circuit breaker for proactive fallback routing based on latency/error rate"
    )


class GlobalConfig(BaseModel):
    """Global configuration settings."""
    model_config = ConfigDict(extra="forbid")

    llm: LLMConfig = Field(default_factory=LLMConfig)
    limits: LimitsConfig = Field(default_factory=LimitsConfig)
    resource_detection: ResourceDetectionConfig = Field(default_factory=ResourceDetectionConfig)
    git: GitConfig = Field(default_factory=GitConfig)
    markdown_write: MarkdownWriteConfig = Field(default_factory=MarkdownWriteConfig)
    gist: GistConfig = Field(default_factory=GistConfig)
    telemetry: TelemetryConfig = Field(default_factory=TelemetryConfig)
    vector_db: VectorDBConfig = Field(default_factory=VectorDBConfig)
    backfill: BackfillConfig = Field(default_factory=BackfillConfig)
    discovery_patterns: DiscoveryPatternsConfig = Field(default_factory=DiscoveryPatternsConfig)
    final_review: FinalReviewConfig = Field(default_factory=FinalReviewConfig)
    drift: DriftConfig = Field(default_factory=DriftConfig)
    timeouts: TimeoutsConfig = Field(default_factory=TimeoutsConfig)
    substitution: SubstitutionConfig = Field(default_factory=SubstitutionConfig)
    context_enforcement: ContextEnforcementConfig = Field(default_factory=ContextEnforcementConfig)
    context_harness: ContextHarnessConfig = Field(default_factory=ContextHarnessConfig)
    auto_learn: AutoLearnConfig = Field(default_factory=AutoLearnConfig)
    pattern_retirement: RetirementPolicyConfig = Field(default_factory=RetirementPolicyConfig)
    model_routing: ModelRoutingConfig = Field(default_factory=ModelRoutingConfig)

    # Paths
    artifact_store_path: str = Field(default="./artifacts")

    # Database configuration
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)


class NuGetPackage(BaseModel):
    """NuGet package reference."""
    model_config = ConfigDict(extra="forbid")
    name: str
    version_strategy: str = Field(default="latest_stable")
    version: Optional[str] = None
    dll_name: Optional[str] = Field(default=None, description="DLL name if different from package name")


class NuGetConfig(BaseModel):
    """NuGet configuration for a family."""
    model_config = ConfigDict(extra="forbid")

    primary_package: NuGetPackage
    additional_packages: List[NuGetPackage] = Field(default_factory=list)
    target_frameworks: List[str] = Field(default_factory=lambda: ["net8.0"])


class CodeDefaults(BaseModel):
    """Default code configuration."""
    model_config = ConfigDict(extra="forbid")

    default_usings: List[str] = Field(default_factory=list)


class RuntimeValidationConfig(BaseModel):
    """Runtime validation configuration."""
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    mode: str = Field(default="strict", pattern="^(strict|lenient)$")
    timeout_seconds: int = Field(default=30, ge=1)
    required_files: List[str] = Field(default_factory=list)
    required_dirs: List[str] = Field(default_factory=list)
    file_aliases: Dict[str, List[str]] = Field(default_factory=dict)
    expected_outputs: List[str] = Field(default_factory=list)
    env: Dict[str, str] = Field(default_factory=dict)


class TestDataConfig(BaseModel):
    """Test data configuration."""
    model_config = ConfigDict(extra="forbid")

    local_path: str = ""
    download_if_missing: bool = True
    inventory_path: str = ""


class ExampleRepoConfig(BaseModel):
    """Example repository configuration."""
    model_config = ConfigDict(extra="forbid")

    url: str = ""
    examples_path: str = ""
    samples_path: str = ""
    test_data_path: str = ""
    ref: str = "main"


class CSDiscoveryConfig(BaseModel):
    """Configuration for .cs file discovery from example repos."""
    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    roots: List[str] = Field(default_factory=list, description="Root directories to scan for .cs files")
    exclude_patterns: List[str] = Field(
        default_factory=list,
        description="Regex patterns for .cs file paths to exclude (e.g. RunExamples\\.cs$)"
    )
    extraction_strategy: str = Field(
        default="exstart_exend",
        description="Extraction strategy: exstart_exend, whole_file, or run_method"
    )
    data_dir_replacements: Dict[str, str] = Field(
        default_factory=dict,
        description="Regex pattern -> replacement for data directory resolution"
    )
    strip_nunit_attributes: bool = Field(
        default=False, description="Strip NUnit [Test]/[SetUp] attributes from extracted code"
    )
    strip_base_class: bool = Field(
        default=False, description="Strip base class inheritance from extracted classes"
    )
    entry_point_pattern: str = Field(
        default="", description="Static method name to invoke (e.g. 'Run' for PDF examples)"
    )


class PipelineOverrides(BaseModel):
    """Per-family overrides for pipeline behavior (compile/runtime retry tuning)."""
    model_config = ConfigDict(extra="forbid")

    max_compile_retries: Optional[int] = Field(
        default=None, ge=1, le=10,
        description="Override global max_retries for compile-phase LLM fixes"
    )
    max_runtime_retries: Optional[int] = Field(
        default=None, ge=1, le=5,
        description="Override global max_retries for runtime-phase LLM fixes"
    )


class FamilyConfig(BaseModel):
    """Per-family configuration settings."""
    model_config = ConfigDict(extra="forbid")

    family: str = Field(..., description="Family identifier")
    display_name: str = ""
    auto_commit: bool = False
    commit_message_template: str = ""
    
    # Content discovery
    content_roots: List[str] = Field(default_factory=list)
    content_pattern: Dict[str, str] = Field(default_factory=dict)
    file_exclude_patterns: List[str] = Field(
        default_factory=list,
        description="Regex patterns for file paths to exclude from discovery"
    )

    # Build configuration
    nuget_config: Optional[NuGetConfig] = None
    code_defaults: CodeDefaults = Field(default_factory=CodeDefaults)
    
    # Validation
    runtime_validation: RuntimeValidationConfig = Field(default_factory=RuntimeValidationConfig)
    test_data: TestDataConfig = Field(default_factory=TestDataConfig)
    
    # External resources
    example_repo: ExampleRepoConfig = Field(default_factory=ExampleRepoConfig)
    gist: Optional[GistConfig] = None

    # API catalog (HEAL-05)
    api_catalog: Optional[APICatalogConfig] = None

    # Fixture resolver (self-healing runtime environment)
    fixture_resolver: Optional[FixtureResolverConfig] = None

    # CS file discovery (for repos with standalone .cs example files)
    cs_discovery: CSDiscoveryConfig = Field(default_factory=CSDiscoveryConfig)

    # Patterns and hints
    api_patterns: Dict[str, Any] = Field(default_factory=dict)
    discovery_patterns: Optional[DiscoveryPatternsConfig] = None

    # Learned patterns (auto-learn module)
    learned_patterns: Dict[str, Any] = Field(default_factory=dict)

    # Pipeline overrides (per-family compile/runtime retry tuning)
    pipeline_overrides: Optional[PipelineOverrides] = None

    def get_nuget_package_name(self) -> str:
        """Get primary NuGet package name."""
        if self.nuget_config:
            return self.nuget_config.primary_package.name
        return f"Aspose.{self.family.title()}"
    
    def get_default_usings(self) -> List[str]:
        """Get default using statements."""
        return self.code_defaults.default_usings or [f"Aspose.{self.family.title()}"]


class ConfigurationManager:
    """
    Manages configuration for the Example Reviewer Pipeline.
    Supports loading global config and family-specific overrides.
    """
    
    def __init__(
        self, 
        config_dir: Optional[Path] = None,
        global_config_path: Optional[Path] = None,
    ):
        """
        Initialize configuration manager.
        
        Args:
            config_dir: Directory containing family configs
            global_config_path: Path to global.json
        """
        self.config_dir = Path(config_dir) if config_dir else Path("config/families")
        self.global_config_path = Path(global_config_path) if global_config_path else self.config_dir.parent / "global.json"
        self._global_config: Optional[GlobalConfig] = None
        self._family_configs: Dict[str, FamilyConfig] = {}
    
    def load_global_config(self) -> GlobalConfig:
        """Load or return cached global configuration."""
        if self._global_config is not None:
            return self._global_config
        
        data = {}
        if self.global_config_path.exists():
            with open(self.global_config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        
        # Parse and apply environment overrides
        config = self._parse_global_config(data)
        config = self._apply_env_overrides(config)
        
        self._global_config = config
        return config
    
    def _parse_global_config(self, data: Dict[str, Any]) -> GlobalConfig:
        """Parse global config from JSON data."""
        parsed = {}
        
        if 'llm' in data:
            parsed['llm'] = LLMConfig(**data['llm'])
        
        if 'limits' in data:
            parsed['limits'] = LimitsConfig(**data['limits'])
        
        if 'resource_detection' in data:
            parsed['resource_detection'] = ResourceDetectionConfig(**data['resource_detection'])
        
        if 'git' in data:
            parsed['git'] = GitConfig(**data['git'])

        if 'markdown_write' in data:
            parsed['markdown_write'] = MarkdownWriteConfig(**data['markdown_write'])

        if 'gist' in data:
            gist_data = data['gist'].copy()
            if 'auth' in gist_data:
                gist_data['auth_method'] = gist_data['auth'].get('method', 'none')
                gist_data['pat_env_var'] = gist_data['auth'].get('pat_env_var', 'GIST_PAT')
                del gist_data['auth']
            parsed['gist'] = GistConfig(**gist_data)
        
        if 'telemetry' in data:
            parsed['telemetry'] = TelemetryConfig(**data['telemetry'])

        if 'vector_db' in data:
            parsed['vector_db'] = VectorDBConfig(**data['vector_db'])

        if 'backfill' in data:
            parsed['backfill'] = BackfillConfig(**data['backfill'])

        if 'discovery_patterns' in data:
            parsed['discovery_patterns'] = DiscoveryPatternsConfig(**data['discovery_patterns'])

        if 'final_review' in data:
            parsed['final_review'] = FinalReviewConfig(**data['final_review'])

        if 'drift' in data:
            parsed['drift'] = DriftConfig(**data['drift'])

        if 'timeouts' in data:
            parsed['timeouts'] = TimeoutsConfig(**data['timeouts'])

        if 'substitution' in data:
            parsed['substitution'] = SubstitutionConfig(**data['substitution'])

        if 'context_enforcement' in data:
            parsed['context_enforcement'] = ContextEnforcementConfig(**data['context_enforcement'])

        if 'context_harness' in data:
            parsed['context_harness'] = ContextHarnessConfig(**data['context_harness'])

        if 'auto_learn' in data:
            parsed['auto_learn'] = AutoLearnConfig(**data['auto_learn'])

        if 'pattern_retirement' in data:
            parsed['pattern_retirement'] = RetirementPolicyConfig(**data['pattern_retirement'])

        if 'model_routing' in data:
            routing_data = data['model_routing'].copy()
            if 'providers' in routing_data:
                routing_data['providers'] = {
                    k: ProviderConfig(**v) for k, v in routing_data['providers'].items()
                }
            parsed['model_routing'] = ModelRoutingConfig(**routing_data)

        if 'artifact_store_path' in data:
            parsed['artifact_store_path'] = data['artifact_store_path']

        # Database configuration
        if 'database' in data:
            parsed['database'] = DatabaseConfig(**data['database'])

        return GlobalConfig(**parsed)
    
    def _apply_env_overrides(self, config: GlobalConfig) -> GlobalConfig:
        """Apply environment variable overrides to config."""
        # Create mutable copies
        llm = config.llm.model_copy()
        git = config.git.model_copy()

        # LLM overrides - resolve coherent provider profiles
        env_provider = os.getenv('LLM_PROVIDER')
        if env_provider:
            if env_provider != llm.provider:
                logger.warning(
                    f"LLM_PROVIDER env var '{env_provider}' overrides config "
                    f"provider '{llm.provider}' (base_url={llm.base_url}, model={llm.model}). "
                    f"Unset LLM_PROVIDER to use config values."
                )
            llm.provider = env_provider
            # Look up full provider profile from model_routing
            provider_profile = config.model_routing.providers.get(env_provider)
            if provider_profile:
                llm.base_url = provider_profile.base_url
                llm.api_key_env_var = provider_profile.api_key_env
                llm.model = provider_profile.model
                logger.info(f"Resolved provider profile '{env_provider}': "
                           f"base_url={provider_profile.base_url}, model={provider_profile.model}")
            elif env_provider == "ollama":
                # Hardcoded fallback for ollama even without routing config
                llm.base_url = "http://localhost:11434/v1"
                llm.api_key_env_var = None
                llm.model = os.getenv('LLM_MODEL') or "qwen2.5-coder:7b"

        # Explicit env overrides still take precedence over profile
        if os.getenv('LLM_MODEL'):
            llm.model = os.getenv('LLM_MODEL')
        if os.getenv('LLM_BASE_URL'):
            llm.base_url = os.getenv('LLM_BASE_URL')
        if os.getenv('LLM_API_KEY_ENV_VAR'):
            llm.api_key_env_var = os.getenv('LLM_API_KEY_ENV_VAR')
        
        # Git overrides
        if os.getenv('GIT_ENABLED'):
            git.enabled = os.getenv('GIT_ENABLED', '').lower() == 'true'

        # Database overrides
        database = config.database.model_copy()
        if os.getenv('EXAMPLE_REVIEWER_DATABASE_PATH'):
            database.path = os.getenv('EXAMPLE_REVIEWER_DATABASE_PATH')
        if os.getenv('EXAMPLE_REVIEWER_PROD_DB_PATH'):
            database.production_path = os.getenv('EXAMPLE_REVIEWER_PROD_DB_PATH')

        return config.model_copy(update={'llm': llm, 'git': git, 'database': database})
    
    def load_family_config(self, family: str) -> FamilyConfig:
        """Load family-specific configuration."""
        if family in self._family_configs:
            return self._family_configs[family]
        
        family_path = self.config_dir / f"{family}.json"
        
        if not family_path.exists():
            raise FileNotFoundError(f"Family config not found: {family_path}")
        
        with open(family_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        config = self._parse_family_config(data, family)
        self._family_configs[family] = config
        return config
    
    def _parse_family_config(self, data: Dict[str, Any], family: str) -> FamilyConfig:
        """Parse family config from JSON data."""
        parsed = {'family': family}
        
        # Simple fields
        for key in ['display_name', 'auto_commit', 'commit_message_template', 
                    'content_roots', 'content_pattern',
                    'api_patterns']:
            if key in data:
                parsed[key] = data[key]
        
        # NuGet config
        if 'nuget_config' in data:
            nc = data['nuget_config']
            parsed['nuget_config'] = NuGetConfig(
                primary_package=NuGetPackage(**nc.get('primary_package', {'name': f'Aspose.{family.title()}'})),
                additional_packages=[NuGetPackage(**p) for p in nc.get('additional_packages', [])],
                target_frameworks=nc.get('target_frameworks', ['net8.0']),
            )
        
        # Code defaults
        if 'code_defaults' in data:
            parsed['code_defaults'] = CodeDefaults(**data['code_defaults'])
        
        # Runtime validation
        if 'runtime_validation' in data:
            parsed['runtime_validation'] = RuntimeValidationConfig(**data['runtime_validation'])
        
        # Test data
        if 'test_data' in data:
            parsed['test_data'] = TestDataConfig(**data['test_data'])
        else:
            parsed['test_data'] = TestDataConfig(local_path=f"test-data/{family}")
        
        # Example repo
        if 'example_repo' in data:
            parsed['example_repo'] = ExampleRepoConfig(**data['example_repo'])
        
        # Discovery patterns
        if 'discovery_patterns' in data:
            parsed['discovery_patterns'] = DiscoveryPatternsConfig(**data['discovery_patterns'])

        # Gist config
        if 'gist' in data:
            gist_data = data['gist'].copy()
            if 'auth' in gist_data:
                gist_data['auth_method'] = gist_data['auth'].get('method', 'none')
                gist_data['pat_env_var'] = gist_data['auth'].get('pat_env_var', 'GIST_PAT')
                del gist_data['auth']
            parsed['gist'] = GistConfig(**gist_data)

        # API catalog config (HEAL-05)
        if 'api_catalog' in data:
            parsed['api_catalog'] = APICatalogConfig(**data['api_catalog'])

        # Fixture resolver config
        if 'fixture_resolver' in data:
            parsed['fixture_resolver'] = FixtureResolverConfig(**data['fixture_resolver'])

        # CS file discovery config
        if 'cs_discovery' in data:
            parsed['cs_discovery'] = CSDiscoveryConfig(**data['cs_discovery'])

        # Learned patterns config
        if 'learned_patterns' in data:
            parsed['learned_patterns'] = data['learned_patterns']

        # File exclude patterns
        if 'file_exclude_patterns' in data:
            parsed['file_exclude_patterns'] = data['file_exclude_patterns']

        # Pipeline overrides (per-family compile/runtime retry tuning)
        if 'pipeline_overrides' in data:
            parsed['pipeline_overrides'] = PipelineOverrides(**data['pipeline_overrides'])

        return FamilyConfig(**parsed)
    
    def list_families(self) -> List[str]:
        """List all available family configurations."""
        if not self.config_dir.exists():
            return []

        families = []
        # Sort glob results deterministically (case-normalized for Windows compatibility)
        for path in sorted(self.config_dir.glob("*.json"), key=lambda p: str(p).lower()):
            if path.name != "global.json":
                families.append(path.stem)

        # Sort family names deterministically (case-normalized)
        return sorted(families, key=lambda f: f.lower())
    
    def get_effective_config(
        self,
        family: str,
        cli_overrides: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get merged global + family + CLI overrides config as dictionary.

        Args:
            family: Family identifier
            cli_overrides: CLI overrides dictionary (e.g., {'llm': {'seed': 12345}})

        Returns:
            Effective configuration dictionary with global, family, and cli_overrides sections
        """
        global_cfg = self.load_global_config()
        family_cfg = self.load_family_config(family)

        effective = {
            'global': global_cfg.model_dump(),
            'family': family_cfg.model_dump(),
        }

        if cli_overrides:
            effective['cli_overrides'] = cli_overrides

        return effective

    def compute_config_hash(
        self,
        family: str,
        cli_overrides: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Compute SHA256 hash of effective configuration.

        Args:
            family: Family identifier
            cli_overrides: CLI overrides dictionary

        Returns:
            SHA256 hash of effective config (hex string)
        """
        effective_config = self.get_effective_config(family, cli_overrides)

        # Convert to deterministic JSON (sorted keys)
        config_json = json.dumps(effective_config, sort_keys=True, indent=None)

        # Compute SHA256
        hash_obj = hashlib.sha256(config_json.encode('utf-8'))
        return hash_obj.hexdigest()
    
    def save_family_config(self, family: str, config: FamilyConfig) -> None:
        """Save family configuration to disk."""
        family_path = self.config_dir / f"{family}.json"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        with open(family_path, 'w', encoding='utf-8') as f:
            json.dump(config.model_dump(exclude_none=True), f, indent=2)
        
        # Update cache
        self._family_configs[family] = config
    
    def save_global_config(self, config: GlobalConfig) -> None:
        """Save global configuration to disk."""
        self.global_config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.global_config_path, 'w', encoding='utf-8') as f:
            json.dump(config.model_dump(exclude_none=True), f, indent=2)
        
        # Update cache
        self._global_config = config
