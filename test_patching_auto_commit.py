"""Tests for auto-commit functionality in patching service."""

import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

import sys
sys.path.insert(0, 'src')

from patching_service import PatchingService, PatchResult


class DummyVersion:
    def __init__(self, code_content: str):
        self.code_content = code_content


class DummySnippet:
    def __init__(self, snippet_id: int, snippet_type: str = "fence"):
        self.snippet_id = snippet_id
        self.snippet_type = snippet_type


class DummyPage:
    def __init__(self, relative_path: str):
        self.relative_path = relative_path


class DummyDB:
    def __init__(self, snippets_with_pages):
        self._snippets_with_pages = snippets_with_pages

    def get_snippets_by_status(self, family: str, status: str):
        return self._snippets_with_pages

    def get_latest_snippet_version(self, snippet_id: int, version_type: str):
        return DummyVersion("// code")


def _init_git_repo(repo_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_path, check=True)


def _commit_file(repo_path: Path, file_path: Path, content: str, message: str) -> None:
    file_path.write_text(content, encoding="utf-8")
    subprocess.run(["git", "add", str(file_path)], cwd=repo_path, check=True)
    subprocess.run(["git", "commit", "-m", message], cwd=repo_path, check=True)


def test_auto_commit_creates_commit():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        _init_git_repo(repo_path)

        file_path = repo_path / "test.md"
        _commit_file(repo_path, file_path, "initial", "init")

        snippet = DummySnippet(1)
        page = DummyPage("test.md")
        db = DummyDB([(snippet, page)])

        patcher = PatchingService(db, repo_path)

        def _fake_patch(snippet_obj, page_obj, original_code, verified_code, dry_run):
            if not dry_run:
                file_path.write_text("updated", encoding="utf-8")
            return PatchResult(snippet_obj.snippet_id, str(file_path), True, "patched", "", "")

        patcher._patch_snippet_in_file = _fake_patch  # type: ignore[assignment]

        results = patcher.patch_verified_snippets("zip", dry_run=False, gist_mode="inline-on-change", auto_commit=True)

        assert results.get("commit_sha")
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_path,
                              capture_output=True, text=True, check=True).stdout.strip()
        assert results["commit_sha"] == head


def test_dry_run_disables_auto_commit():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        _init_git_repo(repo_path)

        file_path = repo_path / "test.md"
        _commit_file(repo_path, file_path, "initial", "init")

        snippet = DummySnippet(1)
        page = DummyPage("test.md")
        db = DummyDB([(snippet, page)])

        patcher = PatchingService(db, repo_path)

        def _fake_patch(snippet_obj, page_obj, original_code, verified_code, dry_run):
            if not dry_run:
                file_path.write_text("updated", encoding="utf-8")
            return PatchResult(snippet_obj.snippet_id, str(file_path), True, "patched", "", "")

        patcher._patch_snippet_in_file = _fake_patch  # type: ignore[assignment]

        before = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_path,
                                capture_output=True, text=True, check=True).stdout.strip()
        results = patcher.patch_verified_snippets("zip", dry_run=True, gist_mode="inline-on-change", auto_commit=True)
        after = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_path,
                               capture_output=True, text=True, check=True).stdout.strip()

        assert results.get("commit_sha") is None
        assert before == after


def test_auto_commit_skipped_on_errors():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        _init_git_repo(repo_path)

        file_path = repo_path / "test.md"
        _commit_file(repo_path, file_path, "initial", "init")

        snippet = DummySnippet(1)
        page = DummyPage("test.md")
        db = DummyDB([(snippet, page)])

        patcher = PatchingService(db, repo_path)

        def _fake_patch(snippet_obj, page_obj, original_code, verified_code, dry_run):
            return PatchResult(snippet_obj.snippet_id, str(file_path), False, "failed", "", "")

        patcher._patch_snippet_in_file = _fake_patch  # type: ignore[assignment]

        before = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_path,
                                capture_output=True, text=True, check=True).stdout.strip()
        results = patcher.patch_verified_snippets("zip", dry_run=False, gist_mode="inline-on-change", auto_commit=True)
        after = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_path,
                               capture_output=True, text=True, check=True).stdout.strip()

        assert results.get("commit_sha") is None
        assert results["errors"] == 1
        assert before == after


def test_auto_commit_skipped_when_no_files_modified():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        _init_git_repo(repo_path)

        file_path = repo_path / "test.md"
        _commit_file(repo_path, file_path, "initial", "init")

        db = DummyDB([])
        patcher = PatchingService(db, repo_path)

        before = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_path,
                                capture_output=True, text=True, check=True).stdout.strip()
        results = patcher.patch_verified_snippets("zip", dry_run=False, gist_mode="inline-on-change", auto_commit=True)
        after = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_path,
                               capture_output=True, text=True, check=True).stdout.strip()

        assert results.get("commit_sha") is None
        assert before == after


def test_git_not_available_graceful_error():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        _init_git_repo(repo_path)

        db = DummyDB([])
        patcher = PatchingService(db, repo_path)

        with patch("patching_service.subprocess.run", side_effect=FileNotFoundError("git")):
            commit_sha = patcher._git_commit_changes({"test.md"}, {"patches_applied": 1}, "zip")

        assert commit_sha is None
