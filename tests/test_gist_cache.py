"""Cache validation tests for GitHub Gist service.

Tests cache structure, JSON format, raw file caching, and ETag handling.
These tests use mocked responses and don't require real API access.

Run with: pytest tests/test_gist_cache.py
"""

import sys
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from gist_service import GistService
from database import Database


class TestGistCacheStructure:
    """Test cache directory structure and file organization."""

    def setup_method(self):
        """Create temporary environment for each test."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.temp_db = self.temp_dir / "test_cache.db"
        self.cache_dir = self.temp_dir / "cache"

        schema_path = Path(__file__).parent.parent / "schema.sql"
        self.db = Database(self.temp_db)
        self.db.initialize_schema(schema_path)
        self.service = GistService(cache_dir=self.cache_dir, db=self.db)

    def test_cache_directory_created(self):
        """Test that cache directory is created on initialization."""
        assert self.cache_dir.exists(), "Cache directory should be created"
        assert self.cache_dir.is_dir(), "Cache path should be a directory"

    @patch('requests.get')
    def test_cache_file_naming(self, mock_get):
        """Test that cache files are named {gist_id}.json."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'ETag': '"abc123"'}
        mock_response.json.return_value = {
            'id': 'test123',
            'description': 'Test gist',
            'updated_at': '2026-01-11T00:00:00Z',
            'files': {
                'test.cs': {
                    'filename': 'test.cs',
                    'content': '// test',
                    'raw_url': 'https://gist.githubusercontent.com/test',
                    'language': 'C#',
                    'size': 7
                }
            }
        }
        mock_get.return_value = mock_response

        result = self.service.fetch_gist('test123', 'testowner', 'test.cs')

        # Verify cache file exists with correct name
        cache_file = self.cache_dir / "test123.json"
        assert cache_file.exists(), f"Cache file should exist at {cache_file}"

    @patch('requests.get')
    def test_cache_json_structure(self, mock_get):
        """Test that cache JSON has required structure: gist_id, etag, cached_at, data."""
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'ETag': '"etag_value_123"'}
        mock_response.json.return_value = {
            'id': 'test456',
            'description': 'Test',
            'updated_at': '2026-01-11T00:00:00Z',
            'files': {
                'example.cs': {
                    'filename': 'example.cs',
                    'content': 'using System;',
                    'raw_url': 'https://example.com',
                    'language': 'C#',
                    'size': 12
                }
            }
        }
        mock_get.return_value = mock_response

        self.service.fetch_gist('test456', 'owner', 'example.cs')

        # Read and validate cache structure
        cache_file = self.cache_dir / "test456.json"
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)

        # Verify required fields
        assert 'gist_id' in cache_data, "Cache should have gist_id"
        assert 'etag' in cache_data, "Cache should have etag"
        assert 'cached_at' in cache_data, "Cache should have cached_at timestamp"
        assert 'data' in cache_data, "Cache should have data section"

        # Verify values
        assert cache_data['gist_id'] == 'test456'
        assert cache_data['etag'] == '"etag_value_123"'

        # Verify cached_at is valid ISO timestamp
        cached_dt = datetime.fromisoformat(cache_data['cached_at'])
        assert isinstance(cached_dt, datetime)

        # Verify data section contains gist response
        assert 'files' in cache_data['data']
        assert 'example.cs' in cache_data['data']['files']

    @patch('requests.get')
    def test_raw_file_caching(self, mock_get):
        """Test that raw file content is cached separately in {gist_id}/{filename}.raw."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'ETag': '"xyz"'}
        mock_response.json.return_value = {
            'id': 'rawtest',
            'description': 'Raw test',
            'updated_at': '2026-01-11T00:00:00Z',
            'files': {
                'Code.cs': {
                    'filename': 'Code.cs',
                    'content': 'namespace Test { }',
                    'raw_url': 'https://raw.example.com',
                    'language': 'C#',
                    'size': 18
                }
            }
        }
        mock_get.return_value = mock_response

        result = self.service.fetch_gist('rawtest', 'owner', 'Code.cs')

        # Verify raw file cached
        raw_file = self.cache_dir / "rawtest" / "Code.cs.raw"
        assert raw_file.exists(), f"Raw file should exist at {raw_file}"

        # Verify content matches
        raw_content = raw_file.read_text(encoding='utf-8')
        assert raw_content == 'namespace Test { }', "Raw file content should match"
        assert raw_content == result.content, "Raw file should match result content"


class TestGistCacheValidation:
    """Test cache validation logic and expiry behavior."""

    def setup_method(self):
        """Create temporary environment for each test."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.temp_db = self.temp_dir / "test_validation.db"
        self.cache_dir = self.temp_dir / "cache"

        schema_path = Path(__file__).parent.parent / "schema.sql"
        self.db = Database(self.temp_db)
        self.db.initialize_schema(schema_path)
        self.service = GistService(cache_dir=self.cache_dir, db=self.db)

    def test_fresh_cache_used_within_one_hour(self):
        """Test that cache less than 1 hour old is used without API call."""
        # Create cache file with recent timestamp
        cache_file = self.cache_dir / "fresh123.json"
        cache_file.parent.mkdir(parents=True, exist_ok=True)

        cache_data = {
            'gist_id': 'fresh123',
            'etag': '"etag_fresh"',
            'cached_at': datetime.utcnow().isoformat(),  # Fresh cache
            'data': {
                'id': 'fresh123',
                'description': 'Fresh',
                'updated_at': '2026-01-11T00:00:00Z',
                'files': {
                    'Fresh.cs': {
                        'filename': 'Fresh.cs',
                        'content': '// fresh cache',
                        'raw_url': 'https://example.com',
                        'language': 'C#',
                        'size': 14
                    }
                }
            }
        }

        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f)

        # Fetch with fresh cache - should NOT hit API
        with patch('requests.get') as mock_get:
            result = self.service.fetch_gist('fresh123', 'owner', 'Fresh.cs')

            # Verify cache was used (no API call)
            mock_get.assert_not_called()
            assert result.success
            assert result.content == '// fresh cache'

    def test_expired_cache_triggers_revalidation(self):
        """Test that cache older than 1 hour triggers ETag revalidation."""
        # Create cache file with old timestamp
        cache_file = self.cache_dir / "expired123.json"
        cache_file.parent.mkdir(parents=True, exist_ok=True)

        old_time = (datetime.utcnow() - timedelta(hours=2)).isoformat()
        cache_data = {
            'gist_id': 'expired123',
            'etag': '"old_etag"',
            'cached_at': old_time,  # 2 hours old
            'data': {
                'id': 'expired123',
                'description': 'Expired',
                'updated_at': '2026-01-11T00:00:00Z',
                'files': {
                    'Expired.cs': {
                        'filename': 'Expired.cs',
                        'content': '// expired',
                        'raw_url': 'https://example.com',
                        'language': 'C#',
                        'size': 11
                    }
                }
            }
        }

        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f)

        # Mock API to return 304 Not Modified
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 304  # Not Modified
            mock_get.return_value = mock_response

            result = self.service.fetch_gist('expired123', 'owner', 'Expired.cs')

            # Verify API was called with ETag
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            headers = call_args[1]['headers']
            assert 'If-None-Match' in headers
            assert headers['If-None-Match'] == '"old_etag"'

            # Verify cached content still used after 304
            assert result.success
            assert result.content == '// expired'

    def test_missing_cache_file_triggers_full_fetch(self):
        """Test that missing cache file triggers full API fetch."""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {'ETag': '"new_etag"'}
            mock_response.json.return_value = {
                'id': 'new123',
                'description': 'New',
                'updated_at': '2026-01-11T00:00:00Z',
                'files': {
                    'New.cs': {
                        'filename': 'New.cs',
                        'content': '// new fetch',
                        'raw_url': 'https://example.com',
                        'language': 'C#',
                        'size': 11
                    }
                }
            }
            mock_get.return_value = mock_response

            result = self.service.fetch_gist('new123', 'owner', 'New.cs')

            # Verify full fetch occurred
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            headers = call_args[1]['headers']
            assert 'If-None-Match' not in headers  # No ETag on first fetch

            # Verify result
            assert result.success
            assert result.content == '// new fetch'

    def test_corrupted_cache_file_triggers_fresh_fetch(self):
        """Test that corrupted cache JSON triggers fresh fetch."""
        # Create corrupted cache file
        cache_file = self.cache_dir / "corrupt123.json"
        cache_file.parent.mkdir(parents=True, exist_ok=True)

        with open(cache_file, 'w', encoding='utf-8') as f:
            f.write("{ invalid json }")

        # Mock successful API response
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {'ETag': '"recovered"'}
            mock_response.json.return_value = {
                'id': 'corrupt123',
                'description': 'Recovered',
                'updated_at': '2026-01-11T00:00:00Z',
                'files': {
                    'Fixed.cs': {
                        'filename': 'Fixed.cs',
                        'content': '// recovered',
                        'raw_url': 'https://example.com',
                        'language': 'C#',
                        'size': 12
                    }
                }
            }
            mock_get.return_value = mock_response

            result = self.service.fetch_gist('corrupt123', 'owner', 'Fixed.cs')

            # Should succeed despite corrupted cache
            assert result.success
            mock_get.assert_called_once()


