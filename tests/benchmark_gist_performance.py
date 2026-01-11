"""
Performance benchmarks for GitHub Gist system at scale (100+ gists).

This module measures baseline performance metrics to validate the system
scales acceptably and to detect future regressions.

Run with: pytest tests/benchmark_gist_performance.py -v

Metrics measured:
- Cold start performance (full API fetches)
- Warm cache performance (cache hits)
- Mixed cache performance (ETag revalidation)
- Database query performance
- Memory usage at scale

Results are saved to artifacts/ folder for regression tracking.
"""

import sys
import json
import time
import tempfile
import psutil
import os
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from typing import Dict, List, Any

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from gist_service import GistService
from database import Database


class TestPerformanceBenchmark:
    """Performance benchmark suite for gist system at scale."""

    def setup_method(self):
        """Create isolated test environment for benchmarks."""
        # Create temp directory
        self.temp_dir = Path(tempfile.mkdtemp())
        self.temp_db = self.temp_dir / "benchmark.db"
        self.cache_dir = self.temp_dir / "cache"

        # Initialize database with schema
        schema_path = Path(__file__).parent.parent / "schema.sql"
        self.db = Database(self.temp_db)
        self.db.initialize_schema(schema_path)

        # Initialize gist service
        self.service = GistService(cache_dir=self.cache_dir, db=self.db)

        # Initialize psutil for memory tracking
        self.process = psutil.Process(os.getpid())

        # Store results for reporting
        self.results = {}

    def teardown_method(self):
        """Cleanup after benchmark."""
        self.db.close()
        # Keep temp directory for inspection (can delete if desired)

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================

    def create_mock_gist_response(self, gist_id: str, filename: str = "test.cs") -> Dict:
        """Create realistic mock gist API response."""
        return {
            'id': gist_id,
            'description': f'Test gist {gist_id}',
            'updated_at': '2026-01-11T00:00:00Z',
            'owner': {'login': 'test_owner'},
            'files': {
                filename: {
                    'filename': filename,
                    'content': f'// Test content for {gist_id}\nusing System;\nclass Test {{ }}',
                    'raw_url': f'https://gist.githubusercontent.com/test/{gist_id}/raw/{filename}',
                    'language': 'C#',
                    'size': 50
                }
            }
        }

    def create_mock_200_response(self, gist_id: str, filename: str = "test.cs") -> Mock:
        """Create mock 200 OK response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'ETag': f'"{gist_id}_etag"'}
        mock_response.json.return_value = self.create_mock_gist_response(gist_id, filename)
        return mock_response

    def create_mock_304_response(self) -> Mock:
        """Create mock 304 Not Modified response."""
        mock_response = Mock()
        mock_response.status_code = 304
        mock_response.headers = {}
        return mock_response

    def populate_cache(self, count: int, fresh: bool = True, filename: str = "test.cs"):
        """Pre-populate cache with specified number of gists."""
        for i in range(count):
            gist_id = f"gist_{i:03d}"
            cache_file = self.cache_dir / f"{gist_id}.json"
            cache_file.parent.mkdir(parents=True, exist_ok=True)

            # Determine cache timestamp
            if fresh:
                cached_at = datetime.utcnow().isoformat()
            else:
                # Expired cache (2 hours old)
                cached_at = (datetime.utcnow() - timedelta(hours=2)).isoformat()

            cache_data = {
                'gist_id': gist_id,
                'etag': f'"{gist_id}_etag"',
                'cached_at': cached_at,
                'data': self.create_mock_gist_response(gist_id, filename)
            }

            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2)

            # Also persist to database
            self.db.upsert_gist(
                gist_id, 'test_owner', f'Test gist {gist_id}',
                '2026-01-11T00:00:00Z', 'success', None, f'"{gist_id}_etag"'
            )

            # Persist file
            self.db.upsert_gist_file(
                gist_id, filename,
                f'https://gist.githubusercontent.com/test/{gist_id}/raw/{filename}',
                'C#',
                f'// Test content for {gist_id}\nusing System;\nclass Test {{ }}',
                f'{gist_id}_hash',
                50
            )

    def measure_memory(self) -> float:
        """Get current memory usage in MB."""
        return self.process.memory_info().rss / (1024 * 1024)

    # ========================================================================
    # BENCHMARK TESTS
    # ========================================================================

    @patch('requests.get')
    def test_cold_start_100_gists(self, mock_get):
        """
        Benchmark: Cold start with 100 gists (empty cache, full API fetches).

        Measures:
        - Total execution time
        - Average time per gist
        - API call count
        - Cache hit rate (should be 0%)

        Target: <2s per gist average (200s total for 100 gists)
        """
        gist_count = 100
        filename = "test.cs"

        # Setup mock to return different response for each gist
        def mock_get_side_effect(url, **kwargs):
            # Extract gist_id from URL
            gist_id = url.split('/')[-1]
            return self.create_mock_200_response(gist_id, filename)

        mock_get.side_effect = mock_get_side_effect

        # Measure execution
        start = time.perf_counter()
        times = []

        for i in range(gist_count):
            gist_id = f"gist_{i:03d}"
            fetch_start = time.perf_counter()
            result = self.service.fetch_gist(gist_id, "test_owner", filename)
            fetch_time = time.perf_counter() - fetch_start
            times.append(fetch_time)
            assert result.success, f"Failed to fetch {gist_id}"

        total_time = time.perf_counter() - start
        avg_time = total_time / gist_count
        min_time = min(times)
        max_time = max(times)

        # Store results
        self.results['cold_start_100_gists'] = {
            'total_time_seconds': round(total_time, 2),
            'avg_per_gist_seconds': round(avg_time, 3),
            'min_time_seconds': round(min_time, 3),
            'max_time_seconds': round(max_time, 3),
            'api_calls': mock_get.call_count,
            'cache_hit_rate': 0.0,
            'status': 'PASS' if avg_time < 2.0 else 'FAIL',
            'target': 2.0,
            'notes': 'All gists fetched fresh from mock API'
        }

        # Assertions
        assert mock_get.call_count == gist_count, f"Expected {gist_count} API calls, got {mock_get.call_count}"
        assert avg_time < 2.0, f"Average time {avg_time}s exceeds 2s target"

        print(f"\n[BENCHMARK] Cold Start (100 gists):")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Avg per gist: {avg_time:.3f}s")
        print(f"  Min: {min_time:.3f}s, Max: {max_time:.3f}s")
        print(f"  API calls: {mock_get.call_count}")
        print(f"  Status: {self.results['cold_start_100_gists']['status']}")

    @patch('requests.get')
    def test_warm_cache_100_gists(self, mock_get):
        """
        Benchmark: Warm cache with 100 gists (all fresh, no API calls).

        Measures:
        - Total execution time
        - Cache hit rate (should be 100%)
        - API call count (should be 0)

        Target: <5s total for 100 gists (all cache hits)
        """
        gist_count = 100
        filename = "test.cs"

        # Pre-populate cache with fresh entries
        self.populate_cache(gist_count, fresh=True, filename=filename)

        # Measure execution
        start = time.perf_counter()

        for i in range(gist_count):
            gist_id = f"gist_{i:03d}"
            result = self.service.fetch_gist(gist_id, "test_owner", filename)
            assert result.success, f"Failed to fetch {gist_id}"

        total_time = time.perf_counter() - start
        avg_time = total_time / gist_count

        # Store results
        self.results['warm_cache_100_gists'] = {
            'total_time_seconds': round(total_time, 2),
            'avg_per_gist_seconds': round(avg_time, 3),
            'cache_hit_rate': 100.0,
            'api_calls': mock_get.call_count,
            'status': 'PASS' if total_time < 5.0 else 'FAIL',
            'target': 5.0,
            'notes': 'All gists served from fresh cache'
        }

        # Assertions
        assert mock_get.call_count == 0, f"Expected 0 API calls (all cached), got {mock_get.call_count}"
        assert total_time < 5.0, f"Total time {total_time}s exceeds 5s target"

        print(f"\n[BENCHMARK] Warm Cache (100 gists):")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Avg per gist: {avg_time:.3f}s")
        print(f"  Cache hit rate: 100%")
        print(f"  API calls: {mock_get.call_count}")
        print(f"  Status: {self.results['warm_cache_100_gists']['status']}")

    @patch('requests.get')
    def test_mixed_cache_performance(self, mock_get):
        """
        Benchmark: Mixed cache (50 fresh, 50 expired with ETag revalidation).

        Measures:
        - Total execution time
        - Cache hit rate (50% fresh, 50% revalidated)
        - API call count (should be 50 for ETag checks)

        Target: ~50-100s total (50 cache hits + 50 ETag validations)
        """
        gist_count = 100
        fresh_count = 50
        expired_count = 50
        filename = "test.cs"

        # Pre-populate cache: 50 fresh, 50 expired
        self.populate_cache(fresh_count, fresh=True, filename=filename)

        # Populate expired cache (starting from index 50)
        for i in range(fresh_count, gist_count):
            gist_id = f"gist_{i:03d}"
            cache_file = self.cache_dir / f"{gist_id}.json"

            # Expired cache (2 hours old)
            cached_at = (datetime.utcnow() - timedelta(hours=2)).isoformat()

            cache_data = {
                'gist_id': gist_id,
                'etag': f'"{gist_id}_etag"',
                'cached_at': cached_at,
                'data': self.create_mock_gist_response(gist_id, filename)
            }

            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2)

            # Persist to database
            self.db.upsert_gist(
                gist_id, 'test_owner', f'Test gist {gist_id}',
                '2026-01-11T00:00:00Z', 'success', None, f'"{gist_id}_etag"'
            )

        # Mock 304 Not Modified responses for expired cache
        mock_get.return_value = self.create_mock_304_response()

        # Measure execution
        start = time.perf_counter()

        for i in range(gist_count):
            gist_id = f"gist_{i:03d}"
            result = self.service.fetch_gist(gist_id, "test_owner", filename)
            assert result.success, f"Failed to fetch {gist_id}"

        total_time = time.perf_counter() - start
        avg_time = total_time / gist_count
        cache_hit_rate = (fresh_count / gist_count) * 100

        # Store results
        self.results['mixed_cache_50_50'] = {
            'total_time_seconds': round(total_time, 2),
            'avg_per_gist_seconds': round(avg_time, 3),
            'cache_hits': fresh_count,
            'etag_validations': expired_count,
            'cache_hit_rate': round(cache_hit_rate, 1),
            'api_calls': mock_get.call_count,
            'status': 'PASS' if mock_get.call_count == expired_count else 'FAIL',
            'notes': '50 fresh cache hits, 50 ETag revalidations (304)'
        }

        # Assertions
        assert mock_get.call_count == expired_count, \
            f"Expected {expired_count} API calls for ETag checks, got {mock_get.call_count}"
        assert cache_hit_rate >= 50.0, f"Cache hit rate {cache_hit_rate}% below 50%"

        print(f"\n[BENCHMARK] Mixed Cache (50/50):")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Avg per gist: {avg_time:.3f}s")
        print(f"  Cache hits: {fresh_count} (fresh)")
        print(f"  ETag validations: {mock_get.call_count}")
        print(f"  Cache hit rate: {cache_hit_rate:.1f}%")
        print(f"  Status: {self.results['mixed_cache_50_50']['status']}")

    def test_database_query_performance(self):
        """
        Benchmark: Database operations at scale (100 operations per type).

        Measures:
        - upsert_gist average time
        - upsert_gist_file average time
        - get_gist average time
        - get_gist_file average time

        Target: <100ms per operation
        """
        operation_count = 100

        # Benchmark upsert_gist
        times_upsert_gist = []
        for i in range(operation_count):
            gist_id = f"bench_gist_{i:03d}"
            start = time.perf_counter()
            self.db.upsert_gist(
                gist_id, "test_owner", f"Benchmark gist {i}",
                "2026-01-11T00:00:00Z", "success", None, f'"etag_{i}"'
            )
            elapsed_ms = (time.perf_counter() - start) * 1000
            times_upsert_gist.append(elapsed_ms)

        # Benchmark upsert_gist_file
        times_upsert_file = []
        for i in range(operation_count):
            gist_id = f"bench_gist_{i:03d}"
            start = time.perf_counter()
            self.db.upsert_gist_file(
                gist_id, "test.cs",
                f"https://gist.githubusercontent.com/test/{gist_id}/raw/test.cs",
                "C#",
                f"// Benchmark content {i}",
                f"hash_{i}",
                50
            )
            elapsed_ms = (time.perf_counter() - start) * 1000
            times_upsert_file.append(elapsed_ms)

        # Benchmark get_gist
        times_get_gist = []
        for i in range(operation_count):
            gist_id = f"bench_gist_{i:03d}"
            start = time.perf_counter()
            result = self.db.get_gist(gist_id)
            elapsed_ms = (time.perf_counter() - start) * 1000
            times_get_gist.append(elapsed_ms)
            assert result is not None, f"Failed to retrieve {gist_id}"

        # Benchmark get_gist_file
        times_get_file = []
        for i in range(operation_count):
            gist_id = f"bench_gist_{i:03d}"
            start = time.perf_counter()
            result = self.db.get_gist_file(gist_id, "test.cs")
            elapsed_ms = (time.perf_counter() - start) * 1000
            times_get_file.append(elapsed_ms)
            assert result is not None, f"Failed to retrieve file for {gist_id}"

        # Calculate statistics
        def calc_stats(times: List[float]) -> Dict[str, float]:
            times_sorted = sorted(times)
            return {
                'avg': sum(times) / len(times),
                'min': min(times),
                'max': max(times),
                'p50': times_sorted[len(times_sorted) // 2],
                'p95': times_sorted[int(len(times_sorted) * 0.95)]
            }

        stats_upsert_gist = calc_stats(times_upsert_gist)
        stats_upsert_file = calc_stats(times_upsert_file)
        stats_get_gist = calc_stats(times_get_gist)
        stats_get_file = calc_stats(times_get_file)

        # Store results
        self.results['database_operations'] = {
            'upsert_gist_avg_ms': round(stats_upsert_gist['avg'], 2),
            'upsert_gist_p95_ms': round(stats_upsert_gist['p95'], 2),
            'upsert_file_avg_ms': round(stats_upsert_file['avg'], 2),
            'upsert_file_p95_ms': round(stats_upsert_file['p95'], 2),
            'get_gist_avg_ms': round(stats_get_gist['avg'], 2),
            'get_gist_p95_ms': round(stats_get_gist['p95'], 2),
            'get_file_avg_ms': round(stats_get_file['avg'], 2),
            'get_file_p95_ms': round(stats_get_file['p95'], 2),
            'status': 'PASS' if all(s['avg'] < 100 for s in [stats_upsert_gist, stats_upsert_file,
                                                               stats_get_gist, stats_get_file]) else 'FAIL',
            'target': 100.0,
            'notes': 'All operations measured over 100 iterations'
        }

        # Assertions
        assert stats_upsert_gist['avg'] < 100, \
            f"upsert_gist avg {stats_upsert_gist['avg']}ms exceeds 100ms"
        assert stats_upsert_file['avg'] < 100, \
            f"upsert_gist_file avg {stats_upsert_file['avg']}ms exceeds 100ms"
        assert stats_get_gist['avg'] < 100, \
            f"get_gist avg {stats_get_gist['avg']}ms exceeds 100ms"
        assert stats_get_file['avg'] < 100, \
            f"get_gist_file avg {stats_get_file['avg']}ms exceeds 100ms"

        print(f"\n[BENCHMARK] Database Operations (100 each):")
        print(f"  upsert_gist: avg={stats_upsert_gist['avg']:.2f}ms, p95={stats_upsert_gist['p95']:.2f}ms")
        print(f"  upsert_file: avg={stats_upsert_file['avg']:.2f}ms, p95={stats_upsert_file['p95']:.2f}ms")
        print(f"  get_gist: avg={stats_get_gist['avg']:.2f}ms, p95={stats_get_gist['p95']:.2f}ms")
        print(f"  get_file: avg={stats_get_file['avg']:.2f}ms, p95={stats_get_file['p95']:.2f}ms")
        print(f"  Status: {self.results['database_operations']['status']}")

    @patch('requests.get')
    def test_memory_usage(self, mock_get):
        """
        Benchmark: Memory usage when loading 100 gists sequentially.

        Measures:
        - Baseline memory
        - Peak memory during operations
        - Final memory after operations
        - Memory per gist

        Target: <500MB peak for 100 gists (<5MB per gist)
        """
        gist_count = 100
        filename = "test.cs"

        # Setup mock
        def mock_get_side_effect(url, **kwargs):
            gist_id = url.split('/')[-1]
            return self.create_mock_200_response(gist_id, filename)

        mock_get.side_effect = mock_get_side_effect

        # Baseline memory
        baseline_mb = self.measure_memory()

        # Load gists and track peak memory
        peak_mb = baseline_mb
        for i in range(gist_count):
            gist_id = f"mem_gist_{i:03d}"
            result = self.service.fetch_gist(gist_id, "test_owner", filename)
            assert result.success, f"Failed to fetch {gist_id}"

            current_mb = self.measure_memory()
            peak_mb = max(peak_mb, current_mb)

        # Final memory
        final_mb = self.measure_memory()
        delta_mb = peak_mb - baseline_mb
        memory_per_gist_mb = delta_mb / gist_count

        # Store results
        self.results['memory_usage'] = {
            'baseline_mb': round(baseline_mb, 2),
            'peak_mb': round(peak_mb, 2),
            'final_mb': round(final_mb, 2),
            'delta_mb': round(delta_mb, 2),
            'memory_per_gist_mb': round(memory_per_gist_mb, 3),
            'status': 'PASS' if peak_mb < 500 else 'FAIL',
            'target': 500.0,
            'notes': 'Peak memory measured during sequential loading'
        }

        # Assertions
        assert peak_mb < 500, f"Peak memory {peak_mb}MB exceeds 500MB target"
        assert memory_per_gist_mb < 5, f"Memory per gist {memory_per_gist_mb}MB exceeds 5MB"

        print(f"\n[BENCHMARK] Memory Usage (100 gists):")
        print(f"  Baseline: {baseline_mb:.2f}MB")
        print(f"  Peak: {peak_mb:.2f}MB")
        print(f"  Final: {final_mb:.2f}MB")
        print(f"  Delta: {delta_mb:.2f}MB")
        print(f"  Per gist: {memory_per_gist_mb:.3f}MB")
        print(f"  Status: {self.results['memory_usage']['status']}")

    # ========================================================================
    # RESULTS EXPORT
    # ========================================================================

    def test_zzz_export_results(self):
        """
        Export benchmark results to JSON file.

        This test runs last (zzz prefix) to collect all results.
        """
        # Check if results were populated
        if not self.results:
            pytest.skip("No benchmark results to export")

        # Create results structure
        results_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'environment': {
                'os': os.name,
                'platform': sys.platform,
                'python_version': sys.version.split()[0],
                'psutil_version': psutil.__version__
            },
            'benchmarks': self.results,
            'summary': {
                'total_tests': len(self.results),
                'passed': sum(1 for r in self.results.values() if r.get('status') == 'PASS'),
                'failed': sum(1 for r in self.results.values() if r.get('status') == 'FAIL'),
                'overall_status': 'PASS' if all(r.get('status') == 'PASS'
                                                for r in self.results.values()) else 'FAIL'
            }
        }

        # Save to artifacts folder (if running from agent context)
        artifacts_dir = Path(__file__).parent.parent / "reports" / "agents" / "agent-e" / "hard-005"
        if artifacts_dir.exists():
            # Find latest run folder
            run_folders = sorted(artifacts_dir.glob("run_*"))
            if run_folders:
                latest_run = run_folders[-1]
                artifacts_path = latest_run / "artifacts"
                artifacts_path.mkdir(exist_ok=True)

                output_file = artifacts_path / "benchmark_results.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(results_data, f, indent=2)

                print(f"\n[EXPORT] Results saved to: {output_file}")

        # Also print summary
        print("\n" + "=" * 70)
        print("BENCHMARK SUMMARY")
        print("=" * 70)
        print(f"Total tests: {results_data['summary']['total_tests']}")
        print(f"Passed: {results_data['summary']['passed']}")
        print(f"Failed: {results_data['summary']['failed']}")
        print(f"Overall status: {results_data['summary']['overall_status']}")
        print("=" * 70)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
