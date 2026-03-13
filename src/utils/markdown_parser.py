"""
Shared Markdown Parsing Utilities.

This module provides canonical markdown parsing functions used by both:
- DiscoveryService (extraction)
- MarkdownUpdateService (md_update)

CRITICAL CONTRACT: code_block_index
===================================
The code_block_index is a 0-based index among ALL fenced code blocks in a markdown file,
regardless of language. Both extraction and md_update MUST use the same parsing logic
to ensure consistent indexing.

This contract enables:
1. Deterministic block targeting in md_update
2. Safe multi-block file updates
3. Self-healing location resolution when files change

Index Semantics:
- 0-based index
- Counts ALL fenced blocks (```language ... ```)
- Includes ALL languages (csharp, python, bash, etc.)
- Sequential order as they appear in the file
- NOT filtered by language or content

Example:
    ```bash
    echo "hello"     # block_index = 0
    ```

    ```csharp
    var x = 1;       # block_index = 1
    ```

    ```python
    print("hi")      # block_index = 2
    ```

    ```csharp
    var y = 2;       # block_index = 3
    ```
"""

import hashlib
from typing import List, Dict, Any


def compute_code_signature(code: str) -> str:
    """
    Compute SHA256 signature of normalized code content.

    Normalization:
    - Strip leading/trailing whitespace from entire block
    - Normalize line endings to LF (\\n)

    This ensures consistent signatures across platforms and editors.

    Args:
        code: Raw code content (without fence markers)

    Returns:
        64-character hexadecimal SHA256 hash
    """
    normalized = code.strip().replace('\r\n', '\n')
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


def parse_fenced_blocks(content: str) -> List[Dict[str, Any]]:
    """
    Parse ALL fenced code blocks in markdown content.

    This is the CANONICAL parser used by both extraction and md_update.
    Any changes to this function affect the block_index contract.

    Returns list of blocks with metadata:
    - block_index: 0-based index among ALL fenced blocks (CANONICAL)
    - start_line: 1-based line number of opening fence
    - end_line: 1-based line number of closing fence
    - language: language tag from fence (lowercase, may be empty)
    - content: code content (without fences)
    - signature: SHA256 hash of normalized content
    - fence_start_idx: 0-based line index of opening fence (for array access)
    - fence_end_idx: 0-based line index of closing fence (for array access)

    Example:
        blocks = parse_fenced_blocks(content)
        # Extract C# blocks only:
        csharp_blocks = [b for b in blocks if b['language'] in ['csharp', 'c#', 'cs']]
        # But block_index is still among ALL blocks!

    Args:
        content: Full markdown file content

    Returns:
        List of block dictionaries
    """
    lines = content.split('\n')
    blocks = []
    block_index = 0
    in_block = False
    block_start_line = 0
    block_language = ''
    block_content_lines = []

    for i, line in enumerate(lines):
        if line.startswith('```') and not in_block:
            # Start of code block
            in_block = True
            block_start_line = i + 1  # 1-based
            block_language = line[3:].strip().lower()
            block_content_lines = []

        elif line.startswith('```') and in_block:
            # End of code block
            in_block = False
            block_content = '\n'.join(block_content_lines)

            blocks.append({
                'block_index': block_index,
                'start_line': block_start_line,
                'end_line': i + 1,  # 1-based
                'language': block_language,
                'content': block_content,
                'signature': compute_code_signature(block_content),
                'fence_start_idx': block_start_line - 1,  # 0-based for array access
                'fence_end_idx': i,  # 0-based for array access
            })

            block_index += 1

        elif in_block:
            block_content_lines.append(line)

    return blocks


def find_block_by_signature(
    blocks: List[Dict[str, Any]],
    target_signature: str
) -> List[Dict[str, Any]]:
    """
    Find all blocks matching a signature.

    Used by md_update fallback resolution and diagnostic tools.

    Args:
        blocks: List of blocks from parse_fenced_blocks()
        target_signature: SHA256 signature to match

    Returns:
        List of matching blocks (empty if no match, may have multiple matches)
    """
    return [
        block for block in blocks
        if block['signature'] == target_signature
    ]


def _normalize_code_lines(lines: List[str]) -> List[str]:
    """Normalize code lines for fuzzy comparison: strip whitespace, lowercase."""
    return [line.strip().lower().rstrip(';') for line in lines if line.strip()]


def find_block_by_signature_fuzzy(
    blocks: List[Dict[str, Any]],
    original_code: str,
    head_lines: int = 5,
) -> List[Dict[str, Any]]:
    """
    Fuzzy fallback for find_block_by_signature when exact SHA256 misses.

    Compares normalized first N lines of original_code against each block.
    Useful when the block was lightly edited (trailing whitespace, comment added)
    but the structural beginning is unchanged.

    Args:
        blocks: List of blocks from parse_fenced_blocks()
        original_code: Original code content to match (from example record)
        head_lines: Number of leading lines to compare (default 5)

    Returns:
        List of matching blocks (empty if no match). Caller must handle ambiguity.
    """
    needle_lines = _normalize_code_lines(original_code.splitlines()[:head_lines])
    if not needle_lines:
        return []

    matches = []
    for block in blocks:
        block_head = _normalize_code_lines(block['content'].splitlines()[:head_lines])
        if block_head == needle_lines:
            matches.append(block)
    return matches


def normalize_language_tag(language: str) -> str:
    """
    Normalize language tag to canonical form.

    Maps common aliases to standard names:
    - c#, cs, C# -> csharp
    - py, python3 -> python
    - sh, shell -> bash
    - js -> javascript
    - ts -> typescript

    Args:
        language: Raw language tag from fence

    Returns:
        Normalized language name (lowercase)
    """
    language = language.strip().lower()

    # C# aliases
    if language in ['c#', 'cs']:
        return 'csharp'

    # Python aliases
    if language in ['py', 'python3']:
        return 'python'

    # Shell aliases
    if language in ['sh', 'shell']:
        return 'bash'

    # JavaScript aliases
    if language == 'js':
        return 'javascript'

    # TypeScript aliases
    if language == 'ts':
        return 'typescript'

    # Return as-is
    return language
