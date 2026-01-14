"""Tests for commit message generation and telemetry association."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import sys
sys.path.insert(0, 'src')

from patching_service import PatchingService, PatchResult


class DummyDB:
    pass


class TelemetryStub:
    def __init__(self):
        self.calls = []

    def associate_commit(self, commit_hash, commit_source, commit_author, commit_timestamp):
        self.calls.append({
            "commit_hash": commit_hash,
            "commit_source": commit_source,
            "commit_author": commit_author,
            "commit_timestamp": commit_timestamp
        })


def test_commit_message_includes_counts_and_snippets():
    with tempfile.TemporaryDirectory() as tmpdir:
        patcher = PatchingService(DummyDB(), Path(tmpdir))

        modified_files = {"a.md", "b.md"}
        results = {
            "patches_applied": 3,
            "errors": 1,
            "patches": [
                PatchResult(1, "a.md", True, "ok", "", ""),
                PatchResult(2, "b.md", True, "ok", "", ""),
                PatchResult(3, "c.md", False, "fail", "", "")
            ]
        }

        message = patcher._generate_commit_message(modified_files, results, "zip")
        assert message.startswith("fix(zip): apply 3 verified patches to 2 file(s)")
        assert "Snippets: #1, #2" in message


def test_commit_message_truncates_long_file_list():
    with tempfile.TemporaryDirectory() as tmpdir:
        patcher = PatchingService(DummyDB(), Path(tmpdir))

        modified_files = {f"file_{i}.md" for i in range(12)}
        results = {
            "patches_applied": 12,
            "errors": 0,
            "patches": [PatchResult(i, f"file_{i}.md", True, "ok", "", "") for i in range(12)]
        }

        message = patcher._generate_commit_message(modified_files, results, "zip")
        assert "... and 2 more files" in message


def test_commit_message_custom_template():
    with tempfile.TemporaryDirectory() as tmpdir:
        patcher = PatchingService(DummyDB(), Path(tmpdir))

        modified_files = {"a.md"}
        results = {
            "patches_applied": 1,
            "errors": 0,
            "patches": [PatchResult(1, "a.md", True, "ok", "", "")]
        }

        template = "fix({family}): {patch_count} patches\n\n{file_list}\n\nSnippets: {snippet_ids}"
        message = patcher._generate_commit_message(modified_files, results, "zip", template)
        assert message.startswith("fix(zip): 1 patches")
        assert "Snippets: #1" in message


def test_associate_commit_with_telemetry_calls_client():
    with tempfile.TemporaryDirectory() as tmpdir:
        telemetry = TelemetryStub()
        patcher = PatchingService(DummyDB(), Path(tmpdir), telemetry_client=telemetry)

        def _fake_run(cmd, **kwargs):
            return type("obj", (), {"stdout": "Test User <test@example.com>\n2026-01-01T00:00:00Z\n"})

        with patch("patching_service.subprocess.run", side_effect=_fake_run):
            patcher._associate_commit_with_telemetry("abc123")

        assert telemetry.calls
        assert telemetry.calls[0]["commit_hash"] == "abc123"
        assert telemetry.calls[0]["commit_source"] == "llm"


def test_associate_commit_telemetry_failure_does_not_raise():
    with tempfile.TemporaryDirectory() as tmpdir:
        class FailingTelemetry:
            def associate_commit(self, *args, **kwargs):
                raise RuntimeError("fail")

        patcher = PatchingService(DummyDB(), Path(tmpdir), telemetry_client=FailingTelemetry())

        def _fake_run(cmd, **kwargs):
            return type("obj", (), {"stdout": "Test User <test@example.com>\n2026-01-01T00:00:00Z\n"})

        with patch("patching_service.subprocess.run", side_effect=_fake_run):
            patcher._associate_commit_with_telemetry("abc123")
