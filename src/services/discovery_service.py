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
from ..pipeline.app_context_classifier import classify_app_context
from ..utils.markdown_parser import parse_fenced_blocks, compute_code_signature, normalize_language_tag

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

    # Task 1: Minimum meaningful lines threshold
    MIN_MEANINGFUL_LINES = 3

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
        # Task 1: Track skipped candidates for reporting
        self.skipped_candidates: List[Dict[str, Any]] = []

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

    def _validate_extraction(self, code: str) -> Tuple[bool, str]:
        """
        Quick syntax validation to catch malformed extractions (TASK-R5).

        Checks for common CS1001 errors without full parsing:
        - Incomplete control flow statements
        - Unbalanced braces

        Args:
            code: Code content to validate

        Returns:
            Tuple of (is_valid: bool, reason: str if invalid)
        """
        # Check 1: Incomplete control flow statements (foreach/for/if/while with unclosed parens)
        # Matches: "foreach (var item in" or "if (condition" without closing ")"
        incomplete_pattern = r'\b(foreach|for|if|while)\s*\([^)]*$'
        if re.search(incomplete_pattern, code, re.MULTILINE):
            return False, "malformed_extraction_incomplete_statement"

        # Check 2: Unbalanced braces
        # Count opening and closing braces (excluding those in strings/comments)
        # Simplified version - doesn't handle all edge cases but catches obvious issues
        code_without_strings = re.sub(r'"(?:[^"\\]|\\.)*"', '', code)  # Remove string literals
        code_without_strings = re.sub(r"'(?:[^'\\]|\\.)*'", '', code_without_strings)  # Remove char literals
        code_without_comments = re.sub(r'//.*$', '', code_without_strings, flags=re.MULTILINE)  # Remove line comments
        code_without_comments = re.sub(r'/\*.*?\*/', '', code_without_comments, flags=re.DOTALL)  # Remove block comments

        open_braces = code_without_comments.count('{')
        close_braces = code_without_comments.count('}')

        if open_braces != close_braces:
            return False, f"malformed_extraction_unbalanced_braces (open:{open_braces}, close:{close_braces})"

        return True, ""

    def _is_meaningful_code(self, code: str) -> Tuple[bool, str]:
        """
        Check if code is meaningful (not empty, whitespace-only, or comment-only).

        Task 1: Skip empty/incomplete snippets from the denominator.

        Args:
            code: Code content to check

        Returns:
            Tuple of (is_meaningful: bool, reason: str if not meaningful)
        """
        if not code or not code.strip():
            return False, "empty_code"

        lines = code.strip().split('\n')

        # Count non-empty, non-comment lines
        meaningful_lines = []
        for line in lines:
            stripped = line.strip()
            # Skip empty lines
            if not stripped:
                continue
            # Skip single-line comments
            if stripped.startswith('//') or stripped.startswith('#'):
                continue
            # Skip block comment markers
            if stripped.startswith('/*') or stripped.startswith('*/') or stripped.startswith('*'):
                continue
            meaningful_lines.append(stripped)

        if len(meaningful_lines) < self.MIN_MEANINGFUL_LINES:
            return False, f"snippet_too_incomplete (only {len(meaningful_lines)} meaningful lines)"

        return True, ""

    def _record_skipped_candidate(
        self,
        file_path: str,
        line_number: int,
        reason: str,
        code_preview: str = ""
    ) -> None:
        """
        Record a skipped candidate for the skipped_candidates artifact.

        Args:
            file_path: Path to the source file
            line_number: Line number where the code block starts
            reason: Reason for skipping
            code_preview: First 100 chars of code (for debugging)
        """
        self.skipped_candidates.append({
            'file_path': file_path,
            'line_number': line_number,
            'reason': reason,
            'code_preview': code_preview[:100] if code_preview else '',
        })

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

        # Task 1: First check if code is meaningful (not empty/comment-only)
        is_meaningful, reason = self._is_meaningful_code(code)
        if not is_meaningful:
            self._track_filter_reason(reason)
            return False, reason

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

    def export_skipped_candidates(self, run_id: str, artifacts_dir: Path) -> Path:
        """
        Export skipped candidates to JSON artifact.

        Task 1: Creates artifacts/runs/<run_id>/skipped_candidates.json

        Args:
            run_id: Current run ID
            artifacts_dir: Base artifacts directory

        Returns:
            Path to the exported JSON file
        """
        import json
        from datetime import datetime

        output_dir = artifacts_dir / "runs" / run_id
        output_dir.mkdir(parents=True, exist_ok=True)

        output_path = output_dir / "skipped_candidates.json"

        # Group by reason for summary
        reason_counts: Dict[str, int] = {}
        for candidate in self.skipped_candidates:
            reason = candidate.get('reason', 'unknown')
            # Normalize reason for counting (remove variable parts)
            if reason.startswith('snippet_too_incomplete'):
                base_reason = 'snippet_too_incomplete'
            else:
                base_reason = reason
            reason_counts[base_reason] = reason_counts.get(base_reason, 0) + 1

        data = {
            'run_id': run_id,
            'generated_at': datetime.utcnow().isoformat(),
            'total_skipped': len(self.skipped_candidates),
            'reason_summary': reason_counts,
            'skipped_candidates': self.skipped_candidates,
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

        logger.info(f"Exported {len(self.skipped_candidates)} skipped candidates to {output_path}")
        return output_path

    def clear_skipped_candidates(self) -> None:
        """Clear skipped candidates list for a new run."""
        self.skipped_candidates = []

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

    def _compute_code_signature(self, code: str) -> str:
        """
        Compute SHA256 signature of normalized code content.

        Normalization:
        - Strip leading/trailing whitespace from the entire block
        - Consistent line endings (LF)

        Args:
            code: Code content

        Returns:
            SHA256 hex digest (full 64 chars)
        """
        # Normalize: strip and use consistent line endings
        normalized = code.strip().replace('\r\n', '\n')
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

    def detect_foreign_families(self, code: str, current_family: str) -> List[str]:
        """
        Detect if code references families other than the current family,
        or uses external libraries, or references invalid Aspose namespaces.

        Args:
            code: C# code to analyze
            current_family: Current family being processed (e.g., 'words')

        Returns:
            List of foreign family names detected (e.g., ['cells', 'pdf'])
            or external libraries (e.g., ['external_microsoft_ml'])
            or invalid namespaces (e.g., ['invalid_namespace_watermarking'])
        """
        foreign = []

        # Family markers: using statements and namespace-qualified references
        # CRITICAL FIX: Removed ambiguous patterns (new Document, new Image) that match multiple families
        # Now using ONLY strong indicators: "using X" statements and "X.Y." namespaced references
        family_markers = {
            'cells': [
                'using Aspose.Cells',
                'Aspose.Cells.',
                'new Workbook(',  # Cells-specific
                'WorksheetCollection',
            ],
            'pdf': [
                'using Aspose.PDF',
                'using Aspose.Pdf',
                'Aspose.PDF.',
                'Aspose.Pdf.',
                'PdfFileEditor',  # PDF-specific
                # REMOVED: 'new Document(' - ambiguous with Words.Document
            ],
            'slides': [
                'using Aspose.Slides',
                'Aspose.Slides.',
                'new Presentation(',  # Slides-specific
                'ISlide',
            ],
            'email': [
                'using Aspose.Email',
                'Aspose.Email.',
                'new MailMessage(',  # Email-specific
                'SmtpClient',
            ],
            'imaging': [
                'using Aspose.Imaging',
                'Aspose.Imaging.',
                # REMOVED: 'new Image(' - ambiguous with System.Drawing.Image
            ],
            'zip': [
                'using Aspose.Zip',
                'Aspose.Zip.',
                # Keep 'new Archive(' - not used in Words
            ],
        }

        # External library patterns (TASK-R7)
        external_markers = {
            'microsoft_ml': ['using Microsoft.ML', 'Microsoft.ML.'],
            'aws': ['using Amazon.', 'Amazon.'],
            'google': ['using Google.', 'Google.'],
            'svg': ['using Svg', 'Svg.'],
            'newtonsoft': ['using Newtonsoft.', 'Newtonsoft.'],
        }

        # Invalid Aspose namespaces (known to not exist in assemblies)
        invalid_namespaces = {
            'words': ['Aspose.Words.Watermarking', 'Aspose.Words.Drawing.Charts'],
            # Add more as discovered during remediation
        }

        for family_name, markers in family_markers.items():
            if family_name != current_family:
                if any(marker in code for marker in markers):
                    foreign.append(family_name)

        # Check external libraries (TASK-R7)
        for lib_name, markers in external_markers.items():
            if any(marker in code for marker in markers):
                foreign.append(f'external_{lib_name}')

        # Check invalid namespaces for current family (TASK-R7)
        if current_family in invalid_namespaces:
            for invalid_ns in invalid_namespaces[current_family]:
                if invalid_ns in code:
                    # Extract last part of namespace for concise marker
                    ns_suffix = invalid_ns.split('.')[-1].lower()
                    foreign.append(f'invalid_namespace_{ns_suffix}')

        return foreign

    def discover_family(
        self,
        family: str,
        family_config: Optional[FamilyConfig] = None,
        max_files: Optional[int] = None,
        max_pages: Optional[int] = None,
        max_examples: Optional[int] = None,
        run_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Discover code examples for a family, up to max_examples limit.

        Discovery processes files sequentially until the specified number of examples
        is reached. This allows efficient discovery without processing unnecessary files.

        Args:
            family: Family identifier
            family_config: Family configuration
            max_files: Maximum files to process (for testing/scan commands)
            max_pages: Alias for max_files (legacy compatibility)
            max_examples: Maximum examples to discover (stops when reached)
            run_id: Run identifier for run-scoped tracking

        Returns:
            Statistics dictionary with examples_found, files_processed, etc.
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
            # Early exit: stop processing if we've reached the example limit
            if max_examples and stats['examples_found'] >= max_examples:
                logger.info(
                    f"Reached max_examples limit ({max_examples}) after processing "
                    f"{stats['files_processed']} files, stopping discovery"
                )
                break

            try:
                examples = self._process_file(file_path, family)

                if self._uses_legacy_schema():
                    # Legacy schema: bulk save (with potential truncation)
                    if max_examples:
                        remaining = max_examples - stats['examples_found']
                        examples = examples[:remaining]
                    self._save_examples_legacy(file_path, family, examples)
                    stats['examples_found'] += len(examples)
                    stats['inline_examples'] += sum(1 for e in examples if e.source_type == SourceType.INLINE)
                    stats['gist_examples'] += sum(1 for e in examples if e.source_type != SourceType.INLINE)
                else:
                    # Modern schema: individual save with per-example check
                    for example in examples:
                        if max_examples and stats['examples_found'] >= max_examples:
                            logger.info(
                                f"Reached max_examples limit ({max_examples}) within "
                                f"file {file_path}, stopping discovery"
                            )
                            break

                        self.db.save_example(example, run_id=run_id)
                        stats['examples_found'] += 1

                        if example.source_type == SourceType.INLINE:
                            stats['inline_examples'] += 1
                        else:
                            stats['gist_examples'] += 1

                stats['files_processed'] += 1

                # Check again after processing this file
                if max_examples and stats['examples_found'] >= max_examples:
                    logger.info(
                        f"Reached max_examples limit ({max_examples}), stopping discovery"
                    )
                    break

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
        import re as _re
        files = []

        # Use content roots from config or instance
        content_roots = family_config.content_roots or self.content_roots

        if family_config.content_pattern:
            # Pair each pattern with its corresponding root by position.
            # Keys ("blog", "kb") map 1:1 with content_roots by insertion order.
            pattern_entries = list(family_config.content_pattern.items())
            for i, (site, pattern) in enumerate(pattern_entries):
                if i >= len(content_roots):
                    logger.warning(f"Pattern '{site}' (index {i}) has no matching content root")
                    continue
                root_path = Path(content_roots[i])
                if not root_path.exists():
                    logger.warning(f"Content root does not exist: {root_path}")
                    continue
                full_pattern = str(root_path / pattern)
                matched = sorted(glob(full_pattern, recursive=True), key=lambda p: str(p).lower())
                logger.info(f"Pattern '{site}' on root [{i}]: {len(matched)} files from {root_path}")
                files.extend(matched)
        else:
            for root in content_roots:
                root_path = Path(root)
                if not root_path.exists():
                    logger.warning(f"Content root does not exist: {root}")
                    continue
                files.extend(str(p) for p in sorted(root_path.rglob("*.md"), key=lambda p: str(p).lower()))

        # Apply file exclusion patterns (defense-in-depth for non-English files)
        if family_config.file_exclude_patterns:
            exclude_res = [_re.compile(p) for p in family_config.file_exclude_patterns]
            before_count = len(files)
            files = [f for f in files if not any(r.search(f) for r in exclude_res)]
            excluded = before_count - len(files)
            if excluded > 0:
                logger.info(f"Excluded {excluded} files matching file_exclude_patterns")

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
        """
        Extract inline fenced code blocks with content context.

        CRITICAL: Uses canonical markdown parser to ensure block_index contract.
        The block_index is computed using parse_fenced_blocks() which counts ALL
        fenced blocks in the file, ensuring consistency with md_update.
        """
        examples = []
        lines = content.split('\n')

        # Extract topic once for the file
        topic = self._extract_topic_from_path(file_path)

        # CANONICAL PARSING: Use shared parser to ensure consistent block_index
        # This parser counts ALL fenced blocks (not just validatable languages)
        all_blocks = parse_fenced_blocks(content)

        # Process each block
        for block in all_blocks:
            code_language = block['language']
            code_content = block['content']
            code_start_line = block['start_line']
            code_end_line = block['end_line']
            block_index = block['block_index']  # CANONICAL: index among ALL blocks
            code_signature = block['signature']  # Pre-computed by parser

            # Only include validatable languages (using configurable patterns)
            if not self._is_validatable_language(code_language):
                # Skip non-validatable languages (but block_index still incremented in parser)
                continue

            if not code_content.strip():
                # Skip empty blocks
                continue

            # TASK-R5: Validate extraction syntax (before other filtering)
            is_valid, validation_reason = self._validate_extraction(code_content)
            if not is_valid:
                logger.info(f"Filtered out malformed snippet at {file_path}:{code_start_line} - {validation_reason}")
                self._record_skipped_candidate(
                    file_path=file_path,
                    line_number=code_start_line,
                    reason=validation_reason,
                    code_preview=code_content
                )
                # Track in filter stats for reporting
                self._track_filter_reason(validation_reason)
                continue

            # TASK-R1: Check for foreign family usage FIRST (before content filtering)
            foreign_families = self.detect_foreign_families(code_content, family)
            if foreign_families:
                filter_reason = f"foreign_family_{','.join(foreign_families)}"
                logger.info(f"Filtered out snippet at {file_path}:{code_start_line} - references foreign families: {', '.join(foreign_families)}")
                self._record_skipped_candidate(
                    file_path=file_path,
                    line_number=code_start_line,
                    reason=filter_reason,
                    code_preview=code_content
                )
                # Track in filter stats for reporting
                self._track_filter_reason(filter_reason)
                # Skip this block (but block_index already accounted for in all_blocks)
                continue

            # CD-02: Apply content-based filtering
            should_include, filter_reason = self.filter_snippet(code_content)

            if not should_include:
                logger.debug(f"Filtered out snippet at {file_path}:{code_start_line} - {filter_reason}")
                # Task 1: Record skipped candidate for artifact
                self._record_skipped_candidate(
                    file_path=file_path,
                    line_number=code_start_line,
                    reason=filter_reason,
                    code_preview=code_content
                )
                # Skip this block (but block_index already accounted for in all_blocks)
                continue

            # Normalize language tag to canonical form
            normalized_language = self.normalize_language(code_language)

            # Extract content context for LLM relevance preservation
            # code_start_line is 1-indexed, but we need 0-indexed for array access
            fence_start_idx = code_start_line - 1  # Index of the ``` line
            section_heading, description_context = self._extract_context(lines, fence_start_idx)

            # Classify application context (Phase-2 Gate B: prevent cross-context substitution)
            app_context = classify_app_context(code_content)

            example = ExampleRecord(
                family=family,
                file_path=file_path,
                source_type=SourceType.INLINE,
                language=normalized_language,
                location=Location(
                    block_index=block_index,  # CANONICAL: from shared parser
                    start_line=code_start_line,
                    end_line=code_end_line,
                ),
                original_code=code_content,
                status=ExampleStatus.DISCOVERED,
                # Content context fields
                section_heading=section_heading or None,
                description_context=description_context or None,
                topic=topic or None,
                app_context=app_context.value,
                # Code block location metadata (Migration 011)
                code_block_signature=code_signature,  # From canonical parser
            )
            # Generate ID is called in model_post_init
            examples.append(example)

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
