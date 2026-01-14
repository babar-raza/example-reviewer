"""
Namespace Validator for Example Review System.
Validates code against namespace policy (whitelist/blacklist/conditional).
"""

import re
from typing import Dict, List, Tuple, Any, Optional


class NamespaceValidator:
    """Validates code against namespace policy (whitelist/blacklist/conditional)."""

    def __init__(self, namespace_policy: Dict[str, Any]):
        """
        Initialize namespace validator.

        Args:
            namespace_policy: Namespace policy configuration with fields:
                - mode: 'whitelist', 'blacklist', or 'permissive' (default: whitelist)
                - allowed_namespaces: List of allowed namespaces (for whitelist mode)
                - blacklist: List of blocked namespaces (for blacklist mode)
                - conditional_allow: Dict of conditional namespace rules (optional)
        """
        self.mode = namespace_policy.get("mode", "whitelist")
        self.allowed = namespace_policy.get("allowed_namespaces", [])
        self.blacklist = namespace_policy.get("blacklist", [])
        self.conditional = namespace_policy.get("conditional_allow", {})

    def validate(self, code: str) -> Tuple[bool, List[str]]:
        """
        Validate code against namespace policy.

        Args:
            code: C# code to validate

        Returns:
            Tuple of (is_valid, violations)
            - is_valid: True if code passes namespace policy
            - violations: List of namespace violation messages
        """
        # Extract using directives from code
        usings = self._extract_usings(code)

        # Check against policy
        violations = []
        for using in usings:
            if not self._is_allowed(using):
                violations.append(f"Namespace not allowed: {using}")

        return (len(violations) == 0, violations)

    def _extract_usings(self, code: str) -> List[str]:
        """
        Extract all 'using X;' directives from code.

        Args:
            code: C# code

        Returns:
            List of namespace strings (e.g., ["System", "Aspose.Words"])
        """
        # Pattern matches: using <namespace>;
        # Handles:
        # - using System;
        # - using System.IO;
        # - using Aspose.Words.Tables;
        # Does NOT match:
        # - using static System.Math;
        # - using (var stream = ...)  // using statement
        # - using alias = Some.Namespace;

        pattern = r'^\s*using\s+(?!static\s)([a-zA-Z_][\w\.]*)\s*;'
        matches = re.findall(pattern, code, re.MULTILINE)

        # Filter out aliases (contain '=')
        namespaces = []
        for line in code.split('\n'):
            line = line.strip()
            if line.startswith('using ') and line.endswith(';'):
                # Skip static usings
                if 'using static ' in line:
                    continue
                # Skip aliases
                if '=' in line:
                    continue
                # Extract namespace
                match = re.match(r'using\s+([a-zA-Z_][\w\.]*)\s*;', line)
                if match:
                    namespaces.append(match.group(1))

        return namespaces

    def _is_allowed(self, namespace: str) -> bool:
        """
        Check if namespace passes policy.

        Args:
            namespace: Namespace to check (e.g., "Aspose.Words.Tables")

        Returns:
            True if namespace is allowed, False otherwise
        """
        if self.mode == "whitelist":
            # Must match allowed list (supports wildcards like "Aspose.Words.*")
            for allowed in self.allowed:
                if allowed.endswith(".*"):
                    prefix = allowed[:-2]
                    if namespace == prefix or namespace.startswith(prefix + "."):
                        return True
                elif namespace == allowed:
                    return True
            return False

        elif self.mode == "blacklist":
            # Must NOT match blacklist
            for blocked in self.blacklist:
                if blocked.endswith(".*"):
                    prefix = blocked[:-2]
                    if namespace == prefix or namespace.startswith(prefix + "."):
                        return False
                elif namespace == blocked:
                    return False
            return True

        else:
            # Permissive mode - allow everything
            return True

    def get_policy_summary(self) -> str:
        """
        Get human-readable summary of namespace policy.

        Returns:
            Policy summary string
        """
        if self.mode == "whitelist":
            namespaces_str = ", ".join(self.allowed) if self.allowed else "NONE"
            return f"Whitelist mode: Only {namespaces_str} allowed"
        elif self.mode == "blacklist":
            namespaces_str = ", ".join(self.blacklist) if self.blacklist else "NONE"
            return f"Blacklist mode: {namespaces_str} blocked"
        else:
            return "Permissive mode: All namespaces allowed"
