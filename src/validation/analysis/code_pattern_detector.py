"""
Code Pattern Detector for C# Source Code

Identifies code pattern types to inform context inference and wrapping strategies.
Supports detection of complete programs, top-level statements, minimal APIs, and fragments.
"""

from enum import Enum
from typing import Tuple
import re


class CodePattern(Enum):
    """Types of code patterns we can detect"""
    COMPLETE_PROGRAM = "complete_program"      # Full Program class with Main
    TOP_LEVEL_STATEMENTS = "top_level_statements"  # C# 9+ top-level statements
    MINIMAL_API = "minimal_api"                # ASP.NET minimal API pattern
    CLASS_ONLY = "class_only"                  # Just class definitions
    METHOD_ONLY = "method_only"                # Just method(s)
    FRAGMENT = "fragment"                      # Incomplete code fragment


class CodePatternDetector:
    """Detects code pattern type from C# source code"""

    def detect(self, code: str) -> Tuple[CodePattern, float]:
        """
        Detect code pattern type.

        Args:
            code: C# source code to analyze

        Returns:
            (pattern, confidence) where confidence is 0.0-1.0
        """
        if not code or not code.strip():
            return (CodePattern.FRAGMENT, 0.60)

        code_clean = self._strip_comments(code)

        # Check for complete program (highest priority)
        if self._has_program_class(code_clean):
            return (CodePattern.COMPLETE_PROGRAM, 0.95)

        # Check for minimal API pattern
        if self._is_minimal_api(code_clean):
            return (CodePattern.MINIMAL_API, 0.90)

        # Check for class-only (before top-level to avoid false positives)
        if self._has_class_definition(code_clean) and not self._has_loose_code(code_clean):
            return (CodePattern.CLASS_ONLY, 0.80)

        # Check for method-only (before top-level to avoid false positives)
        if self._has_method_definition(code_clean) and not self._has_class_definition(code_clean):
            return (CodePattern.METHOD_ONLY, 0.75)

        # Check for top-level statements (more specific than fragment)
        if self._has_top_level_statements(code_clean):
            return (CodePattern.TOP_LEVEL_STATEMENTS, 0.85)

        # Default to fragment
        return (CodePattern.FRAGMENT, 0.60)

    def _strip_comments(self, code: str) -> str:
        """Remove // and /* */ comments"""
        # Remove single-line comments
        code = re.sub(r'//.*?$', '', code, flags=re.MULTILINE)
        # Remove multi-line comments
        code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
        return code

    def _has_program_class(self, code: str) -> bool:
        """Check for Program class with Main method"""
        return bool(re.search(r'class\s+Program\s*{.*?static\s+void\s+Main', code, re.DOTALL))

    def _is_minimal_api(self, code: str) -> bool:
        """Check for ASP.NET minimal API pattern"""
        has_builder = 'WebApplication.CreateBuilder' in code
        has_app_run = re.search(r'app\.Run\s*\(', code)
        return has_builder and has_app_run

    def _has_top_level_statements(self, code: str) -> bool:
        """Check for top-level statements (no class/namespace wrapper)"""
        # Remove using statements and check if there's code outside class/namespace
        lines = [l.strip() for l in code.split('\n') if l.strip() and not l.strip().startswith('using')]
        if not lines:
            return False

        # First non-using line should not be namespace/class
        first_line = lines[0]
        if first_line.startswith('namespace') or first_line.startswith('class') or first_line.startswith('public class') or first_line.startswith('internal class') or first_line.startswith('private class'):
            return False

        # Should have executable statements that suggest top-level (not just method definitions)
        has_executable = any(keyword in code for keyword in ['var ', 'Console.', 'return ', 'if (', 'for (', 'foreach ('])

        # Must NOT be a method definition or class definition
        has_class_or_method_def = bool(re.search(r'\b(class|interface|struct|enum)\s+\w+', code))

        if not has_executable or has_class_or_method_def:
            return False

        # Must have more than just a single variable declaration to be considered top-level
        # Single var declarations are fragments, top-level should have multiple statements or control flow
        non_comment_lines = [l for l in lines if l and not l.startswith('//')]
        if len(non_comment_lines) == 1 and non_comment_lines[0].strip().startswith('var '):
            return False

        return True

    def _has_class_definition(self, code: str) -> bool:
        """Check for class definition"""
        return bool(re.search(r'class\s+\w+', code))

    def _has_method_definition(self, code: str) -> bool:
        """Check for method definition"""
        return bool(re.search(r'(public|private|protected|internal|static)\s+\w+\s+\w+\s*\(', code))

    def _has_loose_code(self, code: str) -> bool:
        """Check for code not inside class"""
        # Simplified check: look for statements outside braces
        return bool(re.search(r'^\s*(var|Console|return)\s', code, re.MULTILINE))
