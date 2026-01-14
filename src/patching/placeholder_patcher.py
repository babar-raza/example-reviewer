"""
Placeholder-based patching system for deterministic code replacement.

Strategy:
1. First patch: Use multi-strategy matching + inject markers
2. Future patches: Use markers for instant location

Markers format (invisible in rendered markdown):
<!-- VERIFIED_SNIPPET_{snippet_id}_START -->
```csharp
// verified code
```
<!-- VERIFIED_SNIPPET_{snippet_id}_END -->
"""

import re
from typing import Tuple, Optional
from pathlib import Path


class PlaceholderPatcher:
    """Patches code using persistent HTML comment markers."""

    @staticmethod
    def has_markers(file_content: str, snippet_id: int) -> bool:
        """Check if snippet already has placeholder markers."""
        start_marker = f"<!-- VERIFIED_SNIPPET_{snippet_id}_START -->"
        end_marker = f"<!-- VERIFIED_SNIPPET_{snippet_id}_END -->"
        return start_marker in file_content and end_marker in file_content

    @staticmethod
    def patch_with_markers(file_content: str, snippet_id: int,
                          verified_code: str, fence_language: str = "csharp") -> Tuple[str, bool]:
        """
        Replace code using markers (fast path for re-patching).

        Args:
            file_content: Full file content
            snippet_id: Snippet ID
            verified_code: Code to insert
            fence_language: Language tag for code fence

        Returns:
            Tuple of (modified_content, success)
        """
        start_marker = f"<!-- VERIFIED_SNIPPET_{snippet_id}_START -->"
        end_marker = f"<!-- VERIFIED_SNIPPET_{snippet_id}_END -->"

        # Find marker positions
        start_pos = file_content.find(start_marker)
        end_pos = file_content.find(end_marker)

        if start_pos == -1 or end_pos == -1:
            return file_content, False

        # Build replacement with markers - ensure newlines are correct
        # Format: marker\n```lang\ncode\n```\nmarker
        replacement = f"{start_marker}\n```{fence_language}\n{verified_code}\n```\n{end_marker}"

        # Replace content between markers
        modified_content = (
            file_content[:start_pos] +
            replacement +
            file_content[end_pos + len(end_marker):]
        )

        return modified_content, True

    @staticmethod
    def inject_markers(file_content: str, snippet_id: int,
                      verified_code: str, original_match_start: int,
                      original_match_end: int, fence_language: str = "csharp") -> str:
        """
        Inject markers around newly patched code.

        Args:
            file_content: Full file content
            snippet_id: Snippet ID
            verified_code: Code to insert
            original_match_start: Start position of original code fence
            original_match_end: End position of original code fence
            fence_language: Language tag for code fence

        Returns:
            Modified content with markers
        """
        start_marker = f"<!-- VERIFIED_SNIPPET_{snippet_id}_START -->"
        end_marker = f"<!-- VERIFIED_SNIPPET_{snippet_id}_END -->"

        # Build replacement with markers - ensure newlines are correct
        # Format: marker\n```lang\ncode\n```\nmarker
        replacement = f"{start_marker}\n```{fence_language}\n{verified_code}\n```\n{end_marker}"

        # Replace original fence with marked version
        modified_content = (
            file_content[:original_match_start] +
            replacement +
            file_content[original_match_end:]
        )

        return modified_content

    @staticmethod
    def extract_language_from_fence(fence_line: str) -> str:
        """Extract language tag from fence opening line."""
        # Match patterns like ```csharp, ```cs, ```c#, etc.
        match = re.match(r'```(\w+)', fence_line.strip())
        return match.group(1) if match else "csharp"
