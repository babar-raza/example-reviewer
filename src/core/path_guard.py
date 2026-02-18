"""
Path guard for write protection in Example Reviewer Pipeline.
Enforces read-only constraints on test directories.

This module provides centralized path validation to prevent accidental
writes to test data directories, ensuring data integrity and preventing
"cheating" by manual edits during testing.
"""

import logging
from pathlib import Path
from typing import Union

logger = logging.getLogger(__name__)

# Read-only path prefixes (normalized to forward slashes)
# These paths are STRICTLY read-only - no writes allowed under any circumstances
READ_ONLY_PREFIXES = (
    'test-data/',
    'test-examples/',
    'tests/fixtures/reference/',
    'tests/fixtures/content/',
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
