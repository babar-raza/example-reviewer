"""
Tests for Gist Publishing functionality.
Tests GistPublisher class and upload modes with mocked API calls.
"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import hashlib

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from gist_publisher import GistPublisher
from patching_service import PatchingService
from database import Database, Snippet


class TestGistPublisher:
    """Test GistPublisher class with mocked requests."""

    def setup_method(self):
        """Create temp database."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test.db"
        self.db = Database(self.db_path)
        self.db.connect()

        # Create gist_publications table
        self.db._conn.executescript("""
            CREATE TABLE IF NOT EXISTS gist_publications (
                publication_id INTEGER PRIMARY KEY,
                snippet_id INTEGER NOT NULL,
                old_gist_id TEXT,
                old_gist_owner TEXT,
                old_gist_filename TEXT,
                new_gist_id TEXT NOT NULL,
                new_gist_owner TEXT NOT NULL,
                new_gist_filename TEXT NOT NULL,
                new_gist_url TEXT NOT NULL,
                new_gist_raw_url TEXT NOT NULL,
                published_at TEXT NOT NULL DEFAULT (datetime('now')),
                status TEXT NOT NULL,
                error_message TEXT,
                code_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
        """)
        self.db._conn.commit()

    def test_publish_gist_success(self):
        """Test successful gist publishing with mocked requests.post."""
        # Create publisher
        publisher = GistPublisher(
            owner='testuser',
            token='test_token_1234',
            db=self.db,
            is_public=True
        )

        # Mock response
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            'id': 'new_gist_id_123',
            'html_url': 'https://gist.github.com/testuser/new_gist_id_123',
            'files': {
                'example.cs': {
                    'raw_url': 'https://gist.githubusercontent.com/testuser/new_gist_id_123/raw/example.cs'
                }
            }
        }

        # Patch requests.post
        with patch('requests.post', return_value=mock_response) as mock_post:
            result = publisher.publish_gist(
                snippet_id=1,
                code_content='class Test { }',
                filename='example.cs',
                description='Test gist',
                old_gist_id='old_123',
                old_owner='olduser'
            )

            # Verify API call
            assert mock_post.called
            call_args = mock_post.call_args
            assert call_args[0][0] == 'https://api.github.com/gists'
            assert 'Authorization' in call_args[1]['headers']
            assert 'Bearer test_token_1234' in call_args[1]['headers']['Authorization']

            # Verify payload
            payload = call_args[1]['json']
            assert payload['description'] == 'Test gist'
            assert payload['public'] is True
            assert 'example.cs' in payload['files']
            assert payload['files']['example.cs']['content'] == 'class Test { }'

        # Verify result
        assert result['success'] is True
        assert result['gist_id'] == 'new_gist_id_123'
        assert result['html_url'] == 'https://gist.github.com/testuser/new_gist_id_123'
        assert 'raw_url' in result

        # Verify database record
        pub = self.db.get_gist_publication(1)
        assert pub is not None
        assert pub['snippet_id'] == 1
        assert pub['new_gist_id'] == 'new_gist_id_123'
        assert pub['new_gist_owner'] == 'testuser'
        assert pub['status'] == 'success'
        assert pub['error_message'] is None

    def test_publish_gist_unauthorized(self):
        """Test handling of 401 Unauthorized."""
        publisher = GistPublisher(
            owner='testuser',
            token='invalid_token',
            db=self.db,
            is_public=True
        )

        # Mock 401 response
        mock_response = Mock()
        mock_response.status_code = 401

        with patch('requests.post', return_value=mock_response):
            result = publisher.publish_gist(
                snippet_id=2,
                code_content='class Test { }',
                filename='test.cs',
                description='Test'
            )

        # Verify failure
        assert result['success'] is False
        assert result['gist_id'] is None
        assert 'Unauthorized' in result['error']

        # Verify database record
        pub = self.db.get_gist_publication(2)
        assert pub is not None
        assert pub['status'] == 'failed'
        assert 'Unauthorized' in pub['error_message']

    def test_publish_gist_rate_limited(self):
        """Test handling of 403 rate limit."""
        publisher = GistPublisher(
            owner='testuser',
            token='test_token',
            db=self.db,
            is_public=True
        )

        # Mock 403 response with rate limit headers
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.headers = {'X-RateLimit-Remaining': '0'}

        with patch('requests.post', return_value=mock_response):
            result = publisher.publish_gist(
                snippet_id=3,
                code_content='class Test { }',
                filename='test.cs',
                description='Test'
            )

        # Verify failure
        assert result['success'] is False
        assert 'rate limit' in result['error'].lower()

        # Verify database record
        pub = self.db.get_gist_publication(3)
        assert pub is not None
        assert pub['status'] == 'failed'
        assert 'rate limit' in pub['error_message'].lower()

    def test_token_never_logged(self, caplog):
        """Test that token never appears in logs (only last 4 chars)."""
        import logging
        caplog.set_level(logging.INFO)

        publisher = GistPublisher(
            owner='testuser',
            token='secret_token_abcd',
            db=self.db,
            is_public=True
        )

        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            'id': 'gist123',
            'html_url': 'https://gist.github.com/testuser/gist123',
            'files': {
                'test.cs': {
                    'raw_url': 'https://gist.githubusercontent.com/testuser/gist123/raw/test.cs'
                }
            }
        }

        with patch('requests.post', return_value=mock_response):
            publisher.publish_gist(
                snippet_id=4,
                code_content='class Test { }',
                filename='test.cs',
                description='Test'
            )

        # Check logs
        log_text = caplog.text

        # Token should NOT appear in full
        assert 'secret_token_abcd' not in log_text

        # Only last 4 chars should appear
        assert '...abcd' in log_text


