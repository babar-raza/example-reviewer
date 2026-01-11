"""
Discovery Service for Example Review System.
Scans markdown files and extracts code snippets.
"""

import re
import hashlib
import frontmatter
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from snippet_locator import create_locator, extract_heading_context, extract_preceding_text, SnippetLocator
from database import Database
from telemetry import TelemetryClient
from gist_service import GistService


@dataclass
class DiscoveredSnippet:
    """Represents a discovered code snippet."""
    ordinal: int
    content: str
    snippet_type: str  # 'fence' | 'gist'
    language: Optional[str]
    line_start: int
    line_end: int
    char_offset_start: int
    char_offset_end: int
    heading_context: List[str]
    preceding_text: str
    gist_id: Optional[str] = None
    gist_file: Optional[str] = None
    gist_shortcode_original: Optional[str] = None  # Original shortcode for patching


class DiscoveryService:
    """
    Service for discovering code snippets in markdown files.
    """

    # Site configurations
    SITE_CONFIGS = {
        'blog': 'content/blog.aspose.net',
        'docs': 'content/docs.aspose.net',
        'kb': 'content/kb.aspose.net',
        'reference': 'content/reference.aspose.net',
        'products': 'content/products.aspose.net'
    }

    def __init__(self, repo_root: Path, db: Database, telemetry: TelemetryClient):
        """
        Initialize discovery service.

        Args:
            repo_root: Root directory of repository
            db: Database instance
            telemetry: Telemetry client
        """
        self.repo_root = repo_root
        self.db = db
        self.telemetry = telemetry

        # Initialize gist service with cache directory
        cache_dir = repo_root / 'cache' / 'gists'
        self.gist_service = GistService(cache_dir, db)

    def discover_family(self, family: str, max_pages: Optional[int] = None) -> Dict[str, int]:
        """
        Discover all snippets for a family across all sites.

        Args:
            family: Product family (e.g., 'zip', 'words')
            max_pages: Optional limit on number of pages to process

        Returns:
            Statistics dictionary
        """
        stats = {
            'pages_found': 0,
            'pages_processed': 0,
            'snippets_found': 0,
            'errors': 0
        }

        # Scan all sites
        for site_name, site_path in self.SITE_CONFIGS.items():
            site_dir = self.repo_root / site_path
            if not site_dir.exists():
                print(f"[!] Site directory not found: {site_dir}")
                continue

            # Find all markdown files containing family name
            family_pattern = f"*{family}*"
            markdown_files = list(site_dir.rglob("*.md"))

            # Filter for family-related files
            relevant_files = [
                f for f in markdown_files
                if family.lower() in str(f).lower()
            ]

            stats['pages_found'] += len(relevant_files)

            # Process files
            for idx, file_path in enumerate(relevant_files):
                if max_pages and stats['pages_processed'] >= max_pages:
                    break

                try:
                    page_stats = self.process_page(file_path, site_name, family)
                    stats['pages_processed'] += 1
                    stats['snippets_found'] += page_stats.get('snippets', 0)

                except Exception as e:
                    stats['errors'] += 1
                    self.telemetry.log_event(
                        "discovery_error",
                        "error",
                        f"Failed to process {file_path}: {str(e)}",
                        {"file_path": str(file_path), "error": str(e)}
                    )
                    print(f"[!] Error processing {file_path}: {e}")

        return stats

    def process_page(self, file_path: Path, site: str, family: str) -> Dict[str, int]:
        """
        Process a single markdown page.

        Args:
            file_path: Path to markdown file
            site: Site name
            family: Product family

        Returns:
            Statistics for this page
        """
        # Read file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Parse frontmatter and content
        try:
            post = frontmatter.loads(content)
            markdown_content = post.content
            frontmatter_data = post.metadata
        except Exception:
            # No frontmatter, treat entire file as markdown
            markdown_content = content
            frontmatter_data = {}

        # Determine language from filename and directory structure
        file_name = file_path.name
        language = 'en'  # Default to English

        # Method 1: Check filename pattern (index.{lang}.md)
        if '.' in file_name and file_name.count('.') >= 2:
            # e.g., index.de.md -> 'de'
            parts = file_name.split('.')
            if len(parts) >= 3 and parts[-2] != 'index':
                language = parts[-2]

        # Method 2: Check directory path for Hugo-style language dirs
        # e.g., /docs.aspose.net/zip/ca/... -> Catalan
        # e.g., /docs.aspose.net/zip/en/... -> English
        path_parts = file_path.parts
        # Look for language code in path (2-letter dir names like /ca/, /de/, /es/)
        for part in path_parts:
            if len(part) == 2 and part.lower() != 'en':
                # Likely a language code directory
                language = part.lower()
                break

        # IMPORTANT: Only process English pages
        # Non-English pages are translations and may have inconsistencies
        # We validate English pages first, then replicate fixes to translations
        if language != 'en':
            return {'snippets': 0}

        # Calculate relative path
        relative_path = str(file_path.relative_to(self.repo_root))

        # Compute content hash
        content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()

        # Get or create page in database
        page_id = self.db.get_or_create_page(
            file_path=str(file_path),
            relative_path=relative_path,
            site=site,
            family=family,
            language=language
        )

        # Update page metadata
        self.db.update_page(
            page_id,
            content_hash=content_hash,
            last_scanned_at=self.db._conn.execute("SELECT datetime('now')").fetchone()[0],
            state='scanned'
        )

        # Extract snippets
        with self.telemetry.track_page(page_id, str(file_path), relative_path, site, family):
            snippets = self.extract_snippets(markdown_content)

            # Save snippets to database
            for snippet in snippets:
                # For gist snippets, preserve original shortcode for patching
                gist_shortcode = None
                if snippet.snippet_type == 'gist' and hasattr(snippet, 'gist_shortcode_original'):
                    gist_shortcode = snippet.gist_shortcode_original

                locator = create_locator(
                    page_path=str(file_path),
                    snippet_ordinal=snippet.ordinal,
                    heading_context=snippet.heading_context,
                    preceding_text=snippet.preceding_text,
                    snippet_content=snippet.content,
                    line_start=snippet.line_start,
                    line_end=snippet.line_end,
                    char_offset_start=snippet.char_offset_start,
                    char_offset_end=snippet.char_offset_end,
                    snippet_type=snippet.snippet_type,
                    language=snippet.language,
                    gist_id=snippet.gist_id,
                    gist_file=snippet.gist_file,
                    gist_shortcode_original=gist_shortcode
                )

                # Create snippet in database
                snippet_id = self.db.create_snippet(
                    page_id=page_id,
                    snippet_ordinal=snippet.ordinal,
                    locator_json=locator.to_json(),
                    snippet_type=snippet.snippet_type,
                    language=snippet.language
                )

                # Save original version
                self.db.create_snippet_version(
                    snippet_id=snippet_id,
                    version_type='original',
                    code_content=snippet.content,
                    created_by='system'
                )

                self.telemetry.increment_metric('snippets_found')

        return {'snippets': len(snippets)}

    def extract_snippets(self, markdown_content: str) -> List[DiscoveredSnippet]:
        """
        Extract all code snippets from markdown content.

        Args:
            markdown_content: Markdown text

        Returns:
            List of discovered snippets
        """
        snippets = []
        lines = markdown_content.split('\n')
        ordinal = 0
        char_offset = 0

        i = 0
        while i < len(lines):
            line = lines[i]

            # Check for code fence
            if line.strip().startswith('```'):
                snippet = self._extract_fence_snippet(lines, i, char_offset, ordinal + 1)
                if snippet:
                    snippets.append(snippet)
                    ordinal += 1
                    i = snippet.line_end
                    char_offset += sum(len(lines[j]) + 1 for j in range(i, snippet.line_end + 1))
                else:
                    char_offset += len(line) + 1
                    i += 1

            # Check for gist shortcode
            elif '{{< gist' in line or '{{<gist' in line:
                snippet = self._extract_gist_snippet(lines, i, char_offset, ordinal + 1)
                if snippet:
                    snippets.append(snippet)
                    ordinal += 1
                char_offset += len(line) + 1
                i += 1

            else:
                char_offset += len(line) + 1
                i += 1

        return snippets

    def _should_skip_snippet(self, content: str, language: Optional[str]) -> bool:
        """
        Determine if a snippet should be skipped based on content and language.

        Args:
            content: Snippet content
            language: Snippet language (from fence marker)

        Returns:
            True if snippet should be skipped
        """
        # CRITICAL: Only process fences with EXPLICIT C# language markers
        # Fences without language markers (just ```) are NOT C# code
        csharp_languages = {'csharp', 'cs', 'c#', 'dotnet', 'net'}
        if not language or language.lower() not in csharp_languages:
            return True

        # Skip empty or very short snippets
        content_stripped = content.strip()
        if len(content_stripped) < 30:  # Minimum viable C# code
            return True

        # Skip Package Manager commands
        pm_patterns = [
            'PM>',
            'Install-Package',
            'dotnet add package',
            'dotnet install',
            'NuGet\\Install-Package',
        ]
        first_line = content_stripped.split('\n')[0]
        if any(pattern in first_line for pattern in pm_patterns):
            return True

        # Skip ASCII art (directory trees)
        ascii_art_chars = ['├', '└', '│', '─', '┌', '┐', '┘', '┴', '┬', '┤', '┼']
        if any(char in content for char in ascii_art_chars):
            return True

        # Skip if it's just a single line without any C# keywords or structure
        lines = [line.strip() for line in content_stripped.split('\n') if line.strip()]
        if len(lines) == 1:
            # Single line - check if it has C# keywords or looks like valid statement
            csharp_indicators = [
                'using ', 'namespace ', 'class ', 'public ', 'private ', 'protected ',
                'void ', 'int ', 'string ', 'var ', 'new ', 'return ', '{ ', ' {',
                'static ', 'async ', 'await ', '//', '/*'
            ]
            has_indicator = any(ind in lines[0] for ind in csharp_indicators)

            # Also check if it ends with semicolon and starts with identifier (likely incomplete)
            if lines[0].endswith(';') and not has_indicator:
                # Something like: parentZip.Save("file.zip");
                return True

        return False

    def _extract_fence_snippet(self, lines: List[str], start_line: int,
                              start_char_offset: int, ordinal: int) -> Optional[DiscoveredSnippet]:
        """
        Extract a code fence snippet.

        Args:
            lines: File lines
            start_line: Line where fence starts
            start_char_offset: Character offset where fence starts
            ordinal: Snippet ordinal (1-indexed)

        Returns:
            DiscoveredSnippet or None
        """
        fence_line = lines[start_line].strip()

        # Parse language from fence
        language = None
        if len(fence_line) > 3:
            lang_part = fence_line[3:].strip()
            if lang_part:
                # Handle cases like ```csharp or ```c# or ```{.csharp}
                lang_part = lang_part.strip('{}.')
                language = lang_part.split()[0] if lang_part else None

        # Find closing fence
        code_lines = []
        end_line = start_line + 1

        while end_line < len(lines):
            if lines[end_line].strip().startswith('```'):
                break
            code_lines.append(lines[end_line])
            end_line += 1

        if end_line >= len(lines):
            # No closing fence found
            return None

        # Extract content
        content = '\n'.join(code_lines)

        # Check if snippet should be skipped
        if self._should_skip_snippet(content, language):
            return None

        # Extract context
        heading_context = extract_heading_context(lines, start_line)
        preceding_text = extract_preceding_text(lines, start_line)

        # Calculate char offsets
        char_start = start_char_offset
        char_end = char_start + sum(len(lines[i]) + 1 for i in range(start_line, end_line + 1))

        return DiscoveredSnippet(
            ordinal=ordinal,
            content=content,
            snippet_type='fence',
            language=language,
            line_start=start_line,
            line_end=end_line,
            char_offset_start=char_start,
            char_offset_end=char_end,
            heading_context=heading_context,
            preceding_text=preceding_text
        )

    def _extract_gist_snippet(self, lines: List[str], line_idx: int,
                            char_offset: int, ordinal: int) -> Optional[DiscoveredSnippet]:
        """
        Extract a gist shortcode snippet and fetch its real content.

        NEW BEHAVIOR: Fetches actual gist code from GitHub API, not just the shortcode.
        - Parses shortcode to extract gist_id, owner, filename
        - Fetches gist content via GistService
        - Returns real C# code for validation
        - Skips non-C# gists or fetch failures with recorded reason

        Args:
            lines: File lines
            line_idx: Line where gist shortcode is
            char_offset: Character offset
            ordinal: Snippet ordinal (1-indexed)

        Returns:
            DiscoveredSnippet with real code content, or None if should be skipped
        """
        line = lines[line_idx]
        shortcode_original = line.strip()  # Preserve exact shortcode for patching

        # Parse gist shortcode using GistService
        parse_result = self.gist_service.parse_gist_shortcode(shortcode_original)

        if not parse_result:
            # Malformed shortcode, skip
            print(f"[!] Failed to parse gist shortcode at line {line_idx + 1}: {shortcode_original}")
            return None

        owner, gist_id, filename = parse_result

        # Fetch gist content from GitHub API (or cache)
        fetch_result = self.gist_service.fetch_gist(gist_id, owner, filename)

        # Handle fetch failures and skip cases
        if not fetch_result.success:
            if fetch_result.skip_reason:
                # Gist was fetched but should be skipped (non-C#, ambiguous, etc.)
                print(f"[i] Skipping gist {gist_id}: {fetch_result.skip_reason}")
            elif fetch_result.error:
                # Fetch error (rate limit, network, etc.)
                print(f"[!] Error fetching gist {gist_id}: {fetch_result.error}")
            return None  # Skip this gist

        # Successfully fetched gist content
        content = fetch_result.content
        gist_filename = fetch_result.filename
        language = fetch_result.language or 'csharp'  # Default to csharp if GitHub didn't detect

        # Extract context from markdown
        heading_context = extract_heading_context(lines, line_idx)
        preceding_text = extract_preceding_text(lines, line_idx)

        char_end = char_offset + len(line) + 1

        # Check if gist code should be validated (same rules as fenced code)
        if self._should_skip_snippet(content, language):
            print(f"[i] Skipping gist {gist_id}: code doesn't meet C# validation criteria")
            return None

        return DiscoveredSnippet(
            ordinal=ordinal,
            content=content,  # REAL gist code, not shortcode
            snippet_type='gist',
            language=language,
            line_start=line_idx,
            line_end=line_idx,
            char_offset_start=char_offset,
            char_offset_end=char_end,
            heading_context=heading_context,
            preceding_text=preceding_text,
            gist_id=gist_id,
            gist_file=gist_filename,
            gist_shortcode_original=shortcode_original  # Preserve for patching
        )

    def get_discovery_stats(self, family: str) -> Dict[str, any]:
        """
        Get discovery statistics for a family.

        Args:
            family: Product family

        Returns:
            Statistics dictionary
        """
        stats = self.db.get_family_statistics(family)
        return stats
