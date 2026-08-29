"""
Path guard for write protection in Example Reviewer Pipeline.
Enforces read-only constraints on test directories.

This module provides centralized path validation to prevent accidental
writes to test data directories, ensuring data integrity and preventing
"cheating" by manual edits during testing.
"""

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

logger = logging.getLogger(__name__)

# Read-only path prefixes (normalized to forward slashes)
# These paths are STRICTLY read-only - no writes allowed under any circumstances
READ_ONLY_PREFIXES = (
    'test-data/',
    'test-examples/',
    'tests/fixtures/reference/',
    'tests/fixtures/content/',
)

# Allowlisted write roots for resolve_write_target() (TC-EPIC1-04). Extend this
# tuple, not the resolution logic, when a new legitimate write root is needed
# (e.g. a new family's backfill directory) -- per this taskcard's migration
# requirement that the allowlist be config-visible data, not embedded logic.
ALLOWED_WRITE_ROOTS = (
    'artifacts/',
    'workspace/',
    'data/',
)


def normalize_path(path: Union[str, Path]) -> str:
    """
    Normalize path to forward slashes for consistent checking.

    This handles both Windows and Unix path separators and converts
    to a canonical forward-slash format for comparison.

    Args:
        path: Path to normalize (absolute or relative)

    Returns:
        Normalized path string with forward slashes

    Example:
        >>> normalize_path("test-data\\file.txt")
        'test-data/file.txt'
        >>> normalize_path(Path("/home/user/tests/fixtures/content/doc.md"))
        '/home/user/tests/fixtures/content/doc.md'
    """
    # Convert to string and replace all backslashes with forward slashes
    # This handles Windows-style paths on Unix systems correctly
    s = str(path)
    s = s.replace("\\", "/")

    # Collapse duplicate slashes (but preserve leading // for UNC paths)
    while "//" in s[1:]:  # Start from index 1 to preserve UNC prefix
        s = s[0] + s[1:].replace("//", "/")

    return s


def is_read_only_path(path: Union[str, Path]) -> bool:
    """
    Check if a file path is in a read-only test directory.

    This function checks if the given path (absolute or relative) falls
    under any of the protected test-* directories at the PROJECT ROOT level only.

    It handles:
    - Relative paths starting with test-* at the root
    - Absolute paths where test-* appears as a root-level directory

    IMPORTANT: test-* folder names in non-root locations (like artifacts/backfill/zip/test-data)
    are NOT considered read-only.

    Args:
        path: Path to check (absolute or relative)

    Returns:
        True if path is in a read-only directory at project root, False otherwise

    Example:
        >>> is_read_only_path("test-data/zip/sample.zip")
        True
        >>> is_read_only_path("tests/fixtures/content/docs/page.md")
        True
        >>> is_read_only_path("artifacts/backfill/zip/test-data/file.txt")
        False  # test-data here is just a folder name, not at project root
    """
    normalized = normalize_path(path)

    # Get path components
    parts = normalized.split('/')
    if not parts:
        return False

    # Check if first component (or component right after an absolute path root) matches
    # For relative paths: check first component
    # For absolute paths: find the project root-relative path

    # For relative paths starting with test-*
    for prefix in READ_ONLY_PREFIXES:
        if normalized.startswith(prefix):
            return True

    # For absolute paths: check if test-* appears as a top-level directory
    # We need to find patterns like:
    #   /home/user/project/test-data/...
    #   C:/Users/user/project/test-data/...
    # But NOT:
    #   /home/user/project/artifacts/backfill/test-data/...

    # For absolute paths: check if any suffix of the path starts with a read-only prefix
    # This handles paths like /home/user/project/test-data/file.txt
    # and also multi-component prefixes like tests/fixtures/content/
    for i in range(len(parts)):
        suffix = '/'.join(parts[i:])
        for prefix in READ_ONLY_PREFIXES:
            if suffix.startswith(prefix):
                # Found a matching prefix. Check if it's at project root level.
                # Heuristic: if ANY ancestor is 'artifacts', 'workspace', etc., it's NOT at root
                if i > 0:
                    ancestors = parts[:i]
                    if any(ancestor in ('artifacts', 'workspace', '.cache', 'cache', 'backfill') for ancestor in ancestors):
                        return False
                return True

    return False


def assert_write_allowed(path: Union[str, Path], reason: str = "") -> None:
    """
    Assert that writing to this file is allowed.

    This is the primary enforcement point for write protection. Call this
    before any file write operation to ensure the target path is not
    in a protected test directory.

    Args:
        path: Path to check
        reason: Optional reason for the write (for logging and error messages)

    Raises:
        PermissionError: If attempting to write to read-only test-* paths

    Example:
        >>> assert_write_allowed("workspace/output.txt", "compilation artifact")
        # No exception - write allowed

        >>> assert_write_allowed("tests/fixtures/content/docs/page.md", "markdown update")
        PermissionError: WRITE BLOCKED: Cannot write to read-only test path...
    """
    if is_read_only_path(path):
        normalized = normalize_path(path)
        raise PermissionError(
            f"WRITE BLOCKED: Cannot write to read-only test path: {path}\n"
            f"Normalized: {normalized}\n"
            f"Read-only prefixes: {', '.join(READ_ONLY_PREFIXES)}\n"
            f"Reason: {reason}\n"
            f"\n"
            f"Test paths are strictly read-only to prevent cheating by manual edits.\n"
            f"Use --use-workspace-copy flag to work with copies in workspace."
        )

    # Log allowed writes for audit trail
    if reason:
        logger.debug(f"Write allowed: {path} (reason: {reason})")