class TestPatchingUploadModes:
    """Test patching service upload modes with mocked GistPublisher."""

    def setup_method(self):
        """Create temp directory and database."""
        self.temp_dir = tempfile.mkdtemp()
        self.content_root = Path(self.temp_dir) / "content"
        self.content_root.mkdir()

        self.db_path = Path(self.temp_dir) / "test.db"
        self.db = Database(self.db_path)
        self.db.connect()

        # Minimal schema
        self.db._conn.executescript("""
            CREATE TABLE IF NOT EXISTS snippet_versions (
                version_id INTEGER PRIMARY KEY,
                snippet_id INTEGER NOT NULL,
                version_type TEXT NOT NULL,
                code_content TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS gist_publications (
                publication_id INTEGER PRIMARY KEY,
                snippet_id INTEGER NOT NULL,
                old_gist_id TEXT,
                old_gist_owner TEXT,
                old_gist_filename TEXT,
                new_gist_id TEXT NOT NULL,
                new_gist_owner TEXT NOT NULL,
                new_gist_filename TEXT NOT NULL,
                new_gist_url TEXT NOT NULL,
                new_gist_raw_url TEXT NOT NULL,
                published_at TEXT NOT NULL DEFAULT (datetime('now')),
                status TEXT NOT NULL,
                error_message TEXT,
                code_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
        """)
        self.db._conn.commit()

    def test_patching_upload_on_change_unchanged(self):
        """Test upload-on-change with unchanged code (no upload)."""
        # Create test file
        test_file = self.content_root / "test.md"
        original_content = '{{< gist "olduser" "old123" "Test.cs" >}}'
        test_file.write_text(original_content, encoding='utf-8')

        # Create snippet
        locator = {
            'gist_id': 'old123',
            'gist_owner': 'olduser',
            'gist_file': 'Test.cs',
            'notes': json.dumps({'gist_shortcode': original_content})
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

        # Insert versions (unchanged)
        code = "class Test { }"
        self.db._conn.execute(
            "INSERT INTO snippet_versions (snippet_id, version_type, code_content, content_hash) VALUES (?, 'original', ?, ?)",
            (1, code, 'hash1')
        )
        self.db._conn.execute(
            "INSERT INTO snippet_versions (snippet_id, version_type, code_content, content_hash) VALUES (?, 'current', ?, ?)",
            (1, code, 'hash1')  # Same = unchanged
        )
        self.db._conn.commit()

        # Mock GistPublisher
        mock_publisher = Mock()

        # Create service
        service = PatchingService(self.db, self.content_root, mock_publisher)

        # Patch with upload-on-change
        result = service._patch_gist_snippet(snippet, page, dry_run=False, gist_mode='upload-on-change')

        # Should succeed without uploading
        assert result.success is True
        assert 'unchanged' in result.message.lower()
        assert 'no upload' in result.message.lower()

        # GistPublisher should NOT be called
        assert not mock_publisher.publish_gist.called

        # File should be unchanged
        final_content = test_file.read_text(encoding='utf-8')
        assert final_content == original_content

    def test_patching_upload_on_change_changed(self):
        """Test upload-on-change with changed code (upload + update shortcode)."""
        # Create test file
        test_file = self.content_root / "test.md"
        original_content = '{{< gist "olduser" "old123" "Test.cs" >}}'
        test_file.write_text(original_content, encoding='utf-8')

        # Create snippet
        locator = {
            'gist_id': 'old123',
            'gist_owner': 'olduser',
            'gist_file': 'Test.cs',
            'notes': json.dumps({'gist_shortcode': original_content})
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

        # Insert versions (changed)
        original_code = "class Test { }"
        fixed_code = "class Test {\n    // Fixed\n    public void Method() { }\n}"

        self.db._conn.execute(
            "INSERT INTO snippet_versions (snippet_id, version_type, code_content, content_hash) VALUES (?, 'original', ?, ?)",
            (1, original_code, 'hash_orig')
        )
        self.db._conn.execute(
            "INSERT INTO snippet_versions (snippet_id, version_type, code_content, content_hash) VALUES (?, 'current', ?, ?)",
            (1, fixed_code, 'hash_fixed')  # Different = changed
        )
        self.db._conn.commit()

        # Mock GistPublisher
        mock_publisher = Mock()
        mock_publisher.owner = 'newuser'
        mock_publisher.publish_gist.return_value = {
            'success': True,
            'gist_id': 'new_gist_456',
            'html_url': 'https://gist.github.com/newuser/new_gist_456',
            'raw_url': 'https://gist.githubusercontent.com/newuser/new_gist_456/raw/Test.cs'
        }

        # Create service
        service = PatchingService(self.db, self.content_root, mock_publisher)

        # Patch with upload-on-change
        result = service._patch_gist_snippet(snippet, page, dry_run=False, gist_mode='upload-on-change')

        # Should succeed and upload
        assert result.success is True
        assert 'published' in result.message.lower()
        assert 'new_gist_456' in result.message

        # GistPublisher should be called
        assert mock_publisher.publish_gist.called
        call_args = mock_publisher.publish_gist.call_args
        assert call_args[1]['snippet_id'] == 1
        assert call_args[1]['code_content'] == fixed_code
        assert call_args[1]['filename'] == 'Test.cs'

        # File should have new shortcode
        final_content = test_file.read_text(encoding='utf-8')
        assert '{{< gist "newuser" "new_gist_456" "Test.cs" >}}' in final_content
        assert 'old123' not in final_content

    def test_patching_upload_always(self):
        """Test upload-always mode (always uploads even if unchanged)."""
        # Create test file
        test_file = self.content_root / "test.md"
        original_content = '{{< gist "olduser" "old123" "Test.cs" >}}'
        test_file.write_text(original_content, encoding='utf-8')

        # Create snippet
        locator = {
            'gist_id': 'old123',
            'gist_owner': 'olduser',
            'gist_file': 'Test.cs',
            'notes': json.dumps({'gist_shortcode': original_content})
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

        # Insert versions (unchanged)
        code = "class Test { }"
        self.db._conn.execute(
            "INSERT INTO snippet_versions (snippet_id, version_type, code_content, content_hash) VALUES (?, 'original', ?, ?)",
            (1, code, 'hash1')
        )
        self.db._conn.execute(
            "INSERT INTO snippet_versions (snippet_id, version_type, code_content, content_hash) VALUES (?, 'current', ?, ?)",
            (1, code, 'hash1')  # Same but should still upload
        )
        self.db._conn.commit()

        # Mock GistPublisher
        mock_publisher = Mock()
        mock_publisher.owner = 'newuser'
        mock_publisher.publish_gist.return_value = {
            'success': True,
            'gist_id': 'new_always_789',
            'html_url': 'https://gist.github.com/newuser/new_always_789',
            'raw_url': 'https://gist.githubusercontent.com/newuser/new_always_789/raw/Test.cs'
        }

        # Create service
        service = PatchingService(self.db, self.content_root, mock_publisher)

        # Patch with upload-always
        result = service._patch_gist_snippet(snippet, page, dry_run=False, gist_mode='upload-always')

        # Should succeed and upload (even though unchanged)
        assert result.success is True
        assert 'published' in result.message.lower()

        # GistPublisher should be called
        assert mock_publisher.publish_gist.called

        # File should have new shortcode
        final_content = test_file.read_text(encoding='utf-8')
        assert 'new_always_789' in final_content

    def test_upload_mode_without_publisher_fails(self):
        """Test that upload mode fails gracefully without GistPublisher."""
        test_file = self.content_root / "test.md"
        test_file.write_text('{{< gist "user" "123" >}}', encoding='utf-8')

        locator = {
            'gist_id': '123',
            'notes': json.dumps({'gist_shortcode': '{{< gist "user" "123" >}}'})
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

        # Insert versions (changed to trigger upload)
        self.db._conn.execute(
            "INSERT INTO snippet_versions (snippet_id, version_type, code_content, content_hash) VALUES (?, 'original', ?, ?)",
            (1, "old", 'hash1')
        )
        self.db._conn.execute(
            "INSERT INTO snippet_versions (snippet_id, version_type, code_content, content_hash) VALUES (?, 'current', ?, ?)",
            (1, "new", 'hash2')
        )
        self.db._conn.commit()

        # Create service WITHOUT gist_publisher
        service = PatchingService(self.db, self.content_root, gist_publisher=None)

        # Patch with upload mode should fail
        result = service._patch_gist_snippet(snippet, page, dry_run=False, gist_mode='upload-on-change')

        assert result.success is False
        assert 'GistPublisher' in result.message
        assert 'env vars' in result.message.lower()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
