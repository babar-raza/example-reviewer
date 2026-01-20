"""
Discovery Service for Example Reviewer Pipeline.
Implements Phase A: Discovery and Extraction.
"""

import re
import hashlib
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Generator
from glob import glob
import fnmatch

from ..core.models import ExampleRecord, ExampleStatus, SourceType, Location, GistInfo
from ..core.database import Database
from ..core.config import FamilyConfig, DiscoveryPatternsConfig, GlobalConfig

logger = logging.getLogger(__name__)


# Regex patterns for code extraction
FENCE_PATTERN = re.compile(
    r'^```(\w*)\s*\n(.*?)^```',
    re.MULTILINE | re.DOTALL
)

GIST_SHORTCODE_PATTERN = re.compile(
    r'\{\{<\s*gist\s+([^\s]+)\s+([^\s]+)(?:\s+["\']?([^"\'>\s]+)["\']?)?\s*>\}\}',
    re.IGNORECASE
)

GIST_SCRIPT_PATTERN = re.compile(
    r'<script\s+src=["\']https://gist\.github\.com/([^/]+)/([^.]+)\.js(?:\?file=([^"\']+))?["\']',
    re.IGNORECASE
)

# Languages we want to validate (primarily C#)
VALIDATABLE_LANGUAGES = {'cs', 'csharp', 'c#'}


