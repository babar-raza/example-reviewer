"""Tests for rollback functionality."""

import subprocess
import tempfile
from pathlib import Path

import sys
sys.path.insert(0, 'src')

from database import Database
from patching_service import PatchingService


def _init_git_repo(repo_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_path, check=True)


def _commit_file(repo_path: Path, file_path: Path, content: str, message: str) -> str:
    file_path.write_text(content, encoding="utf-8")
    subprocess.run(["git", "add", str(file_path)], cwd=repo_path, check=True)
    subprocess.run(["git", "commit", "-m", message], cwd=repo_path, check=True)
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_path,
                             capture_output=True, text=True, check=True)
    return result.stdout.strip()


def _init_db(db_path: Path) -> Database:
    db = Database(db_path)
    schema_path = Path(__file__).parent / "schema.sql"
    db.initialize_schema(schema_path)
    return db


def test_rollback_history_recorded_and_listed():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        _init_git_repo(repo_path)

        db = _init_db(repo_path / "test.db")
        patcher = PatchingService(db, repo_path)

        patcher._store_rollback_entry(
            "zip",
            commit_sha="abc123",
            backup_info={"branch": "backup/zip-000", "commit": "def456"},
            results={"modified_files": {"a.md"}, "patches_applied": 1}
        )

        history = patcher.get_rollback_history()
        assert history
        assert history[0]["family"] == "zip"
        assert history[0]["commit_sha"] == "abc123"
        db.close()


def test_rollback_last_operation_resets_repo():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        _init_git_repo(repo_path)

        file_path = repo_path / "test.md"
        initial_commit = _commit_file(repo_path, file_path, "initial", "init")

        db = _init_db(repo_path / "test.db")
        patcher = PatchingService(db, repo_path)

        backup_info = patcher._create_backup_branch("zip")

        new_commit = _commit_file(repo_path, file_path, "updated", "update")

        patcher._store_rollback_entry(
            "zip",
            commit_sha=new_commit,
            backup_info=backup_info,
            results={"modified_files": {str(file_path)}, "patches_applied": 1}
        )

        assert patcher.rollback_last_operation() is True
        assert file_path.read_text(encoding="utf-8") == "initial"
        db.close()


def test_rollback_file_restores_single_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        _init_git_repo(repo_path)

        file_path = repo_path / "test.md"
        _commit_file(repo_path, file_path, "initial", "init")

        db = _init_db(repo_path / "test.db")
        patcher = PatchingService(db, repo_path)

        backup_info = patcher._create_backup_branch("zip")

        _commit_file(repo_path, file_path, "updated", "update")

        patcher._store_rollback_entry(
            "zip",
            commit_sha="",
            backup_info=backup_info,
            results={"modified_files": {str(file_path)}, "patches_applied": 1}
        )

        assert patcher.rollback_file(str(file_path)) is True
        assert file_path.read_text(encoding="utf-8") == "initial"
        db.close()
