"""
Fixture Resolver Service — Intelligent self-healing runtime environment.

When C# examples reference files at runtime that don't exist, this service
resolves them via a 5-tier priority chain:

  1. EXISTING        — find_test_file() (exact, alias, case-insensitive)
  2. REGISTRY        — fixture-registry.json (previously auto-generated)
  3. REVERSE_ALIAS   — reverse lookup of file_aliases config
  4. EXTENSION_MATCH — find any file with same extension, ranked by name similarity
  5. GENERATE        — file-type-specific generator (copy canonical or create minimal valid file)

Resolved fixtures are persisted in the test-data directory and registered
in fixture-registry.json for future reuse across runs.
"""

import difflib
import json
import logging
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

from ..core.path_roles import PathRole, classify_path_role, is_safe_path_alias

# Deferred import to avoid circular dependency
try:
    from ..core.models import SourceType
except ImportError:
    SourceType = None


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ResolveResult:
    """Result of a fixture resolution attempt."""
    resolved: bool
    filename: str
    source_path: Optional[Path] = None
    method: str = ""          # existing, registry, reverse_alias, extension_match, generate
    message: str = ""


# ---------------------------------------------------------------------------
# Filename extraction from .NET error messages
# ---------------------------------------------------------------------------

_MISSING_FILE_PATTERNS = [
    # "Could not find file 'C:\...\ReportTemplate.docx'."
    re.compile(r"Could not find file '([^']+)'", re.IGNORECASE),
    # "Could not find file \"ReportTemplate.docx\"."
    re.compile(r'Could not find file "([^"]+)"', re.IGNORECASE),
    # FileNotFoundException: ... 'path'
    re.compile(r"FileNotFoundException[^'\"]*['\"]([^'\"]+)['\"]", re.IGNORECASE),
]

_MISSING_DIR_PATTERNS = [
    # "Could not find a part of the path 'C:\...\output\'."
    re.compile(r"Could not find a part of the path '([^']+)'", re.IGNORECASE),
    re.compile(r'Could not find a part of the path "([^"]+)"', re.IGNORECASE),
    re.compile(r"DirectoryNotFoundException[^'\"]*['\"]([^'\"]+)['\"]", re.IGNORECASE),
]

# File extensions that indicate a file reference in code string literals
_CODE_FILE_EXTENSIONS = (
    # Document formats
    ".docx", ".doc", ".pdf", ".html", ".htm", ".txt", ".csv", ".xml",
    ".rtf", ".odt", ".xls", ".xlsx", ".pptx", ".pot",
    # Image formats
    ".png", ".jpg", ".jpeg", ".bmp", ".gif", ".svg", ".tiff", ".tif",
    ".psd", ".psb", ".ai", ".dicom", ".dcm", ".djvu", ".webp",
    ".emf", ".wmf", ".dng", ".j2k", ".jp2",
    # Archive formats
    ".zip", ".7z", ".gz", ".rar",
    # E-book / document conversion
    ".epub", ".mobi", ".chm", ".mhtml", ".mht", ".xps",
    # Email formats
    ".eml", ".msg", ".mbox", ".pst", ".ics",
    # CAD formats
    ".dwg", ".dxf", ".dwf",
    # Page / TeX formats
    ".ps", ".eps", ".tex", ".ltx",
    # Project formats
    ".mpp", ".mpt",
)

# Pattern to extract string literals from C# code
_CSHARP_STRING_LITERAL = re.compile(
    r'(?:'
    r'@"([^"]*(?:""[^"]*)*)"'     # Verbatim string @"..."
    r'|'
    r'"([^"\\]*(?:\\.[^"\\]*)*)"'  # Regular string "..."
    r'|'
    r'\$"([^"\\]*(?:\\.[^"\\]*)*(?:\{[^}]*\}[^"\\]*(?:\\.[^"\\]*)*)*)"'  # Interpolated $"..."
    r')'
)


