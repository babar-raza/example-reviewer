"""
Tests for the _replace_block no-op guard (SR-01 / GAP-TEST-1, GAP-TEST-2, GAP-TEST-3).

The 2026-03-11 fix made _replace_block() return None when the block content *and*
language tag already match what the pipeline would write, avoiding unnecessary file I/O.

Coverage:
  (a) _replace_block unit — no-op / active paths, edge cases
  (b) update_markdown_file integration — no write when all blocks unchanged
  (c) regression — existing call sites still work after Optional[Tuple] return type change
"""
import hashlib
import os
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from src.core.database import Database
from src.core.models import ExampleRecord, ExampleStatus, Location, SourceType
from src.services.markdown_service import MarkdownUpdateService
from tests.conftest import make_pdp


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sig(code: str) -> str:
    normalized = code.strip().replace('\r\n', '\n')
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


def _make_block(
    content: str,
    language: str = "csharp",
    block_index: int = 0,
    fence_start_idx: int = 0,
    fence_end_idx: int = 2,
    start_line: int = 1,
    end_line: int = 3,
) -> dict:
    """Build a block dict as returned by parse_fenced_blocks."""
    return {
        'block_index': block_index,
        'content': content,
        'language': language,
        'signature': _sig(content),
        'fence_start_idx': fence_start_idx,
        'fence_end_idx': fence_end_idx,
        'start_line': start_line,
        'end_line': end_line,
    }


def _make_example(
    verified_code: str,
    language: str = "csharp",
    file_path: str = "/fake/file.md",
    family: str = "test-family",
) -> ExampleRecord:
    return ExampleRecord(
        family=family,
        file_path=file_path,
        source_type=SourceType.INLINE,
        language=language,
        verified_code=verified_code,
        status=ExampleStatus.VERIFIED,
        location=Location(block_index=0, start_line=1, end_line=3),
        code_block_signature=_sig(verified_code),
    )


def _make_fenced(language: str, code: str) -> str:
    return f"```{language}\n{code}\n```"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_db(tmp_path):
    db_path = tmp_path / "test.db"
    db = Database(db_path)
    db.initialize_schema()
    with db.get_connection() as conn:
        conn.execute(
            "INSERT INTO run_records (run_id, family, started_at, status) VALUES (?,?,?,?)",
            ("test-run", "test-family", datetime.utcnow().isoformat(), "running"),
        )
    yield db
    db.close()


@pytest.fixture
def svc(temp_db):
    return MarkdownUpdateService(db=temp_db, pdp=make_pdp(allow_writes=True), run_id="test-run")


# ---------------------------------------------------------------------------
# (a) _replace_block unit tests
# ---------------------------------------------------------------------------

