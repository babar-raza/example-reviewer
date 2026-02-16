"""
Run fingerprint capture for determinism tracking.

Captures all environmental and configuration factors that affect run determinism:
- Configuration hash
- Selection hash (deterministic set of examples processed)
- Vector DB and drift detection decisions
- LLM provider capabilities
- Environment versions and platform info
- Git commit hash
"""

import json
import os
import sys
import platform
import subprocess
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any


class RunFingerprint:
    """
    Captures complete run fingerprint for determinism verification.

    Fields align with Plan v2.1 Section B (Run Fingerprint Fields):
    - run_id: Unique run identifier
    - config_hash: SHA256 of effective config
    - selection_hash: SHA256 of sorted example_keys
    - vector_db_startup_decision: Startup decision for VectorDB
    - drift_enabled: Whether drift detection was enabled
    - llm_provider_capabilities: Detected capabilities (seed support, etc.)
    - llm_seed: Seed value if configured
    - deterministic_mode: Whether deterministic mode was enabled
    - timestamp: When fingerprint was captured
    - python_version: Python interpreter version
    - platform: OS and architecture
    - git_commit_hash: Current git commit (if available)
    """

    def __init__(
        self,
        run_id: str,
        config_hash: str,
        selection_hash: Optional[str] = None,
        vector_db_startup_decision: Optional[Dict[str, Any]] = None,
        drift_enabled: bool = False,
        llm_provider_capabilities: Optional[Dict[str, Any]] = None,
        llm_seed: Optional[int] = None,
        deterministic_mode: bool = False,
        timestamp: Optional[datetime] = None,
        python_version: Optional[str] = None,
        platform_info: Optional[str] = None,
        git_commit_hash: Optional[str] = None,
    ):
        """
        Initialize run fingerprint.

        Args:
            run_id: Unique run identifier
            config_hash: SHA256 hash of effective configuration
            selection_hash: SHA256 hash of sorted example_keys
            vector_db_startup_decision: VectorDB startup decision metadata
            drift_enabled: Whether drift detection was enabled
            llm_provider_capabilities: LLM capabilities (seed_supported, etc.)
            llm_seed: Random seed if configured
            deterministic_mode: Whether deterministic mode was enabled
            timestamp: Fingerprint capture timestamp
            python_version: Python version string
            platform_info: Platform information string
            git_commit_hash: Git commit hash if available
        """
        self.run_id = run_id
        self.config_hash = config_hash
        self.selection_hash = selection_hash or ""
        self.vector_db_startup_decision = vector_db_startup_decision or {}
        self.drift_enabled = drift_enabled
        self.llm_provider_capabilities = llm_provider_capabilities or {}
        self.llm_seed = llm_seed
        self.deterministic_mode = deterministic_mode
        self.timestamp = timestamp or datetime.now(timezone.utc)
        self.python_version = python_version or self._get_python_version()
        self.platform_info = platform_info or self._get_platform_info()
        self.git_commit_hash = git_commit_hash or self._get_git_commit_hash()

    @staticmethod
    def _get_python_version() -> str:
        """Get Python version string."""
        return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    @staticmethod
    def _get_platform_info() -> str:
        """Get platform information."""
        return f"{platform.system()} {platform.release()} ({platform.machine()})"

    @staticmethod
    def _get_git_commit_hash() -> Optional[str]:
        """
        Get current git commit hash.

        Returns:
            Git commit hash (short form) or None if not in a git repo
        """
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None

    @classmethod
    def capture_fingerprint(cls, orchestrator: 'PipelineOrchestrator') -> 'RunFingerprint':
        """
        Capture run fingerprint from orchestrator state.

        Args:
            orchestrator: PipelineOrchestrator instance with initialized config and services

        Returns:
            RunFingerprint with all captured metadata
        """
        from ..pipeline.orchestrator import PipelineOrchestrator

        # Get latest run_id
        # Note: This assumes run_id is tracked in orchestrator or we capture it from DB
        # For now, we'll generate a fingerprint without run_id and let caller set it

        # Get global config
        global_config = orchestrator.config_manager.load_global_config()

        # Compute config hash (we'll need to know the family)
        # This will be set by caller
        config_hash = "unknown"

        # Get vector DB startup decision
        vector_db_decision = orchestrator._vector_db_startup_decision
        drift_enabled = orchestrator._drift_enabled

        # Get LLM capabilities (if LLM service initialized)
        llm_capabilities = {}
        if orchestrator._llm_service:
            # Get detected capabilities from LLM service
            caps = orchestrator._llm_service.get_provider_capabilities()
            llm_capabilities = {
                'provider': global_config.llm.provider,
                'model': global_config.llm.model,
                'temperature': global_config.llm.temperature,
                'seed_supported': caps.seed_supported,
                'timeout_supported': caps.timeout_supported,
                'model_hash': caps.model_hash,
                'detected_at': caps.detected_at,
            }

        # LLM seed and deterministic mode
        llm_seed = global_config.llm.seed
        deterministic_mode = global_config.llm.deterministic_mode

        return cls(
            run_id="",  # Will be set by caller
            config_hash=config_hash,  # Will be set by caller
            selection_hash=None,  # Will be set after example selection
            vector_db_startup_decision=vector_db_decision,
            drift_enabled=drift_enabled,
            llm_provider_capabilities=llm_capabilities,
            llm_seed=llm_seed,
            deterministic_mode=deterministic_mode,
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert fingerprint to dictionary matching Plan v2.1 Section B format (lines 60-107).

        Returns:
            Dictionary representation with all required nested sections
        """
        # Extract values from llm_provider_capabilities
        llm_caps = self.llm_provider_capabilities or {}

        # Parse platform_info for OS details
        platform_parts = self.platform_info.split() if self.platform_info else ['Unknown']
        os_name = platform_parts[0]
        os_version = ' '.join(platform_parts[1:]) if len(platform_parts) > 1 else 'Unknown'

        return {
            'run_id': self.run_id,
            'timestamp_utc': self.timestamp.isoformat() if self.timestamp else None,
            'config_hash': self.config_hash,

            # LLM section (lines 65-78)
            'llm': {
                'provider': llm_caps.get('provider', 'unknown'),
                'base_url': llm_caps.get('base_url'),
                'model': llm_caps.get('model', 'unknown'),
                'model_hash': llm_caps.get('model_hash'),
                'temperature': llm_caps.get('temperature', 0.0),
                'seed': self.llm_seed,
                'timeout_seconds': llm_caps.get('timeout_seconds', 120),
                'deterministic_mode': self.deterministic_mode,
                'provider_capabilities': {
                    'seed_supported': llm_caps.get('seed_supported', True),
                    'timeout_supported': llm_caps.get('timeout_supported', True),
                },
            },

            # Final review section (lines 79-84)
            'final_review': {
                'enabled': llm_caps.get('final_review_enabled', True),
                'provider': llm_caps.get('final_review_provider', 'anthropic'),
                'model': llm_caps.get('final_review_model', 'claude-3-5-sonnet-latest'),
                'timeout_seconds': llm_caps.get('final_review_timeout', 30),
            },

            # Vector DB section (lines 85-92)
            'vector_db': {
                'enabled': self.drift_enabled,
                'provider': llm_caps.get('vector_db_provider', 'chromadb'),
                'embedding_model': llm_caps.get('embedding_model', 'all-MiniLM-L6-v2'),
                'embedding_model_version': llm_caps.get('embedding_model_version'),
                'device': llm_caps.get('embedding_device', 'cpu'),
                'drift_tolerance': llm_caps.get('drift_tolerance', 0.02),
            },

            # Environment section (lines 93-99)
            'environment': {
                'os': os_name,
                'os_version': os_version,
                'python_version': self.python_version,
                'dotnet_version': llm_caps.get('dotnet_version'),
                'git_commit': self.git_commit_hash,
            },

            # Content snapshot section (lines 100-106)
            'content_snapshot': {
                'family': llm_caps.get('family', 'unknown'),
                'total_examples_selected': llm_caps.get('total_examples_selected', 0),
                'content_hash': llm_caps.get('content_hash'),
                'selection_hash': self.selection_hash or "",
            },

            # Additional runtime state (for backward compatibility and debugging)
            '_runtime_state': {
                'vector_db_startup_decision': self.vector_db_startup_decision,
                'drift_enabled': self.drift_enabled,
            },
        }

    def to_json(self) -> str:
        """
        Convert fingerprint to JSON string.

        Returns:
            JSON-formatted string
        """
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)

    def save_to_db(self, db: 'Database', run_id: str) -> None:
        """
        Save fingerprint to database.

        Args:
            db: Database instance
            run_id: Run identifier
        """
        # Ensure run_id is set
        if not self.run_id:
            self.run_id = run_id

        # Database save is done via database.save_run_fingerprint()
        # (to be implemented in database.py)
        db.save_run_fingerprint(self)

    def save_to_file(self, path: Path) -> None:
        """
        Save fingerprint to JSON file.

        Args:
            path: Output file path
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'w', encoding='utf-8') as f:
            f.write(self.to_json())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RunFingerprint':
        """
        Create fingerprint from dictionary.

        Handles both Plan v2.1 nested format and legacy flat format.

        Args:
            data: Dictionary with fingerprint data

        Returns:
            RunFingerprint instance
        """
        # Check if this is Plan v2.1 format (has nested sections)
        if 'llm' in data and isinstance(data['llm'], dict):
            # Plan v2.1 format
            llm_section = data.get('llm', {})
            env_section = data.get('environment', {})
            content_section = data.get('content_snapshot', {})
            final_review_section = data.get('final_review', {})
            vector_db_section = data.get('vector_db', {})
            runtime_state = data.get('_runtime_state', {})

            # Reconstruct llm_provider_capabilities from nested sections
            llm_caps = {
                'provider': llm_section.get('provider'),
                'base_url': llm_section.get('base_url'),
                'model': llm_section.get('model'),
                'model_hash': llm_section.get('model_hash'),
                'temperature': llm_section.get('temperature', 0.0),
                'timeout_seconds': llm_section.get('timeout_seconds'),
                'seed_supported': llm_section.get('provider_capabilities', {}).get('seed_supported'),
                'timeout_supported': llm_section.get('provider_capabilities', {}).get('timeout_supported'),
                'final_review_enabled': final_review_section.get('enabled'),
                'final_review_provider': final_review_section.get('provider'),
                'final_review_model': final_review_section.get('model'),
                'final_review_timeout': final_review_section.get('timeout_seconds'),
                'vector_db_provider': vector_db_section.get('provider'),
                'embedding_model': vector_db_section.get('embedding_model'),
                'embedding_model_version': vector_db_section.get('embedding_model_version'),
                'embedding_device': vector_db_section.get('device'),
                'drift_tolerance': vector_db_section.get('drift_tolerance'),
                'dotnet_version': env_section.get('dotnet_version'),
                'family': content_section.get('family'),
                'total_examples_selected': content_section.get('total_examples_selected'),
                'content_hash': content_section.get('content_hash'),
            }

            # Reconstruct platform_info from env_section
            platform_info = f"{env_section.get('os', 'Unknown')} {env_section.get('os_version', '')}"

            return cls(
                run_id=data.get('run_id', ''),
                config_hash=data.get('config_hash', ''),
                selection_hash=content_section.get('selection_hash'),
                vector_db_startup_decision=runtime_state.get('vector_db_startup_decision'),
                drift_enabled=vector_db_section.get('enabled', False),
                llm_provider_capabilities=llm_caps,
                llm_seed=llm_section.get('seed'),
                deterministic_mode=llm_section.get('deterministic_mode', False),
                timestamp=datetime.fromisoformat(data['timestamp_utc']) if data.get('timestamp_utc') else None,
                python_version=env_section.get('python_version'),
                platform_info=platform_info.strip(),
                git_commit_hash=env_section.get('git_commit'),
            )
        else:
            # Legacy flat format
            env = data.get('environment', {})

            return cls(
                run_id=data.get('run_id', ''),
                config_hash=data.get('config_hash', ''),
                selection_hash=data.get('selection_hash'),
                vector_db_startup_decision=data.get('vector_db_startup_decision'),
                drift_enabled=data.get('drift_enabled', False),
                llm_provider_capabilities=data.get('llm_provider_capabilities'),
                llm_seed=data.get('llm_seed'),
                deterministic_mode=data.get('deterministic_mode', False),
                timestamp=datetime.fromisoformat(data['timestamp_utc']) if data.get('timestamp_utc') else None,
                python_version=env.get('python_version'),
                platform_info=env.get('platform'),
                git_commit_hash=env.get('git_commit_hash'),
            )

    @classmethod
    def from_json(cls, json_str: str) -> 'RunFingerprint':
        """
        Create fingerprint from JSON string.

        Args:
            json_str: JSON-formatted string

        Returns:
            RunFingerprint instance
        """
        data = json.loads(json_str)
        return cls.from_dict(data)

    @classmethod
    def load_from_file(cls, path: Path) -> 'RunFingerprint':
        """
        Load fingerprint from JSON file.

        Args:
            path: Input file path

        Returns:
            RunFingerprint instance
        """
        with open(path, 'r', encoding='utf-8') as f:
            return cls.from_json(f.read())
