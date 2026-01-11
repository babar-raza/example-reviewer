"""Tests for cache validation and recovery in GistService.

Tests verify_cache() method which detects and removes corrupted cache files.
These tests ensure the system never crashes from cache corruption.

Run with: pytest tests/test_cache_validation.py -v
"""

import sys
import json
import tempfile
import logging
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from gist_service import GistService
from database import Database


class TestCacheValidation:
    """Test verify_cache() method for cache integrity checking."""

    def setup_method(self):
        """Create temporary environment for each test."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.temp_db = self.temp_dir / "test_validation.db"
        self.cache_dir = self.temp_dir / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        schema_path = Path(__file__).parent.parent / "schema.sql"
        self.db = Database(self.temp_db)
        self.db.initialize_schema(schema_path)
        self.service = GistService(cache_dir=self.cache_dir, db=self.db)

        # Setup logging to capture warnings
        self.log_capture = []
        self.handler = logging.Handler()
        self.handler.emit = lambda record: self.log_capture.append(record)
        logging.getLogger('gist_service').addHandler(self.handler)
        logging.getLogger('gist_service').setLevel(logging.WARNING)

    def teardown_method(self):
        """Clean up logging handler."""
        logging.getLogger('gist_service').removeHandler(self.handler)

    def create_valid_cache_file(self, gist_id: str) -> Path:
        """Helper to create a valid cache file."""
        cache_file = self.cache_dir / f"{gist_id}.json"
        cache_data = {
            'gist_id': gist_id,
            'etag': '"test_etag_123"',
            'cached_at': datetime.utcnow().isoformat(),
            'data': {
                'id': gist_id,
                'description': 'Test gist',
                'updated_at': '2026-01-11T00:00:00Z',
                'files': {
                    'test.cs': {
                        'filename': 'test.cs',
                        'content': '// test',
                        'raw_url': 'https://example.com',
                        'language': 'C#',
                        'size': 7
                    }
                }
            }
        }

        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2)

        return cache_file

    def test_verify_cache_all_valid(self):
        """Test that all valid cache files pass validation."""
        # Create 3 valid cache files
        self.create_valid_cache_file('valid001')
        self.create_valid_cache_file('valid002')
        self.create_valid_cache_file('valid003')

        # Verify cache
        result = self.service.verify_cache()

        # Assertions
        assert result['total_files'] == 3, "Should find 3 cache files"
        assert result['valid_files'] == 3, "All files should be valid"
        assert result['corrupted_files'] == 0, "No files should be corrupted"
        assert len(result['removed_files']) == 0, "No files should be removed"
        assert len(result['errors']) == 0, "No errors should occur"

        # Verify files still exist
        assert (self.cache_dir / "valid001.json").exists()
        assert (self.cache_dir / "valid002.json").exists()
        assert (self.cache_dir / "valid003.json").exists()

    def test_verify_cache_corrupted_json(self):
        """Test that corrupted JSON files are detected and removed."""
        # Create 1 valid file
        self.create_valid_cache_file('valid001')

        # Create 2 corrupted files with invalid JSON
        corrupt1 = self.cache_dir / "corrupt001.json"
        with open(corrupt1, 'w', encoding='utf-8') as f:
            f.write("{ invalid json }")

        corrupt2 = self.cache_dir / "corrupt002.json"
        with open(corrupt2, 'w', encoding='utf-8') as f:
            f.write("not json at all")

        # Verify cache
        result = self.service.verify_cache()

        # Assertions
        assert result['total_files'] == 3, "Should find 3 cache files"
        assert result['valid_files'] == 1, "Only 1 file should be valid"
        assert result['corrupted_files'] == 2, "2 files should be corrupted"
        assert len(result['removed_files']) == 2, "2 files should be removed"

        # Verify corrupted files removed
        assert not corrupt1.exists(), "Corrupted file 1 should be removed"
        assert not corrupt2.exists(), "Corrupted file 2 should be removed"

        # Verify valid file still exists
        assert (self.cache_dir / "valid001.json").exists()

        # Verify logging
        assert len(self.log_capture) >= 2, "Should log warnings for corrupted files"
        warning_messages = [rec.getMessage() for rec in self.log_capture if rec.levelno == logging.WARNING]
        assert any('corrupt001.json' in msg for msg in warning_messages), "Should log corrupt001 file path"
        assert any('corrupt002.json' in msg for msg in warning_messages), "Should log corrupt002 file path"

    def test_verify_cache_missing_required_fields(self):
        """Test that cache files with missing required fields are removed."""
        # Missing gist_id
        missing_gist_id = self.cache_dir / "missing_gist_id.json"
        with open(missing_gist_id, 'w', encoding='utf-8') as f:
            json.dump({
                'etag': '"test"',
                'cached_at': datetime.utcnow().isoformat(),
                'data': {'files': {}}
            }, f)

        # Missing etag
        missing_etag = self.cache_dir / "missing_etag.json"
        with open(missing_etag, 'w', encoding='utf-8') as f:
            json.dump({
                'gist_id': 'test123',
                'cached_at': datetime.utcnow().isoformat(),
                'data': {'files': {}}
            }, f)

        # Missing cached_at
        missing_cached_at = self.cache_dir / "missing_cached_at.json"
        with open(missing_cached_at, 'w', encoding='utf-8') as f:
            json.dump({
                'gist_id': 'test456',
                'etag': '"test"',
                'data': {'files': {}}
            }, f)

        # Missing data
        missing_data = self.cache_dir / "missing_data.json"
        with open(missing_data, 'w', encoding='utf-8') as f:
            json.dump({
                'gist_id': 'test789',
                'etag': '"test"',
                'cached_at': datetime.utcnow().isoformat()
            }, f)

        # Verify cache
        result = self.service.verify_cache()

        # Assertions
        assert result['total_files'] == 4, "Should find 4 cache files"
        assert result['valid_files'] == 0, "No files should be valid"
        assert result['corrupted_files'] == 4, "All 4 files should be corrupted"
        assert len(result['removed_files']) == 4, "All 4 files should be removed"

        # Verify all files removed
        assert not missing_gist_id.exists()
        assert not missing_etag.exists()
        assert not missing_cached_at.exists()
        assert not missing_data.exists()

        # Verify error messages mention missing fields
        warning_messages = [rec.getMessage() for rec in self.log_capture if rec.levelno == logging.WARNING]
        assert any('Missing required fields' in msg for msg in warning_messages), "Should log missing fields"

    def test_verify_cache_invalid_timestamp(self):
        """Test that cache files with invalid cached_at format are removed."""
        # Invalid timestamp format
        invalid_ts = self.cache_dir / "invalid_timestamp.json"
        with open(invalid_ts, 'w', encoding='utf-8') as f:
            json.dump({
                'gist_id': 'test123',
                'etag': '"test"',
                'cached_at': 'not-a-valid-timestamp',
                'data': {'files': {}}
            }, f)

        # Verify cache
        result = self.service.verify_cache()

        # Assertions
        assert result['total_files'] == 1, "Should find 1 cache file"
        assert result['valid_files'] == 0, "File should be invalid"
        assert result['corrupted_files'] == 1, "File should be corrupted"
        assert len(result['removed_files']) == 1, "File should be removed"

        # Verify file removed
        assert not invalid_ts.exists(), "Invalid timestamp file should be removed"

        # Verify error message
        warning_messages = [rec.getMessage() for rec in self.log_capture if rec.levelno == logging.WARNING]
        assert any('Invalid cached_at timestamp' in msg for msg in warning_messages), "Should log timestamp error"

    def test_verify_cache_invalid_data_structure(self):
        """Test that cache files with invalid data structure are removed."""
        # data is not a dict
        invalid_data_type = self.cache_dir / "invalid_data_type.json"
        with open(invalid_data_type, 'w', encoding='utf-8') as f:
            json.dump({
                'gist_id': 'test123',
                'etag': '"test"',
                'cached_at': datetime.utcnow().isoformat(),
                'data': "should be dict"
            }, f)

        # data missing files key
        missing_files = self.cache_dir / "missing_files.json"
        with open(missing_files, 'w', encoding='utf-8') as f:
            json.dump({
                'gist_id': 'test456',
                'etag': '"test"',
                'cached_at': datetime.utcnow().isoformat(),
                'data': {'no_files_key': True}
            }, f)

        # Verify cache
        result = self.service.verify_cache()

        # Assertions
        assert result['total_files'] == 2, "Should find 2 cache files"
        assert result['valid_files'] == 0, "No files should be valid"
        assert result['corrupted_files'] == 2, "Both files should be corrupted"
        assert len(result['removed_files']) == 2, "Both files should be removed"

        # Verify files removed
        assert not invalid_data_type.exists()
        assert not missing_files.exists()

    def test_verify_cache_empty_directory(self):
        """Test that empty cache directory returns zero counts."""
        # Cache directory is empty (created in setup but no files added)
        result = self.service.verify_cache()

        # Assertions
        assert result['total_files'] == 0, "Should find 0 cache files"
        assert result['valid_files'] == 0, "Should have 0 valid files"
        assert result['corrupted_files'] == 0, "Should have 0 corrupted files"
        assert len(result['removed_files']) == 0, "Should remove 0 files"
        assert len(result['errors']) == 0, "Should have 0 errors"

    def test_verify_cache_nonexistent_directory(self):
        """Test that nonexistent cache directory is handled gracefully."""
        # Create service with nonexistent cache directory
        nonexistent_cache = self.temp_dir / "does_not_exist"
        service = GistService(cache_dir=nonexistent_cache, db=self.db)

        # Verify cache
        result = service.verify_cache()

        # Assertions
        assert result['total_files'] == 0, "Should find 0 cache files"
        assert result['valid_files'] == 0, "Should have 0 valid files"
        assert result['corrupted_files'] == 0, "Should have 0 corrupted files"
        assert len(result['removed_files']) == 0, "Should remove 0 files"
        assert len(result['errors']) == 0, "Should have 0 errors"

    def test_verify_cache_filesystem_error(self):
        """Test that filesystem errors during removal are captured gracefully."""
        # Create a corrupted file
        corrupt = self.cache_dir / "corrupt_locked.json"
        with open(corrupt, 'w', encoding='utf-8') as f:
            f.write("{ invalid }")

        # Mock unlink to raise permission error
        original_unlink = Path.unlink

        def mock_unlink(self, *args, **kwargs):
            if 'corrupt_locked' in str(self):
                raise PermissionError("Permission denied")
            return original_unlink(self, *args, **kwargs)

        with patch.object(Path, 'unlink', mock_unlink):
            # Verify cache
            result = self.service.verify_cache()

            # Assertions
            assert result['total_files'] == 1, "Should find 1 cache file"
            assert result['valid_files'] == 0, "File should be invalid"
            assert result['corrupted_files'] == 0, "File removal should fail"
            assert len(result['removed_files']) == 0, "No files successfully removed"
            assert len(result['errors']) == 1, "Should capture removal error"

            # Verify error details
            error = result['errors'][0]
            assert 'corrupt_locked' in error['file'], "Error should reference file"
            assert 'validation_error' in error, "Should include validation error"
            assert 'removal_error' in error, "Should include removal error"
            assert 'Permission denied' in error['removal_error']

    def test_verify_cache_mixed_valid_and_corrupted(self):
        """Test verification with mix of valid and corrupted files."""
        # Create 2 valid files
        self.create_valid_cache_file('valid001')
        self.create_valid_cache_file('valid002')

        # Create 2 corrupted files
        corrupt1 = self.cache_dir / "corrupt001.json"
        with open(corrupt1, 'w', encoding='utf-8') as f:
            f.write("{ bad json }")

        corrupt2 = self.cache_dir / "corrupt002.json"
        with open(corrupt2, 'w', encoding='utf-8') as f:
            json.dump({
                'gist_id': 'test',
                'etag': '"test"',
                'cached_at': 'invalid-timestamp',
                'data': {'files': {}}
            }, f)

        # Verify cache
        result = self.service.verify_cache()

        # Assertions
        assert result['total_files'] == 4, "Should find 4 cache files"
        assert result['valid_files'] == 2, "2 files should be valid"
        assert result['corrupted_files'] == 2, "2 files should be corrupted"
        assert len(result['removed_files']) == 2, "2 files should be removed"

        # Verify valid files still exist
        assert (self.cache_dir / "valid001.json").exists()
        assert (self.cache_dir / "valid002.json").exists()

        # Verify corrupted files removed
        assert not corrupt1.exists()
        assert not corrupt2.exists()

    def test_verify_cache_logging_includes_file_paths(self):
        """Test that WARNING logs include full file paths."""
        # Create corrupted file
        corrupt = self.cache_dir / "corrupt_with_path.json"
        with open(corrupt, 'w', encoding='utf-8') as f:
            f.write("{ invalid }")

        # Verify cache
        result = self.service.verify_cache()

        # Verify logging
        assert result['corrupted_files'] == 1, "Should detect 1 corrupted file"

        warning_messages = [rec.getMessage() for rec in self.log_capture if rec.levelno == logging.WARNING]
        assert len(warning_messages) >= 1, "Should log at least 1 warning"

        # Check that file path is in warning message
        found_path_in_log = False
        for msg in warning_messages:
            if 'corrupt_with_path.json' in msg and str(corrupt) in msg:
                found_path_in_log = True
                break

        assert found_path_in_log, f"Log should contain full file path. Logs: {warning_messages}"


class TestCacheValidationEdgeCases:
    """Test edge cases and boundary conditions for cache validation."""

    def setup_method(self):
        """Create temporary environment for each test."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.temp_db = self.temp_dir / "test_edge.db"
        self.cache_dir = self.temp_dir / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        schema_path = Path(__file__).parent.parent / "schema.sql"
        self.db = Database(self.temp_db)
        self.db.initialize_schema(schema_path)
        self.service = GistService(cache_dir=self.cache_dir, db=self.db)

    def test_verify_cache_ignores_non_json_files(self):
        """Test that non-.json files in cache directory are ignored."""
        # Create various non-json files
        (self.cache_dir / "readme.txt").write_text("Not a cache file")
        (self.cache_dir / "data.xml").write_text("<xml/>")
        (self.cache_dir / ".gitkeep").write_text("")

        # Create one valid json file
        valid_cache = self.cache_dir / "valid123.json"
        with open(valid_cache, 'w', encoding='utf-8') as f:
            json.dump({
                'gist_id': 'valid123',
                'etag': '"test"',
                'cached_at': datetime.utcnow().isoformat(),
                'data': {'files': {}}
            }, f)

        # Verify cache
        result = self.service.verify_cache()

        # Should only process .json file
        assert result['total_files'] == 1, "Should only count .json files"
        assert result['valid_files'] == 1, "Valid .json file should pass"

        # Non-json files should still exist
        assert (self.cache_dir / "readme.txt").exists()
        assert (self.cache_dir / "data.xml").exists()
        assert (self.cache_dir / ".gitkeep").exists()

    def test_verify_cache_handles_empty_json_object(self):
        """Test that empty JSON object {} is detected as invalid."""
        empty = self.cache_dir / "empty.json"
        with open(empty, 'w', encoding='utf-8') as f:
            json.dump({}, f)

        result = self.service.verify_cache()

        assert result['total_files'] == 1
        assert result['valid_files'] == 0
        assert result['corrupted_files'] == 1
        assert not empty.exists(), "Empty cache file should be removed"

    def test_verify_cache_handles_null_values(self):
        """Test that null values in required fields are detected."""
        null_values = self.cache_dir / "null_values.json"
        with open(null_values, 'w', encoding='utf-8') as f:
            json.dump({
                'gist_id': None,
                'etag': None,
                'cached_at': None,
                'data': None
            }, f)

        result = self.service.verify_cache()

        assert result['total_files'] == 1
        assert result['valid_files'] == 0
        assert result['corrupted_files'] == 1
        assert not null_values.exists(), "File with null values should be removed"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