class TestGistCacheETag:
    """Test ETag handling in cache."""

    def setup_method(self):
        """Create temporary environment for each test."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.temp_db = self.temp_dir / "test_etag.db"
        self.cache_dir = self.temp_dir / "cache"

        schema_path = Path(__file__).parent.parent / "schema.sql"
        self.db = Database(self.temp_db)
        self.db.initialize_schema(schema_path)
        self.service = GistService(cache_dir=self.cache_dir, db=self.db)

    @patch('requests.get')
    def test_etag_stored_in_cache(self, mock_get):
        """Test that ETag from API response is stored in cache."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'ETag': '"test_etag_value_12345"'}
        mock_response.json.return_value = {
            'id': 'etag_test',
            'description': 'ETag test',
            'updated_at': '2026-01-11T00:00:00Z',
            'files': {
                'ETag.cs': {
                    'filename': 'ETag.cs',
                    'content': '// etag',
                    'raw_url': 'https://example.com',
                    'language': 'C#',
                    'size': 7
                }
            }
        }
        mock_get.return_value = mock_response

        self.service.fetch_gist('etag_test', 'owner', 'ETag.cs')

        # Verify ETag in cache
        cache_file = self.cache_dir / "etag_test.json"
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)

        assert cache_data['etag'] == '"test_etag_value_12345"'

    @patch('requests.get')
    def test_etag_sent_on_revalidation(self, mock_get):
        """Test that cached ETag is sent in If-None-Match header."""
        # Create expired cache with ETag
        cache_file = self.cache_dir / "revalidate123.json"
        cache_file.parent.mkdir(parents=True, exist_ok=True)

        old_time = (datetime.utcnow() - timedelta(hours=2)).isoformat()
        cache_data = {
            'gist_id': 'revalidate123',
            'etag': '"stored_etag_abc"',
            'cached_at': old_time,
            'data': {
                'id': 'revalidate123',
                'description': 'Revalidate',
                'updated_at': '2026-01-11T00:00:00Z',
                'files': {
                    'Rev.cs': {
                        'filename': 'Rev.cs',
                        'content': '// old',
                        'raw_url': 'https://example.com',
                        'language': 'C#',
                        'size': 6
                    }
                }
            }
        }

        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f)

        # Mock 304 response
        mock_response = Mock()
        mock_response.status_code = 304
        mock_get.return_value = mock_response

        self.service.fetch_gist('revalidate123', 'owner', 'Rev.cs')

        # Verify If-None-Match header sent
        call_args = mock_get.call_args
        headers = call_args[1]['headers']
        assert 'If-None-Match' in headers
        assert headers['If-None-Match'] == '"stored_etag_abc"'

    @patch('requests.get')
    def test_missing_etag_still_works(self, mock_get):
        """Test that cache without ETag still works (degrades to full fetch)."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}  # No ETag
        mock_response.json.return_value = {
            'id': 'no_etag',
            'description': 'No ETag',
            'updated_at': '2026-01-11T00:00:00Z',
            'files': {
                'NoETag.cs': {
                    'filename': 'NoETag.cs',
                    'content': '// no etag',
                    'raw_url': 'https://example.com',
                    'language': 'C#',
                    'size': 10
                }
            }
        }
        mock_get.return_value = mock_response

        result = self.service.fetch_gist('no_etag', 'owner', 'NoETag.cs')

        # Should succeed without ETag
        assert result.success

        # Cache should have None/null for ETag
        cache_file = self.cache_dir / "no_etag.json"
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)

        # ETag may be None or missing
        assert cache_data.get('etag') is None or 'etag' not in cache_data


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
