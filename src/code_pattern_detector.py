"""Detect basic C# code patterns for context inference."""

from __future__ import annotations

import re
from enum import Enum
from typing import Tuple


class CodePattern(str, Enum):
    COMPLETE_PROGRAM = "complete_program"
    TOP_LEVEL_STATEMENTS = "top_level_statements"
    MINIMAL_API = "minimal_api"
    CLASS_ONLY = "class_only"
    METHOD_ONLY = "method_only"
    FRAGMENT = "fragment"


class CodePatternDetector:
    """Heuristic detector for common C# snippet shapes."""

    _CONFIDENCE = {
        CodePattern.COMPLETE_PROGRAM: 0.95,
        CodePattern.MINIMAL_API: 0.90,
        CodePattern.TOP_LEVEL_STATEMENTS: 0.85,
        CodePattern.CLASS_ONLY: 0.80,
        CodePattern.METHOD_ONLY: 0.75,
        CodePattern.FRAGMENT: 0.60,
    }

    def detect(self, code: str) -> Tuple[CodePattern, float]:
        cleaned = self._strip_comments(code)
        cleaned = self._strip_usings(cleaned)
        cleaned = cleaned.strip()

        if not cleaned:
            return CodePattern.FRAGMENT, self._CONFIDENCE[CodePattern.FRAGMENT]

        if self._is_complete_program(cleaned):
            return CodePattern.COMPLETE_PROGRAM, self._CONFIDENCE[CodePattern.COMPLETE_PROGRAM]

        if self._is_minimal_api(cleaned):
            return CodePattern.MINIMAL_API, self._CONFIDENCE[CodePattern.MINIMAL_API]

        if self._has_class_declaration(cleaned):
            return CodePattern.CLASS_ONLY, self._CONFIDENCE[CodePattern.CLASS_ONLY]

        if self._has_method_declaration(cleaned):
            return CodePattern.METHOD_ONLY, self._CONFIDENCE[CodePattern.METHOD_ONLY]

        if self._has_top_level_statements(cleaned):
            return CodePattern.TOP_LEVEL_STATEMENTS, self._CONFIDENCE[CodePattern.TOP_LEVEL_STATEMENTS]

        return CodePattern.FRAGMENT, self._CONFIDENCE[CodePattern.FRAGMENT]

    @staticmethod
    def _strip_comments(code: str) -> str:
        code = re.sub(r"/\*.*?\*/", "", code, flags=re.DOTALL)
        code = re.sub(r"//.*?$", "", code, flags=re.MULTILINE)
        return code

    @staticmethod
    def _strip_usings(code: str) -> str:
        lines = []
        for line in code.splitlines():
            if re.match(r"^\s*using\s+[\w\.]+\s*;", line):
                continue
            lines.append(line)
        return "\n".join(lines)

    @staticmethod
    def _is_complete_program(code: str) -> bool:
        has_program = re.search(r"\bclass\s+Program\b", code)
        has_main = re.search(r"\bstatic\s+(?:void|int)\s+Main\s*\(", code)
        return bool(has_program and has_main)

    @staticmethod
    def _is_minimal_api(code: str) -> bool:
        if "WebApplication" not in code:
            return False
        if re.search(r"WebApplication\.CreateBuilder\s*\(", code) and re.search(r"\bapp\.Run\s*\(", code):
            return True
        return bool(re.search(r"\bapp\.Map\w+\s*\(", code) and re.search(r"\bapp\.Run\s*\(", code))

    @staticmethod
    def _has_class_declaration(code: str) -> bool:
        return bool(re.search(r"\b(class|interface|struct|enum)\s+\w+", code))

    @staticmethod
    def _has_method_declaration(code: str) -> bool:
        return bool(
            re.search(
                r"\b(public|private|protected|internal|static)\s+[\w\<\>\[\],\s]+\s+\w+\s*\(",
                code,
            )
        )

    @staticmethod
    def _has_top_level_statements(code: str) -> bool:
        semicolons = code.count(";")
        if semicolons >= 2:
            return True
        if re.search(r"\bConsole\.\w+\s*\(", code) or re.search(r"\breturn\b", code):
            return True
        return False