class TestReplaceBlockUnit:

    def test_returns_none_when_code_and_language_identical(self, svc):
        """GAP-TEST-1 happy path: identical code + same language → no-op."""
        code = 'var x = 1;'
        block = _make_block(content=code, language='csharp')
        example = _make_example(verified_code=code, language='csharp')
        content = _make_fenced('csharp', code)

        result = svc._replace_block(content, block, example)

        assert result is None, "No-op guard must return None when code and language are identical"

    def test_returns_tuple_when_code_differs(self, svc):
        """GAP-TEST-1: differing code → Tuple returned, content updated."""
        old_code = 'var x = 1;'
        new_code = 'var x = 42;'
        block = _make_block(content=old_code, language='csharp')
        example = _make_example(verified_code=new_code)
        content = _make_fenced('csharp', old_code)

        result = svc._replace_block(content, block, example)

        assert result is not None, "Should return Tuple when code differs"
        updated_content, change_info = result
        assert new_code in updated_content
        assert old_code not in updated_content
        assert change_info['type'] == 'inline_replace'

    def test_noop_strips_trailing_newlines(self, svc):
        """GAP-TEST-3: trailing newlines (common from compiler/harness output) are normalised — treated as no-op."""
        code = 'var x = 1;'
        block = _make_block(content=code, language='csharp')
        example = _make_example(verified_code=f"{code}\n\n")  # trailing newlines from harness
        content = _make_fenced('csharp', code)

        result = svc._replace_block(content, block, example)

        assert result is None, "Trailing-newline-only differences must be treated as no-op"

    def test_not_noop_for_internal_whitespace_diff(self, svc):
        """GAP-TEST-3: internal whitespace (indentation) is a substantive change — NOT a no-op."""
        old_code = 'var x = 1;'
        new_code = '  var x = 1;'  # two leading spaces added
        block = _make_block(content=old_code, language='csharp')
        example = _make_example(verified_code=new_code)
        content = _make_fenced('csharp', old_code)

        result = svc._replace_block(content, block, example)

        assert result is not None, "Internal whitespace diff must trigger a write"
        updated_content, _ = result
        assert new_code in updated_content

    def test_noop_when_both_sides_empty(self, svc):
        """GAP-TEST-3: verified_code=None and block content empty → no-op (both strip to '')."""
        block = _make_block(content='', language='csharp')
        example = _make_example(verified_code='')
        content = _make_fenced('csharp', '')

        result = svc._replace_block(content, block, example)

        assert result is None, "Empty-on-both-sides must be a no-op"

    def test_noop_when_verified_code_is_none_and_block_empty(self, svc):
        """GAP-TEST-3: verified_code=None with empty block → (None or '') == '' → no-op."""
        block = _make_block(content='', language='csharp')
        # Build example manually to allow None verified_code
        example = ExampleRecord(
            family="test-family",
            file_path="/fake/file.md",
            source_type=SourceType.INLINE,
            language='csharp',
            verified_code=None,
            status=ExampleStatus.VERIFIED,
            location=Location(block_index=0, start_line=1, end_line=3),
        )
        content = _make_fenced('csharp', '')

        result = svc._replace_block(content, block, example)

        assert result is None, "None verified_code + empty block must be a no-op"

    def test_language_tag_diff_triggers_write(self, svc):
        """SR-02 / GAP-LANG: same code but empty fence tag → pipeline normalises to 'csharp' → NOT a no-op."""
        code = 'var x = 1;'
        # File has no language tag on the fence
        block = _make_block(content=code, language='')
        example = _make_example(verified_code=code, language='csharp')
        content = _make_fenced('', code)  # ```\n...\n```

        result = svc._replace_block(content, block, example)

        assert result is not None, (
            "Language tag normalisation ('' -> 'csharp') must NOT be suppressed by no-op guard"
        )
        updated_content, change_info = result
        assert '```csharp' in updated_content, "Fence should be rewritten with 'csharp' tag"
        assert change_info['language'] == 'csharp'

    def test_crlf_mid_string_behaviour_is_documented(self, svc):
        """GAP-TEST-3: CRLF vs LF mid-string — .strip() does NOT normalise this.

        This test documents the current behaviour: mid-string CRLF differences ARE
        treated as substantive changes (not a no-op). The test is intentionally
        assertive so any future change in behaviour is immediately visible.
        """
        code_lf = 'line1\nline2'
        code_crlf = 'line1\r\nline2'
        block = _make_block(content=code_lf, language='csharp')
        example = _make_example(verified_code=code_crlf)
        content = _make_fenced('csharp', code_lf)

        result = svc._replace_block(content, block, example)

        # Both are truthy but strip() only removes leading/trailing — mid CRLF persists.
        # Current behaviour: treated as a change (result is not None).
        assert result is not None, (
            "Mid-string CRLF vs LF is treated as a substantive difference (current behaviour). "
            "If this assertion fails, the normalisation semantics have changed — update accordingly."
        )


# ---------------------------------------------------------------------------
# (b) update_markdown_file integration tests
# ---------------------------------------------------------------------------

