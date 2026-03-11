"""
Discovery Service for Example Reviewer Pipeline.
Implements Phase A: Discovery and Extraction.
"""

import re
import hashlib
import json
import logging
import yaml
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

    # P1-C: Placeholder path/key patterns
    PLACEHOLDER_PATTERNS = [
        r'"path[\\/]to[\\/]',
        r'"your[\s_-]',
        r'"YOUR_',
        r'@"[A-Z]:\\[^"]*path\\to',
        r'"<[^>]+>"',              # "<your-api-key>"
    ]

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

        # Check: Using-only snippets (no executable code beyond using/namespace declarations)
        executable_lines = [l for l in meaningful_lines
                            if not l.startswith('using ') and not l.startswith('namespace ')]
        if not executable_lines:
            return False, "using_only_snippet"

        # Check: Short fragments referencing undeclared variables (outer-context dependency)
        # Skip when allow_cross_block_variable_context is True (e.g. Words sequential tutorials)
        if len(meaningful_lines) <= 25 and not self.discovery_patterns.allow_cross_block_variable_context:
            if self._has_undeclared_loop_variables(code):
                return False, "fragment_outer_context"
            if self._has_undeclared_context_variables(code):
                return False, "fragment_undeclared_context_variable"

        # Check: Interface/class stubs with method signatures but no implementations
        if self._is_stub_definition(code):
            return False, "interface_stub_no_implementation"

        return True, ""

    def _has_undeclared_loop_variables(self, code: str) -> bool:
        """Detect foreach loops iterating over variables never declared in the snippet."""
        foreach_matches = re.findall(r'foreach\s*\([^)]*\bin\s+(\w+)\)', code)
        for var_name in foreach_matches:
            # Check if variable is declared anywhere before the foreach
            decl_pattern = rf'(?:var|string|int|bool|List|IEnumerable|string\[\]|Image\[\]|RasterImage\[\]|IList|ICollection)\s+{re.escape(var_name)}\b'
            assign_pattern = rf'\b{re.escape(var_name)}\s*='
            param_pattern = rf'\(\s*(?:[\w.<>\[\]]+\s+)*{re.escape(var_name)}\s*[,)]'
            if not re.search(decl_pattern, code) and not re.search(assign_pattern, code) and not re.search(param_pattern, code):
                return True
        return False

    def _has_undeclared_context_variables(self, code: str) -> bool:
        """Detect variables used but never declared in the snippet (broader than just loops)."""
        lines = code.strip().split('\n')
        meaningful = [l.strip() for l in lines if l.strip() and not l.strip().startswith('//')]

        # Find variables used at the START of statements in property/method access
        # Pattern: identifier.Something (at statement start, not after a type declaration)
        used_vars = set()
        for line in meaningful:
            # Match: varName.Property or varName.Method(
            m = re.match(r'\s*(\w+)\s*\.', line)
            if m:
                var = m.group(1)
                # Skip known keywords and type names
                if var not in ('var', 'string', 'int', 'bool', 'Console', 'File', 'Path',
                              'Directory', 'Environment', 'Math', 'Convert', 'Task', 'Thread',
                              'Image', 'Bitmap', 'Graphics', 'Color', 'new', 'return', 'if',
                              'for', 'foreach', 'while', 'using', 'await', 'this', 'base',
                              'typeof', 'nameof', 'sizeof', 'default'):
                    # Check if it looks like a type name (PascalCase with no prior declaration)
                    # Skip if it starts with uppercase and could be a static class call
                    if not var[0].isupper():
                        used_vars.add(var)

        if not used_vars:
            return False

        # Check if each used variable is declared somewhere in the snippet
        for var in used_vars:
            # Look for declaration: Type varName, var varName, varName =
            decl_found = False
            for line in meaningful:
                stripped = line.strip()
                # Assignment: var =
                if re.search(rf'\b{re.escape(var)}\s*=', stripped):
                    decl_found = True
                    break
                # Type declaration: SomeType varName
                if re.search(rf'(?:var|[\w.<>\[\]]+)\s+{re.escape(var)}\s*[=;,)]', stripped):
                    decl_found = True
                    break
                # Parameter: (Type varName
                if re.search(rf'\(\s*[\w.<>\[\]]+\s+{re.escape(var)}\s*[,)]', stripped):
                    decl_found = True
                    break
                # foreach: foreach (var varName in
                if re.search(rf'foreach\s*\(.*\b{re.escape(var)}\s+in\b', stripped):
                    decl_found = True
                    break
            if not decl_found:
                return True

        return False

    def _is_stub_definition(self, code: str) -> bool:
        """Detect class/interface with method signatures but no method bodies."""
        lines = code.strip().splitlines()
        meaningful = [l.strip() for l in lines if l.strip() and not l.strip().startswith('//')]
        # Must have class/interface declaration
        has_type_decl = any(re.match(r'(public\s+)?(abstract\s+)?(class|interface|struct)\s+\w+', l) for l in meaningful)
        if not has_type_decl:
            return False
        # Find method signatures (lines with return type + method name + parentheses)
        method_sig_pattern = r'^\s*(public|private|protected|internal)?\s*(static\s+)?(async\s+)?(override\s+)?(virtual\s+)?(void|Task|string|int|bool|[\w.<>]+)\s+\w+\s*\('
        method_sig_indices = [i for i, l in enumerate(meaningful) if re.match(method_sig_pattern, l)]
        if not method_sig_indices:
            return False
        # A method has no body if its signature line ends with ';' (abstract/interface),
        # OR ends with ')' and is NOT followed by a '{' in the next 1-2 meaningful lines.
        # This avoids false-positives for allman-brace style: "void Main()\n{"
        stubs_count = 0
        for idx in method_sig_indices:
            sig = meaningful[idx].rstrip()
            if sig.endswith(';'):
                stubs_count += 1
            elif sig.endswith(')'):
                # Check if opening brace appears within the next 2 meaningful lines
                next_lines = meaningful[idx + 1: idx + 3]
                if not any('{' in l for l in next_lines):
                    stubs_count += 1
            # A line ending with '{' already opens the body — not a stub
        return stubs_count == len(method_sig_indices)

    def _count_placeholder_indicators(self, code: str) -> int:
        """Count placeholder path/key indicators in code."""
        count = 0
        for pattern in self.PLACEHOLDER_PATTERNS:
            count += len(re.findall(pattern, code, re.IGNORECASE))
        return count

    def _is_license_only_example(self, code: str) -> bool:
        """Detect examples that primarily demonstrate license/metering setup."""
        lines = code.strip().split('\n')
        meaningful = [l.strip() for l in lines if l.strip() and not l.strip().startswith('//') and not l.strip().startswith('using ')]
        if len(meaningful) > 8:
            return False  # Only filter short license-only snippets
        has_metered = any('Metered' in l or 'SetMeteredKey' in l for l in meaningful)
        has_license = any('License' in l and ('SetLicense' in l or '.License(' in l or 'new License' in l) for l in meaningful)
        return has_metered or has_license

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

        # Check for excessive placeholder content
        placeholder_count = self._count_placeholder_indicators(code)
        if placeholder_count >= 3:
            self._track_filter_reason("excessive_placeholder_content")
            return False, "excessive_placeholder_content"

        # Check: Metered license examples (require API keys, always fail)
        if self._is_license_only_example(code):
            self._track_filter_reason("license_api_key_required")
            return False, "license_api_key_required"

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

    def _extract_frontmatter_intent(
        self,
        content: str,
        step_prefix: str = "step",
        intent_fields: Optional[List[str]] = None,
        fallback_to_prose: bool = False,
    ) -> Optional[str]:
        """
        Extract a compact intent string from YAML frontmatter or prose.

        Strategy 1: Parse YAML frontmatter if present (--- block). Extracts
        fields listed in intent_fields (default: title, description) and
        numbered step keys using step_prefix (default: step1..step10).

        Strategy 2: If Strategy 1 yields nothing and fallback_to_prose is True,
        extract H1 heading + first two prose paragraphs (capped at 600 chars).

        Returns:
            Compact intent string or None if nothing useful was found.
        """
        if intent_fields is None:
            intent_fields = ["title", "description"]

        # Strategy 1: YAML frontmatter
        if content.startswith('---'):
            rest = content[3:]
            end_idx = rest.find('\n---')
            if end_idx != -1:
                yaml_block = rest[:end_idx]
                try:
                    data = yaml.safe_load(yaml_block)
                except Exception:
                    data = None

                if isinstance(data, dict):
                    # Extract configured intent fields
                    field_values: Dict[str, str] = {}
                    for field_name in intent_fields:
                        val = data.get(field_name, '')
                        if val:
                            field_values[field_name] = str(val)

                    # Extract numbered steps using step_prefix
                    steps = []
                    for i in range(1, 11):
                        step = data.get(f'{step_prefix}{i}', '')
                        if not step:
                            break
                        steps.append(str(step))

                    if field_values or steps:
                        parts = []
                        # title gets "Title:" label, description gets "Summary:", others get capitalized key
                        title_val = field_values.get('title', '')
                        desc_val = field_values.get('description', '')
                        if title_val:
                            parts.append(f"Title: {title_val}")
                        if desc_val:
                            parts.append(f"Summary: {desc_val[:300]}")
                        for field_name, val in field_values.items():
                            if field_name not in ('title', 'description'):
                                parts.append(f"{field_name.capitalize()}: {val[:300]}")
                        if steps:
                            parts.append(f"Steps: {'; '.join(steps)}")
                        intent = '\n'.join(parts)
                        return intent[:800]

        # Strategy 2: Prose fallback
        if not fallback_to_prose:
            return None

        h1_title = None
        prose_paragraphs: List[str] = []
        lines = content.splitlines()
        past_h1 = False

        for line in lines:
            stripped = line.strip()
            if not past_h1:
                if stripped.startswith('# '):
                    h1_title = stripped[2:].strip()
                    past_h1 = True
            else:
                # Skip headings, fences, and empty lines while collecting prose
                if stripped.startswith('#') or stripped.startswith('```') or stripped.startswith('---'):
                    continue
                if stripped:
                    prose_paragraphs.append(stripped)
                    if len(prose_paragraphs) >= 2:
                        break

        if h1_title is None and not prose_paragraphs:
            return None

        prose_text = ' '.join(prose_paragraphs)
        parts = []
        if h1_title:
            parts.append(f"Title: {h1_title}")
        if prose_text:
            parts.append(f"Context: {prose_text[:400]}")

        intent = '\n'.join(parts)
        return intent[:600] if intent else None

    def _extract_product_calls(self, code: str, catalog) -> Optional[str]:
        """
        Scan framework-wrapper code for family API catalog calls.

        If the code contains calls to types in the family catalog, extract
        those lines as a minimal product-logic snippet. Returns None if no
        catalog types are found.

        P1 compliance: Detection uses catalog type names only, not hardcoded strings.
        P2 compliance: Generic mechanism -- family-specific harness wrapping is separate.

        Args:
            code: The framework-wrapper code (e.g., ASP.NET controller action)
            catalog: APICatalogService instance for the family

        Returns:
            Extracted product-relevant lines joined as string, or None
        """
        if not catalog:
            return None

        try:
            catalog_types = set(catalog.get_all_type_names() if hasattr(catalog, 'get_all_type_names') else [])
            if not catalog_types:
                return None
        except Exception:
            return None

        product_lines = []
        for line in code.split('\n'):
            stripped = line.strip()
            if not stripped or stripped.startswith('//') or stripped.startswith('*'):
                continue
            # Check if any catalog type appears in this line
            if any(t in line for t in catalog_types):
                product_lines.append(line)

        if not product_lines:
            return None

        return '\n'.join(product_lines)

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

        # External framework markers (not Aspose cross-family, but foreign frameworks)
        external_framework_markers = {
            'aspnet_mvc': ['Microsoft.AspNetCore.Mvc', ': Controller', ': ControllerBase'],
            'wpf': ['System.Windows.Presentation', 'xmlns:x='],
            'winforms': ['System.Windows.Forms', 'InitializeComponent()'],
            'blazor': ['Microsoft.AspNetCore.Components', '@page '],
        }
        for framework, markers in external_framework_markers.items():
            for marker in markers:
                if marker in code:
                    foreign.append(f"foreign_framework_{framework}")
                    break  # One match per framework is sufficient

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
            'cs_file_examples': 0,
            'errors': 0,
            'snippets_filtered_out': 0,
            'filter_reasons': {},
            'filtered_gists': 0,
        }

        # Update family config for this discovery run (enables family-specific overrides)
        self.family_config = family_config
        self.discovery_patterns = self._get_effective_discovery_patterns()
        # Sync filtering_config so filter_snippet() picks up family overrides
        # (e.g. require_code_indicators: [] in words.json)
        self.filtering_config = self.discovery_patterns
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
                    stats['gist_examples'] += sum(1 for e in examples if e.source_type == SourceType.GIST)
                    stats['cs_file_examples'] += sum(1 for e in examples if e.source_type == SourceType.CS_FILE)
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
                        elif example.source_type == SourceType.GIST:
                            stats['gist_examples'] += 1
                        elif example.source_type == SourceType.CS_FILE:
                            stats['cs_file_examples'] += 1

                stats['files_processed'] += 1

                # Track files that produced zero examples (Task 4 -- zero-example reporting)
                if not examples:
                    file_path_obj = Path(file_path)
                    file_skipped = [
                        s for s in self.skipped_candidates
                        if s.get('file_path') == str(file_path)
                    ]
                    reason_summary = ', '.join(
                        set(s.get('reason', 'unknown') for s in file_skipped)
                    ) or 'no extractable snippets'
                    logger.warning(
                        f"Zero examples from {file_path_obj.name} "
                        f"-- all snippets filtered ({reason_summary})"
                    )
                    if 'zero_example_files' not in stats:
                        stats['zero_example_files'] = []
                    stats['zero_example_files'].append({
                        'file': file_path_obj.name,
                        'reasons': reason_summary,
                    })

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

        # CS file discovery (for repos with standalone .cs example files)
        if family_config.cs_discovery.enabled:
            cs_stats = self._discover_cs_files(family, family_config, max_examples, run_id, stats)
            stats['cs_file_examples'] = cs_stats.get('cs_file_examples', 0)

        stats['pages_scanned'] = stats['files_processed']
        stats['snippets_found'] = stats['examples_found']

        logger.info(f"Discovery complete: {stats['examples_found']} examples found, {stats['snippets_filtered_out']} snippets filtered out, {stats['filtered_gists']} gists filtered out")

        zero_count = len(stats.get('zero_example_files', []))
        if zero_count > 0:
            logger.info(f"Discovery: {zero_count} files produced zero examples (see WARNING logs above)")

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
            snippet_type = {
                SourceType.INLINE: "fence",
                SourceType.GIST: "gist",
                SourceType.CS_FILE: "csfile"
            }.get(example.source_type, "fence")

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

    # ── CS File Discovery ──────────────────────────────────────────────

    def _discover_cs_files(
        self,
        family: str,
        family_config: FamilyConfig,
        max_examples: Optional[int],
        run_id: Optional[str],
        stats: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Discover examples from standalone .cs files using configurable extraction."""
        import re as _re
        cs_config = family_config.cs_discovery
        cs_stats = {'cs_file_examples': 0, 'cs_files_scanned': 0}

        roots = list(cs_config.roots)

        # Auto-resolve roots from example_repo if no explicit roots configured
        if not roots and family_config.example_repo.url:
            repo_root = self._resolve_example_repo_path(family, family_config)
            if repo_root:
                # If examples_path specified, use it as sub-root
                examples_path = family_config.example_repo.examples_path
                if examples_path:
                    candidate = repo_root / examples_path
                    if candidate.exists():
                        roots.append(str(candidate))
                    else:
                        roots.append(str(repo_root))
                else:
                    roots.append(str(repo_root))

        if not roots:
            logger.warning(f"CS discovery enabled for {family} but no roots resolved")
            return cs_stats

        for root in roots:
            root_path = Path(root)
            if not root_path.exists():
                logger.warning(f"CS discovery root does not exist: {root}")
                continue

            cs_files = sorted(root_path.rglob("*.cs"), key=lambda p: str(p).lower())
            logger.info(f"CS discovery: found {len(cs_files)} .cs files in {root}")

            for cs_file in cs_files:
                if max_examples and stats['examples_found'] >= max_examples:
                    logger.info(f"Reached max_examples limit ({max_examples}), stopping CS discovery")
                    break

                # Apply exclude patterns
                rel_path = str(cs_file.relative_to(root_path))
                if any(_re.search(pat, rel_path) for pat in cs_config.exclude_patterns):
                    continue

                try:
                    content = cs_file.read_text(encoding='utf-8-sig')
                except Exception as e:
                    logger.warning(f"Failed to read {cs_file}: {e}")
                    stats['errors'] += 1
                    continue

                cs_stats['cs_files_scanned'] += 1
                strategy = cs_config.extraction_strategy

                if strategy == 'exstart_exend':
                    examples = self._extract_exstart_examples(str(cs_file), content, family)
                elif strategy == 'whole_file':
                    examples = self._extract_whole_file_example(str(cs_file), content, family)
                elif strategy == 'run_method':
                    examples = self._extract_run_method_example(str(cs_file), content, family)
                else:
                    logger.warning(f"Unknown CS extraction strategy: {strategy}")
                    continue

                for example in examples:
                    if max_examples and stats['examples_found'] >= max_examples:
                        break
                    self.db.save_example(example, run_id=run_id)
                    stats['examples_found'] += 1
                    cs_stats['cs_file_examples'] += 1

                stats['files_processed'] += 1

        logger.info(f"CS discovery: {cs_stats['cs_file_examples']} examples from {cs_stats['cs_files_scanned']} files")
        return cs_stats

    def _extract_exstart_examples(
        self, file_path: str, content: str, family: str
    ) -> List[ExampleRecord]:
        """Extract examples from ExStart/ExEnd marker pairs."""
        examples = []
        # Match // ExStart:TagName ... // ExEnd:TagName (possibly with leading whitespace)
        pattern = re.compile(
            r'//\s*ExStart:(\S+)\s*\n(.*?)//\s*ExEnd:\1',
            re.DOTALL
        )

        parent_dir = Path(file_path).parent.name
        block_idx = 0

        for match in pattern.finditer(content):
            tag = match.group(1)
            code = match.group(2).rstrip()

            if not code.strip():
                continue

            # Skip nested/helper blocks (ExStart within ExStart typically means a sub-snippet)
            # Only keep blocks that contain substantive code (at least 3 non-empty lines)
            non_empty = [l for l in code.split('\n') if l.strip() and not l.strip().startswith('//')]
            if len(non_empty) < 2:
                continue

            code_signature = compute_code_signature(code)
            app_context = classify_app_context(code)

            example = ExampleRecord(
                family=family,
                file_path=file_path,
                source_type=SourceType.CS_FILE,
                language='csharp',
                location=Location(
                    block_index=block_idx,
                    start_line=content[:match.start()].count('\n') + 1,
                    end_line=content[:match.end()].count('\n') + 1,
                ),
                original_code=code,
                status=ExampleStatus.DISCOVERED,
                section_heading=parent_dir,
                topic=tag,
                app_context=app_context.value,
                code_block_signature=code_signature,
            )
            examples.append(example)
            block_idx += 1

        return examples

    def _extract_whole_file_example(
        self, file_path: str, content: str, family: str
    ) -> List[ExampleRecord]:
        """Treat the entire .cs file as one example."""
        if not content.strip():
            return []

        code_signature = compute_code_signature(content)
        app_context = classify_app_context(content)
        parent_dir = Path(file_path).parent.name
        topic = Path(file_path).stem

        example = ExampleRecord(
            family=family,
            file_path=file_path,
            source_type=SourceType.CS_FILE,
            language='csharp',
            location=Location(block_index=0, start_line=1, end_line=content.count('\n') + 1),
            original_code=content,
            status=ExampleStatus.DISCOVERED,
            section_heading=parent_dir,
            topic=topic,
            app_context=app_context.value,
            code_block_signature=code_signature,
        )
        return [example]

    def _extract_run_method_example(
        self, file_path: str, content: str, family: str
    ) -> List[ExampleRecord]:
        """Extract the Run() method body as the example."""
        match = re.search(
            r'public\s+static\s+void\s+Run\s*\(\s*\)\s*\{',
            content
        )
        if not match:
            return self._extract_whole_file_example(file_path, content, family)

        # Find matching closing brace
        start = match.end()
        depth = 1
        pos = start
        while pos < len(content) and depth > 0:
            if content[pos] == '{':
                depth += 1
            elif content[pos] == '}':
                depth -= 1
            pos += 1

        method_body = content[start:pos - 1].strip()
        if not method_body:
            return []

        code_signature = compute_code_signature(method_body)
        app_context = classify_app_context(method_body)
        parent_dir = Path(file_path).parent.name
        topic = Path(file_path).stem

        example = ExampleRecord(
            family=family,
            file_path=file_path,
            source_type=SourceType.CS_FILE,
            language='csharp',
            location=Location(
                block_index=0,
                start_line=content[:match.start()].count('\n') + 1,
                end_line=content[:pos].count('\n') + 1,
            ),
            original_code=method_body,
            status=ExampleStatus.DISCOVERED,
            section_heading=parent_dir,
            topic=topic,
            app_context=app_context.value,
            code_block_signature=code_signature,
        )
        return [example]

    def _resolve_example_repo_path(self, family: str, family_config: FamilyConfig) -> Optional[Path]:
        """Resolve example repo to a local path, cloning if needed."""
        url = family_config.example_repo.url
        ref = family_config.example_repo.ref or "master"
        if not url:
            return None

        repo_name = url.rstrip('/').split('/')[-1].replace('.git', '')
        cache_dir = Path(".cache/backfill") / family / repo_name

        if cache_dir.exists() and (cache_dir / '.git').exists():
            logger.info(f"Using cached example repo at {cache_dir}")
            return cache_dir

        # Attempt to clone via git CLI (no GitPython dependency required)
        try:
            import subprocess
            logger.info(f"Cloning example repo {url} (ref={ref}) to {cache_dir}")
            cache_dir.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                ["git", "clone", "--depth", "1", "--branch", ref, url, str(cache_dir)],
                check=True, capture_output=True, text=True, timeout=300,
            )
            logger.info(f"Successfully cloned {url} to {cache_dir}")
            return cache_dir
        except Exception as e:
            logger.warning(f"Failed to clone example repo: {e}")
            return None

    # ── Markdown File Discovery ───────────────────────────────────────

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

        # Extract article intent from YAML frontmatter or prose (once per file)
        article_intent = self._extract_frontmatter_intent(
            content,
            step_prefix=getattr(self.discovery_patterns, 'frontmatter_step_prefix', 'step'),
            intent_fields=getattr(self.discovery_patterns, 'frontmatter_intent_fields', ['title', 'description']),
            fallback_to_prose=getattr(self.discovery_patterns, 'intent_fallback_to_prose', True),
        )

        # Extract inline code examples
        inline_examples = self._extract_inline_examples(content, file_path, family, article_intent=article_intent)
        examples.extend(inline_examples)

        # Extract gist examples
        gist_examples = self._extract_gist_examples(content, file_path, family, article_intent=article_intent)
        examples.extend(gist_examples)

        return examples
    
    def _extract_inline_examples(
        self,
        content: str,
        file_path: str,
        family: str,
        article_intent: Optional[str] = None,
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
                # TODO (Task 4 -- Product Logic Extraction): Call _extract_product_calls() here
                # to extract product API calls from framework-wrapper snippets before discarding.
                # Only attempt if catalog is available and snippet was filtered for foreign_framework reason.
                # Example:
                #   if 'foreign_framework' in filter_reason and self._catalog:
                #       extracted = self._extract_product_calls(code_content, self._catalog)
                #       if extracted:
                #           ... synthesize harness and add to examples
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
                article_intent=article_intent or None,
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
        family: str,
        article_intent: Optional[str] = None,
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
                        article_intent=article_intent or None,
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
                        article_intent=article_intent or None,
                    )
                    examples.append(example)

        return examples
    


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
