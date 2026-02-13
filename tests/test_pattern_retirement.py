"""
Unit tests for automated pattern retirement logic.

Tests the retire_patterns() method in LearnedPatternsService and its
integration with the retirement policy configuration.

Part of SR-04-B: Automated Pattern Retirement Logic
"""

import pytest
import sqlite3
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from src.services.learned_patterns_service import LearnedPatternsService
from src.core.config import RetirementPolicyConfig


@pytest.fixture
def temp_db():
    """Create temporary database with schema."""
    # Create temp file
    temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db')
    temp_path = Path(temp_file.name)
    temp_file.close()

    # Initialize schema
    conn = sqlite3.connect(str(temp_path))
    conn.execute("""
        CREATE TABLE learned_patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            family TEXT NOT NULL,
            pattern_type TEXT NOT NULL,
            error_signature TEXT,
            match_condition TEXT,
            fix_template TEXT NOT NULL,
            confidence REAL DEFAULT 0.5,
            auto_approved BOOLEAN DEFAULT FALSE,
            source TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            fix_type TEXT DEFAULT 'template',
            fix_code TEXT,
            priority INTEGER DEFAULT 50,
            requires_llm BOOLEAN DEFAULT FALSE,
            example_before TEXT,
            example_after TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE pattern_performance (
            pattern_id INTEGER PRIMARY KEY,
            family TEXT NOT NULL,
            times_applied INTEGER DEFAULT 0,
            times_succeeded INTEGER DEFAULT 0,
            success_rate REAL DEFAULT 0.0,
            last_used TEXT,
            retire_if_below_threshold REAL DEFAULT 0.5,
            FOREIGN KEY (pattern_id) REFERENCES learned_patterns(id)
        )
    """)
    conn.commit()
    conn.close()

    yield temp_path

    # Cleanup
    temp_path.unlink()


