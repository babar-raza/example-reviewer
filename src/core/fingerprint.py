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
from datetime import datetime
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
        self.timestamp = timestamp or datetime.utcnow()
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
            llm_capabilities = {
                'provider': global_config.llm.provider,
                'model': global_config.llm.model,
                'temperature': global_config.llm.temperature,
                'seed_supported': True,  # Will be updated if capability detection runs
                'timeout_supported': True,
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
        Convert fingerprint to dictionary.

        Returns:
            Dictionary representation suitable for JSON serialization
        """
        return {
            'run_id': self.run_id,
            'timestamp_utc': self.timestamp.isoformat() if self.timestamp else None,
            'config_hash': self.config_hash,
            'selection_hash': self.selection_hash,
            'vector_db_startup_decision': self.vector_db_startup_decision,
            'drift_enabled': self.drift_enabled,
            'llm_provider_capabilities': self.llm_provider_capabilities,
            'llm_seed': self.llm_seed,
            'deterministic_mode': self.deterministic_mode,
            'environment': {
                'python_version': self.python_version,
                'platform': self.platform_info,
                'git_commit_hash': self.git_commit_hash,
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

        Args:
            data: Dictionary with fingerprint data

        Returns:
            RunFingerprint instance
        """
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
