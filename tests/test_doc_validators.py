"""
Unit tests for documentation validation scripts.

Tests check_doc_links.py and check_doc_freshness.py.
"""
import importlib.util
import subprocess
from pathlib import Path
from unittest import mock

import pytest


SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts" / "validation"


def _load_module(name, filename):
    """Load a validation script as a module."""
    spec = importlib.util.spec_from_file_location(name, SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# check_doc_links tests
# ---------------------------------------------------------------------------

class TestDocLinks:
    """Tests for scripts/validation/check_doc_links.py."""

    def _build_doc_tree(self, tmp_path, files: dict):
        """Create a temp directory tree with markdown files.

        Args:
            files: dict mapping relative paths to file contents.
        """
        for rel_path, content in files.items():
            p = tmp_path / rel_path
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")

    def test_valid_links_pass(self, tmp_path):
        """All links resolve to existing files."""
        self._build_doc_tree(tmp_path, {
            "docs/index.md": "See [overview](architecture/overview.md).",
            "docs/architecture/overview.md": "# Overview",
            "README.md": "See [docs](docs/index.md).",
        })
        mod = _load_module("check_doc_links", "check_doc_links.py")

        with mock.patch.object(mod, "REPO_ROOT", tmp_path), \
             mock.patch.object(mod, "ROOT_MD_FILES", list(tmp_path.glob("*.md"))), \
             mock.patch.object(mod, "SCAN_ROOTS", [tmp_path / "docs"]):
            result = mod.main()

        assert result == 0

    def test_broken_link_detected(self, tmp_path):
        """A link to a nonexistent file is reported as broken."""
        self._build_doc_tree(tmp_path, {
            "docs/index.md": "See [missing](nonexistent.md).",
        })
        mod = _load_module("check_doc_links", "check_doc_links.py")

        with mock.patch.object(mod, "REPO_ROOT", tmp_path), \
             mock.patch.object(mod, "ROOT_MD_FILES", []), \
             mock.patch.object(mod, "SCAN_ROOTS", [tmp_path / "docs"]):
            result = mod.main()

        assert result == 1

    def test_external_links_ignored(self, tmp_path):
        """HTTP and mailto links are not checked for file existence."""
        self._build_doc_tree(tmp_path, {
            "docs/index.md": (
                "See [web](https://example.com) and "
                "[email](mailto:test@example.com) and "
                "[anchor](#section)."
            ),
        })
        mod = _load_module("check_doc_links", "check_doc_links.py")

        with mock.patch.object(mod, "REPO_ROOT", tmp_path), \
             mock.patch.object(mod, "ROOT_MD_FILES", []), \
             mock.patch.object(mod, "SCAN_ROOTS", [tmp_path / "docs"]):
            result = mod.main()

        assert result == 0

    def test_anchor_links_resolve(self, tmp_path):
        """Links with anchors resolve to the base file."""
        self._build_doc_tree(tmp_path, {
            "docs/guide.md": "See [section](overview.md#details).",
            "docs/overview.md": "# Overview\n## Details",
        })
        mod = _load_module("check_doc_links", "check_doc_links.py")

        with mock.patch.object(mod, "REPO_ROOT", tmp_path), \
             mock.patch.object(mod, "ROOT_MD_FILES", []), \
             mock.patch.object(mod, "SCAN_ROOTS", [tmp_path / "docs"]):
            result = mod.main()

        assert result == 0


# ---------------------------------------------------------------------------
# check_doc_freshness tests
# ---------------------------------------------------------------------------

class TestDocFreshness:
    """Tests for scripts/validation/check_doc_freshness.py."""

    def test_fresh_docs_pass(self, tmp_path):
        """Documents modified recently are within threshold."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "fresh.md").write_text("# Fresh doc")

        mod = _load_module("check_doc_freshness", "check_doc_freshness.py")

        # Mock git log to return today's date
        from datetime import datetime, timezone
        today = datetime.now(timezone.utc).isoformat()

        def mock_run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 0, stdout=today, stderr="")

        with mock.patch.object(mod, "REPO_ROOT", tmp_path), \
             mock.patch.object(mod, "DOC_ROOTS", [docs_dir]), \
             mock.patch("subprocess.run", side_effect=mock_run), \
             mock.patch("sys.argv", ["check_doc_freshness.py"]):
            result = mod.main()

        assert result == 0

    def test_stale_docs_detected(self, tmp_path):
        """Documents older than threshold are flagged."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "stale.md").write_text("# Old doc")

        mod = _load_module("check_doc_freshness", "check_doc_freshness.py")

        # Mock git log to return a date 365 days ago
        old_date = "2025-06-01T00:00:00+00:00"

        def mock_run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 0, stdout=old_date, stderr="")

        with mock.patch.object(mod, "REPO_ROOT", tmp_path), \
             mock.patch.object(mod, "DOC_ROOTS", [docs_dir]), \
             mock.patch("subprocess.run", side_effect=mock_run), \
             mock.patch("sys.argv", ["check_doc_freshness.py", "--max-age-days", "180"]):
            result = mod.main()

        assert result == 1

    def test_adr_directory_skipped(self, tmp_path):
        """Files in adr/ directory are excluded from freshness check."""
        docs_dir = tmp_path / "docs"
        adr_dir = docs_dir / "adr"
        adr_dir.mkdir(parents=True)
        (adr_dir / "0001-decision.md").write_text("# ADR 0001")

        mod = _load_module("check_doc_freshness", "check_doc_freshness.py")

        with mock.patch.object(mod, "REPO_ROOT", tmp_path), \
             mock.patch.object(mod, "DOC_ROOTS", [docs_dir]), \
             mock.patch("sys.argv", ["check_doc_freshness.py"]):
            result = mod.main()

        # Should return 0 because no files were checked (only adr/ exists)
        assert result == 0

    def test_untracked_files_skipped(self, tmp_path):
        """Files with no git history are silently skipped."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "new.md").write_text("# New untracked doc")

        mod = _load_module("check_doc_freshness", "check_doc_freshness.py")

        # Mock git log returning empty (untracked file)
        def mock_run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        with mock.patch.object(mod, "REPO_ROOT", tmp_path), \
             mock.patch.object(mod, "DOC_ROOTS", [docs_dir]), \
             mock.patch("subprocess.run", side_effect=mock_run), \
             mock.patch("sys.argv", ["check_doc_freshness.py"]):
            result = mod.main()

        assert result == 0