def _insert_pattern(
    db_path: Path,
    family: str,
    error_signature: str,
    times_applied: int,
    times_succeeded: int,
    created_at_offset_days: int = 0,
    auto_approved: bool = True,
    source: str = "auto_learn"
) -> int:
    """Helper to insert test pattern."""
    conn = sqlite3.connect(str(db_path))

    # Calculate created_at
    created_at = datetime.now(timezone.utc) - timedelta(days=created_at_offset_days)
    created_at_str = created_at.strftime('%Y-%m-%d %H:%M:%S')

    cursor = conn.execute("""
        INSERT INTO learned_patterns
        (family, pattern_type, error_signature, fix_template, confidence,
         auto_approved, source, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (family, 'compile_error', error_signature, 'Test fix',
          0.7, auto_approved, source, created_at_str))

    pattern_id = cursor.lastrowid

    # Insert performance
    success_rate = times_succeeded / times_applied if times_applied > 0 else 0.0
    conn.execute("""
        INSERT INTO pattern_performance
        (pattern_id, family, times_applied, times_succeeded, success_rate)
        VALUES (?, ?, ?, ?, ?)
    """, (pattern_id, family, times_applied, times_succeeded, success_rate))

    conn.commit()
    conn.close()

    return pattern_id


class TestRetirementDisabled:
    """Test retirement when disabled in config."""

    def test_retirement_disabled_returns_empty_stats(self, temp_db):
        """Test that disabled retirement returns 0 for all stats."""
        # Insert pattern that would normally be retired
        _insert_pattern(temp_db, 'zip', 'CS0246', times_applied=20, times_succeeded=0)

        # Create disabled policy
        policy = RetirementPolicyConfig(enabled=False)

        # Run retirement
        service = LearnedPatternsService('zip', db_path=temp_db)
        stats = service.retire_patterns(policy)
        service.close()

        # Verify no retirement occurred
        assert stats['candidates_evaluated'] == 0
        assert stats['retired_count'] == 0
        assert stats['retired_patterns'] == []

        # Verify pattern still auto_approved
        conn = sqlite3.connect(str(temp_db))
        row = conn.execute(
            "SELECT auto_approved FROM learned_patterns WHERE error_signature = 'CS0246'"
        ).fetchone()
        conn.close()
        assert row[0] == 1  # Still approved


class TestRetirementDryRun:
    """Test dry-run mode (log without deletion)."""

    def test_dry_run_logs_but_does_not_retire(self, temp_db):
        """Test that dry_run mode logs retirements but doesn't modify database."""
        # Insert low-performing pattern
        pattern_id = _insert_pattern(
            temp_db, 'zip', 'CS0246',
            times_applied=20, times_succeeded=0
        )

        # Create dry-run policy
        policy = RetirementPolicyConfig(
            enabled=True,
            dry_run=True,
            min_attempts=10,
            max_success_rate=0.1
        )

        # Run retirement
        service = LearnedPatternsService('zip', db_path=temp_db)
        stats = service.retire_patterns(policy)
        service.close()

        # Verify stats show it WOULD be retired
        assert stats['candidates_evaluated'] == 1
        assert stats['retired_count'] == 1
        assert len(stats['retired_patterns']) == 1
        assert stats['retired_patterns'][0]['pattern_id'] == pattern_id

        # Verify pattern STILL auto_approved (not actually retired)
        conn = sqlite3.connect(str(temp_db))
        row = conn.execute(
            "SELECT auto_approved, source FROM learned_patterns WHERE id = ?",
            (pattern_id,)
        ).fetchone()
        conn.close()

        assert row[0] == 1  # Still approved
        assert row[1] == 'auto_learn'  # Source unchanged


class TestRetirementLowSuccessRate:
    """Test retirement based on low success rate."""

    def test_retire_pattern_with_zero_success_rate(self, temp_db):
        """Test retiring pattern with 0% success rate."""
        # Insert pattern: 0/20 success (0%)
        pattern_id = _insert_pattern(
            temp_db, 'zip', 'CS9999',
            times_applied=20, times_succeeded=0
        )

        # Create policy: retire if <= 10%
        policy = RetirementPolicyConfig(
            enabled=True,
            dry_run=False,
            min_attempts=10,
            max_success_rate=0.1
        )

        # Run retirement
        service = LearnedPatternsService('zip', db_path=temp_db)
        stats = service.retire_patterns(policy)
        service.close()

        # Verify retirement occurred
        assert stats['retired_count'] == 1
        assert stats['retired_patterns'][0]['pattern_id'] == pattern_id
        assert 'Low success rate: 0.0% <= 10.0%' in stats['retired_patterns'][0]['reason']

        # Verify database updated
        conn = sqlite3.connect(str(temp_db))
        row = conn.execute(
            "SELECT auto_approved, source FROM learned_patterns WHERE id = ?",
            (pattern_id,)
        ).fetchone()
        conn.close()

        assert row[0] == 0  # Not approved
        assert row[1] == 'retired_auto_learn'  # Source prefixed

    def test_retire_pattern_with_5_percent_success_rate(self, temp_db):
        """Test retiring pattern with 5% success rate (1/20)."""
        pattern_id = _insert_pattern(
            temp_db, 'words', 'CS1234',
            times_applied=20, times_succeeded=1
        )

        policy = RetirementPolicyConfig(
            enabled=True,
            dry_run=False,
            min_attempts=10,
            max_success_rate=0.1
        )

        service = LearnedPatternsService('words', db_path=temp_db)
        stats = service.retire_patterns(policy)
        service.close()

        assert stats['retired_count'] == 1
        assert '5.0% <= 10.0%' in stats['retired_patterns'][0]['reason']

    def test_do_not_retire_pattern_above_threshold(self, temp_db):
        """Test NOT retiring pattern with 15% success rate (above 10% threshold)."""
        _insert_pattern(
            temp_db, 'zip', 'CS0103',
            times_applied=20, times_succeeded=3  # 15%
        )

        policy = RetirementPolicyConfig(
            enabled=True,
            dry_run=False,
            min_attempts=10,
            max_success_rate=0.1
        )

        service = LearnedPatternsService('zip', db_path=temp_db)
        stats = service.retire_patterns(policy)
        service.close()

        # Should NOT retire (15% > 10% threshold)
        assert stats['retired_count'] == 0


class TestRetirementMinAttempts:
    """Test min_attempts gate."""

    def test_do_not_retire_pattern_below_min_attempts(self, temp_db):
        """Test that patterns with < min_attempts are NOT retired."""
        # Insert pattern with 0/5 success (0%), but only 5 attempts
        _insert_pattern(
            temp_db, 'zip', 'CS8888',
            times_applied=5, times_succeeded=0
        )

        policy = RetirementPolicyConfig(
            enabled=True,
            dry_run=False,
            min_attempts=10,  # Requires 10 attempts
            max_success_rate=0.1
        )

        service = LearnedPatternsService('zip', db_path=temp_db)
        stats = service.retire_patterns(policy)
        service.close()

        # Should NOT retire (only 5 attempts < 10 min)
        assert stats['candidates_evaluated'] == 0  # Filtered out by query
        assert stats['retired_count'] == 0

    def test_retire_pattern_exactly_at_min_attempts(self, temp_db):
        """Test retiring pattern with exactly min_attempts."""
        pattern_id = _insert_pattern(
            temp_db, 'zip', 'CS7777',
            times_applied=10, times_succeeded=0  # Exactly 10 attempts
        )

        policy = RetirementPolicyConfig(
            enabled=True,
            dry_run=False,
            min_attempts=10,
            max_success_rate=0.1
        )

        service = LearnedPatternsService('zip', db_path=temp_db)
        stats = service.retire_patterns(policy)
        service.close()

        # SHOULD retire (10 attempts >= 10 min)
        assert stats['retired_count'] == 1


class TestRetirementMaxAge:
    """Test age-based retirement."""

    def test_retire_pattern_older_than_max_age(self, temp_db):
        """Test retiring pattern older than 90 days."""
        # Insert pattern 100 days old
        pattern_id = _insert_pattern(
            temp_db, 'zip', 'CS0246',
            times_applied=15, times_succeeded=8,  # 53% success (good)
            created_at_offset_days=100
        )

        policy = RetirementPolicyConfig(
            enabled=True,
            dry_run=False,
            min_attempts=10,
            max_success_rate=0.1,  # Won't trigger (53% > 10%)
            max_age_days=90  # Will trigger (100 > 90)
        )

        service = LearnedPatternsService('zip', db_path=temp_db)
        stats = service.retire_patterns(policy)
        service.close()

        # Should retire due to age (even though success rate is good)
        assert stats['retired_count'] == 1
        assert 'Exceeded max age' in stats['retired_patterns'][0]['reason']
        assert '100 days > 90 days' in stats['retired_patterns'][0]['reason']

    def test_do_not_retire_pattern_below_max_age(self, temp_db):
        """Test NOT retiring pattern younger than max_age_days."""
        # Insert pattern 80 days old
        _insert_pattern(
            temp_db, 'zip', 'CS0103',
            times_applied=15, times_succeeded=8,
            created_at_offset_days=80
        )

        policy = RetirementPolicyConfig(
            enabled=True,
            dry_run=False,
            min_attempts=10,
            max_success_rate=0.1,
            max_age_days=90
        )

        service = LearnedPatternsService('zip', db_path=temp_db)
        stats = service.retire_patterns(policy)
        service.close()

        # Should NOT retire (80 days < 90 days, good success rate)
        assert stats['retired_count'] == 0


class TestRetirementBothCriteria:
    """Test patterns failing multiple criteria."""

    def test_retire_pattern_failing_both_rate_and_age(self, temp_db):
        """Test pattern failing both success rate AND age criteria."""
        pattern_id = _insert_pattern(
            temp_db, 'words', 'CS9999',
            times_applied=36, times_succeeded=0,  # 0% success
            created_at_offset_days=120  # 120 days old
        )

        policy = RetirementPolicyConfig(
            enabled=True,
            dry_run=False,
            min_attempts=10,
            max_success_rate=0.1,
            max_age_days=90
        )

        service = LearnedPatternsService('words', db_path=temp_db)
        stats = service.retire_patterns(policy)
        service.close()

        # Should retire for BOTH reasons
        assert stats['retired_count'] == 1
        reason = stats['retired_patterns'][0]['reason']
        assert 'Low success rate' in reason
        assert 'Exceeded max age' in reason


class TestRetirementSoftDelete:
    """Test soft delete mechanism."""

    def test_retirement_sets_auto_approved_false(self, temp_db):
        """Test that retirement sets auto_approved=FALSE."""
        pattern_id = _insert_pattern(
            temp_db, 'zip', 'CS0001',
            times_applied=20, times_succeeded=0,
            auto_approved=True
        )

        policy = RetirementPolicyConfig(
            enabled=True, dry_run=False, min_attempts=10, max_success_rate=0.1
        )

        service = LearnedPatternsService('zip', db_path=temp_db)
        service.retire_patterns(policy)
        service.close()

        # Verify auto_approved changed to FALSE
        conn = sqlite3.connect(str(temp_db))
        row = conn.execute(
            "SELECT auto_approved FROM learned_patterns WHERE id = ?",
            (pattern_id,)
        ).fetchone()
        conn.close()

        assert row[0] == 0  # FALSE

    def test_retirement_prefixes_source_with_retired(self, temp_db):
        """Test that retirement prefixes source with 'retired_'."""
        pattern_id = _insert_pattern(
            temp_db, 'zip', 'CS0002',
            times_applied=20, times_succeeded=0,
            source='auto_learn_llm'
        )

        policy = RetirementPolicyConfig(
            enabled=True, dry_run=False, min_attempts=10, max_success_rate=0.1
        )

        service = LearnedPatternsService('zip', db_path=temp_db)
        service.retire_patterns(policy)
        service.close()

        # Verify source prefixed
        conn = sqlite3.connect(str(temp_db))
        row = conn.execute(
            "SELECT source FROM learned_patterns WHERE id = ?",
            (pattern_id,)
        ).fetchone()
        conn.close()

        assert row[0] == 'retired_auto_learn_llm'

    def test_retirement_preserves_pattern_data(self, temp_db):
        """Test that retirement doesn't DELETE, only marks inactive."""
        pattern_id = _insert_pattern(
            temp_db, 'zip', 'CS0003',
            times_applied=20, times_succeeded=0
        )

        policy = RetirementPolicyConfig(
            enabled=True, dry_run=False, min_attempts=10, max_success_rate=0.1
        )

        service = LearnedPatternsService('zip', db_path=temp_db)
        service.retire_patterns(policy)
        service.close()

        # Verify pattern still exists in database
        conn = sqlite3.connect(str(temp_db))
        row = conn.execute(
            "SELECT id, error_signature, fix_template FROM learned_patterns WHERE id = ?",
            (pattern_id,)
        ).fetchone()
        conn.close()

        assert row is not None  # Still exists
        assert row[0] == pattern_id
        assert row[1] == 'CS0003'
        assert row[2] == 'Test fix'


class TestRetirementStats:
    """Test return statistics."""

    def test_retirement_stats_structure(self, temp_db):
        """Test that return dict has correct structure."""
        _insert_pattern(
            temp_db, 'zip', 'CS1111',
            times_applied=20, times_succeeded=0
        )

        policy = RetirementPolicyConfig(
            enabled=True, dry_run=False, min_attempts=10, max_success_rate=0.1
        )

        service = LearnedPatternsService('zip', db_path=temp_db)
        stats = service.retire_patterns(policy)
        service.close()

        # Verify structure
        assert 'candidates_evaluated' in stats
        assert 'retired_count' in stats
        assert 'retired_patterns' in stats

        assert isinstance(stats['candidates_evaluated'], int)
        assert isinstance(stats['retired_count'], int)
        assert isinstance(stats['retired_patterns'], list)

    def test_retirement_stats_pattern_details(self, temp_db):
        """Test that retired_patterns contains detailed info."""
        pattern_id = _insert_pattern(
            temp_db, 'zip', 'CS2222',
            times_applied=30, times_succeeded=1
        )

        policy = RetirementPolicyConfig(
            enabled=True, dry_run=False, min_attempts=10, max_success_rate=0.1
        )

        service = LearnedPatternsService('zip', db_path=temp_db)
        stats = service.retire_patterns(policy)
        service.close()

        # Verify pattern details
        assert len(stats['retired_patterns']) == 1
        p = stats['retired_patterns'][0]

        assert p['pattern_id'] == pattern_id
        assert p['error_signature'] == 'CS2222'
        assert 'reason' in p
        assert 'performance' in p

        perf = p['performance']
        assert perf['success_rate'] == pytest.approx(1/30, abs=0.01)
        assert perf['times_applied'] == 30
        assert perf['times_succeeded'] == 1
        assert 'age_days' in perf


class TestRetirementMultiplePatterns:
    """Test retiring multiple patterns at once."""

    def test_retire_multiple_patterns(self, temp_db):
        """Test retiring 3 out of 5 patterns."""
        # Insert 5 patterns
        p1 = _insert_pattern(temp_db, 'zip', 'CS1001', 20, 0)  # 0% - RETIRE
        p2 = _insert_pattern(temp_db, 'zip', 'CS1002', 20, 10)  # 50% - KEEP
        p3 = _insert_pattern(temp_db, 'zip', 'CS1003', 20, 1)  # 5% - RETIRE
        p4 = _insert_pattern(temp_db, 'zip', 'CS1004', 20, 15)  # 75% - KEEP
        p5 = _insert_pattern(temp_db, 'zip', 'CS1005', 20, 2)  # 10% - RETIRE (equal to threshold)

        policy = RetirementPolicyConfig(
            enabled=True, dry_run=False, min_attempts=10, max_success_rate=0.1
        )

        service = LearnedPatternsService('zip', db_path=temp_db)
        stats = service.retire_patterns(policy)
        service.close()

        # Should retire 3 patterns (p1, p3, p5)
        assert stats['candidates_evaluated'] == 5
        assert stats['retired_count'] == 3

        retired_ids = [p['pattern_id'] for p in stats['retired_patterns']]
        assert p1 in retired_ids
        assert p3 in retired_ids
        assert p5 in retired_ids
        assert p2 not in retired_ids
        assert p4 not in retired_ids

    def test_retire_none_when_all_above_threshold(self, temp_db):
        """Test that 0 patterns retired when all perform well."""
        _insert_pattern(temp_db, 'zip', 'CS2001', 20, 5)  # 25%
        _insert_pattern(temp_db, 'zip', 'CS2002', 20, 10)  # 50%
        _insert_pattern(temp_db, 'zip', 'CS2003', 20, 18)  # 90%

        policy = RetirementPolicyConfig(
            enabled=True, dry_run=False, min_attempts=10, max_success_rate=0.1
        )

        service = LearnedPatternsService('zip', db_path=temp_db)
        stats = service.retire_patterns(policy)
        service.close()

        # Should retire 0 patterns
        assert stats['candidates_evaluated'] == 3
        assert stats['retired_count'] == 0


class TestRetirementEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_retirement_with_no_patterns_in_database(self, temp_db):
        """Test retirement on empty database."""
        policy = RetirementPolicyConfig(
            enabled=True, dry_run=False, min_attempts=10, max_success_rate=0.1
        )

        service = LearnedPatternsService('zip', db_path=temp_db)
        stats = service.retire_patterns(policy)
        service.close()

        assert stats['candidates_evaluated'] == 0
        assert stats['retired_count'] == 0

    def test_retirement_ignores_already_retired_patterns(self, temp_db):
        """Test that patterns with auto_approved=FALSE are ignored."""
        # Insert pattern already retired (auto_approved=FALSE)
        _insert_pattern(
            temp_db, 'zip', 'CS9000',
            times_applied=20, times_succeeded=0,
            auto_approved=False  # Already retired
        )

        policy = RetirementPolicyConfig(
            enabled=True, dry_run=False, min_attempts=10, max_success_rate=0.1
        )

        service = LearnedPatternsService('zip', db_path=temp_db)
        stats = service.retire_patterns(policy)
        service.close()

        # Should not evaluate already-retired patterns
        assert stats['candidates_evaluated'] == 0
        assert stats['retired_count'] == 0

    def test_retirement_respects_family_isolation(self, temp_db):
        """Test that retirement only affects specified family."""
        # Insert patterns for different families
        zip_pattern = _insert_pattern(temp_db, 'zip', 'CS1111', 20, 0)
        words_pattern = _insert_pattern(temp_db, 'words', 'CS2222', 20, 0)

        policy = RetirementPolicyConfig(
            enabled=True, dry_run=False, min_attempts=10, max_success_rate=0.1
        )

        # Retire only 'zip' family
        service = LearnedPatternsService('zip', db_path=temp_db)
        stats = service.retire_patterns(policy)
        service.close()

        # Only zip pattern should be retired
        assert stats['retired_count'] == 1
        assert stats['retired_patterns'][0]['pattern_id'] == zip_pattern

        # Verify words pattern still active
        conn = sqlite3.connect(str(temp_db))
        row = conn.execute(
            "SELECT auto_approved FROM learned_patterns WHERE id = ?",
            (words_pattern,)
        ).fetchone()
        conn.close()
        assert row[0] == 1  # Still approved

    def test_retirement_with_null_created_at(self, temp_db):
        """Test retirement gracefully handles NULL created_at."""
        # Insert pattern with NULL created_at
        conn = sqlite3.connect(str(temp_db))
        cursor = conn.execute("""
            INSERT INTO learned_patterns
            (family, pattern_type, error_signature, fix_template,
             confidence, auto_approved, source, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, NULL)
        """, ('zip', 'compile_error', 'CS9999', 'Test', 0.7, True, 'test'))
        pattern_id = cursor.lastrowid
        conn.execute("""
            INSERT INTO pattern_performance
            (pattern_id, family, times_applied, times_succeeded, success_rate)
            VALUES (?, ?, ?, ?, ?)
        """, (pattern_id, 'zip', 20, 0, 0.0))
        conn.commit()
        conn.close()

        policy = RetirementPolicyConfig(
            enabled=True, dry_run=False, min_attempts=10,
            max_success_rate=0.1, max_age_days=90
        )

        service = LearnedPatternsService('zip', db_path=temp_db)
        stats = service.retire_patterns(policy)
        service.close()

        # Should still retire based on success rate (age check skipped)
        assert stats['retired_count'] == 1
        assert 'Low success rate' in stats['retired_patterns'][0]['reason']


class TestRetirementConfigValidation:
    """Test config validation edge cases."""

    def test_retirement_with_zero_max_success_rate(self, temp_db):
        """Test max_success_rate=0.0 (retire everything)."""
        _insert_pattern(temp_db, 'zip', 'CS1111', 20, 20)  # 100% success

        policy = RetirementPolicyConfig(
            enabled=True, dry_run=False, min_attempts=10,
            max_success_rate=0.0  # Retire everything (<= 0%)
        )

        service = LearnedPatternsService('zip', db_path=temp_db)
        stats = service.retire_patterns(policy)
        service.close()

        # Even 100% success should NOT be retired (100% > 0%)
        assert stats['retired_count'] == 0

    def test_retirement_with_max_success_rate_one(self, temp_db):
        """Test max_success_rate=1.0 (retire nothing based on success)."""
        _insert_pattern(temp_db, 'zip', 'CS1111', 20, 0)  # 0% success

        policy = RetirementPolicyConfig(
            enabled=True, dry_run=False, min_attempts=10,
            max_success_rate=1.0  # Never retire based on success rate
        )

        service = LearnedPatternsService('zip', db_path=temp_db)
        stats = service.retire_patterns(policy)
        service.close()

        # Even 0% success should NOT be retired (0% <= 100%, but not < 100%)
        # Wait, 0% <= 1.0, so it SHOULD retire
        assert stats['retired_count'] == 1  # 0.0 <= 1.0 is True
