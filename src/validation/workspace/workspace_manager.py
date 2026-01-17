"""Minimal workspace manager for legacy runtime tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict


class WorkspaceManager:
    """Stub workspace manager for test compatibility."""

    def __init__(self, workspaces_dir: Path, family_config: Dict[str, Any]):
        self.workspaces_dir = Path(workspaces_dir)
        self.family = family_config.get("family", "default")
        self.validator_dir = self.workspaces_dir / self.family / "validator"

    def setup_workspace(self) -> None:
        self.validator_dir.mkdir(parents=True, exist_ok=True)

    def compile_code(self, code: str) -> Dict[str, Any]:
        return {"success": False, "errors": ["Compilation not implemented"]}

    def execute_code(self, code: str, exec_params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "success": False,
            "exit_code": 1,
            "stdout": "",
            "stderr": "Execution not implemented",
        }
