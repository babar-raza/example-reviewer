"""
Configuration system for Example Reviewer Pipeline.
Uses Pydantic for validation and supports multi-family configurations.
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class LLMConfig(BaseModel):
    """LLM provider configuration."""
    provider: str = Field(default="openai", description="LLM provider (openai, ollama, azure)")
    model: str = Field(default="gpt-4o-mini", description="Model name")
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_retries: int = Field(default=3, ge=1)
    retry_backoff_seconds: int = Field(default=5, ge=1)
    api_key_env_var: str = Field(default="OPENAI_API_KEY")
    base_url: Optional[str] = Field(default=None, description="Custom API base URL")
    timeout_seconds: int = Field(default=120)


class LimitsConfig(BaseModel):
    """Resource limit configuration."""
    cpu_max_percent: int = Field(default=90, ge=0, le=100)
    ram_max_mb: int = Field(default=0, description="0 = no limit")
    vram_max_mb: int = Field(default=0, description="0 = no limit")


class ResourceDetectionConfig(BaseModel):
    """Resource detection settings."""
    auto_detect_vram: bool = True
    prefer_gpu_when_available: bool = True
    fallback_to_cpu: bool = True
    telemetry_log_resource_decisions: bool = True


class GitConfig(BaseModel):
    """Git integration configuration."""
    enabled: bool = True
    commit_message_template: str = "chore({family}): verify {count} examples"
    commit_description_template: str = "Automated verification of {count} examples.\n\nRunId: {run_id}\nFamily: {family}"
    only_commit_touched_files: bool = True


class GistConfig(BaseModel):
    """GitHub Gist configuration."""
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


class TelemetryConfig(BaseModel):
    """Telemetry configuration."""
    internal_enabled: bool = True
    local_telemetry_enabled: bool = True
    local_telemetry_path: str = "./local-telemetry"
    http_api_enabled: bool = True
    http_api_url: str = "http://localhost:8765"
    http_api_timeout_seconds: int = 10
    http_api_retry_count: int = 3


class VectorDBConfig(BaseModel):
    """Vector database configuration for similarity search."""
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


class BackfillConfig(BaseModel):
    """Backfill configuration for auto-downloading missing data."""
    auto_enabled: bool = Field(default=False, description="Enable automatic backfill")
    targets: List[str] = Field(
        default_factory=lambda: ["test_data", "api_reference", "examples", "gist_source_code"],
        description="Backfill targets (test_data, api_reference, examples, gist_source_code)"
    )
    github_timeout_seconds: int = Field(default=120, ge=10)
    retry_on_failure: bool = Field(default=True)


class ContextExtractionConfig(BaseModel):
    """Configuration for context extraction around code snippets."""
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
        default=5,
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
            r"\bnamespace\b"
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
    enabled: bool = Field(default=True, description="Enable final LLM review phase")
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


class DriftConfig(BaseModel):
    """Configuration for drift detection during LLM fix iterations."""
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


class GlobalConfig(BaseModel):
    """Global configuration settings."""
    llm: LLMConfig = Field(default_factory=LLMConfig)
    limits: LimitsConfig = Field(default_factory=LimitsConfig)
    resource_detection: ResourceDetectionConfig = Field(default_factory=ResourceDetectionConfig)
    git: GitConfig = Field(default_factory=GitConfig)
    gist: GistConfig = Field(default_factory=GistConfig)
    telemetry: TelemetryConfig = Field(default_factory=TelemetryConfig)
    vector_db: VectorDBConfig = Field(default_factory=VectorDBConfig)
    backfill: BackfillConfig = Field(default_factory=BackfillConfig)
    discovery_patterns: DiscoveryPatternsConfig = Field(default_factory=DiscoveryPatternsConfig)
    final_review: FinalReviewConfig = Field(default_factory=FinalReviewConfig)
    drift: DriftConfig = Field(default_factory=DriftConfig)

    # Paths
    artifact_store_path: str = Field(default="./artifacts")
    database_path: str = Field(default="./data/example_reviewer.db")


class NuGetPackage(BaseModel):
    """NuGet package reference."""
    name: str
    version_strategy: str = Field(default="latest_stable")
    version: Optional[str] = None


class NuGetConfig(BaseModel):
    """NuGet configuration for a family."""
    primary_package: NuGetPackage
    additional_packages: List[NuGetPackage] = Field(default_factory=list)
    target_frameworks: List[str] = Field(default_factory=lambda: ["net8.0"])


class CodeDefaults(BaseModel):
    """Default code configuration."""
    default_usings: List[str] = Field(default_factory=list)


class RuntimeValidationConfig(BaseModel):
    """Runtime validation configuration."""
    enabled: bool = True
    mode: str = Field(default="strict", pattern="^(strict|lenient)$")
    timeout_seconds: int = Field(default=30, ge=1)
    required_files: List[str] = Field(default_factory=list)
    file_aliases: Dict[str, List[str]] = Field(default_factory=dict)
    expected_outputs: List[str] = Field(default_factory=list)
    env: Dict[str, str] = Field(default_factory=dict)


class TestDataConfig(BaseModel):
    """Test data configuration."""
    local_path: str = ""
    download_if_missing: bool = True


class ExampleRepoConfig(BaseModel):
    """Example repository configuration."""
    url: str = ""
    examples_path: str = ""
    test_data_path: str = ""
    ref: str = "main"


class ApiReferenceConfig(BaseModel):
    """API reference configuration."""
    sources: List[str] = Field(default_factory=list)
    cache_path: str = ""


class FamilyConfig(BaseModel):
    """Per-family configuration settings."""
    family: str = Field(..., description="Family identifier")
    display_name: str = ""
    auto_commit: bool = False
    commit_message_template: str = ""
    
    # Content discovery
    content_roots: List[str] = Field(default_factory=list)
    content_pattern: Dict[str, str] = Field(default_factory=dict)
    
    # Build configuration
    nuget_config: Optional[NuGetConfig] = None
    code_defaults: CodeDefaults = Field(default_factory=CodeDefaults)
    
    # Validation
    runtime_validation: RuntimeValidationConfig = Field(default_factory=RuntimeValidationConfig)
    test_data: TestDataConfig = Field(default_factory=TestDataConfig)
    
    # External resources
    example_repo: ExampleRepoConfig = Field(default_factory=ExampleRepoConfig)
    api_reference: ApiReferenceConfig = Field(default_factory=ApiReferenceConfig)
    
    # Patterns and hints
    patterns: List[Dict[str, Any]] = Field(default_factory=list)
    api_patterns: Dict[str, Any] = Field(default_factory=dict)
    non_existent_apis: List[str] = Field(default_factory=list)
    discovery_patterns: Optional[DiscoveryPatternsConfig] = None

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

        if 'artifact_store_path' in data:
            parsed['artifact_store_path'] = data['artifact_store_path']

        if 'database_path' in data:
            parsed['database_path'] = data['database_path']

        return GlobalConfig(**parsed)
    
    def _apply_env_overrides(self, config: GlobalConfig) -> GlobalConfig:
        """Apply environment variable overrides to config."""
        # Create mutable copies
        llm = config.llm.model_copy()
        git = config.git.model_copy()
        
        # LLM overrides
        if os.getenv('LLM_PROVIDER'):
            llm.provider = os.getenv('LLM_PROVIDER')
        if os.getenv('LLM_MODEL'):
            llm.model = os.getenv('LLM_MODEL')
        if os.getenv('LLM_BASE_URL'):
            llm.base_url = os.getenv('LLM_BASE_URL')
        if os.getenv('LLM_API_KEY_ENV_VAR'):
            llm.api_key_env_var = os.getenv('LLM_API_KEY_ENV_VAR')
        
        # Git overrides
        if os.getenv('GIT_ENABLED'):
            git.enabled = os.getenv('GIT_ENABLED', '').lower() == 'true'
        
        return config.model_copy(update={'llm': llm, 'git': git})
    
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
                    'content_roots', 'content_pattern', 'patterns', 
                    'api_patterns', 'non_existent_apis']:
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
        
        # API reference
        if 'api_reference' in data:
            parsed['api_reference'] = ApiReferenceConfig(**data['api_reference'])

        # Discovery patterns
        if 'discovery_patterns' in data:
            parsed['discovery_patterns'] = DiscoveryPatternsConfig(**data['discovery_patterns'])

        return FamilyConfig(**parsed)
    
    def list_families(self) -> List[str]:
        """List all available family configurations."""
        if not self.config_dir.exists():
            return []
        
        families = []
        for path in self.config_dir.glob("*.json"):
            if path.name != "global.json":
                families.append(path.stem)
        
        return sorted(families)
    
    def get_effective_config(self, family: str) -> Dict[str, Any]:
        """Get merged global + family config as dictionary."""
        global_cfg = self.load_global_config()
        family_cfg = self.load_family_config(family)
        
        return {
            'global': global_cfg.model_dump(),
            'family': family_cfg.model_dump(),
        }
    
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
