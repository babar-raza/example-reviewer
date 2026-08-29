"""Tests for TC-EPIC1-04: path_guard rewritten as an allowlist-based PDP resource resolver.

Co-exists with, does not replace, tests/test_path_guard.py (kept passing unmodified
against the untouched is_read_only_path()/assert_write_allowed() functions).
"""

import os
import tempfile
from pathlib import Path

import pytest

from src.core.path_guard import (
    ALLOWED_WRITE_ROOTS,
    READ_ONLY_PREFIXES,
    is_read_only_path,
    resolve_write_target,
)


def _reference_old_is_read_only_path(path: str) -> bool:
    """Frozen snapshot of pre-TC-EPIC1-04 is_read_only_path() logic (string-prefix
    matching only, no resolve()). Used as the negative-control reference to prove
    the OLD model missed a symlink escape that the new resolve_write_target()
    catches. Deliberately copied here rather than imported, so it stays frozen
    even if the real function is ever changed later."""
    normalized = str(path).replace("\\", "/")
    for prefix in READ_ONLY_PREFIXES:
        if normalized.startswith(prefix):
            return True
    return False


@pytest.fixture
def repo_root(tmp_path):
    """A fake repo root with an allowlisted dir and a denylisted test-data dir."""
    (tmp_path / "workspace").mkdir()
    (tmp_path / "artifacts" / "backfill" / "zip" / "test-data").mkdir(parents=True)
    (tmp_path / "test-data").mkdir()
    return tmp_path


def test_artifacts_backfill_test_data_still_writable(repo_root):
    """Regression-pins the artifacts/backfill/zip/test-data/ nuance: a test-data
    directory NESTED under an allowlisted root is legitimately writable, distinct
    from test-data/ at the repo root."""
    target = repo_root / "artifacts" / "backfill" / "zip" / "test-data" / "file.txt"
    resolved = resolve_write_target(target, repo_root=repo_root)
    assert resolved.allowed is True
    assert resolved.is_denylisted is False


def test_repo_root_test_data_is_denylisted(repo_root):
    target = repo_root / "test-data" / "file.txt"
    resolved = resolve_write_target(target, repo_root=repo_root)
    assert resolved.allowed is False
    assert resolved.is_denylisted is True


def test_unc_path_denied_by_default():
    resolved = resolve_write_target(r"\\server\share\file.txt")
    assert resolved.is_unc is True
    assert resolved.allowed is False


def test_dotdot_traversal_via_resolve(repo_root):
    """artifacts/../test-data/file.txt resolves to the real test-data/ target
    and is denied -- proving traversal survives the allowlist rewrite, not just
    a string-prefix check (test_security_baseline.py's TestPathTraversalGuard
    covers the string-level case; this covers the resolve()-level case)."""
    target = repo_root / "artifacts" / ".." / "test-data" / "file.txt"
    resolved = resolve_write_target(target, repo_root=repo_root)
    assert resolved.allowed is False
    assert resolved.is_denylisted is True


def test_path_outside_repo_root_denied(repo_root, tmp_path_factory):
    other_root = tmp_path_factory.mktemp("elsewhere")
    target = other_root / "file.txt"
    resolved = resolve_write_target(target, repo_root=repo_root)
    assert resolved.allowed is False


def test_workspace_write_allowed(repo_root):
    target = repo_root / "workspace" / "run123" / "output.txt"
    resolved = resolve_write_target(target, repo_root=repo_root)
    assert resolved.allowed is True
    assert resolved.is_denylisted is False


def test_symlink_escape_is_detected(repo_root):
    """A path whose STRING looks benign (inside workspace/) but whose resolved
    target is a symlink pointing into test-data/ must be denied."""
    target_in_readonly = repo_root / "test-data" / "real_target.txt"
    target_in_readonly.write_text("secret")
    symlink_path = repo_root / "workspace" / "output.txt"

    try:
        os.symlink(target_in_readonly, symlink_path)
    except (OSError, NotImplementedError):
        pytest.skip("Symlink creation requires elevated privilege/developer mode on this platform.")

    resolved = resolve_write_target(symlink_path, repo_root=repo_root)
    assert resolved.is_symlink is True
    assert resolved.allowed is False
    assert resolved.is_denylisted is True


def test_old_string_prefix_model_missed_symlink_escape(repo_root):
    """NEGATIVE CONTROL: proves the pre-TC-EPIC1-04 model would have allowed the
    exact symlink escape above, since it never resolves the path -- it only
    string-matches the literal path text."""
    target_in_readonly = repo_root / "test-data" / "real_target.txt"
    target_in_readonly.write_text("secret")
    symlink_path = repo_root / "workspace" / "output.txt"

    try:
        os.symlink(target_in_readonly, symlink_path)
    except (OSError, NotImplementedError):
        pytest.skip("Symlink creation requires elevated privilege/developer mode on this platform.")

    # The OLD model, given the symlink's own path string ("workspace/output.txt"),
    # says "not read-only" -- it never looks at what the symlink points to.
    old_model_result = _reference_old_is_read_only_path(str(symlink_path))
    assert old_model_result is False  # OLD model: incorrectly allowed

    # The CURRENT (unchanged) is_read_only_path() has the exact same blind spot,
    # confirmed live (not just via the frozen reference copy above).
    assert is_read_only_path(str(symlink_path)) is False

    # The NEW resolve_write_target() correctly catches it.
    resolved = resolve_write_target(symlink_path, repo_root=repo_root)
    assert resolved.allowed is False


@pytest.mark.parametrize("allowed_root", ALLOWED_WRITE_ROOTS)
def test_each_allowed_root_is_actually_allowed(repo_root, allowed_root):
    root_dir = repo_root / allowed_root.rstrip("/")
    root_dir.mkdir(parents=True, exist_ok=True)
    target = root_dir / "some_file.txt"
    resolved = resolve_write_target(target, repo_root=repo_root)
    assert resolved.allowed is True
