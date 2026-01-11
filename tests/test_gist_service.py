"""
Tests for Gist Service.
Tests gist shortcode parsing, file selection, and API integration (mocked).
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from gist_service import GistService
from database import Database


class TestGistShortcodeParsing:
    """Test gist shortcode parsing with various formats."""

    def setup_method(self):
        """Create temp database and gist service for tests."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_dir = Path(self.temp_dir) / "cache"
        self.db_path = Path(self.temp_dir) / "test.db"

        self.db = Database(self.db_path)
        self.db.connect()

        # Initialize schema (minimal for testing)
        self.db._conn.executescript("""
            CREATE TABLE IF NOT EXISTS gists (
                gist_id TEXT PRIMARY KEY,
                owner TEXT NOT NULL,
                description TEXT,
                updated_at TEXT,
                etag TEXT,
                last_fetched_at TEXT,
                last_status TEXT,
                last_error TEXT
            );

            CREATE TABLE IF NOT EXISTS gist_files (
                gist_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                raw_url TEXT NOT NULL,
                language TEXT,
                content TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                file_size INTEGER,
                fetched_at TEXT,
                PRIMARY KEY (gist_id, filename)
            );
        """)

        self.service = GistService(self.cache_dir, self.db)

    def test_parse_quoted_shortcode(self):
        """Test parsing quoted shortcode format."""
        shortcode = '{{< gist "aspose" "abc123" >}}'
        result = self.service.parse_gist_shortcode(shortcode)

        assert result is not None
        owner, gist_id, filename = result
        assert owner == "aspose"
        assert gist_id == "abc123"
        assert filename is None

    def test_parse_quoted_with_filename(self):
        """Test parsing quoted shortcode with filename."""
        shortcode = '{{< gist "aspose" "abc123" "Example.cs" >}}'
        result = self.service.parse_gist_shortcode(shortcode)

        assert result is not None
        owner, gist_id, filename = result
        assert owner == "aspose"
        assert gist_id == "abc123"
        assert filename == "Example.cs"

    def test_parse_unquoted_shortcode(self):
        """Test parsing unquoted shortcode format."""
        shortcode = '{{< gist aspose abc123 >}}'
        result = self.service.parse_gist_shortcode(shortcode)

        assert result is not None
        owner, gist_id, filename = result
        assert owner == "aspose"
        assert gist_id == "abc123"
        assert filename is None

    def test_parse_no_space_after_opening(self):
        """Test parsing shortcode without space after {{<."""
        shortcode = '{{<gist "aspose" "abc123">}}'
        result = self.service.parse_gist_shortcode(shortcode)

        assert result is not None
        owner, gist_id, filename = result
        assert owner == "aspose"
        assert gist_id == "abc123"

    def test_parse_malformed_shortcode(self):
        """Test parsing malformed shortcode returns None."""
        shortcode = '{{< gist incomplete'
        result = self.service.parse_gist_shortcode(shortcode)

        assert result is None


