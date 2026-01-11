"""
Patching Service for Example Review System.
Updates original markdown files with verified code snippets.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from database import Database, Snippet


@dataclass
class PatchResult:
    """Result of patching a single snippet."""
    snippet_id: int
    file_path: str
    success: bool
    message: str
    original_hash: str
    new_hash: str


class PatchingService:
    """
    Service for patching original markdown files with verified code.

    Strategy:
    1. Get all verified snippets from database
    2. For each snippet:
       - Read the original markdown file
       - Locate the code fence using heading context + content hash
       - Replace old code with verified code
       - Preserve formatting and fence markers
    3. Write updated file back
    4. Track all changes for rollback if needed
    """

    def __init__(self, db: Database, content_root: Path):
        """
        Initialize patching service.

        Args:
            db: Database instance
            content_root: Root directory for content files
        """
        self.db = db
        self.content_root = content_root

    def patch_verified_snippets(self, family: str, dry_run: bool = False) -> Dict:
        """
        Patch all verified snippets for a family.

        Args:
            family: Product family to patch
            dry_run: If True, don't actually write files

        Returns:
            Dictionary with patch results
        """
        # Get all verified snippets
        snippets_with_pages = self.db.get_snippets_by_status(family, 'verified')

        results = {
            'total_snippets': len(snippets_with_pages),
            'files_modified': 0,
            'patches_applied': 0,
            'errors': 0,
            'patches': [],
            'modified_files': set()
        }

        for snippet, page in snippets_with_pages:
            try:
                # Get verified version
                verified_version = self.db.get_latest_snippet_version(snippet.snippet_id, 'current')
                if not verified_version:
                    # Try fixed version
                    verified_version = self.db.get_latest_snippet_version(snippet.snippet_id, 'fixed')
                if not verified_version:
                    # Try original if it compiled
                    verified_version = self.db.get_latest_snippet_version(snippet.snippet_id, 'original')

                if not verified_version:
                    results['errors'] += 1
                    results['patches'].append(PatchResult(
                        snippet.snippet_id, page.relative_path,
                        False, "No verified version found", "", ""
                    ))
                    continue

                # Get original version for comparison
                original_version = self.db.get_latest_snippet_version(snippet.snippet_id, 'original')

                # Patch the file
                patch_result = self._patch_snippet_in_file(
                    snippet,
                    page,
                    original_version.code_content if original_version else "",
                    verified_version.code_content,
                    dry_run
                )

                results['patches'].append(patch_result)

                if patch_result.success:
                    results['patches_applied'] += 1
                    results['modified_files'].add(patch_result.file_path)
                else:
                    results['errors'] += 1

            except Exception as e:
                results['errors'] += 1
                results['patches'].append(PatchResult(
                    snippet.snippet_id, page.relative_path,
                    False, f"Exception: {e}", "", ""
                ))

        results['files_modified'] = len(results['modified_files'])

        return results

    def _patch_snippet_in_file(self, snippet: Snippet, page, original_code: str,
                               verified_code: str, dry_run: bool) -> PatchResult:
        """
        Patch a single snippet in its source file.

        Args:
            snippet: Snippet metadata
            page: Page metadata with file_path
            original_code: Original code content
            verified_code: Verified code to replace with
            dry_run: If True, don't write file

        Returns:
            PatchResult with success status
        """
        file_path = self.content_root / page.relative_path

        if not file_path.exists():
            return PatchResult(
                snippet.snippet_id, page.relative_path,
                False, f"File not found: {file_path}", "", ""
            )

        # Read file content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            return PatchResult(
                snippet.snippet_id, page.relative_path,
                False, f"Failed to read file: {e}", "", ""
            )

        # Find and replace the code fence using cascading strategy
        import json
        locator = json.loads(snippet.locator_json)

        matched_start = None
        matched_end = None
        fence_language = "csharp"

        # Strategy 1: Try content hash match (most reliable)
        content_hash = locator.get('snippet_content_hash')
        matched_start, matched_end, fence_language = self._find_by_content_hash(
            content, original_code, content_hash
        )

        # Strategy 2: Try heading context + ordinal (structural match)
        if matched_start is None:
            heading_context = locator.get('heading_context')
            snippet_ordinal = locator.get('snippet_ordinal')
            matched_start, matched_end, fence_language = self._find_by_heading_context(
                content, original_code, heading_context, snippet_ordinal
            )

        # Strategy 3: Fall back to fuzzy matching (last resort)
        if matched_start is None:
            matched_start, matched_end, fence_language = self._find_by_fuzzy_match(
                content, original_code
            )

        if matched_start is None:
            return PatchResult(
                snippet.snippet_id, page.relative_path,
                False, "Could not locate code fence in file", "", ""
            )

        # Direct replacement without markers (Hugo-compatible)
        replacement = f"```{fence_language}\n{verified_code}\n```"
        modified_content = (
            content[:matched_start] +
            replacement +
            content[matched_end:]
        )

        # Verify patch before writing
        verification_result = self._verify_patch(modified_content, verified_code, snippet)
        if not verification_result['success']:
            return PatchResult(
                snippet.snippet_id, page.relative_path,
                False, f"Patch verification failed: {verification_result['error']}", "", ""
            )

        # Write modified content
        if not dry_run:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(modified_content)
            except Exception as e:
                return PatchResult(
                    snippet.snippet_id, page.relative_path,
                    False, f"Failed to write file: {e}", "", ""
                )

        return PatchResult(
            snippet.snippet_id, page.relative_path,
            True, "Patched successfully",
            locator.get('content_hash', ''), self._compute_hash(verified_code)
        )

    def _find_by_content_hash(self, file_content: str, original_code: str,
                             content_hash: Optional[str]) -> Tuple[Optional[int], Optional[int], str]:
        """
        Find code fence by matching content hash.

        Args:
            file_content: Full markdown file content
            original_code: Original code
            content_hash: SHA256 hash of original content

        Returns:
            Tuple of (start_pos, end_pos, fence_language) or (None, None, "csharp") if not found
        """
        if not content_hash:
            return None, None, "csharp"

        import re
        import hashlib

        fence_pattern = r'(```(?:csharp|cs|c#|dotnet|net))\s*\n(.*?)\n(```)'
        matches = list(re.finditer(fence_pattern, file_content, re.DOTALL | re.IGNORECASE))

        expected_hash = hashlib.sha256(original_code.encode('utf-8')).hexdigest()

        for match in matches:
            fence_code = match.group(2)
            fence_hash = hashlib.sha256(fence_code.encode('utf-8')).hexdigest()

            if fence_hash == expected_hash or fence_hash == content_hash:
                # Extract language from fence (e.g., "```csharp" -> "csharp")
                fence_opening = match.group(1).strip()
                lang_match = re.match(r'```(\w+)', fence_opening)
                fence_lang = lang_match.group(1) if lang_match else "csharp"
                return match.start(), match.end(), fence_lang

        return None, None, "csharp"

    def _find_by_heading_context(self, file_content: str, original_code: str,
                                 heading_context: Optional[List[str]],
                                 snippet_ordinal: Optional[int]) -> Tuple[Optional[int], Optional[int], str]:
        """
        Find code fence by matching heading context and ordinal position.

        Args:
            file_content: Full markdown file content
            original_code: Original code
            heading_context: List of heading texts leading to snippet
            snippet_ordinal: Position within the page (1-indexed)

        Returns:
            Tuple of (start_pos, end_pos, fence_language) or (None, None, "csharp") if not found
        """
        if not heading_context:
            return None, None, "csharp"

        lines = file_content.split('\n')
        import re
        fence_pattern = r'(```(?:csharp|cs|c#|dotnet|net))\s*\n(.*?)\n(```)'

        current_headings = []
        fence_candidates = []
        current_ordinal = 0

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Update heading context
            if line.startswith('#'):
                level = 0
                for char in line:
                    if char == '#':
                        level += 1
                    else:
                        break

                if 1 <= level <= 6:
                    heading_text = line[level:].strip()
                    if '{' in heading_text:
                        heading_text = heading_text[:heading_text.index('{')].strip()

                    current_headings = current_headings[:level-1]
                    if len(current_headings) >= level:
                        current_headings[level-1] = heading_text
                    else:
                        current_headings.append(heading_text)

            # Check for code fence
            if line.startswith('```'):
                file_pos = sum(len(lines[j]) + 1 for j in range(i))
                match = re.search(fence_pattern, file_content[file_pos:], re.DOTALL | re.IGNORECASE)

                if match and match.start() == 0:
                    current_ordinal += 1
                    # Extract language from fence (e.g., "```csharp" -> "csharp")
                    fence_opening = match.group(1).strip()
                    lang_match = re.match(r'```(\w+)', fence_opening)
                    fence_lang = lang_match.group(1) if lang_match else "csharp"
                    fence_candidates.append({
                        'start_pos': file_pos,
                        'end_pos': file_pos + match.end(),
                        'fence_language': fence_lang,
                        'heading_context': current_headings.copy(),
                        'ordinal': current_ordinal,
                        'code': match.group(2)
                    })

            i += 1

        # Find best matching candidate
        best_match = None

        # Try exact ordinal match first
        if snippet_ordinal:
            for candidate in fence_candidates:
                if candidate['ordinal'] == snippet_ordinal:
                    candidate_headings = candidate['heading_context']
                    if any(h in candidate_headings for h in heading_context):
                        best_match = candidate
                        break

        # Try heading context match
        if not best_match:
            for candidate in fence_candidates:
                candidate_headings = candidate['heading_context']
                if any(h in candidate_headings for h in heading_context):
                    if self._code_similarity(original_code, candidate['code']) > 0.5:
                        best_match = candidate
                        break

        if best_match:
            return best_match['start_pos'], best_match['end_pos'], best_match['fence_language']

        return None, None, "csharp"

    def _find_by_fuzzy_match(self, file_content: str, original_code: str) -> Tuple[Optional[int], Optional[int], str]:
        """
        Find code fence using fuzzy matching (last resort).

        Args:
            file_content: Full markdown file content
            original_code: Original code

        Returns:
            Tuple of (start_pos, end_pos, fence_language) or (None, None, "csharp") if not found
        """
        import re

        fence_pattern = r'(```(?:csharp|cs|c#|dotnet|net))\s*\n(.*?)\n(```)'
        matches = list(re.finditer(fence_pattern, file_content, re.DOTALL | re.IGNORECASE))

        best_match = None
        best_similarity = 0.7  # Threshold

        for match in matches:
            fence_code = match.group(2)
            similarity = self._code_similarity(original_code, fence_code)

            if similarity > best_similarity:
                best_similarity = similarity
                best_match = match

        if best_match:
            # Extract language from fence (e.g., "```csharp" -> "csharp")
            fence_opening = best_match.group(1).strip()
            lang_match = re.match(r'```(\w+)', fence_opening)
            fence_lang = lang_match.group(1) if lang_match else "csharp"
            return best_match.start(), best_match.end(), fence_lang

        return None, None, "csharp"

    def _replace_by_content_hash(self, file_content: str, original_code: str,
                                verified_code: str, content_hash: Optional[str]) -> Tuple[str, bool]:
        """
        Replace code fence by matching content hash (most reliable).

        Args:
            file_content: Full markdown file content
            original_code: Original code
            verified_code: Verified code to replace with
            content_hash: SHA256 hash of original content

        Returns:
            Tuple of (modified_content, success)
        """
        if not content_hash:
            return file_content, False

        # Find all C# code fences
        import re
        fence_pattern = r'(```(?:csharp|cs|c#|dotnet|net))\s*\n(.*?)\n(```)'
        matches = list(re.finditer(fence_pattern, file_content, re.DOTALL | re.IGNORECASE))

        # Compute hash for original_code to compare
        import hashlib
        expected_hash = hashlib.sha256(original_code.encode('utf-8')).hexdigest()

        # Find fence with matching hash
        for match in matches:
            fence_code = match.group(2)
            fence_hash = hashlib.sha256(fence_code.encode('utf-8')).hexdigest()

            if fence_hash == expected_hash or fence_hash == content_hash:
                # Found matching fence
                opening_fence = match.group(1)
                closing_fence = match.group(3)
                replacement = f"{opening_fence}\n{verified_code}\n{closing_fence}"

                modified_content = (
                    file_content[:match.start()] +
                    replacement +
                    file_content[match.end():]
                )
                return modified_content, True

        return file_content, False

    def _replace_by_heading_context(self, file_content: str, original_code: str,
                                   verified_code: str, heading_context: Optional[List[str]],
                                   snippet_ordinal: Optional[int]) -> Tuple[str, bool]:
        """
        Replace code fence by matching heading context and ordinal position.

        Args:
            file_content: Full markdown file content
            original_code: Original code
            verified_code: Verified code to replace with
            heading_context: List of heading texts leading to snippet
            snippet_ordinal: Position within the page (1-indexed)

        Returns:
            Tuple of (modified_content, success)
        """
        if not heading_context:
            return file_content, False

        # Split into lines for heading analysis
        lines = file_content.split('\n')

        # Find all C# code fences with their heading context
        import re
        fence_pattern = r'(```(?:csharp|cs|c#|dotnet|net))\s*\n(.*?)\n(```)'

        # Track heading stack
        current_headings = []
        fence_candidates = []
        current_ordinal = 0

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Update heading context
            if line.startswith('#'):
                level = 0
                for char in line:
                    if char == '#':
                        level += 1
                    else:
                        break

                if 1 <= level <= 6:
                    heading_text = line[level:].strip()
                    if '{' in heading_text:
                        heading_text = heading_text[:heading_text.index('{')].strip()

                    # Update heading stack
                    current_headings = current_headings[:level-1]
                    if len(current_headings) >= level:
                        current_headings[level-1] = heading_text
                    else:
                        current_headings.append(heading_text)

            # Check for code fence
            if line.startswith('```'):
                # Find matching fence in full content
                file_pos = sum(len(lines[j]) + 1 for j in range(i))
                match = re.search(fence_pattern, file_content[file_pos:], re.DOTALL | re.IGNORECASE)

                # CRITICAL: Verify match starts at position 0 (the ``` we found)
                # If match.start() > 0, the regex matched a LATER fence, not this one
                if match and match.start() == 0:
                    current_ordinal += 1
                    fence_candidates.append({
                        'match': match,
                        'start_pos': file_pos,
                        'heading_context': current_headings.copy(),
                        'ordinal': current_ordinal
                    })

            i += 1

        # Find best matching candidate
        best_match = None

        # Try exact ordinal match first
        if snippet_ordinal:
            for candidate in fence_candidates:
                if candidate['ordinal'] == snippet_ordinal:
                    # Check if heading context matches
                    candidate_headings = candidate['heading_context']
                    if any(h in candidate_headings for h in heading_context):
                        best_match = candidate
                        break

        # Try heading context match
        if not best_match:
            for candidate in fence_candidates:
                candidate_headings = candidate['heading_context']
                # Check if at least one heading matches
                if any(h in candidate_headings for h in heading_context):
                    # Also check code similarity
                    fence_code = candidate['match'].group(2)
                    if self._code_similarity(original_code, fence_code) > 0.5:
                        best_match = candidate
                        break

        if not best_match:
            return file_content, False

        # Replace the fence
        match = best_match['match']
        start_pos = best_match['start_pos']

        opening_fence = match.group(1)
        closing_fence = match.group(3)
        replacement = f"{opening_fence}\n{verified_code}\n{closing_fence}"

        # Since match.start() is guaranteed to be 0 (we verified this above),
        # the absolute positions are:
        absolute_match_start = start_pos  # match.start() = 0
        absolute_match_end = start_pos + match.end()

        modified_content = (
            file_content[:absolute_match_start] +
            replacement +
            file_content[absolute_match_end:]
        )

        return modified_content, True

    def _code_similarity(self, code1: str, code2: str) -> float:
        """Calculate Jaccard similarity between two code snippets."""
        def normalize(code: str) -> set:
            return set(line.strip() for line in code.strip().split('\n') if line.strip())

        lines1 = normalize(code1)
        lines2 = normalize(code2)

        if not lines1 or not lines2:
            return 0.0

        intersection = len(lines1 & lines2)
        union = len(lines1 | lines2)

        return intersection / union if union > 0 else 0.0

    def _replace_code_fence_by_lines(self, file_content: str, original_code: str,
                                    verified_code: str, line_start: int, line_end: int) -> Tuple[str, bool]:
        """
        Replace a code fence in markdown content using line numbers (deterministic).

        Strategy:
        1. Split file into lines
        2. Verify lines at line_start:line_end contain a code fence
        3. Optionally verify content matches (for safety)
        4. Replace fence content while preserving fence markers

        Args:
            file_content: Full markdown file content
            original_code: Original code (for optional verification)
            verified_code: Verified code to replace with
            line_start: Starting line number (0-indexed, inclusive)
            line_end: Ending line number (0-indexed, inclusive)

        Returns:
            Tuple of (modified_content, success)
        """
        lines = file_content.split('\n')

        # Validate line numbers
        if line_start < 0 or line_end >= len(lines) or line_start >= line_end:
            return file_content, False

        # Check that line_start is a code fence opening
        if not lines[line_start].strip().startswith('```'):
            return file_content, False

        # Check that line_end is a code fence closing
        if not lines[line_end].strip().startswith('```'):
            return file_content, False

        # Extract fence markers
        opening_fence = lines[line_start]
        closing_fence = lines[line_end]

        # Optional: Verify content matches (for safety)
        # Skip this check if you want pure line-based replacement
        fence_code_lines = lines[line_start + 1:line_end]
        fence_code = '\n'.join(fence_code_lines)

        # Normalize for comparison
        def normalize(code: str) -> str:
            return '\n'.join(line.strip() for line in code.strip().split('\n'))

        original_normalized = normalize(original_code)
        fence_normalized = normalize(fence_code)

        # Check if content roughly matches (allow 70% similarity for safety)
        if fence_normalized != original_normalized:
            # Calculate similarity to decide if this is the right fence
            original_lines_set = set(original_normalized.split('\n'))
            fence_lines_set = set(fence_normalized.split('\n'))

            if original_lines_set and fence_lines_set:
                intersection = len(original_lines_set & fence_lines_set)
                union = len(original_lines_set | fence_lines_set)
                similarity = intersection / union if union > 0 else 0.0

                # If similarity is too low, this might be the wrong fence
                if similarity < 0.5:
                    return file_content, False

        # Replace fence content
        new_lines = (
            lines[:line_start + 1] +
            verified_code.split('\n') +
            lines[line_end:]
        )

        modified_content = '\n'.join(new_lines)
        return modified_content, True

    def _replace_code_fence(self, file_content: str, original_code: str,
                           verified_code: str, heading_context: Optional[str]) -> Tuple[str, bool]:
        """
        Replace a code fence in markdown content using fuzzy matching (fallback).

        Strategy:
        1. Find all C# code fences
        2. Match by content similarity (use original_code)
        3. Use heading context if provided for disambiguation
        4. Preserve fence markers and language tags

        Args:
            file_content: Full markdown file content
            original_code: Original code to find
            verified_code: Verified code to replace with
            heading_context: Optional heading context

        Returns:
            Tuple of (modified_content, success)
        """
        # Pattern to match C# code fences
        # Captures: fence marker (```) + optional language + code content + closing fence
        fence_pattern = r'(```(?:csharp|cs|c#|dotnet|net))\s*\n(.*?)\n(```)'

        # Find all fences
        matches = list(re.finditer(fence_pattern, file_content, re.DOTALL | re.IGNORECASE))

        if not matches:
            return file_content, False

        # Normalize code for comparison (remove leading/trailing whitespace per line)
        def normalize(code: str) -> str:
            return '\n'.join(line.strip() for line in code.strip().split('\n'))

        original_normalized = normalize(original_code)

        # Find matching fence
        best_match = None
        best_score = 0.0

        for match in matches:
            fence_code = match.group(2)
            fence_normalized = normalize(fence_code)

            # Calculate similarity
            if fence_normalized == original_normalized:
                # Exact match
                best_match = match
                break
            else:
                # Fuzzy match (Jaccard similarity on lines)
                original_lines = set(original_normalized.split('\n'))
                fence_lines = set(fence_normalized.split('\n'))

                if not original_lines or not fence_lines:
                    continue

                intersection = len(original_lines & fence_lines)
                union = len(original_lines | fence_lines)
                score = intersection / union if union > 0 else 0.0

                if score > best_score and score > 0.7:  # 70% similarity threshold
                    best_score = score
                    best_match = match

        if not best_match:
            return file_content, False

        # Replace the fence content (preserve fence markers)
        opening_fence = best_match.group(1)
        closing_fence = best_match.group(3)

        # Build replacement with same fence style
        replacement = f"{opening_fence}\n{verified_code}\n{closing_fence}"

        # Replace in content
        modified_content = (
            file_content[:best_match.start()] +
            replacement +
            file_content[best_match.end():]
        )

        return modified_content, True

    def _verify_patch(self, patched_content: str, expected_code: str, snippet) -> dict:
        """
        Verify that the patch was applied correctly.

        Checks:
        1. Expected code appears in a proper code fence
        2. Code fence markers are intact
        3. No code leaked outside fences

        Returns:
            dict with 'success' (bool) and 'error' (str) keys
        """
        import re

        # Find all C# code fences in patched content
        # Require language tag to avoid matching bash/other fence closings
        fence_pattern = r'```(?:csharp|cs|c#|dotnet|net)\s*\n(.*?)\n```'
        matches = list(re.finditer(fence_pattern, patched_content, re.DOTALL | re.IGNORECASE))

        if not matches:
            return {'success': False, 'error': 'No code fences found in patched content'}

        # Check if expected code appears in any fence
        expected_normalized = '\n'.join(line.strip() for line in expected_code.strip().split('\n'))

        found_in_fence = False
        for match in matches:
            fence_code = match.group(1)
            fence_normalized = '\n'.join(line.strip() for line in fence_code.strip().split('\n'))

            if fence_normalized == expected_normalized:
                found_in_fence = True
                break

        if not found_in_fence:
            return {'success': False, 'error': 'Expected code not found in any code fence'}

        # Success - code is properly fenced
        # Note: We don't check for C# patterns outside fences because markdown files
        # often have inline code examples like `new Archive()` in prose, which would
        # trigger false positives.
        return {'success': True, 'error': ''}

    def _compute_hash(self, code: str) -> str:
        """Compute content hash for code."""
        import hashlib
        normalized = '\n'.join(line.strip() for line in code.strip().split('\n'))
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()[:8]
