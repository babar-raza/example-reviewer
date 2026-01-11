"""
Tests for Gist Patching.
Tests gist patch behavior: unchanged gists stay as shortcodes, changed gists become inline fences.
"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from patching_service import PatchingService
from database import Database, Snippet


class TestGistPatching:
    """Test gist-specific patching behavior."""

    def setup_method(self):
        """Create temp directory and minimal database setup."""
        self.temp_dir = tempfile.mkdtemp()
        self.content_root = Path(self.temp_dir) / "content"
        self.content_root.mkdir()

        self.db_path = Path(self.temp_dir) / "test.db"
        self.db = Database(self.db_path)
        self.db.connect()

        # Minimal schema for testing
        self.db._conn.executescript("""
            CREATE TABLE IF NOT EXISTS snippet_versions (
                version_id INTEGER PRIMARY KEY,
                snippet_id INTEGER NOT NULL,
                version_type TEXT NOT NULL,
                code_content TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                created_at TEXT
            );
        """)

        self.service = PatchingService(self.db, self.content_root)

    def test_unchanged_gist_no_patch(self):
        """Test that unchanged gist shortcode is preserved."""
        # Create test file with gist shortcode
        test_file = self.content_root / "test.md"
        original_content = '''---
title: Test
---

# Example

{{< gist "aspose" "abc123" "Test.cs" >}}

More text.
'''
        test_file.write_text(original_content, encoding='utf-8')

        # Create mock snippet
        locator = {
            'gist_id': 'abc123',
            'gist_file': 'Test.cs',
            'notes': json.dumps({'gist_shortcode': '{{< gist "aspose" "abc123" "Test.cs" >}}'})
        }

        snippet = Snippet(
            snippet_id=1,
            page_id=1,
            snippet_ordinal=1,
            locator_json=json.dumps(locator),
            snippet_type='gist',
            language='csharp',
            status='verified'
        )

        page = Mock()
        page.relative_path = "test.md"

        # Insert snippet versions (original == verified)
        original_code = "class Test { }"
        self.db._conn.execute(
            """INSERT INTO snippet_versions
               (snippet_id, version_type, code_content, content_hash)
               VALUES (?, 'original', ?, ?)""",
            (1, original_code, 'hash123')
        )
        self.db._conn.execute(
            """INSERT INTO snippet_versions
               (snippet_id, version_type, code_content, content_hash)
               VALUES (?, 'current', ?, ?)""",
            (1, original_code, 'hash123')  # Same code = unchanged
        )
        self.db._conn.commit()

        # Patch with inline-on-change mode (default)
        result = self.service._patch_gist_snippet(snippet, page, dry_run=False, gist_mode='inline-on-change')

        # Should succeed without modifying file
        assert result.success is True
        assert 'unchanged' in result.message.lower()

        # File should be unchanged
        final_content = test_file.read_text(encoding='utf-8')
        assert final_content == original_content
        assert '{{< gist' in final_content

    def test_changed_gist_inline_replacement(self):
        """Test that changed gist shortcode is replaced with inline fence."""
        # Create test file with gist shortcode
        test_file = self.content_root / "test.md"
        original_content = '''---
title: Test
---

# Example

{{< gist "aspose" "abc123" "Test.cs" >}}

More text.
'''
        test_file.write_text(original_content, encoding='utf-8')

        # Create mock snippet
        locator = {
            'gist_id': 'abc123',
            'gist_file': 'Test.cs',
            'notes': json.dumps({'gist_shortcode': '{{< gist "aspose" "abc123" "Test.cs" >}}'})
        }

        snippet = Snippet(
            snippet_id=1,
            page_id=1,
            snippet_ordinal=1,
            locator_json=json.dumps(locator),
            snippet_type='gist',
            language='csharp',
            status='verified'
        )

        page = Mock()
        page.relative_path = "test.md"

        # Insert snippet versions (original != verified)
        original_code = "class Test { }"
        verified_code = "class Test {\n    // Fixed\n    public void Method() { }\n}"

        self.db._conn.execute(
            """INSERT INTO snippet_versions
               (snippet_id, version_type, code_content, content_hash)
               VALUES (?, 'original', ?, ?)""",
            (1, original_code, 'hash_original')
        )
        self.db._conn.execute(
            """INSERT INTO snippet_versions
               (snippet_id, version_type, code_content, content_hash)
               VALUES (?, 'current', ?, ?)""",
            (1, verified_code, 'hash_verified')  # Different code = changed
        )
        self.db._conn.commit()

        # Patch with inline-on-change mode
        result = self.service._patch_gist_snippet(snippet, page, dry_run=False, gist_mode='inline-on-change')

        # Should succeed and inline the gist
        assert result.success is True
        assert 'inlined' in result.message.lower()

        # File should be modified
        final_content = test_file.read_text(encoding='utf-8')

        # Gist shortcode should be gone
        assert '{{< gist' not in final_content

        # Should have inline fence with csharp marker
        assert '```csharp' in final_content
        assert 'class Test {' in final_content
        assert '// Fixed' in final_content
        assert 'public void Method()' in final_content
        assert '```' in final_content

        # Context should be preserved
        assert '# Example' in final_content
        assert 'More text.' in final_content

    def test_preserve_mode_never_inlines(self):
        """Test that preserve mode never replaces gists."""
        test_file = self.content_root / "test.md"
        original_content = '{{< gist "aspose" "abc123" >}}'
        test_file.write_text(original_content, encoding='utf-8')

        locator = {
            'gist_id': 'abc123',
            'notes': json.dumps({'gist_shortcode': '{{< gist "aspose" "abc123" >}}'})
        }

        snippet = Snippet(
            snippet_id=1,
            page_id=1,
            snippet_ordinal=1,
            locator_json=json.dumps(locator),
            snippet_type='gist',
            language='csharp',
            status='verified'
        )

        page = Mock()
        page.relative_path = "test.md"

        # Insert versions (code changed)
        self.db._conn.execute(
            """INSERT INTO snippet_versions
               (snippet_id, version_type, code_content, content_hash)
               VALUES (?, 'original', ?, ?)""",
            (1, "original", 'hash1')
        )
        self.db._conn.execute(
            """INSERT INTO snippet_versions
               (snippet_id, version_type, code_content, content_hash)
               VALUES (?, 'current', ?, ?)""",
            (1, "changed", 'hash2')
        )
        self.db._conn.commit()

        # Patch with preserve mode
        result = self.service._patch_gist_snippet(snippet, page, dry_run=False, gist_mode='preserve')

        # Should preserve gist
        assert result.success is True
        assert 'preserved' in result.message.lower()

        # File unchanged
        final_content = test_file.read_text(encoding='utf-8')
        assert final_content == original_content


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
