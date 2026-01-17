"""Namespace validation for cross-domain API detection."""

from __future__ import annotations

import re
from typing import Dict, List, Tuple


class NamespaceValidator:
    """Validate using directives against allow/deny policies."""

    def __init__(self, policy: Dict[str, List[str]]):
        self.mode = policy.get("mode", "whitelist")
        self.allowed = policy.get("allowed_namespaces", []) or []
        self.blacklist = policy.get("blacklist", []) or []

    def validate(self, code: str) -> Tuple[bool, List[str]]:
        usings = self._extract_usings(code)
        if self.mode == "permissive":
            return True, []

        violations: List[str] = []
        if self.mode == "whitelist":
            for ns in usings:
                if not any(self._matches_pattern(ns, allowed) for allowed in self.allowed):
                    violations.append(ns)
        elif self.mode == "blacklist":
            for ns in usings:
                if any(self._matches_pattern(ns, blocked) for blocked in self.blacklist):
                    violations.append(ns)

        return len(violations) == 0, violations

    def get_policy_summary(self) -> str:
        if self.mode == "permissive":
            return "Permissive mode: All namespaces allowed"
        if self.mode == "blacklist":
            return f"Blacklist mode: blocked={', '.join(self.blacklist) if self.blacklist else 'none'}"
        return f"Whitelist mode: allowed={', '.join(self.allowed) if self.allowed else 'none'}"

    def _extract_usings(self, code: str) -> List[str]:
        cleaned = self._strip_comments(code)
        usings: List[str] = []
        for line in cleaned.splitlines():
            stripped = line.strip()
            if not stripped.startswith("using "):
                continue
            if stripped.startswith("using static "):
                continue
            if "=" in stripped:
                continue
            if "using (" in stripped:
                continue
            match = re.match(r"using\s+([A-Za-z_][\w\.]*)\s*;", stripped)
            if match:
                usings.append(match.group(1))
        return usings

    @staticmethod
    def _strip_comments(code: str) -> str:
        code = re.sub(r"/\*.*?\*/", "", code, flags=re.DOTALL)
        code = re.sub(r"//.*?$", "", code, flags=re.MULTILINE)
        return code

    @staticmethod
    def _matches_pattern(namespace: str, pattern: str) -> bool:
        if pattern.endswith(".*"):
            prefix = pattern[:-2]
            return namespace.startswith(prefix + ".")
        return namespace == pattern
