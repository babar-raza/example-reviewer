"""
Snippet Wrapper Service for wrapping code fragments into compilable units.

This service handles the wrapping of incomplete code snippets (fragments without
Main methods, classes, etc.) into complete compilable C# programs.
"""

import re
import logging
from pathlib import Path
from typing import Optional, Tuple, List, Dict

logger = logging.getLogger(__name__)


class SnippetWrapperService:
    """Service for wrapping code fragments into compilable units."""

    # Standard using statements for ZIP family
    STANDARD_USINGS = [
        "using System;",
        "using System.IO;",
        "using System.Collections.Generic;",
        "using System.Linq;",
        "using Aspose.Zip;",
        "using Aspose.Zip.Saving;",
        "using Aspose.Zip.SevenZip;",
    ]

    def __init__(
        self,
        family: str = "zip",
        test_data_path: Optional[Path] = None,
        default_usings: Optional[List[str]] = None,
    ):
        """
        Initialize the snippet wrapper service.

        Args:
            family: Product family (e.g., "zip", "pdf")
            test_data_path: Path to test data directory for file mapping
            default_usings: Optional list of default using namespaces (without "using " prefix)
        """
        self.family = family.lower()
        self.test_data_path = test_data_path

        # Configure using statements from provided defaults or fallback to STANDARD_USINGS
        if default_usings:
            self.using_statements = [f"using {ns};" for ns in default_usings]
        else:
            self.using_statements = self.STANDARD_USINGS

    def needs_wrapping(self, code: str) -> bool:
        """
        Determine if code needs to be wrapped.

        Args:
            code: Code snippet to check

        Returns:
            True if code needs wrapping, False if it's already complete
        """
        code_stripped = code.strip()

        # Check for indicators of complete program
        has_main = bool(re.search(r'\bstatic\s+void\s+Main\s*\(', code_stripped))
        has_top_level_statements = self._has_top_level_statements(code_stripped)

        # If it has Main or top-level statements, it's likely complete
        if has_main or has_top_level_statements:
            return False

        # Check if it's just a fragment (method calls, variable declarations)
        if self._is_fragment(code_stripped):
            return True

        # Check if it's a standalone method or class without Main
        has_class = bool(re.search(r'\bclass\s+\w+', code_stripped))
        has_method = bool(re.search(r'\b(public|private|protected|internal|static)\s+\w+\s+\w+\s*\(', code_stripped))

        if has_class and not has_main:
            # Has class but no Main - needs wrapping
            return True

        if has_method and not has_main and not has_class:
            # Has method but no class or Main - needs wrapping
            return True

        return False

    def wrap_snippet(
        self,
        code: str,
        map_file_paths: bool = True,
        class_name: str = "Program",
    ) -> Tuple[str, bool]:
        """
        Wrap a code snippet into a compilable program.

        Args:
            code: Code snippet to wrap
            map_file_paths: Whether to map placeholder file paths to real test data
            class_name: Class name to use for wrapping

        Returns:
            Tuple of (wrapped_code, was_wrapped)
        """
        if not self.needs_wrapping(code):
            # Code is already complete, but might need file path mapping
            if map_file_paths and self.test_data_path:
                code = self._map_file_paths(code)
            return code, False

        # Map file paths first
        if map_file_paths and self.test_data_path:
            code = self._map_file_paths(code)

        # Check if code already has using statements at the top
        existing_usings = self._extract_existing_usings(code)
        code_without_usings = self._remove_usings(code)

        # Combine existing usings with standard ones (deduplicate)
        all_usings = list(dict.fromkeys(self.using_statements + existing_usings))

        # Build the wrapped program
        wrapped = self._build_wrapper(
            code_without_usings.strip(),
            all_usings,
            class_name,
        )

        return wrapped, True

    def _has_top_level_statements(self, code: str) -> bool:
        """Check if code uses C# 9+ top-level statements."""
        # This is a heuristic - look for statements not inside any class/method
        lines = code.split('\n')
        depth = 0
        has_statements_at_zero = False

        for line in lines:
            stripped = line.strip()

            # Skip empty lines and comments
            if not stripped or stripped.startswith('//') or stripped.startswith('/*'):
                continue

            # Track brace depth
            depth += stripped.count('{') - stripped.count('}')

            # If we find a statement at depth 0 (not in class/method), it's top-level
            if depth == 0 and stripped.endswith(';'):
                # Make sure it's not a using statement
                if not stripped.startswith('using '):
                    has_statements_at_zero = True

        return has_statements_at_zero

    def _is_fragment(self, code: str) -> bool:
        """Check if code is just a fragment (no structure)."""
        # Look for method or class declarations
        has_method = bool(re.search(r'\b(public|private|protected|internal|static)?\s*(void|int|string|bool|var|class|interface)\s+\w+\s*\(', code))
        has_class = bool(re.search(r'\bclass\s+\w+', code))

        # If no structure indicators, check if most lines are statements
        if not has_method and not has_class:
            lines = code.split('\n')
            non_empty_lines = [l.strip() for l in lines if l.strip() and not l.strip().startswith('//')]

            if len(non_empty_lines) == 0:
                return False

            # Count statements (lines ending with semicolon)
            statement_count = sum(1 for line in non_empty_lines if line.endswith(';') or line.endswith('{') or line.endswith('}'))

            # If most lines are statements, it's a fragment
            if statement_count >= len(non_empty_lines) * 0.5:
                return True

        return False

    def _extract_existing_usings(self, code: str) -> List[str]:
        """Extract existing using statements from code."""
        usings = []
        for line in code.split('\n'):
            stripped = line.strip()
            if stripped.startswith('using ') and stripped.endswith(';'):
                usings.append(stripped)
        return usings

    def _remove_usings(self, code: str) -> str:
        """Remove using statements from code."""
        lines = []
        for line in code.split('\n'):
            stripped = line.strip()
            if not (stripped.startswith('using ') and stripped.endswith(';')):
                lines.append(line)
        return '\n'.join(lines)

    def _build_wrapper(
        self,
        code: str,
        usings: List[str],
        class_name: str,
    ) -> str:
        """Build the complete wrapped program."""
        # Build using statements section
        usings_section = '\n'.join(usings)

        # Indent the user code
        indented_code = self._indent_code(code, 12)  # 3 levels of indentation

        # Build the complete program
        wrapped = f"""{usings_section}

namespace SnippetWrapper
{{
    class {class_name}
    {{
        static void Main(string[] args)
        {{
{indented_code}
        }}
    }}
}}
"""
        return wrapped

    def _indent_code(self, code: str, spaces: int) -> str:
        """Indent code by the specified number of spaces."""
        indent = ' ' * spaces
        lines = code.split('\n')
        indented_lines = [indent + line if line.strip() else line for line in lines]
        return '\n'.join(indented_lines)

    def _map_file_paths(self, code: str) -> str:
        """
        Map placeholder file paths to real test data paths.

        This method looks for common placeholder patterns and replaces them
        with actual file paths from the test data directory.

        Args:
            code: Code with placeholder paths

        Returns:
            Code with mapped paths
        """
        if not self.test_data_path or not self.test_data_path.exists():
            return code

        # Common placeholder patterns for ZIP family
        placeholder_mappings = {
            r'"sample\.zip"': self._find_test_file('sample.zip', 'archive.zip'),
            r'"test\.zip"': self._find_test_file('test.zip', 'archive.zip'),
            r'"input\.zip"': self._find_test_file('input.zip', 'archive.zip'),
            r'"archive\.zip"': self._find_test_file('archive.zip'),
            r'"sample\.txt"': self._find_test_file('sample.txt', 'alice29.txt'),
            r'"test\.txt"': self._find_test_file('test.txt', 'alice29.txt'),
            r'"input\.txt"': self._find_test_file('input.txt', 'alice29.txt'),
        }

        mapped_code = code
        for pattern, replacement in placeholder_mappings.items():
            if replacement:
                mapped_code = re.sub(pattern, f'"{replacement}"', mapped_code, flags=re.IGNORECASE)

        return mapped_code

    def _find_test_file(self, filename: str, fallback: Optional[str] = None) -> Optional[str]:
        """
        Find a test file in the test data directory.

        Args:
            filename: Filename to look for
            fallback: Fallback filename if primary not found

        Returns:
            Path string relative to test_data_path, or None if not found
        """
        if not self.test_data_path:
            return None

        # Try exact match first
        exact_path = self.test_data_path / filename
        if exact_path.exists():
            return filename

        # Try fallback
        if fallback:
            fallback_path = self.test_data_path / fallback
            if fallback_path.exists():
                return fallback

        # Try finding any file with the same extension
        ext = Path(filename).suffix
        if ext:
            matching_files = list(self.test_data_path.glob(f'*{ext}'))
            if matching_files:
                return matching_files[0].name

        return None
