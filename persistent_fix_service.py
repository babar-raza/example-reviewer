"""Minimal persistent fix service for context inference tests."""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

from code_pattern_detector import CodePattern, CodePatternDetector


class PersistentFixService:
    """Compatibility service exposing _needs_context with pattern detection."""

    def __init__(
        self,
        workspace: Any,
        ollama: Any,
        db: Any,
        telemetry: Any,
        family_config: Optional[Dict[str, Any]] = None,
    ):
        self.workspace = workspace
        self.ollama = ollama
        self.db = db
        self.telemetry = telemetry
        self.family_config = family_config or {}
        self.pattern_detector = CodePatternDetector()

    def _needs_context(self, code: str) -> bool:
        config = self.family_config.get("persistent_fix", {})
        if not config.get("enable_context_inference", False):
            return False

        if code is None:
            return False

        stripped = code.strip()
        if not stripped:
            return False

        cleaned = self._strip_comments(code)

        if self._is_using_only(cleaned):
            return True

        if re.search(r"\bnamespace\s+\w+", cleaned):
            self._log_pattern(CodePattern.CLASS_ONLY)
            return False

        if re.search(r"\b(class|interface|struct|enum)\s+\w+", cleaned):
            self._log_pattern(CodePattern.CLASS_ONLY)
            return False

        if self._has_property_declaration(cleaned) or self._has_field_declaration(cleaned):
            self._log_pattern(CodePattern.FRAGMENT)
            return True

        pattern, _ = self.pattern_detector.detect(cleaned)
        self._log_pattern(pattern)

        return pattern in (CodePattern.METHOD_ONLY, CodePattern.FRAGMENT)

    def _log_pattern(self, pattern: CodePattern) -> None:
        if hasattr(self.telemetry, "increment_metric"):
            try:
                self.telemetry.increment_metric(f"pattern_detected_{pattern.value}")
            except Exception:
                pass

    @staticmethod
    def _strip_comments(code: str) -> str:
        code = re.sub(r"/\*.*?\*/", "", code, flags=re.DOTALL)
        code = re.sub(r"//.*?$", "", code, flags=re.MULTILINE)
        return code

    @staticmethod
    def _is_using_only(code: str) -> bool:
        lines = [line.strip() for line in code.splitlines() if line.strip()]
        if not lines:
            return False
        for line in lines:
            if not line.startswith("using "):
                return False
            if ";" not in line:
                return False
        return True

    @staticmethod
    def _has_property_declaration(code: str) -> bool:
        auto_property = re.search(
            r"\b(public|private|protected|internal|static)\s+[\w\<\>\[\],\s]+\s+\w+\s*\{[^}]*\bget\s*;[^}]*\}",
            code,
            re.DOTALL,
        )
        expression_property = re.search(
            r"\b(public|private|protected|internal|static)\s+[\w\<\>\[\],\s]+\s+\w+\s*=>\s*[^;]+;",
            code,
        )
        return bool(auto_property or expression_property)

    @staticmethod
    def _has_field_declaration(code: str) -> bool:
        return bool(
            re.search(
                r"\b(public|private|protected|internal|static|readonly|const|volatile)\s+[\w\<\>\[\],\s]+\s+\w+\s*;",
                code,
            )
        )