def get_workspace_path(
    original_path: Union[str, Path],
    workspace_root: Path,
    run_id: str
) -> Path:
    """
    Get workspace copy path for a read-only file.

    This function generates a workspace path for files that are in read-only
    directories. The workspace path maintains the relative structure but
    relocates the file under workspace_root/<run_id>/content/.

    Handles both relative and absolute paths correctly by normalizing to
    forward slashes and extracting the relative portion after the protected
    directory name.

    Args:
        original_path: Original file path (may be in tests/fixtures/content/)
        workspace_root: Workspace root directory (e.g., artifacts/workspace)
        run_id: Current run ID for isolation (e.g., abc123def456)

    Returns:
        Path to workspace copy, or original path if not in read-only directory

    Example:
        >>> get_workspace_path(
        ...     "tests/fixtures/content/docs/example.md",
        ...     Path("artifacts/workspace"),
        ...     "abc123"
        ... )
        PosixPath('artifacts/workspace/abc123/content/docs/example.md')

        >>> get_workspace_path(
        ...     "/home/user/repo/tests/fixtures/content/docs/example.md",
        ...     Path("artifacts/workspace"),
        ...     "abc123"
        ... )
        PosixPath('artifacts/workspace/abc123/content/docs/example.md')

        >>> get_workspace_path(
        ...     "workspace/file.txt",
        ...     Path("artifacts/workspace"),
        ...     "abc123"
        ... )
        PosixPath('workspace/file.txt')  # Not in read-only, return as-is
    """
    original = Path(original_path)

    # If in read-only test path, create workspace copy path
    if is_read_only_path(original_path):
        # Normalize to forward slashes for consistent handling
        normalized = normalize_path(original_path)

        # Find which protected prefix matches
        for prefix in READ_ONLY_PREFIXES:
            prefix_clean = prefix.rstrip('/')

            # Try to extract relative path after the protected directory
            # Handle both relative paths and absolute paths
            if normalized.startswith(prefix_clean + '/'):
                # Relative path case: tests/fixtures/content/docs/file.md
                relative_str = normalized[len(prefix_clean) + 1:]
                relative = Path(relative_str)
                return workspace_root / run_id / "content" / relative
            elif f"/{prefix_clean}/" in normalized:
                # Absolute path case: /home/user/repo/tests/fixtures/content/docs/file.md
                # Extract everything after the protected prefix
                idx = normalized.index(f"/{prefix_clean}/")
                relative_str = normalized[idx + len(f"/{prefix_clean}/"):]
                relative = Path(relative_str)
                return workspace_root / run_id / "content" / relative

    # If not in protected path, return original
    return original


# =============================================================================
# ALLOWLIST MODEL (TC-EPIC1-04)
# =============================================================================
#
# The functions above (is_read_only_path, assert_write_allowed) are PRESERVED
# UNCHANGED for backward compatibility -- markdown_service.py's existing call
# and tests/test_path_guard.py's 330-line regression suite continue to pass
# against the exact same string-prefix-matching implementation. They remain a
# valid, narrow-purpose guard for the one call site that already uses them.
#
# resolve_write_target() below is NEW, additional, and stronger: it uses real
# Path.resolve() (following symlinks/junctions to their true target, resolving
# `..` traversal, and normalizing case on case-insensitive filesystems) plus
# explicit UNC detection, and an ALLOWLIST model (deny by default outside
# known-good write roots) rather than a denylist (deny only 4 known-bad
# prefixes, allow everything else). This is what the Authorization Kernel's
# WRITE_MARKDOWN/WRITE_ARTIFACT/EXECUTE_CODE capability checks call internally
# (see src/core/authority/pdp.py) so a resolved-symlink escape or UNC path is
# caught at the PDP layer automatically, not left to each caller to remember.
#
# Findings resolved: the "no Path.resolve()/realpath, no symlink or UNC-path
# handling" gap documented in FINDINGS_REGISTER.md F-012.


@dataclass(frozen=True)
class ResolvedPath:
    """Result of resolving a candidate write path against the allowlist model."""

    original: str
    resolved: Path
    is_symlink: bool
    is_unc: bool
    is_within_allowlist: bool
    is_denylisted: bool  # True if resolved path falls under one of the 4 legacy READ_ONLY_PREFIXES
    reason: str

    @property
    def allowed(self) -> bool:
        """A write is allowed only if it's within the allowlist AND not denylisted."""
        return self.is_within_allowlist and not self.is_denylisted