class DiscoveryService:
    """
    Service for discovering and extracting code examples from markdown files.
    Implements the A_discovery_extraction phase from the spec.
    """

    def __init__(
        self,
        db: Database,
        content_roots: Optional[List[str]] = None,
        filtering_config: Optional[DiscoveryPatternsConfig] = None,
        global_config: Optional[GlobalConfig] = None,
        family_config: Optional[FamilyConfig] = None,
    ):
        """
        Initialize discovery service.

        Args:
            db: Database instance
            content_roots: List of content root directories to scan
            filtering_config: Optional filtering configuration (uses defaults if not provided)
            global_config: Global configuration
            family_config: Family-specific configuration
        """
        self.db = db
        self.content_roots = content_roots or []
        self.filtering_config = filtering_config or DiscoveryPatternsConfig()
        self.global_config = global_config
        self.family_config = family_config
        self.filter_stats = {
            'total_checked': 0,
            'filtered_out': 0,
            'reasons': {},
            'filtered_gists': 0,
        }
        self._legacy_schema: Optional[bool] = None

        # Get effective discovery patterns (family overrides global)
        self.discovery_patterns = self._get_effective_discovery_patterns()

        # Compile fence patterns with safety checks
        self.compiled_fence_patterns = self._compile_fence_patterns()

        # CD-03: Compile gist patterns with safety checks
        self.compiled_gist_shortcode_patterns = self._compile_gist_shortcode_patterns()
        self.compiled_gist_script_patterns = self._compile_gist_script_patterns()

    def _get_effective_discovery_patterns(self) -> DiscoveryPatternsConfig:
        """Get effective discovery patterns (family overrides global)."""
        if self.family_config and self.family_config.discovery_patterns:
            return self.family_config.discovery_patterns
        if self.global_config and self.global_config.discovery_patterns:
            return self.global_config.discovery_patterns
        # Fallback to defaults
        return DiscoveryPatternsConfig()

    def _compile_fence_patterns(self) -> List[Any]:
        """Compile fence patterns with catastrophic backtracking prevention."""
        compiled = []
        for pattern in self.discovery_patterns.fence_patterns:
            try:
                compiled.append(re.compile(pattern, re.MULTILINE | re.DOTALL))
            except re.error as e:
                logger.error(f"Failed to compile fence pattern '{pattern}': {e}")
        return compiled or [FENCE_PATTERN]  # Fallback to default if all fail

    def _compile_gist_shortcode_patterns(self) -> List[Any]:
        """Compile gist shortcode patterns with error handling."""
        if not self.discovery_patterns.gist_extraction.enabled:
            return []

        compiled = self.discovery_patterns.gist_extraction.compile_shortcode_patterns()

        # Fallback to hardcoded pattern if all fail
        if not compiled:
            logger.warning("All gist shortcode patterns failed to compile, using fallback")
            compiled = [GIST_SHORTCODE_PATTERN]

        return compiled

    def _compile_gist_script_patterns(self) -> List[Any]:
        """Compile gist script tag patterns with error handling."""
        if not self.discovery_patterns.gist_extraction.enabled:
            return []

        compiled = self.discovery_patterns.gist_extraction.compile_script_patterns()

        # Fallback to hardcoded pattern if all fail
        if not compiled:
            logger.warning("All gist script patterns failed to compile, using fallback")
            compiled = [GIST_SCRIPT_PATTERN]

        return compiled

    def normalize_language(self, language_tag: str) -> str:
        """Normalize language tag to canonical form."""
        if not self.discovery_patterns.normalize_to_canonical:
            return language_tag

        tag_lower = language_tag.lower()
        for canonical, aliases in self.discovery_patterns.language_aliases.items():
            if tag_lower in [a.lower() for a in aliases]:
                return canonical

        return language_tag

    def _is_validatable_language(self, language_tag: str) -> bool:
        """Check if language is validatable (after normalization)."""
        normalized = self.normalize_language(language_tag)
        validatable_lower = [lang.lower() for lang in self.discovery_patterns.validatable_languages]
        return normalized.lower() in validatable_lower

    def filter_snippet(self, code: str, config: Optional[DiscoveryPatternsConfig] = None) -> Tuple[bool, str]:
        """
        Filter snippet based on content rules.

        Args:
            code: Code content to filter
            config: Optional filtering config (uses instance config if not provided)

        Returns:
            Tuple of (should_include: bool, reason: str)
        """
        if config is None:
            config = self.filtering_config

        self.filter_stats['total_checked'] += 1

        # Line count check
        lines = code.strip().split('\n')
        line_count = len(lines)

        if line_count < config.min_line_count:
            reason = f"Too short ({line_count} lines < {config.min_line_count})"
            self._track_filter_reason(reason)
            return False, reason

        if line_count > config.max_line_count:
            reason = f"Too long ({line_count} lines > {config.max_line_count})"
            self._track_filter_reason(reason)
            return False, reason

        # Content exclusion patterns
        for pattern in config.content_exclude_patterns:
            try:
                if re.search(pattern, code, re.MULTILINE):
                    reason = f"Matched exclusion pattern: {pattern}"
                    self._track_filter_reason(reason)
                    return False, reason
            except re.error as e:
                logger.warning(f"Invalid regex pattern '{pattern}': {e}")

        # Require code indicators (at least one must match)
        if config.require_code_indicators:
            has_indicator = False
            for pattern in config.require_code_indicators:
                try:
                    if re.search(pattern, code, re.MULTILINE | re.IGNORECASE):
                        has_indicator = True
                        break
                except re.error as e:
                    logger.warning(f"Invalid regex pattern '{pattern}': {e}")

            if not has_indicator:
                reason = "No C# code indicators found"
                self._track_filter_reason(reason)
                return False, reason

        return True, "Passed all filters"

    def _track_filter_reason(self, reason: str):
        """Track filter reason for statistics."""
        self.filter_stats['filtered_out'] += 1
        if reason not in self.filter_stats['reasons']:
            self.filter_stats['reasons'][reason] = 0
        self.filter_stats['reasons'][reason] += 1

    def get_filter_stats(self) -> Dict[str, Any]:
        """Get filter statistics."""
        return self.filter_stats.copy()

    def _extract_context(self, lines: List[str], code_start: int) -> Tuple[str, str]:
        """
        Extract context (heading and description) around code snippet with configurable settings.

        Args:
            lines: All lines of the markdown file
            code_start: Line index where the code block starts

        Returns:
            Tuple of (section_heading, description_context)
        """
        config = self.discovery_patterns.context_extraction

        # If context extraction is disabled, return empty strings
        if not config.enabled:
            return "", ""

        # Calculate the context window boundaries
        context_window_start = max(0, code_start - config.context_window_lines)
        context_window = lines[context_window_start:code_start]

        # Extract section heading within max_heading_distance
        section_heading = ""
        lines_to_check = min(len(context_window), config.max_heading_distance)
        for i in range(lines_to_check):
            line = context_window[-(i + 1)].strip()
            if line.startswith('#'):
                section_heading = line.lstrip('#').strip()
                break

        # Extract paragraphs
        paragraphs = []
        current_paragraph = []

        if config.max_paragraphs > 0:
            for i in range(len(context_window) - 1, -1, -1):
                line = context_window[i].strip()

                # Stop at headings or other code blocks
                if line.startswith('#') or line.startswith('```'):
                    break

                # Empty line signals paragraph break
                if not line:
                    if current_paragraph:
                        paragraphs.insert(0, ' '.join(reversed(current_paragraph)))
                        current_paragraph = []
                        if len(paragraphs) >= config.max_paragraphs:
                            break
                else:
                    current_paragraph.append(line)

            # Don't forget the last paragraph if not empty
            if current_paragraph and len(paragraphs) < config.max_paragraphs:
                paragraphs.insert(0, ' '.join(reversed(current_paragraph)))

        description_context = '\n\n'.join(paragraphs)

        # Include file header if configured
        if config.include_file_header:
            file_header = ""
            for line in lines[:10]:  # Check first 10 lines
                if line.strip().startswith('# '):
                    file_header = line.strip().lstrip('#').strip()
                    break

            if file_header and file_header != section_heading:
                # Prepend file header to description context
                if description_context:
                    description_context = f"File: {file_header}\n\n{description_context}"
                else:
                    description_context = f"File: {file_header}"

        # Filter by minimum context length
        if len(description_context) < config.min_context_length:
            description_context = ""

        return section_heading, description_context

    def _extract_topic_from_path(self, file_path: str) -> str:
        """
        Extract topic from file path.

        Args:
            file_path: Path to the markdown file

        Returns:
            Human-readable topic string
        """
        # Get filename without extension
        stem = Path(file_path).stem

        # Handle index files - use parent directory name
        if stem.lower() in ('index', '_index', 'readme'):
            parent = Path(file_path).parent.name
            stem = parent if parent else stem

        # Convert hyphens/underscores to spaces, remove common prefixes
        topic = stem.replace('-', ' ').replace('_', ' ')

        # Remove common prefixes like "how to"
        for prefix in ['how to ', 'how-to-']:
            if topic.lower().startswith(prefix):
                topic = topic[len(prefix):]

        return topic.strip()
    
    def discover_family(
        self,
        family: str,
        family_config: Optional[FamilyConfig] = None,
        max_files: Optional[int] = None,
        max_pages: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Discover all code examples for a family.
        
        Args:
            family: Family identifier
            family_config: Family configuration
            max_files: Maximum files to process (for testing)
            max_pages: Alias for max_files (legacy compatibility)
            
        Returns:
            Statistics dictionary
        """
        if family_config is None:
            family_config = FamilyConfig(family=family, content_roots=self.content_roots)

        if max_pages is not None and max_files is None:
            max_files = max_pages
        stats = {
            'files_found': 0,
            'files_processed': 0,
            'examples_found': 0,
            'inline_examples': 0,
            'gist_examples': 0,
            'errors': 0,
            'snippets_filtered_out': 0,
            'filter_reasons': {},
            'filtered_gists': 0,
        }

        # Update family config for this discovery run (enables family-specific overrides)
        self.family_config = family_config
        self.discovery_patterns = self._get_effective_discovery_patterns()
        self.compiled_fence_patterns = self._compile_fence_patterns()

        # CD-03: Recompile gist patterns for family-specific overrides
        self.compiled_gist_shortcode_patterns = self._compile_gist_shortcode_patterns()
        self.compiled_gist_script_patterns = self._compile_gist_script_patterns()

        # Get files to process
        files = self._find_markdown_files(family_config)
        stats['files_found'] = len(files)
        
        if max_files:
            files = files[:max_files]
        
        logger.info(f"Processing {len(files)} files for family {family}")
        
        for file_path in files:
            try:
                examples = self._process_file(file_path, family)

                if self._uses_legacy_schema():
                    self._save_examples_legacy(file_path, family, examples)
                    stats['examples_found'] += len(examples)
                    stats['inline_examples'] += sum(1 for e in examples if e.source_type == SourceType.INLINE)
                    stats['gist_examples'] += sum(1 for e in examples if e.source_type != SourceType.INLINE)
                else:
                    for example in examples:
                        self.db.save_example(example)
                        stats['examples_found'] += 1
                        
                        if example.source_type == SourceType.INLINE:
                            stats['inline_examples'] += 1
                        else:
                            stats['gist_examples'] += 1
                
                stats['files_processed'] += 1

            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                stats['errors'] += 1

        # Add filter statistics
        filter_stats = self.get_filter_stats()
        stats['snippets_filtered_out'] = filter_stats['filtered_out']
        stats['filter_reasons'] = filter_stats['reasons']
        stats['filtered_gists'] = filter_stats['filtered_gists']

        stats['pages_scanned'] = stats['files_processed']
        stats['snippets_found'] = stats['examples_found']

        logger.info(f"Discovery complete: {stats['examples_found']} examples found, {stats['snippets_filtered_out']} snippets filtered out, {stats['filtered_gists']} gists filtered out")

        return stats

    def _uses_legacy_schema(self) -> bool:
        if self._legacy_schema is not None:
            return self._legacy_schema
        try:
            with self.db.get_connection() as conn:
                row = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='example_records'"
                ).fetchone()
                self._legacy_schema = row is None
        except Exception:
            self._legacy_schema = False
        return self._legacy_schema

    def _save_examples_legacy(self, file_path: str, family: str, examples: List[ExampleRecord]) -> None:
        conn = self.db.connect()
        file_path_obj = Path(file_path)
        relative_path = file_path_obj.as_posix()
        for root in self.content_roots:
            try:
                relative_path = file_path_obj.relative_to(root).as_posix()
                break
            except Exception:
                continue
        site = "blog" if "blog.aspose.net" in file_path_obj.as_posix() else "docs"

        row = conn.execute(
            "SELECT page_id FROM pages WHERE file_path = ?",
            (file_path,),
        ).fetchone()
        if row:
            page_id = row[0]
        else:
            result = conn.execute(
                """
                INSERT INTO pages (file_path, relative_path, site, family, state)
                VALUES (?, ?, ?, ?, 'scanned')
                """,
                (file_path, relative_path, site, family),
            )
            page_id = result.lastrowid

        for example in examples:
            snippet_ordinal = example.location.block_index + 1
            locator = {"snippet_ordinal": snippet_ordinal}
            if example.section_heading:
                locator["heading_context"] = [example.section_heading]
            locator_json = json.dumps(locator)
            snippet_type = "fence" if example.source_type == SourceType.INLINE else "gist"

            result = conn.execute(
                """
                INSERT OR REPLACE INTO snippets (
                    page_id, snippet_ordinal, locator_json,
                    snippet_type, language, status
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (page_id, snippet_ordinal, locator_json, snippet_type, example.language, "unverified"),
            )
            snippet_id = result.lastrowid

            content_hash = hashlib.sha256((example.original_code or "").encode("utf-8")).hexdigest()
            conn.execute(
                """
                INSERT INTO snippet_versions (
                    snippet_id, version_type, code_content, content_hash
                ) VALUES (?, 'original', ?, ?)
                """,
                (snippet_id, example.original_code or "", content_hash),
            )

        conn.commit()

    def _find_markdown_files(self, family_config: FamilyConfig) -> List[str]:
        """Find all markdown files matching family patterns."""
        files = []
        
        # Use content roots from config or instance
        content_roots = family_config.content_roots or self.content_roots
        
        for root in content_roots:
            root_path = Path(root)
            if not root_path.exists():
                logger.warning(f"Content root does not exist: {root}")
                continue
            
            # If patterns defined, use them
            if family_config.content_pattern:
                for site, pattern in family_config.content_pattern.items():
                    full_pattern = str(root_path / pattern)
                    matched = glob(full_pattern, recursive=True)
                    files.extend(matched)
            else:
                # Default: find all .md files (sorted deterministically)
                files.extend(str(p) for p in sorted(root_path.rglob("*.md"), key=lambda p: str(p).lower()))

        # Sort final file list deterministically (case-normalized for Windows compatibility)
        return sorted(set(files), key=lambda f: f.lower())
    
    def _process_file(self, file_path: str, family: str) -> List[ExampleRecord]:
        """
        Process a single markdown file and extract code examples.
        
        Args:
            file_path: Path to markdown file
            family: Family identifier
            
        Returns:
            List of extracted ExampleRecord objects
        """
        examples = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract inline code examples
        inline_examples = self._extract_inline_examples(content, file_path, family)
        examples.extend(inline_examples)
        
        # Extract gist examples
        gist_examples = self._extract_gist_examples(content, file_path, family)
        examples.extend(gist_examples)
        
        return examples
    
    def _extract_inline_examples(
        self,
        content: str,
        file_path: str,
        family: str
    ) -> List[ExampleRecord]:
        """Extract inline fenced code blocks with content context."""
        examples = []
        lines = content.split('\n')

        # Extract topic once for the file
        topic = self._extract_topic_from_path(file_path)

        block_index = 0
        in_code_block = False
        code_start_line = 0
        code_language = ''
        code_lines = []

        for i, line in enumerate(lines):
            if line.startswith('```') and not in_code_block:
                # Start of code block
                in_code_block = True
                code_start_line = i + 1
                code_language = line[3:].strip().lower()
                code_lines = []

            elif line.startswith('```') and in_code_block:
                # End of code block
                in_code_block = False
                code_content = '\n'.join(code_lines)

                # Only include validatable languages (using configurable patterns)
                if self._is_validatable_language(code_language) and code_content.strip():
                    # CD-02: Apply content-based filtering
                    should_include, filter_reason = self.filter_snippet(code_content)

                    if not should_include:
                        logger.debug(f"Filtered out snippet at {file_path}:{code_start_line} - {filter_reason}")
                        block_index += 1
                        continue

                    # Normalize language tag to canonical form
                    normalized_language = self.normalize_language(code_language)

                    # Extract content context for LLM relevance preservation
                    # code_start_line is 1-indexed, but we need 0-indexed for array access
                    fence_start_idx = code_start_line - 1  # Index of the ``` line
                    section_heading, description_context = self._extract_context(lines, fence_start_idx)

                    example = ExampleRecord(
                        family=family,
                        file_path=file_path,
                        source_type=SourceType.INLINE,
                        language=normalized_language,
                        location=Location(
                            block_index=block_index,
                            start_line=code_start_line,
                            end_line=i + 1,
                        ),
                        original_code=code_content,
                        status=ExampleStatus.DISCOVERED,
                        # Content context fields
                        section_heading=section_heading or None,
                        description_context=description_context or None,
                        topic=topic or None,
                    )
                    # Generate ID is called in model_post_init
                    examples.append(example)

                block_index += 1

            elif in_code_block:
                code_lines.append(line)

        return examples
    
    def _extract_gist_examples(
        self,
        content: str,
        file_path: str,
        family: str
    ) -> List[ExampleRecord]:
        """Extract gist shortcode references with content context."""
        examples = []

        # CD-03: Check if gist extraction is enabled
        if not self.discovery_patterns.gist_extraction.enabled:
            return examples

        lines = content.split('\n')

        # Extract topic once for the file
        topic = self._extract_topic_from_path(file_path)

        # CD-03: Use configurable shortcode patterns
        for i, line in enumerate(lines):
            # Try all configured shortcode patterns
            for pattern in self.compiled_gist_shortcode_patterns:
                for match in pattern.finditer(line):
                    owner = match.group(1)
                    gist_id = match.group(2)
                    filename = match.group(3) if match.lastindex >= 3 else ""
                    filename = filename or ""

                    # CD-03: Apply owner filtering
                    should_include, filter_reason = self.discovery_patterns.gist_extraction.should_include_owner(owner)
                    if not should_include:
                        logger.debug(f"Filtered out gist {owner}/{gist_id} at {file_path}:{i+1} - {filter_reason}")
                        self.filter_stats['filtered_gists'] += 1
                        continue

                    # Generate example ID from gist reference
                    ref_str = f"{owner}/{gist_id}/{filename}"
                    example_id = hashlib.sha256(
                        f"{file_path}:{ref_str}".encode()
                    ).hexdigest()[:16]

                    # Extract content context
                    section_heading, description_context = self._extract_context(lines, i)

                    example = ExampleRecord(
                        example_id=example_id,
                        family=family,
                        file_path=file_path,
                        source_type=SourceType.GIST,
                        language='csharp',  # Assume C# for now
                        location=Location(
                            block_index=-1,  # Not applicable for gists
                            start_line=i + 1,
                            end_line=i + 1,
                        ),
                        gist=GistInfo(
                            owner=owner,
                            gist_id=gist_id,
                            filename=filename,
                        ),
                        original_code="",  # Will be fetched later
                        status=ExampleStatus.DISCOVERED,
                        # Content context fields
                        section_heading=section_heading or None,
                        description_context=description_context or None,
                        topic=topic or None,
                    )
                    examples.append(example)

            # CD-03: Try all configured script tag patterns
            for pattern in self.compiled_gist_script_patterns:
                for match in pattern.finditer(line):
                    owner = match.group(1)
                    gist_id = match.group(2)
                    filename = match.group(3) if match.lastindex >= 3 else ""
                    filename = filename or ""

                    # CD-03: Apply owner filtering
                    should_include, filter_reason = self.discovery_patterns.gist_extraction.should_include_owner(owner)
                    if not should_include:
                        logger.debug(f"Filtered out gist script {owner}/{gist_id} at {file_path}:{i+1} - {filter_reason}")
                        self.filter_stats['filtered_gists'] += 1
                        continue

                    # Generate example ID from gist reference
                    ref_str = f"{owner}/{gist_id}/{filename}"
                    example_id = hashlib.sha256(
                        f"{file_path}:{ref_str}".encode()
                    ).hexdigest()[:16]

                    # Extract content context
                    section_heading, description_context = self._extract_context(lines, i)

                    example = ExampleRecord(
                        example_id=example_id,
                        family=family,
                        file_path=file_path,
                        source_type=SourceType.GIST,
                        language='csharp',  # Assume C# for now
                        location=Location(
                            block_index=-1,  # Not applicable for gists
                            start_line=i + 1,
                            end_line=i + 1,
                        ),
                        gist=GistInfo(
                            owner=owner,
                            gist_id=gist_id,
                            filename=filename,
                        ),
                        original_code="",  # Will be fetched later
                        status=ExampleStatus.DISCOVERED,
                        # Content context fields
                        section_heading=section_heading or None,
                        description_context=description_context or None,
                        topic=topic or None,
                    )
                    examples.append(example)

        return examples
    
    def discover_directory(
        self,
        directory: str,
        family: str,
        recursive: bool = True,
    ) -> Dict[str, Any]:
        """
        Discover examples from a directory (for directory mode scan).
        
        Args:
            directory: Directory path
            family: Family identifier
            recursive: Whether to scan recursively
            
        Returns:
            Statistics dictionary
        """
        stats = {
            'files_found': 0,
            'files_processed': 0,
            'examples_found': 0,
            'errors': 0,
        }
        
        dir_path = Path(directory)
        if not dir_path.exists():
            logger.error(f"Directory does not exist: {directory}")
            return stats
        
        if recursive:
            # Sort glob results deterministically (case-normalized for Windows compatibility)
            files = sorted(dir_path.rglob("*.md"), key=lambda p: str(p).lower())
        else:
            # Sort glob results deterministically (case-normalized for Windows compatibility)
            files = sorted(dir_path.glob("*.md"), key=lambda p: str(p).lower())

        stats['files_found'] = len(files)
        
        for file_path in files:
            try:
                examples = self._process_file(str(file_path), family)
                
                for example in examples:
                    self.db.save_example(example)
                    stats['examples_found'] += 1
                
                stats['files_processed'] += 1
                
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                stats['errors'] += 1
        
        return stats


class GistResolver:
    """
    Resolves gist content from GitHub Gist API.
    """
    
    def __init__(self, token: Optional[str] = None):
        """
        Initialize gist resolver.
        
        Args:
            token: GitHub personal access token (optional)
        """
        self.token = token
        self._cache: Dict[str, str] = {}
    
    def resolve_gist(
        self,
        owner: str,
        gist_id: str,
        filename: Optional[str] = None
    ) -> Optional[str]:
        """
        Fetch gist content from GitHub.
        
        Args:
            owner: Gist owner
            gist_id: Gist ID
            filename: Specific file in the gist
            
        Returns:
            Gist content or None if not found
        """
        cache_key = f"{owner}/{gist_id}/{filename or ''}"
        
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            import urllib.request
            import json
            
            url = f"https://api.github.com/gists/{gist_id}"
            headers = {"Accept": "application/vnd.github.v3+json"}
            
            if self.token:
                headers["Authorization"] = f"token {self.token}"
            
            req = urllib.request.Request(url, headers=headers)
            
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
            
            files = data.get('files', {})
            
            if filename and filename in files:
                content = files[filename].get('content', '')
            elif files:
                # Return first file if no specific filename
                first_file = next(iter(files.values()))
                content = first_file.get('content', '')
            else:
                content = None
            
            self._cache[cache_key] = content
            return content
            
        except Exception as e:
            logger.error(f"Failed to fetch gist {gist_id}: {e}")
            return None
