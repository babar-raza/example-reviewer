"""
Configuration system for Example Reviewer Pipeline.
Uses Pydantic for validation and supports multi-family configurations.
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
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
    commit_message_template: str = "Verify examples: {family} ({count} files)"
    commit_description_template: str = "Updated verified examples. RunId={run_id}"
    only_commit_touched_files: bool = True


class GistConfig(BaseModel):
    """GitHub Gist configuration."""
    enabled: bool = True
    target_account: str = ""
    auth_method: str = Field(default="none", pattern="^(pat|oauth|none)$")
    pat_env_var: str = "GIST_PAT"


class TelemetryConfig(BaseModel):
    """Telemetry configuration."""
    internal_enabled: bool = True
    local_telemetry_enabled: bool = True
    local_telemetry_path: str = "./local-telemetry"


class GlobalConfig(BaseModel):
    """Global configuration settings."""
    llm: LLMConfig = Field(default_factory=LLMConfig)
    limits: LimitsConfig = Field(default_factory=LimitsConfig)
    resource_detection: ResourceDetectionConfig = Field(default_factory=ResourceDetectionConfig)
    git: GitConfig = Field(default_factory=GitConfig)
    gist: GistConfig = Field(default_factory=GistConfig)
    telemetry: TelemetryConfig = Field(default_factory=TelemetryConfig)
    
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