class TestUpdateMarkdownFileNoop:

    def _save_example_verified(self, db, example: ExampleRecord, verified_code: str) -> None:
        db.save_example(example, run_id="test-run")
        db.update_example_code(example.example_id, verified_code=verified_code, run_id="test-run")
        db.update_example_status(example.example_id, ExampleStatus.VERIFIED, run_id="test-run")

    def test_no_file_write_when_all_blocks_unchanged(self, svc, temp_db, tmp_path):
        """GAP-TEST-1 / GAP-TEST-2: update_markdown_file returns empty changes and does NOT
        touch the file when every example's verified_code already matches the file content."""
        code = '// Already correct\nConsole.WriteLine("ok");'
        md_path = tmp_path / "post.md"
        md_path.write_text(f"# Post\n\n```csharp\n{code}\n```\n", encoding='utf-8')
        mtime_before = md_path.stat().st_mtime

        example = ExampleRecord(
            family="test-family",
            file_path=str(md_path),
            source_type=SourceType.INLINE,
            language="csharp",
            location=Location(block_index=0, start_line=3, end_line=6),
            original_code=code,
            status=ExampleStatus.DISCOVERED,
            code_block_signature=_sig(code),
        )
        self._save_example_verified(temp_db, example, verified_code=code)

        success, changes = svc.update_markdown_file(str(md_path), dry_run=False)

        assert success is True
        assert changes == [], f"Expected no changes, got: {changes}"
        mtime_after = md_path.stat().st_mtime
        assert mtime_before == mtime_after, "File must not be written when code is already correct"

    def test_file_written_when_at_least_one_block_differs(self, svc, temp_db, tmp_path):
        """Regression: update_markdown_file still writes when verified_code differs."""
        old_code = '// Old version'
        new_code = '// New version'
        md_path = tmp_path / "post.md"
        md_path.write_text(f"# Post\n\n```csharp\n{old_code}\n```\n", encoding='utf-8')

        example = ExampleRecord(
            family="test-family",
            file_path=str(md_path),
            source_type=SourceType.INLINE,
            language="csharp",
            location=Location(block_index=0, start_line=3, end_line=5),
            original_code=old_code,
            status=ExampleStatus.DISCOVERED,
            code_block_signature=_sig(old_code),
        )
        self._save_example_verified(temp_db, example, verified_code=new_code)

        success, changes = svc.update_markdown_file(str(md_path), dry_run=False)

        assert success is True
        assert len(changes) == 1
        assert new_code in md_path.read_text(encoding='utf-8')

    def test_mixed_changed_and_unchanged_blocks(self, svc, temp_db, tmp_path):
        """Regression (GAP-TEST-2): 1 unchanged + 1 changed → only changed block written."""
        code_same = '// Unchanged'
        code_old = '// OldChanged'
        code_new = '// NewChanged'
        md_content = (
            f"# Post\n\n"
            f"```csharp\n{code_same}\n```\n\n"
            f"```csharp\n{code_old}\n```\n"
        )
        md_path = tmp_path / "post.md"
        md_path.write_text(md_content, encoding='utf-8')

        example1 = ExampleRecord(
            family="test-family", file_path=str(md_path), source_type=SourceType.INLINE,
            language="csharp", location=Location(block_index=0, start_line=3, end_line=5),
            original_code=code_same, status=ExampleStatus.DISCOVERED,
            code_block_signature=_sig(code_same),
        )
        example2 = ExampleRecord(
            family="test-family", file_path=str(md_path), source_type=SourceType.INLINE,
            language="csharp", location=Location(block_index=1, start_line=7, end_line=9),
            original_code=code_old, status=ExampleStatus.DISCOVERED,
            code_block_signature=_sig(code_old),
        )
        self._save_example_verified(temp_db, example1, verified_code=code_same)  # unchanged
        self._save_example_verified(temp_db, example2, verified_code=code_new)   # changed

        success, changes = svc.update_markdown_file(str(md_path), dry_run=False)

        assert success is True
        assert len(changes) == 1, f"Only 1 block differs; expected 1 change, got {len(changes)}"
        result_text = md_path.read_text(encoding='utf-8')
        assert code_same in result_text, "Unchanged block must still be present"
        assert code_new in result_text, "Changed block must be updated"
        assert code_old not in result_text, "Old code must be replaced"

    def test_dry_run_never_writes(self, svc, temp_db, tmp_path):
        """Regression: dry_run=True must not write even when code differs."""
        old_code = '// Old'
        new_code = '// New'
        md_path = tmp_path / "post.md"
        md_path.write_text(f"# Post\n\n```csharp\n{old_code}\n```\n", encoding='utf-8')
        original_text = md_path.read_text(encoding='utf-8')

        example = ExampleRecord(
            family="test-family", file_path=str(md_path), source_type=SourceType.INLINE,
            language="csharp", location=Location(block_index=0, start_line=3, end_line=5),
            original_code=old_code, status=ExampleStatus.DISCOVERED,
            code_block_signature=_sig(old_code),
        )
        self._save_example_verified(temp_db, example, verified_code=new_code)

        success, changes = svc.update_markdown_file(str(md_path), dry_run=True)

        assert success is True
        assert len(changes) == 1  # change is reported but not applied
        assert md_path.read_text(encoding='utf-8') == original_text, "dry_run must not modify file"
