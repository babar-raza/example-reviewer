"""
Example Substitution Service for Phase-2 Gate B remediation.

Automatically substitutes failing examples with verified examples from the example repository
when specific compile error patterns are detected.
"""

import json
import logging
import re
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

# Import app_context classifier for context-aware filtering
try:
    from ..pipeline.app_context_classifier import classify_app_context
except ImportError:
    # Fallback if classifier not available
    def classify_app_context(code: str) -> str:
        return "unknown"

logger = logging.getLogger(__name__)


class ExampleSubstitutionService:
    """
    Service for substituting code examples based on compile error patterns.

    Phase-2 Task 3: Implement automatic substitution for compile failures that match
    known patterns indicating wrong API usage (e.g., System.IO.Compression instead of Aspose.Zip).
    """

    # Compile error patterns that trigger substitution
    SUBSTITUTION_TRIGGERS = {
        # ZipArchiveMode errors indicate System.IO.Compression usage instead of Aspose.Zip
        r"(type|namespace).*'ZipArchiveMode'.*does not exist": {
            'reason': 'wrong_system_io_compression',
            'keywords': ['zip', 'archive', 'compression'],
            'avoid_classes': ['ZipArchiveMode'],  # Avoid these in substitutes
        },

        # Microsoft.AspNetCore errors in ZIP examples
        r"(type|namespace).*'Microsoft\.AspNetCore'": {
            'reason': 'wrong_aspnetcore_dependency',
            'keywords': ['zip', 'stream', 'memory'],
            'avoid_classes': ['IFormFile', 'AspNetCore'],
        },

        # CompressionLevel missing from wrong namespace
        r"(type|namespace).*'CompressionLevel'.*could not be found": {
            'reason': 'wrong_compression_namespace',
            'keywords': ['compression', 'deflate', 'settings'],
            'target_class': 'DeflateCompressionSettings',
        },

        # RAR-specific errors when RarArchiveLoadOptions missing
        r"(type|namespace).*'RarArchiveLoadOptions'.*could not be found": {
            'reason': 'missing_rar_loadoptions',
            'keywords': ['rar', 'password', 'decrypt'],
            'target_class': 'RarArchive',
        },

        # SevenZip-specific errors
        r"(type|namespace).*'SevenZipArchiveSaveOptions'.*could not be found": {
            'reason': 'missing_7z_saveoptions',
            'keywords': ['7z', 'sevenzip', 'compression'],
            'target_class': 'SevenZipArchive',
        },

        # ArchiveSaveOptions missing CompressionSettings
        r"(type|namespace).*'ArchiveSaveOptions'.*'CompressionSettings'": {
            'reason': 'missing_compression_settings',
            'keywords': ['archive', 'save', 'compression'],
            'target_class': 'Archive',
        },

        # Generic SevenZip namespace errors (e.g., using SevenZip; instead of Aspose.Zip.SevenZip;)
        r"(type|namespace).*'SevenZip'.*could not be found": {
            'reason': 'wrong_sevenzip_namespace',
            'keywords': ['7z', 'sevenzip', 'archive'],
            'target_class': 'SevenZipArchive',
        },

        # Generic RAR-related type errors (RarOptions, RarEntry, etc.)
        r"(type|namespace).*'Rar(Options|Entry|Archive)'.*could not be found": {
            'reason': 'missing_rar_types',
            'keywords': ['rar', 'extract', 'archive'],
            'target_class': 'RarArchive',
        },

        # Generic LoadOptions errors
        r"(type|namespace).*'LoadOptions'.*could not be found": {
            'reason': 'missing_loadoptions',
            'keywords': ['archive', 'load', 'extract'],
            'target_class': 'Archive',
        },

        # AspNetCore errors (more general pattern)
        r"(type|namespace).*'AspNetCore'.*does not exist": {
            'reason': 'wrong_aspnetcore_namespace',
            'keywords': ['zip', 'stream', 'file'],
            'avoid_classes': ['IFormFile', 'AspNetCore', 'IActionResult'],
        },
    }

    def __init__(self, backfill_dir: Path, same_context_only: bool = False):
        """
        Initialize substitution service.

        Args:
            backfill_dir: Path to backfill artifacts (e.g., artifacts/backfill/zip/)
            same_context_only: If True, only substitute with same app_context examples
        """
        self.backfill_dir = backfill_dir
        self.same_context_only = same_context_only
        self.examples_index: Optional[Dict[str, Any]] = None
        self._load_examples_index()

    def _load_examples_index(self) -> None:
        """Load the examples index from backfill directory."""
        index_path = self.backfill_dir / "examples-index.json"

        if not index_path.exists():
            logger.warning(f"Examples index not found at {index_path}")
            self.examples_index = {'examples': []}
            return

        try:
            with open(index_path, 'r', encoding='utf-8') as f:
                self.examples_index = json.load(f)
            logger.info(f"Loaded {len(self.examples_index.get('examples', []))} examples from index")
        except Exception as e:
            logger.error(f"Failed to load examples index: {e}")
            self.examples_index = {'examples': []}

    def should_substitute(self, errors: List[str]) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Check if errors match substitution triggers.

        Args:
            errors: List of compilation error messages

        Returns:
            Tuple of (should_substitute, trigger_info)
        """
        combined_errors = '\n'.join(errors)

        for pattern, trigger_info in self.SUBSTITUTION_TRIGGERS.items():
            if re.search(pattern, combined_errors, re.IGNORECASE):
                logger.info(f"Substitution trigger matched: {trigger_info['reason']}")
                return True, trigger_info

        return False, None

    def find_substitute_example(
        self,
        original_code: str,
        trigger_info: Dict[str, Any],
        family: str,  # Required parameter, no default
        original_app_context: Optional[str] = None,
    ) -> Optional[Tuple[str, str, Dict[str, Any]]]:
        """
        Find a suitable substitute example from the backfill repository.

        Matching strategy:
        1. Filter by keywords (tags, class name, path)
        2. Filter out examples that use avoided classes
        3. [NEW] Filter by app_context if same_context_only=True
        4. Prefer examples with target_class if specified
        5. Return the smallest matching example (simpler is better)

        Args:
            original_code: Original failing code
            trigger_info: Trigger pattern information
            family: Product family (default: zip)
            original_app_context: Application context of original code (console, aspnet_core_minimal, etc.)

        Returns:
            Tuple of (substitute_code, example_id, metadata) or None if no match
        """
        if not self.examples_index or not self.examples_index.get('examples'):
            logger.warning("No examples available for substitution")
            return None

        keywords = trigger_info.get('keywords', [])
        avoid_classes = trigger_info.get('avoid_classes', [])
        target_class = trigger_info.get('target_class')

        # Filter candidates
        candidates = []

        for example in self.examples_index['examples']:
            example_id = example.get('id')
            path = example.get('path', '')
            class_name = example.get('class_name', '')
            tags = example.get('tags', [])
            size = example.get('size_bytes', 999999)

            # Check if any keyword matches path, class name, or tags
            has_keyword = any(
                kw.lower() in path.lower() or
                kw.lower() in class_name.lower() or
                kw.lower() in ' '.join(tags).lower()
                for kw in keywords
            )

            if not has_keyword:
                continue

            # Load example code to check for avoided classes
            example_code = self._load_example_code(example_id, path)
            if not example_code:
                continue

            # Skip if uses avoided classes
            has_avoided = any(
                avoided in example_code
                for avoided in avoid_classes
            )
            if has_avoided:
                continue

            # Phase-2 Gate B: Filter by app_context if same_context_only enabled
            if self.same_context_only and original_app_context:
                candidate_context = classify_app_context(example_code)
                # Normalize both contexts to strings for comparison
                candidate_context_str = candidate_context.value if hasattr(candidate_context, 'value') else str(candidate_context)
                original_context_str = original_app_context.lower() if isinstance(original_app_context, str) else str(original_app_context)

                if candidate_context_str != original_context_str:
                    logger.debug(
                        f"Filtered out {example_id}: context mismatch "
                        f"(original={original_context_str}, candidate={candidate_context_str})"
                    )
                    continue

            # Prioritize examples with target class
            has_target = target_class and target_class in example_code

            candidates.append({
                'id': example_id,
                'code': example_code,
                'size': size,
                'has_target': has_target,
                'path': path,
                'class_name': class_name,
            })

        if not candidates:
            if self.same_context_only and original_app_context:
                logger.warning(
                    f"No substitute candidates found for keywords: {keywords} "
                    f"with matching context: {original_app_context}"
                )
            else:
                logger.warning(f"No substitute candidates found for keywords: {keywords}")
            return None

        # Sort: prioritize target class, then by size (smaller is simpler)
        candidates.sort(key=lambda x: (not x['has_target'], x['size']))

        best = candidates[0]
        logger.info(
            f"Found substitute: {best['id']} ({best['path']}) - "
            f"{best['size']} bytes, has_target={best['has_target']}"
        )

        metadata = {
            'original_example_id': 'unknown',  # Will be filled by caller
            'substitute_example_id': best['id'],
            'substitute_path': best['path'],
            'substitute_class': best['class_name'],
            'trigger_reason': trigger_info['reason'],
            'fix_strategy': 'example_repo_substitution',
        }

        return best['code'], best['id'], metadata

    def _load_example_code(self, example_id: str, path: Optional[str] = None) -> Optional[str]:
        """
        Load example code from backfill directory.

        Args:
            example_id: Example ID
            path: Optional path from index (e.g., "CancelWithToken/CancelArjExtraction.cs")

        Returns:
            Example code or None if not found
        """
        # Try using the path from the index first
        if path:
            code_path = self.backfill_dir / "examples" / path
            if code_path.exists():
                try:
                    return code_path.read_text(encoding='utf-8')
                except Exception as e:
                    logger.error(f"Failed to read example {example_id} at {path}: {e}")
                    return None

        # Fallback: Try to find the example file by ID
        code_path = self.backfill_dir / "examples" / f"{example_id}.cs"

        if not code_path.exists():
            # Try alternate structure
            code_path = self.backfill_dir / f"{example_id}.cs"

        if not code_path.exists():
            logger.debug(f"Example code not found for {example_id}")
            return None

        try:
            return code_path.read_text(encoding='utf-8')
        except Exception as e:
            logger.error(f"Failed to read example {example_id}: {e}")
            return None


def apply_quick_fixes(code: str, errors: List[str]) -> Tuple[str, List[str]]:
    """
    Apply deterministic quick fixes for common compilation errors.

    Phase-2 Task 2: DirectoryNotFoundException and missing using statements.

    Args:
        code: Original code
        errors: Compilation errors

    Returns:
        Tuple of (fixed_code, applied_fixes)
    """
    fixed_code = code
    applied_fixes = []

    # Fix 1: DirectoryNotFoundException - inject Directory.CreateDirectory
    if any('DirectoryNotFoundException' in err for err in errors):
        # Find directory variables/paths in code
        dir_patterns = [
            r'"([^"]+_folder)"',
            r'"([^"]+_dir)"',
            r'"([^"]+\\+output[^"]*)"',
            r'"([^"]+/output[^"]*)"',
        ]

        directories_to_create = set()
        for pattern in dir_patterns:
            matches = re.findall(pattern, code, re.IGNORECASE)
            for match in matches:
                if not match.endswith(('.zip', '.rar', '.7z', '.txt', '.gz')):
                    directories_to_create.add(match)

        if directories_to_create:
            # Insert Directory.CreateDirectory calls at the beginning of Main
            create_calls = '\n'.join([
                f'        Directory.CreateDirectory(@"{d}");'
                for d in sorted(directories_to_create)
            ])

            # Find insertion point (after Main method opening brace)
            main_pattern = r'(static\s+(?:async\s+)?(?:void|Task|int)\s+Main\s*\([^)]*\)\s*\{)'
            match = re.search(main_pattern, fixed_code)

            if match:
                insert_pos = match.end()
                fixed_code = (
                    fixed_code[:insert_pos] +
                    '\n' + create_calls + '\n' +
                    fixed_code[insert_pos:]
                )
                applied_fixes.append('directory_create_injection')
                logger.info(f"Injected Directory.CreateDirectory for {len(directories_to_create)} paths")

    # Fix 2: Missing using Aspose.Zip.Saving (for compression settings)
    needs_saving = any(
        'CompressionSettings' in err or 'DeflateCompressionSettings' in err or
        'ParallelCompressionOptions' in err or 'ArchiveEntrySettings' in err
        for err in errors
    )

    if needs_saving and 'using Aspose.Zip.Saving;' not in fixed_code:
        # Insert using statement after existing usings or at top
        using_insert = 'using Aspose.Zip.Saving;\n'

        # Find last using statement
        using_pattern = r'(using\s+[\w\.]+\s*;)'
        matches = list(re.finditer(using_pattern, fixed_code))

        if matches:
            last_using = matches[-1]
            insert_pos = last_using.end()
            fixed_code = (
                fixed_code[:insert_pos] +
                '\n' + using_insert +
                fixed_code[insert_pos:]
            )
        else:
            fixed_code = using_insert + fixed_code

        applied_fixes.append('using_aspose_zip_saving')
        logger.info("Added using Aspose.Zip.Saving;")

    # Fix 3: Missing using Aspose.Zip.SevenZip
    needs_sevenzip = any(
        'SevenZipArchive' in err or 'SevenZipArchiveEntry' in err
        for err in errors
    )

    if needs_sevenzip and 'using Aspose.Zip.SevenZip;' not in fixed_code:
        using_insert = 'using Aspose.Zip.SevenZip;\n'

        using_pattern = r'(using\s+[\w\.]+\s*;)'
        matches = list(re.finditer(using_pattern, fixed_code))

        if matches:
            last_using = matches[-1]
            insert_pos = last_using.end()
            fixed_code = (
                fixed_code[:insert_pos] +
                '\n' + using_insert +
                fixed_code[insert_pos:]
            )
        else:
            fixed_code = using_insert + fixed_code

        applied_fixes.append('using_aspose_zip_sevenzip')
        logger.info("Added using Aspose.Zip.SevenZip;")

    # Fix 4: System.IO.Compression Ban Transformer
    # Detect and remove System.IO.Compression usage, replace with Aspose.Zip
    if 'using System.IO.Compression;' in fixed_code:
        # Remove the using statement
        fixed_code = re.sub(
            r'using\s+System\.IO\.Compression\s*;[\r\n]*',
            '',
            fixed_code
        )

        # Ensure Aspose.Zip using is present
        if 'using Aspose.Zip;' not in fixed_code:
            using_insert = 'using Aspose.Zip;\n'
            using_pattern = r'(using\s+[\w\.]+\s*;)'
            matches = list(re.finditer(using_pattern, fixed_code))

            if matches:
                last_using = matches[-1]
                insert_pos = last_using.end()
                fixed_code = (
                    fixed_code[:insert_pos] +
                    '\n' + using_insert +
                    fixed_code[insert_pos:]
                )
            else:
                fixed_code = using_insert + fixed_code

        applied_fixes.append('system_io_compression_ban')
        logger.info("Removed System.IO.Compression and ensured Aspose.Zip usage")

    # Fix 5: Known Hallucination Patterns Transformer
    # Detect and fix common System.IO.Compression hallucination patterns
    hallucination_patterns = [
        (r'ZipArchiveMode\.\w+', 'ZipArchiveMode'),
        (r'ZipFile\.OpenRead\s*\([^)]*\)', 'ZipFile.OpenRead'),
        (r'ZipFile\.CreateFromDirectory\s*\([^)]*\)', 'ZipFile.CreateFromDirectory'),
    ]

    for pattern, pattern_name in hallucination_patterns:
        if re.search(pattern, fixed_code):
            # Comment out lines containing these patterns
            lines = fixed_code.split('\n')
            modified = False

            for i, line in enumerate(lines):
                if re.search(pattern, line) and not line.strip().startswith('//'):
                    # Add comment explaining the issue
                    indent = len(line) - len(line.lstrip())
                    lines[i] = (
                        ' ' * indent +
                        f'// REMOVED: {pattern_name} is not available in Aspose.Zip API\n' +
                        ' ' * indent + '// ' + line.strip()
                    )
                    modified = True

            if modified:
                fixed_code = '\n'.join(lines)
                applied_fixes.append(f'hallucination_fix_{pattern_name.lower().replace(".", "_")}')
                logger.info(f"Commented out hallucinated pattern: {pattern_name}")

    # Ensure Aspose.Zip using is present if hallucinations were found
    if any('hallucination_fix' in fix for fix in applied_fixes):
        if 'using Aspose.Zip;' not in fixed_code:
            using_insert = 'using Aspose.Zip;\n'
            using_pattern = r'(using\s+[\w\.]+\s*;)'
            matches = list(re.finditer(using_pattern, fixed_code))

            if matches:
                last_using = matches[-1]
                insert_pos = last_using.end()
                fixed_code = (
                    fixed_code[:insert_pos] +
                    '\n' + using_insert +
                    fixed_code[insert_pos:]
                )
            else:
                fixed_code = using_insert + fixed_code

    # Fix 6: Async-to-Sync Normalization Transformer
    # Convert unnecessary async Task Main to void/int Main when no await is used
    main_async_pattern = r'static\s+async\s+Task(?:<int>)?\s+Main\s*\([^)]*\)\s*\{'

    if re.search(main_async_pattern, fixed_code):
        # Check if there's any await keyword used (as a keyword, not in strings/comments)
        # Remove string literals and comments before checking for await
        code_without_strings = re.sub(r'"[^"]*"', '', fixed_code)
        code_without_comments = re.sub(r'//[^\n]*', '', code_without_strings)

        # Look for await followed by whitespace, which indicates actual usage
        has_await = re.search(r'\bawait\s+', code_without_comments)

        if not has_await:
            # Replace async Task Main with void Main
            fixed_code = re.sub(
                r'static\s+async\s+Task\s+Main\s*\(',
                'static void Main(',
                fixed_code
            )

            # Remove any unnecessary async Task<int> pattern
            fixed_code = re.sub(
                r'static\s+async\s+Task<int>\s+Main\s*\(',
                'static int Main(',
                fixed_code
            )

            applied_fixes.append('async_to_sync_normalization')
            logger.info("Converted unnecessary async Task Main to synchronous Main")

    # Fix 7: Path Handling Fixes Transformer
    # Replace hardcoded Windows paths with Path.Combine or platform-independent paths
    windows_path_pattern = r'"([A-Za-z]:\\[^"]+)"'
    windows_paths = re.findall(windows_path_pattern, fixed_code)

    if windows_paths:
        for win_path in windows_paths:
            # Split path into components
            parts = win_path.replace('\\\\', '\\').split('\\')

            # Skip if it's just a drive letter or single component
            if len(parts) <= 1:
                continue

            # Create Path.Combine replacement
            path_parts = ', '.join([f'"{part}"' for part in parts if part])
            path_combine = f'Path.Combine({path_parts})'

            # Replace in code
            fixed_code = fixed_code.replace(f'"{win_path}"', path_combine)

        # Ensure System.IO using is present
        if 'using System.IO;' not in fixed_code:
            using_insert = 'using System.IO;\n'
            using_pattern = r'(using\s+[\w\.]+\s*;)'
            matches = list(re.finditer(using_pattern, fixed_code))

            if matches:
                last_using = matches[-1]
                insert_pos = last_using.end()
                fixed_code = (
                    fixed_code[:insert_pos] +
                    '\n' + using_insert +
                    fixed_code[insert_pos:]
                )
            else:
                fixed_code = using_insert + fixed_code

        applied_fixes.append('path_handling_fixes')
        logger.info(f"Replaced {len(windows_paths)} hardcoded Windows paths with Path.Combine")

    # Fix 8: Inject MyDir / ArtifactsDir / master declarations for partial snippets
    # These are test-harness constants from Aspose example repos
    harness_vars = {
        'MyDir': 'string MyDir = @"./";',
        'ArtifactsDir': 'string ArtifactsDir = @"./artifacts/";',
        'master': 'var master = new Document();',
    }
    injected_vars = []
    for var_name, declaration in harness_vars.items():
        # Check if the variable is used but never declared
        if re.search(rf'\b{var_name}\b', fixed_code):
            # Skip if already declared (var X, Type X, string X patterns)
            if re.search(rf'(?:string|var|Document)\s+{var_name}\b', fixed_code):
                continue
            injected_vars.append(declaration)

    if injected_vars:
        # Try inserting after Main opening brace (post-wrap)
        main_pattern = r'(static\s+(?:async\s+)?(?:void|Task|int)\s+Main\s*\([^)]*\)\s*\{)'
        match = re.search(main_pattern, fixed_code)
        if match:
            inject_block = '\n'.join(f'        {d}' for d in injected_vars)
            insert_pos = match.end()
            fixed_code = (
                fixed_code[:insert_pos] +
                '\n' + inject_block + '\n' +
                fixed_code[insert_pos:]
            )
        else:
            # Pre-wrap: prepend declarations at top of raw code (before usings)
            inject_block = '\n'.join(injected_vars)
            fixed_code = inject_block + '\n' + fixed_code
        applied_fixes.append('harness_var_injection')
        logger.info(f"Injected harness variable declarations: {[v for v in harness_vars if any(v in d for d in injected_vars)]}")

    return fixed_code, applied_fixes
