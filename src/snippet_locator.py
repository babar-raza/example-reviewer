"""
Snippet Locator module for Example Review System.
Provides stable identifiers for snippets that don't rely solely on line numbers.
"""

import hashlib
import json
from dataclasses import dataclass, asdict
from typing import List, Optional


@dataclass
class SnippetLocator:
    """
    Stable identifier for a snippet within a markdown file.
    Uses multiple signals to reliably locate snippets even if file structure changes.
    """

    # Primary identifiers
    page_path: str              # Absolute file path
    snippet_ordinal: int        # 1-indexed position (1st snippet, 2nd snippet, etc.)

    # Context for resilience (fallback matching)
    heading_context: List[str]  # H1-H6 hierarchy leading to snippet
    preceding_text_hash: str    # Hash of text before snippet (for context matching)
    snippet_content_hash: str   # SHA256 of original snippet content

    # Advisory only (may change between scans)
    line_start: int             # Starting line number
    line_end: int               # Ending line number
    char_offset_start: int      # Character offset in file
    char_offset_end: int        # Character offset end

    # Metadata
    snippet_type: str           # "fence" | "gist"
    language: Optional[str]     # "csharp" | "vb" | etc.
    gist_id: Optional[str] = None      # If type == "gist"
    gist_file: Optional[str] = None    # If type == "gist"

    def to_json(self) -> str:
        """Serialize to JSON string for database storage."""
        return json.dumps(asdict(self), indent=None)

    @staticmethod
    def from_json(json_str: str) -> 'SnippetLocator':
        """Deserialize from JSON string."""
        data = json.loads(json_str)
        return SnippetLocator(**data)

    def matches_content(self, content: str) -> bool:
        """
        Check if snippet content matches the locator's content hash.

        Args:
            content: Snippet content to check

        Returns:
            True if content matches
        """
        content_hash = compute_content_hash(content)
        return content_hash == self.snippet_content_hash

    def matches_context(self, heading_context: List[str], preceding_text: str) -> bool:
        """
        Check if heading context and preceding text match.

        Args:
            heading_context: Current heading hierarchy
            preceding_text: Text before snippet

        Returns:
            True if context matches
        """
        # Check heading context similarity (allow partial match)
        if len(self.heading_context) > 0 and len(heading_context) > 0:
            # At least one heading must match
            if not any(h in heading_context for h in self.heading_context):
                return False

        # Check preceding text hash
        preceding_hash = compute_text_hash(preceding_text)
        return preceding_hash == self.preceding_text_hash


def compute_content_hash(content: str) -> str:
    """
    Compute SHA256 hash of content.

    Args:
        content: Content to hash

    Returns:
        Hex digest of SHA256 hash
    """
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def compute_text_hash(text: str, length: int = 200) -> str:
    """
    Compute hash of text snippet (for context matching).
    Takes last N characters to be resilient to additions at the beginning.

    Args:
        text: Text to hash
        length: Number of characters to use (default 200)

    Returns:
        Hex digest of SHA256 hash
    """
    # Take last N characters (more resilient to edits at start)
    snippet = text[-length:] if len(text) > length else text
    # Normalize whitespace
    normalized = ' '.join(snippet.split())
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


def create_locator(page_path: str, snippet_ordinal: int, heading_context: List[str],
                  preceding_text: str, snippet_content: str, line_start: int, line_end: int,
                  char_offset_start: int, char_offset_end: int, snippet_type: str,
                  language: Optional[str], gist_id: Optional[str] = None,
                  gist_file: Optional[str] = None) -> SnippetLocator:
    """
    Factory function to create a SnippetLocator.

    Args:
        page_path: Absolute file path
        snippet_ordinal: Position on page (1-indexed)
        heading_context: List of headings leading to snippet
        preceding_text: Text before snippet (for context)
        snippet_content: The actual snippet code
        line_start: Starting line number
        line_end: Ending line number
        char_offset_start: Starting character offset
        char_offset_end: Ending character offset
        snippet_type: 'fence' or 'gist'
        language: Programming language
        gist_id: Gist ID (if applicable)
        gist_file: Gist filename (if applicable)

    Returns:
        SnippetLocator instance
    """
    return SnippetLocator(
        page_path=page_path,
        snippet_ordinal=snippet_ordinal,
        heading_context=heading_context,
        preceding_text_hash=compute_text_hash(preceding_text),
        snippet_content_hash=compute_content_hash(snippet_content),
        line_start=line_start,
        line_end=line_end,
        char_offset_start=char_offset_start,
        char_offset_end=char_offset_end,
        snippet_type=snippet_type,
        language=language,
        gist_id=gist_id,
        gist_file=gist_file
    )