def extract_missing_filename(error_text: str) -> Optional[str]:
    """
    Extract the missing filename from a .NET runtime error message.

    Handles patterns like:
      - Could not find file 'C:\\...\\ReportTemplate.docx'.
      - System.IO.FileNotFoundException: ... 'file.txt'

    Returns:
        Basename of the missing file, or None if not extractable.
    """
    for pattern in _MISSING_FILE_PATTERNS:
        m = pattern.search(error_text)
        if m:
            raw_path = m.group(1)
            # Normalise separators and extract basename
            name = PurePosixPath(raw_path.replace("\\", "/")).name
            if name:
                return name
    return None


def extract_missing_dirname(error_text: str) -> Optional[str]:
    """
    Extract the missing directory name from a .NET runtime error message.

    Returns:
        Basename of the missing directory, or None.
    """
    for pattern in _MISSING_DIR_PATTERNS:
        m = pattern.search(error_text)
        if m:
            raw_path = m.group(1).rstrip("/\\")
            name = PurePosixPath(raw_path.replace("\\", "/")).name
            if name and "." not in name:  # directories typically have no extension
                return name
    return None


def extract_file_references_from_code(code: str) -> List[str]:
    """
    Scan C# code for string literals that reference files.

    Returns list of filenames (basenames only) that look like file references.
    """
    filenames: List[str] = []
    seen: set = set()

    for m in _CSHARP_STRING_LITERAL.finditer(code):
        # Pick the first non-None group
        literal = m.group(1) or m.group(2) or m.group(3) or ""
        if not literal:
            continue

        # Unescape common C# escape sequences
        literal = literal.replace("\\\\", "/").replace("\\", "/")

        # Split on path separators to get potential filename
        parts = literal.split("/")
        for part in parts:
            # Remove interpolation braces remnants
            part = re.sub(r'\{[^}]*\}', '', part).strip()
            if not part:
                continue
            lower = part.lower()
            if any(lower.endswith(ext) for ext in _CODE_FILE_EXTENSIONS):
                if part not in seen:
                    seen.add(part)
                    filenames.append(part)

    return filenames


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class FixtureResolverService:
    """
    Centralized fixture resolver for runtime missing-file errors.

    Resolves fixtures via a 5-tier priority chain and persists results
    in a per-family fixture registry for future reuse.
    """

    # Bump this when generators are added or improved. Entries in the
    # unresolvable list recorded at an older version are retried.
    _GENERATOR_VERSION = 2

    def __init__(
        self,
        family: str,
        test_data_dir: Path,
        file_aliases: Dict[str, List[str]],
        max_generations_per_run: int = 50,
        registry_path: Optional[Path] = None,
        skip_output_patterns: Optional[List[str]] = None,
        example_repo_test_data_dir: Optional[Path] = None,
    ):
        self._family = family
        self._test_data_dir = Path(test_data_dir)
        self._file_aliases = file_aliases
        self._max_generations = max_generations_per_run
        self._generations_this_run = 0
        self._skip_patterns = skip_output_patterns or ["output*", "result*", "*.out"]
        self._example_repo_test_data_dir = Path(example_repo_test_data_dir) if example_repo_test_data_dir else None

        # Registry path defaults to test-data sibling
        if registry_path:
            self._registry_path = Path(registry_path)
        else:
            self._registry_path = self._test_data_dir.parent / "fixture-registry.json"

        self._registry = self._load_registry()
        self._stats: Dict[str, int] = {"resolved": 0, "generated": 0, "failed": 0}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def resolve_missing_file(
        self,
        filename: str,
        workspace_dir: Optional[Path] = None,
    ) -> ResolveResult:
        """
        Resolve a missing file via 5-tier priority chain.

        If resolved, copies the file to:
          1. test-data dir (persistent, for future runs)
          2. workspace_dir (immediate, for current retry)

        Args:
            filename: Basename of the missing file (e.g. "ReportTemplate.docx")
            workspace_dir: Current runtime workspace directory (optional)

        Returns:
            ResolveResult with resolution details.
        """
        if self._should_skip(filename):
            return ResolveResult(
                resolved=False, filename=filename,
                method="skipped", message=f"Skipped: matches output pattern",
            )

        # Early exit: known-unresolvable at current generator version
        if self._is_known_unresolvable(filename):
            self._stats["failed"] += 1
            return ResolveResult(
                resolved=False, filename=filename,
                method="cached_unresolvable",
                message=f"Previously unresolvable (generator v{self._GENERATOR_VERSION})",
            )

        # Tier 1: Existing file in test-data (exact, alias, case-insensitive)
        result = self._tier1_existing(filename)
        if result.resolved:
            self._copy_to_workspace(result.source_path, filename, workspace_dir)
            self._bump_usage(filename)
            self._stats["resolved"] += 1
            return result

        # Tier 2: Registry (previously resolved/generated)
        result = self._tier2_registry(filename)
        if result.resolved:
            self._copy_to_workspace(result.source_path, filename, workspace_dir)
            self._bump_usage(filename)
            self._stats["resolved"] += 1
            return result

        # Tier 2.5: Example repo test data (if configured)
        result = self._tier2_5_example_repo(filename)
        if result.resolved:
            self._place_in_test_data(result.source_path, filename)
            self._copy_to_workspace(self._test_data_dir / filename, filename, workspace_dir)
            self._register_fixture(filename, str(result.source_path), "example_repo")
            self._stats["resolved"] += 1
            return result

        # Tier 3: Reverse alias lookup
        result = self._tier3_reverse_alias(filename)
        if result.resolved:
            self._place_in_test_data(result.source_path, filename)
            self._copy_to_workspace(self._test_data_dir / filename, filename, workspace_dir)
            self._register_fixture(filename, str(result.source_path), "reverse_alias")
            self._stats["resolved"] += 1
            return result

        # Tier 4: Extension match (best similarity)
        result = self._tier4_extension_match(filename)
        if result.resolved:
            self._place_in_test_data(result.source_path, filename)
            self._copy_to_workspace(self._test_data_dir / filename, filename, workspace_dir)
            self._register_fixture(filename, str(result.source_path), "extension_match")
            self._stats["resolved"] += 1
            return result

        # Tier 5: Generate
        result = self._tier5_generate(filename)
        if result.resolved:
            self._copy_to_workspace(self._test_data_dir / filename, filename, workspace_dir)
            self._register_fixture(filename, None, "generate")
            self._stats["generated"] += 1
            return result

        # All tiers exhausted
        self._record_unresolvable(filename)
        self._stats["failed"] += 1
        return ResolveResult(
            resolved=False, filename=filename,
            method="exhausted", message="All 5 resolution tiers exhausted",
        )

    def resolve_missing_directory(
        self,
        dirname: str,
        workspace_dir: Optional[Path] = None,
    ) -> ResolveResult:
        """
        Resolve a missing directory by creating it with sample files.
        """
        if self._should_skip(dirname):
            return ResolveResult(
                resolved=False, filename=dirname,
                method="skipped", message="Skipped: matches output pattern",
            )

        # Check if directory already exists in test-data
        target = self._test_data_dir / dirname
        if target.is_dir():
            # Already exists in test-data; copy to workspace
            if workspace_dir:
                ws_target = workspace_dir / dirname
                if not ws_target.exists():
                    shutil.copytree(target, ws_target)
            return ResolveResult(
                resolved=True, filename=dirname,
                source_path=target, method="existing",
                message=f"Directory already exists in test-data",
            )

        # Create directory with sample files
        target.mkdir(parents=True, exist_ok=True)
        # Add a few sample files
        (target / "sample.txt").write_text("Sample text content for testing.\n", encoding="utf-8")
        (target / "data.txt").write_text("Sample data file.\n", encoding="utf-8")

        if workspace_dir:
            ws_target = workspace_dir / dirname
            if not ws_target.exists():
                shutil.copytree(target, ws_target)

        self._register_fixture(dirname, None, "generate_dir")
        self._stats["generated"] += 1
        return ResolveResult(
            resolved=True, filename=dirname,
            source_path=target, method="generate",
            message=f"Created directory with sample files",
        )

    def precheck_code_references(
        self,
        code: str,
        workspace_dir: Optional[Path] = None,
    ) -> List[ResolveResult]:
        """
        Proactively scan code for file references and resolve missing ones.

        Scans C# string literals for filenames that don't exist in workspace.
        Resolves them before runtime to prevent FileNotFoundException.

        Args:
            code: C# source code to scan
            workspace_dir: Runtime workspace directory

        Returns:
            List of ResolveResults for each resolved file.
        """
        refs = extract_file_references_from_code(code)
        results: List[ResolveResult] = []

        for filename in refs:
            # Check if already in workspace
            if workspace_dir and (workspace_dir / filename).exists():
                continue
            # Check if already in test-data (will be copied by _copy_test_data)
            if (self._test_data_dir / filename).exists():
                continue

            result = self.resolve_missing_file(filename, workspace_dir)
            if result.resolved:
                results.append(result)
                logger.info(f"Proactive fixture: {filename} via {result.method}")

        return results

    # ------------------------------------------------------------------
    # Tier implementations
    # ------------------------------------------------------------------

    def _tier1_existing(self, filename: str) -> ResolveResult:
        """Tier 1: Find file already in test-data via RuntimeService patterns."""
        from .runtime_service import RuntimeService

        found = RuntimeService.find_test_file(
            required_name=filename,
            source_dir=self._test_data_dir,
            file_aliases=self._file_aliases,
            inventory=None,
        )
        if found:
            return ResolveResult(
                resolved=True, filename=filename,
                source_path=found, method="existing",
                message=f"Found in test-data: {found.name}",
            )
        return ResolveResult(resolved=False, filename=filename)

    def _tier2_registry(self, filename: str) -> ResolveResult:
        """Tier 2: Look up in fixture registry."""
        fixtures = self._registry.get("fixtures", {})
        entry = fixtures.get(filename)
        if not entry:
            return ResolveResult(resolved=False, filename=filename)

        # Registry says this was previously resolved — check if file still exists
        target = self._test_data_dir / filename
        if target.exists():
            return ResolveResult(
                resolved=True, filename=filename,
                source_path=target, method="registry",
                message=f"Found in registry (previously {entry.get('method', 'resolved')})",
            )

        # Registry entry exists but file is gone — try to recreate from canonical
        canonical = entry.get("canonical_source")
        if canonical:
            canonical_path = self._test_data_dir / canonical
            if canonical_path.exists():
                shutil.copy2(canonical_path, target)
                return ResolveResult(
                    resolved=True, filename=filename,
                    source_path=target, method="registry",
                    message=f"Recreated from canonical {canonical}",
                )

        return ResolveResult(resolved=False, filename=filename)

    def _tier2_5_example_repo(self, filename: str) -> ResolveResult:
        """Tier 2.5: Check example repo test data directory (recursive)."""
        if not self._example_repo_test_data_dir or not self._example_repo_test_data_dir.exists():
            return ResolveResult(resolved=False, filename=filename)

        # Exact match first
        candidate = self._example_repo_test_data_dir / filename
        if candidate.exists() and candidate.is_file():
            return ResolveResult(
                resolved=True, filename=filename,
                source_path=candidate, method="example_repo",
                message=f"Found in example repo test data: {filename}",
            )

        # Recursive search (repos often organize data in subdirectories)
        for f in self._example_repo_test_data_dir.rglob(filename):
            if f.is_file():
                rel = f.relative_to(self._example_repo_test_data_dir)
                return ResolveResult(
                    resolved=True, filename=filename,
                    source_path=f, method="example_repo",
                    message=f"Found in example repo (recursive): {rel}",
                )

        # Case-insensitive fallback
        filename_lower = filename.lower()
        for f in self._example_repo_test_data_dir.rglob("*"):
            if f.is_file() and f.name.lower() == filename_lower:
                rel = f.relative_to(self._example_repo_test_data_dir)
                return ResolveResult(
                    resolved=True, filename=filename,
                    source_path=f, method="example_repo",
                    message=f"Found in example repo (case-insensitive): {rel}",
                )

        return ResolveResult(resolved=False, filename=filename)

    def _tier3_reverse_alias(self, filename: str) -> ResolveResult:
        """Tier 3: Reverse lookup — if filename is an alias for a canonical file."""
        filename_lower = filename.lower()

        for canonical, aliases in self._file_aliases.items():
            if not is_safe_path_alias(canonical, filename):
                continue
            aliases_lower = [a.lower() for a in aliases]
            if filename_lower in aliases_lower or filename_lower == canonical.lower():
                # Found canonical — check if it exists in test-data
                canonical_path = self._test_data_dir / canonical
                if canonical_path.exists():
                    return ResolveResult(
                        resolved=True, filename=filename,
                        source_path=canonical_path, method="reverse_alias",
                        message=f"Reverse alias: {filename} -> {canonical}",
                    )
                # Also try find_test_file for the canonical
                from .runtime_service import RuntimeService
                found = RuntimeService.find_test_file(
                    canonical, self._test_data_dir, self._file_aliases,
                )
                if found:
                    return ResolveResult(
                        resolved=True, filename=filename,
                        source_path=found, method="reverse_alias",
                        message=f"Reverse alias: {filename} -> {found.name}",
                    )

        return ResolveResult(resolved=False, filename=filename)

    def _tier4_extension_match(self, filename: str) -> ResolveResult:
        """Tier 4: Find any file with same extension, ranked by name similarity."""
        ext = Path(filename).suffix.lower()
        if not ext:
            return ResolveResult(resolved=False, filename=filename)

        # Collect all files with matching extension
        candidates: List[Path] = []
        for f in self._test_data_dir.rglob(f"*{ext}"):
            if f.is_file():
                candidates.append(f)

        if not candidates:
            return ResolveResult(resolved=False, filename=filename)

        # Rank by filename similarity using difflib
        candidate_names = [c.name for c in candidates]
        matches = difflib.get_close_matches(filename, candidate_names, n=1, cutoff=0.0)

        if matches:
            best_name = matches[0]
            best_path = next(c for c in candidates if c.name == best_name)
            return ResolveResult(
                resolved=True, filename=filename,
                source_path=best_path, method="extension_match",
                message=f"Extension match: closest '{best_name}' (similarity to '{filename}')",
            )

        # Fallback: just use the first one
        return ResolveResult(
            resolved=True, filename=filename,
            source_path=candidates[0], method="extension_match",
            message=f"Extension match: using '{candidates[0].name}' (first available {ext})",
        )

    def _tier5_generate(self, filename: str) -> ResolveResult:
        """Tier 5: Generate a fixture file using type-specific generators."""
        if self._generations_this_run >= self._max_generations:
            return ResolveResult(
                resolved=False, filename=filename,
                method="generation_cap",
                message=f"Generation cap reached ({self._max_generations}/run)",
            )

        from .test_data_generator import generate_file_for_family

        dest = self._test_data_dir / filename
        dest.parent.mkdir(parents=True, exist_ok=True)

        success, msg = generate_file_for_family(
            filename=filename,
            dest=dest,
            test_data_dir=self._test_data_dir,
            family=self._family,
        )

        if success:
            self._generations_this_run += 1
            return ResolveResult(
                resolved=True, filename=filename,
                source_path=dest, method="generate",
                message=msg,
            )

        return ResolveResult(
            resolved=False, filename=filename,
            method="generate_failed", message=msg,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _should_skip(self, filename: str) -> bool:
        """Check if filename matches output patterns (shouldn't be generated)."""
        import fnmatch
        if classify_path_role(filename) == PathRole.OUTPUT:
            return True
        lower = filename.lower()
        for pattern in self._skip_patterns:
            if fnmatch.fnmatch(lower, pattern.lower()):
                return True
        return False

    def _place_in_test_data(self, source_path: Path, filename: str):
        """Copy a resolved file into the test-data directory for persistence."""
        target = self._test_data_dir / filename
        if not target.exists() and source_path and source_path.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, target)

    def _copy_to_workspace(
        self,
        source_path: Optional[Path],
        filename: str,
        workspace_dir: Optional[Path],
    ):
        """Copy file to runtime workspace for immediate retry."""
        if not workspace_dir or not source_path or not source_path.exists():
            return
        target = workspace_dir / filename
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, target)

    def _load_registry(self) -> Dict[str, Any]:
        """Load fixture registry from JSON file, auto-migrating old formats."""
        if self._registry_path.exists():
            try:
                data = json.loads(self._registry_path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    # Auto-migrate old list-based unresolvable format to versioned dict
                    self._migrate_unresolvable_list(data)
                    return data
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Failed to load fixture registry: {e}")
        return {"version": 1, "family": self._family, "fixtures": {}, "unresolvable": {}}

    @staticmethod
    def _migrate_unresolvable_list(data: Dict[str, Any]):
        """Convert old list-based unresolvable to versioned dict (in-place)."""
        unresolvable = data.get("unresolvable")
        if isinstance(unresolvable, list):
            migrated = {}
            for entry in unresolvable:
                if not isinstance(entry, str):
                    continue
                # Drop glob/wildcard patterns during migration
                if any(c in entry for c in ('*', '?', '{')):
                    continue
                migrated[entry] = {
                    "recorded_at": None,
                    "generator_version": 1,  # Assume old version
                }
            data["unresolvable"] = migrated

    def _save_registry(self):
        """Persist fixture registry to JSON file."""
        try:
            self._registry_path.parent.mkdir(parents=True, exist_ok=True)
            self._registry_path.write_text(
                json.dumps(self._registry, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError as e:
            logger.warning(f"Failed to save fixture registry: {e}")

    def _register_fixture(
        self,
        filename: str,
        canonical_source: Optional[str],
        method: str,
    ):
        """Register a resolved fixture in the registry and save."""
        fixtures = self._registry.setdefault("fixtures", {})
        fixtures[filename] = {
            "canonical_source": canonical_source,
            "method": method,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "usage_count": 1,
        }
        self._save_registry()

    def _bump_usage(self, filename: str):
        """Increment usage count for a registered fixture."""
        fixtures = self._registry.get("fixtures", {})
        if filename in fixtures:
            fixtures[filename]["usage_count"] = fixtures[filename].get("usage_count", 0) + 1
            self._save_registry()

    def _is_known_unresolvable(self, filename: str) -> bool:
        """Check if filename is known-unresolvable and not stale.

        Returns True (skip resolution) only if:
        - Entry exists for this filename
        - Entry's generator_version matches current version
        - File doesn't now exist in test-data or example repo
        """
        unresolvable = self._registry.get("unresolvable", {})
        if not isinstance(unresolvable, dict):
            return False
        entry = unresolvable.get(filename)
        if not entry:
            return False

        # Stale if generator version changed (new generators may handle it)
        if entry.get("generator_version") != self._GENERATOR_VERSION:
            return False

        # Stale if file now exists in test-data (externally backfilled)
        if (self._test_data_dir / filename).exists():
            unresolvable.pop(filename, None)
            return False

        # Stale if file now exists in example repo (repo was cloned/updated)
        if self._example_repo_test_data_dir and self._example_repo_test_data_dir.exists():
            for f in self._example_repo_test_data_dir.rglob(filename):
                if f.is_file():
                    unresolvable.pop(filename, None)
                    return False

        return True

    def _record_unresolvable(self, filename: str):
        """Record a filename that couldn't be resolved (versioned dict format)."""
        # Reject glob/wildcard patterns — only record concrete filenames
        if any(c in filename for c in ('*', '?', '{')):
            return

        unresolvable = self._registry.setdefault("unresolvable", {})
        # Force migration if still in old list format
        if isinstance(unresolvable, list):
            self._migrate_unresolvable_list(self._registry)
            unresolvable = self._registry["unresolvable"]

        unresolvable[filename] = {
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "generator_version": self._GENERATOR_VERSION,
        }
        self._save_registry()