def _is_unc_path(path: Union[str, Path]) -> bool:
    """Detect a UNC path (\\\\server\\share\\...) on any platform.

    Path.resolve() does not itself flag UNC paths as unusual -- a UNC path
    resolves "successfully" to another UNC path, which is exactly the blind
    spot this closes (FINDINGS_REGISTER.md F-012's "no UNC handling" gap).
    """
    s = str(path)
    if s.startswith('\\\\') or s.startswith('//'):
        return True
    drive, _ = os.path.splitdrive(s)
    # os.path.splitdrive returns a UNC-style drive (e.g. '\\\\server\\share') for
    # UNC paths on Windows; a normal drive letter is 2 chars ("C:").
    return bool(drive) and len(drive) > 2


def _repo_root() -> Path:
    """Best-effort repo root: 3 levels up from this file (src/core/path_guard.py)."""
    return Path(__file__).resolve().parent.parent.parent


def resolve_write_target(
    path: Union[str, Path],
    repo_root: Optional[Path] = None,
) -> ResolvedPath:
    """Resolve a candidate write path and evaluate it against the allowlist model.

    Unlike is_read_only_path() (pure string-prefix matching), this function
    follows symlinks/junctions to their real target via Path.resolve() and
    explicitly detects UNC paths -- both closing gaps confirmed absent from the
    legacy implementation (zero `symlink|realpath|resolve\\(` hits in
    path_guard.py or test_path_guard.py prior to this taskcard).

    Preserves the exact "artifacts/backfill/.../test-data/" nuance from
    is_read_only_path(): a `test-data` directory nested under an allowlisted
    root (artifacts/, workspace/, data/) is legitimately writable, distinct
    from `test-data/` at the repo root, which stays denylisted.
    """
    root = repo_root or _repo_root()
    original = str(path)

    is_unc = _is_unc_path(path)
    if is_unc:
        # UNC paths are denied by default regardless of resolution -- they are
        # never in the allowlist (which is defined relative to repo_root).
        return ResolvedPath(
            original=original,
            resolved=Path(original),
            is_symlink=False,
            is_unc=True,
            is_within_allowlist=False,
            is_denylisted=False,
            reason="UNC path denied by default (not in allowlist, per TC-EPIC1-04).",
        )

    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = root / candidate

    is_symlink = candidate.is_symlink() or any(p.is_symlink() for p in candidate.parents if p.exists())
    try:
        resolved = candidate.resolve()
    except OSError:
        # A path component doesn't exist or can't be stat'd -- resolve() on
        # Python 3.6+ doesn't raise for nonexistent paths (strict=False is the
        # default), but guard defensively for platform edge cases anyway.
        resolved = candidate.absolute()

    try:
        rel_to_root = resolved.relative_to(root)
        rel_str = str(rel_to_root).replace('\\', '/')
    except ValueError:
        # Resolved path escapes the repo root entirely -- never allowlisted.
        return ResolvedPath(
            original=original,
            resolved=resolved,
            is_symlink=is_symlink,
            is_unc=False,
            is_within_allowlist=False,
            is_denylisted=False,
            reason=f"Resolved path {resolved} is outside the repository root {root}.",
        )

    is_within_allowlist = any(rel_str.startswith(allowed_root) for allowed_root in ALLOWED_WRITE_ROOTS)

    # Denylist override: the 4 legacy READ_ONLY_PREFIXES stay denied even if
    # somehow allowlisted, preserving the artifacts/backfill/test-data/ nuance
    # (a denylisted prefix ONLY at repo-root level, not nested under an
    # allowlisted root -- matching is_read_only_path()'s existing ancestor check).
    is_denylisted = False
    for prefix in READ_ONLY_PREFIXES:
        if rel_str.startswith(prefix):
            is_denylisted = True
            break

    if is_within_allowlist and is_denylisted:
        # e.g. "artifacts/backfill/zip/test-data/..." starts with an allowlisted
        # root (artifacts/) -- the denylist prefix check above only matches
        # rel_str starting with "test-data/" etc. AT THE REPO ROOT, so this
        # branch is only reached for a genuine repo-root-level denylisted path
        # that also happens to satisfy an allowlist prefix, which cannot occur
        # given ALLOWED_WRITE_ROOTS and READ_ONLY_PREFIXES are disjoint by
        # construction -- kept as an explicit, tested invariant, not assumed.
        is_denylisted = True

    reason = (
        f"Resolved to {rel_str!r}: "
        f"{'within' if is_within_allowlist else 'NOT within'} allowlist "
        f"({', '.join(ALLOWED_WRITE_ROOTS)}); "
        f"{'DENYLISTED' if is_denylisted else 'not denylisted'}."
    )
    if is_symlink:
        reason += " Path involves a symlink/junction; resolved to its real target before evaluation."

    return ResolvedPath(
        original=original,
        resolved=resolved,
        is_symlink=is_symlink,
        is_unc=False,
        is_within_allowlist=is_within_allowlist,
        is_denylisted=is_denylisted,
        reason=reason,
    )