class SnippetMatcher:
    """
    Matches snippets in updated files using locators.
    Implements fallback strategy for robust matching.
    """

    @staticmethod
    def find_snippet(locator: SnippetLocator, file_content: str,
                    all_snippets: List[tuple]) -> Optional[int]:
        """
        Find snippet in file using locator.

        Matching strategy:
        1. Try exact content hash match at expected ordinal
        2. Try content hash match at any ordinal
        3. Try context match (heading + preceding text)
        4. Try approximate line/char offset match

        Args:
            locator: SnippetLocator to match
            file_content: Current file content
            all_snippets: List of (ordinal, content, context, line_info) tuples

        Returns:
            Matching snippet ordinal, or None if not found
        """

        # Strategy 1: Exact match at expected ordinal
        for ordinal, content, context, line_info in all_snippets:
            if ordinal == locator.snippet_ordinal:
                if locator.matches_content(content):
                    return ordinal

        # Strategy 2: Content hash match at any ordinal
        for ordinal, content, context, line_info in all_snippets:
            if locator.matches_content(content):
                return ordinal

        # Strategy 3: Context match (heading + preceding text)
        for ordinal, content, context, line_info in all_snippets:
            heading_ctx = context.get('heading_context', [])
            preceding_text = context.get('preceding_text', '')
            if locator.matches_context(heading_ctx, preceding_text):
                return ordinal

        # Strategy 4: Approximate position match (within ±5 lines)
        for ordinal, content, context, line_info in all_snippets:
            line_start = line_info.get('line_start', 0)
            if abs(line_start - locator.line_start) <= 5:
                # Close enough position-wise
                return ordinal

        return None


def extract_heading_context(lines: List[str], snippet_line: int) -> List[str]:
    """
    Extract heading hierarchy leading to a snippet.

    Args:
        lines: File lines
        snippet_line: Line number where snippet starts

    Returns:
        List of heading texts (H1 to H6)
    """
    headings = []
    current_level = 7  # Start higher than H6

    for i in range(snippet_line):
        line = lines[i].strip()
        if line.startswith('#'):
            # Count heading level
            level = 0
            for char in line:
                if char == '#':
                    level += 1
                else:
                    break

            if 1 <= level <= 6:
                heading_text = line[level:].strip()
                # Remove any anchor links or extra markdown
                if '{' in heading_text:
                    heading_text = heading_text[:heading_text.index('{')].strip()

                # Add to context (replace if same or higher level)
                if level <= current_level:
                    # Remove deeper headings
                    headings = [h for h in headings if not h.startswith('#' * (level + 1))]
                    headings.append(heading_text)
                    current_level = level

    return headings


def extract_preceding_text(lines: List[str], snippet_line: int, char_limit: int = 200) -> str:
    """
    Extract text before snippet for context matching.

    Args:
        lines: File lines
        snippet_line: Line number where snippet starts
        char_limit: Maximum characters to extract

    Returns:
        Preceding text (up to char_limit characters)
    """
    preceding_lines = []
    char_count = 0

    # Work backwards from snippet line
    for i in range(snippet_line - 1, -1, -1):
        line = lines[i].strip()

        # Skip empty lines and markdown headings
        if not line or line.startswith('#'):
            continue

        # Skip code fences
        if line.startswith('```') or line.startswith('{{<'):
            continue

        char_count += len(line)
        preceding_lines.insert(0, line)

        if char_count >= char_limit:
            break

    # Join and truncate to char_limit
    text = ' '.join(preceding_lines)
    if len(text) > char_limit:
        text = text[-char_limit:]

    return text
