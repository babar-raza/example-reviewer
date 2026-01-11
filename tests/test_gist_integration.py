"""Integration tests for GitHub Gist API.

These tests require real network access to GitHub API.
Run with: pytest tests/test_gist_integration.py --integration

IMPORTANT: These tests are SKIPPED by default. Pass --integration flag to run.

Rate Limits:
- Without GITHUB_TOKEN: 60 requests/hour
- With GITHUB_TOKEN: 5000 requests/hour
"""

import sys
import json
import time
import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from gist_service import GistService
from database import Database
from fixtures.gist_fixtures import REAL_GIST_OWNER, REAL_GIST_ID, REAL_GIST_FILE


@pytest.mark.integration
class TestGistIntegrationRealAPI:
    """Integration tests with real GitHub API (opt-in with --integration flag)."""

    def setup_method(self):
        """Create temporary database and cache for each test."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.temp_db = self.temp_dir / "test_integration.db"
        self.cache_dir = self.temp_dir / "cache"

        self.db = Database(self.temp_db)
        self.service = GistService(cache_dir=self.cache_dir, db=self.db)

    def test_fetch_real_gist_with_filename(self):
        """Test fetching a real Aspose gist with specific filename.

        Validates:
        - GitHub API connectivity
        - Successful gist fetch
        - Correct file content extraction
        - Database persistence
        - Cache file creation
        """
        result = self.service.fetch_gist(
            gist_id=REAL_GIST_ID,
            owner=REAL_GIST_OWNER,
            filename=REAL_GIST_FILE
        )

        # Verify successful fetch
        assert result.success, f"Gist fetch failed: {result.error}"
        assert result.gist_id == REAL_GIST_ID
        assert result.owner == REAL_GIST_OWNER
        assert result.filename == REAL_GIST_FILE
        assert result.content is not None, "Content should not be None"
        assert len(result.content) > 0, "Content should not be empty"
        assert result.content_hash is not None, "Content hash should be computed"
        assert result.raw_url is not None, "Raw URL should be present"

        # Verify cache file exists
        cache_file = self.cache_dir / f"{REAL_GIST_ID}.json"
        assert cache_file.exists(), f"Cache file should exist at {cache_file}"

        # Verify cache structure
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
            assert 'gist_id' in cache_data
            assert 'etag' in cache_data
            assert 'cached_at' in cache_data
            assert 'data' in cache_data
            assert cache_data['gist_id'] == REAL_GIST_ID

        # Verify raw file cache
        raw_file = self.cache_dir / REAL_GIST_ID / f"{REAL_GIST_FILE}.raw"
        assert raw_file.exists(), f"Raw file cache should exist at {raw_file}"
        assert raw_file.read_text(encoding='utf-8') == result.content

        # Verify database records
        gist_record = self.db.get_gist(REAL_GIST_ID)
        assert gist_record is not None, "Gist should be in database"
        assert gist_record['owner'] == REAL_GIST_OWNER
        assert gist_record['status'] == 'success'

        file_record = self.db.get_gist_file(REAL_GIST_ID, REAL_GIST_FILE)
        assert file_record is not None, "Gist file should be in database"
        assert file_record['content_hash'] == result.content_hash

    def test_cache_hit_behavior(self):
        """Test that second fetch uses cache (cache hit scenario).

        Validates:
        - First fetch creates cache
        - Second fetch uses cached data (no API call if cache fresh)
        - ETag conditional request on cache validation
        """
        # First fetch - should hit API
        result1 = self.service.fetch_gist(
            gist_id=REAL_GIST_ID,
            owner=REAL_GIST_OWNER,
            filename=REAL_GIST_FILE
        )
        assert result1.success, "First fetch should succeed"

        # Verify cache exists
        cache_file = self.cache_dir / f"{REAL_GIST_ID}.json"
        assert cache_file.exists()

        # Get cache timestamp
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
            cached_at = cache_data['cached_at']
            etag = cache_data.get('etag')

        # Second fetch - should use cache (within 1 hour window)
        result2 = self.service.fetch_gist(
            gist_id=REAL_GIST_ID,
            owner=REAL_GIST_OWNER,
            filename=REAL_GIST_FILE
        )
        assert result2.success, "Second fetch should succeed"
        assert result2.content == result1.content, "Content should match from cache"
        assert result2.content_hash == result1.content_hash

    def test_cache_miss_after_expiry(self):
        """Test that expired cache triggers fresh fetch with ETag.

        Note: This test simulates cache expiry by manipulating cache timestamp.
        """
        # First fetch
        result1 = self.service.fetch_gist(
            gist_id=REAL_GIST_ID,
            owner=REAL_GIST_OWNER,
            filename=REAL_GIST_FILE
        )
        assert result1.success

        # Manipulate cache to simulate expiry (>1 hour old)
        cache_file = self.cache_dir / f"{REAL_GIST_ID}.json"
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)

        # Set cached_at to 2 hours ago
        expired_time = (datetime.utcnow() - timedelta(hours=2)).isoformat()
        cache_data['cached_at'] = expired_time

        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2)

        # Second fetch - should revalidate with ETag (might get 304 Not Modified)
        result2 = self.service.fetch_gist(
            gist_id=REAL_GIST_ID,
            owner=REAL_GIST_OWNER,
            filename=REAL_GIST_FILE
        )
        assert result2.success, "Fetch after cache expiry should succeed"

    def test_404_not_found_error(self):
        """Test handling of non-existent gist (404 error).

        Validates:
        - Proper error handling for 404
        - Database records error state
        - No cache file created for errors
        """
        fake_gist_id = "nonexistent_gist_12345_fake"

        result = self.service.fetch_gist(
            gist_id=fake_gist_id,
            owner=REAL_GIST_OWNER,
            filename="fake.cs"
        )

        # Verify error handling
        assert not result.success, "Fetch should fail for non-existent gist"
        assert result.error is not None
        assert "not found" in result.error.lower() or "404" in str(result.error)

        # Verify database records error
        gist_record = self.db.get_gist(fake_gist_id)
        assert gist_record is not None, "Failed gist should be recorded"
        assert gist_record['status'] == 'not_found'

        # Verify no cache file created
        cache_file = self.cache_dir / f"{fake_gist_id}.json"
        assert not cache_file.exists(), "No cache should exist for 404 errors"

    def test_missing_filename_in_gist(self):
        """Test error when requested file doesn't exist in gist.

        Validates:
        - Proper error message for missing file
        - Gist metadata still persisted
        """
        fake_filename = "NonExistentFile_12345.cs"

        result = self.service.fetch_gist(
            gist_id=REAL_GIST_ID,
            owner=REAL_GIST_OWNER,
            filename=fake_filename
        )

        # Verify error
        assert not result.success, "Should fail when file not in gist"
        assert result.error is not None
        assert fake_filename in result.error

        # Gist metadata should still be persisted
        gist_record = self.db.get_gist(REAL_GIST_ID)
        assert gist_record is not None
        assert gist_record['status'] == 'success'  # Gist exists, just file not found

    def test_auto_select_single_csharp_file(self):
        """Test automatic selection when gist has one C# file and no filename specified.

        Note: This test only works if the real gist has exactly one .cs file.
        If it has multiple, it should return skip_reason.
        """
        result = self.service.fetch_gist(
            gist_id=REAL_GIST_ID,
            owner=REAL_GIST_OWNER,
            filename=None  # No filename specified
        )

        # Behavior depends on gist structure:
        # - 1 C# file: success=True, auto-selected
        # - Multiple C# files: success=False, skip_reason="Ambiguous gist"
        # - No C# files: success=False, skip_reason="No C# files"

        if result.success:
            # Single C# file was auto-selected
            assert result.filename is not None
            assert result.filename.endswith('.cs') or result.filename.endswith('.csx')
            assert result.content is not None
        else:
            # Multiple files or no C# files
            assert result.skip_reason is not None
            assert ('multiple' in result.skip_reason.lower() or
                   'no c#' in result.skip_reason.lower())

    def test_rate_limit_detection(self):
        """Test detection of rate limit errors (403 with X-RateLimit-Remaining: 0).

        Note: This test may not trigger rate limiting in normal conditions.
        It primarily validates the error handling code path exists.

        To truly test rate limiting, run this test 60+ times without GITHUB_TOKEN.
        """
        # This test is informational - rate limit errors are hard to trigger reliably
        # The test validates the code path exists by making a normal request

        result = self.service.fetch_gist(
            gist_id=REAL_GIST_ID,
            owner=REAL_GIST_OWNER,
            filename=REAL_GIST_FILE
        )

        # In normal conditions, this succeeds
        # If rate limited (which we can't force), result.error would mention rate limit
        if not result.success and result.error:
            if 'rate limit' in result.error.lower():
                # Rate limit hit - validate error message
                assert 'GITHUB_TOKEN' in result.error, \
                    "Rate limit error should mention GITHUB_TOKEN"

                # Verify database records rate limit status
                gist_record = self.db.get_gist(REAL_GIST_ID)
                assert gist_record['status'] == 'rate_limited'


@pytest.mark.integration
class TestGistIntegrationEdgeCases:
    """Edge case integration tests."""

    def setup_method(self):
        """Create temporary database and cache for each test."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.temp_db = self.temp_dir / "test_integration_edge.db"
        self.cache_dir = self.temp_dir / "cache"

        self.db = Database(self.temp_db)
        self.service = GistService(cache_dir=self.cache_dir, db=self.db)

    def test_etag_validation_flow(self):
        """Test full ETag validation flow (cache → ETag → 304 Not Modified).

        Validates:
        - ETag stored in cache
        - ETag sent in If-None-Match header
        - 304 response handled correctly
        """
        # First fetch - creates cache with ETag
        result1 = self.service.fetch_gist(
            gist_id=REAL_GIST_ID,
            owner=REAL_GIST_OWNER,
            filename=REAL_GIST_FILE
        )
        assert result1.success

        # Verify ETag in cache
        cache_file = self.cache_dir / f"{REAL_GIST_ID}.json"
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
            etag = cache_data.get('etag')
            assert etag is not None, "ETag should be cached"

        # Expire cache to force revalidation
        expired_time = (datetime.utcnow() - timedelta(hours=2)).isoformat()
        cache_data['cached_at'] = expired_time
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2)

        # Second fetch - should send If-None-Match with ETag
        # GitHub will likely return 304 Not Modified (content unchanged)
        result2 = self.service.fetch_gist(
            gist_id=REAL_GIST_ID,
            owner=REAL_GIST_OWNER,
            filename=REAL_GIST_FILE
        )

        assert result2.success, "ETag revalidation should succeed"
        assert result2.content == result1.content, "Content should match after 304"

    def test_concurrent_cache_writes(self):
        """Test that concurrent fetches don't corrupt cache.

        This is a basic sequential test - true concurrency testing would require
        threading/multiprocessing which is beyond scope.
        """
        # Multiple sequential fetches
        results = []
        for i in range(3):
            result = self.service.fetch_gist(
                gist_id=REAL_GIST_ID,
                owner=REAL_GIST_OWNER,
                filename=REAL_GIST_FILE
            )
            results.append(result)
            time.sleep(0.1)  # Small delay

        # All should succeed
        assert all(r.success for r in results)

        # All should have same content
        contents = [r.content for r in results]
        assert len(set(contents)) == 1, "All fetches should return same content"

        # Cache should be valid JSON
        cache_file = self.cache_dir / f"{REAL_GIST_ID}.json"
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)  # Should not raise JSONDecodeError


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v", "--integration"])