class TestGistFileFetching:
    """Test gist fetching and file selection logic."""

    def setup_method(self):
        """Create temp database and gist service for tests."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_dir = Path(self.temp_dir) / "cache"
        self.db_path = Path(self.temp_dir) / "test.db"

        self.db = Database(self.db_path)
        self.db.connect()

        # Initialize schema
        self.db._conn.executescript("""
            CREATE TABLE IF NOT EXISTS gists (
                gist_id TEXT PRIMARY KEY,
                owner TEXT NOT NULL,
                description TEXT,
                updated_at TEXT,
                etag TEXT,
                last_fetched_at TEXT,
                last_status TEXT,
                last_error TEXT
            );

            CREATE TABLE IF NOT EXISTS gist_files (
                gist_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                raw_url TEXT NOT NULL,
                language TEXT,
                content TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                file_size INTEGER,
                fetched_at TEXT,
                PRIMARY KEY (gist_id, filename)
            );
        """)

        self.service = GistService(self.cache_dir, self.db)

    @patch('gist_service.requests.get')
    def test_fetch_single_csharp_file(self, mock_get):
        """Test fetching gist with single C# file (auto-select)."""
        # Mock API response with single .cs file
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'ETag': '"abc123"'}
        mock_response.json.return_value = {
            'id': 'gist123',
            'description': 'Test gist',
            'updated_at': '2026-01-11T00:00:00Z',
            'files': {
                'Example.cs': {
                    'filename': 'Example.cs',
                    'language': 'C#',
                    'size': 100,
                    'raw_url': 'https://gist.githubusercontent.com/...',
                    'content': 'using System;\n\nclass Program { }'
                }
            }
        }
        mock_get.return_value = mock_response

        result = self.service.fetch_gist('gist123', 'aspose')

        assert result.success is True
        assert result.filename == 'Example.cs'
        assert 'using System' in result.content
        assert result.language == 'C#'

    @patch('gist_service.requests.get')
    def test_fetch_explicit_filename(self, mock_get):
        """Test fetching gist with explicit filename."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'ETag': '"abc123"'}
        mock_response.json.return_value = {
            'id': 'gist123',
            'description': 'Test gist',
            'updated_at': '2026-01-11T00:00:00Z',
            'files': {
                'File1.cs': {
                    'filename': 'File1.cs',
                    'language': 'C#',
                    'size': 50,
                    'raw_url': 'https://gist.githubusercontent.com/...',
                    'content': 'class File1 { }'
                },
                'File2.cs': {
                    'filename': 'File2.cs',
                    'language': 'C#',
                    'size': 50,
                    'raw_url': 'https://gist.githubusercontent.com/...',
                    'content': 'class File2 { }'
                }
            }
        }
        mock_get.return_value = mock_response

        # Request specific file
        result = self.service.fetch_gist('gist123', 'aspose', 'File2.cs')

        assert result.success is True
        assert result.filename == 'File2.cs'
        assert 'File2' in result.content

    @patch('gist_service.requests.get')
    def test_fetch_ambiguous_multi_file(self, mock_get):
        """Test fetching gist with multiple C# files returns skip reason."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'ETag': '"abc123"'}
        mock_response.json.return_value = {
            'id': 'gist123',
            'description': 'Multi-file gist',
            'updated_at': '2026-01-11T00:00:00Z',
            'files': {
                'File1.cs': {
                    'filename': 'File1.cs',
                    'language': 'C#',
                    'size': 50,
                    'raw_url': 'https://gist.githubusercontent.com/...',
                    'content': 'class File1 { }'
                },
                'File2.cs': {
                    'filename': 'File2.cs',
                    'language': 'C#',
                    'size': 50,
                    'raw_url': 'https://gist.githubusercontent.com/...',
                    'content': 'class File2 { }'
                }
            }
        }
        mock_get.return_value = mock_response

        # No filename specified - should be ambiguous
        result = self.service.fetch_gist('gist123', 'aspose')

        assert result.success is False
        assert result.skip_reason is not None
        assert 'ambiguous' in result.skip_reason.lower()
        assert 'File1.cs' in result.skip_reason
        assert 'File2.cs' in result.skip_reason

    @patch('gist_service.requests.get')
    def test_fetch_no_csharp_files(self, mock_get):
        """Test fetching gist with no C# files returns skip reason."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'ETag': '"abc123"'}
        mock_response.json.return_value = {
            'id': 'gist123',
            'description': 'Python gist',
            'updated_at': '2026-01-11T00:00:00Z',
            'files': {
                'script.py': {
                    'filename': 'script.py',
                    'language': 'Python',
                    'size': 50,
                    'raw_url': 'https://gist.githubusercontent.com/...',
                    'content': 'print("hello")'
                }
            }
        }
        mock_get.return_value = mock_response

        result = self.service.fetch_gist('gist123', 'aspose')

        assert result.success is False
        assert result.skip_reason is not None
        assert 'no c#' in result.skip_reason.lower()

    @patch('gist_service.requests.get')
    def test_fetch_rate_limited(self, mock_get):
        """Test handling of rate limit response."""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.headers = {'X-RateLimit-Remaining': '0'}
        mock_get.return_value = mock_response

        result = self.service.fetch_gist('gist123', 'aspose')

        assert result.success is False
        assert result.error is not None
        assert 'rate limit' in result.error.lower()

    @patch('gist_service.requests.get')
    def test_fetch_not_found(self, mock_get):
        """Test handling of 404 response."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = self.service.fetch_gist('nonexistent', 'aspose')

        assert result.success is False
        assert result.error is not None
        assert 'not found' in result.error.lower()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
