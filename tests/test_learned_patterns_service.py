"""
Unit tests for LearnedPatternsService.

Tests pattern querying, application, and feedback tracking.
Part of Auto-Learn Full LLM Integration (2026-02-06).
"""

import json
import pytest
import sqlite3
import tempfile
from pathlib import Path

from src.services.learned_patterns_service import (
    LearnedPatternsService,
    LearnedPattern,
    extract_error_signature,
)


@pytest.fixture
def temp_db():
    """Create a temporary database with schema for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    conn = sqlite3.connect(str(db_path))

    # Create schema (V3 with scope column)
    conn.executescript("""
        CREATE TABLE learned_patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            family TEXT NOT NULL,
            pattern_type TEXT NOT NULL,
            error_signature TEXT,
            match_condition TEXT,
            fix_template TEXT NOT NULL,
            fix_type TEXT DEFAULT 'template',
            fix_code TEXT,
            confidence REAL DEFAULT 0.5,
            auto_approved BOOLEAN DEFAULT FALSE,
            priority INTEGER DEFAULT 50,
            requires_llm BOOLEAN DEFAULT FALSE,
            example_before TEXT,
            example_after TEXT,
            source TEXT,
            scope TEXT DEFAULT 'family',
            schema_version INTEGER DEFAULT 2,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE pattern_performance (
            pattern_id INTEGER PRIMARY KEY,
            family TEXT NOT NULL,
            times_applied INTEGER DEFAULT 0,
            times_succeeded INTEGER DEFAULT 0,
            success_rate REAL DEFAULT 0.0,
            last_used TEXT,
            retire_if_below_threshold REAL DEFAULT 0.5
        );

        CREATE TABLE learning_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            family TEXT NOT NULL,
            run_id TEXT NOT NULL,
            failure_cluster_id TEXT,
            pattern_type TEXT,
            fix_applied TEXT,
            auto_approved BOOLEAN,
            confidence REAL,
            validation_status TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    conn.close()

    yield db_path

    # Cleanup
    db_path.unlink(missing_ok=True)


@pytest.fixture
def service(temp_db):
    """Create a service instance with temp database."""
    svc = LearnedPatternsService("zip", db_path=temp_db)
    yield svc
    svc.close()


class TestLearnedPattern:
    """Tests for LearnedPattern dataclass."""

    def test_from_row(self, temp_db):
        """Test creating LearnedPattern from database row."""
        conn = sqlite3.connect(str(temp_db))
        conn.row_factory = sqlite3.Row

        # Insert test data
        conn.execute("""
            INSERT INTO learned_patterns
            (family, pattern_type, error_signature, fix_template, fix_type, fix_code,
             confidence, auto_approved, priority, requires_llm, source)
            VALUES ('zip', 'compile_error', 'CS0246', 'Add using directive', 'using_directive',
                    '{"directive": "using Aspose.Zip;", "trigger_type": "Archive"}',
                    0.9, TRUE, 20, FALSE, 'bootstrap')
        """)
        conn.commit()

        row = conn.execute("SELECT * FROM learned_patterns WHERE id = 1").fetchone()
        pattern = LearnedPattern.from_row(row)

        assert pattern.id == 1
        assert pattern.family == "zip"
        assert pattern.error_signature == "CS0246"
        assert pattern.fix_type == "using_directive"
        assert pattern.fix_code == {"directive": "using Aspose.Zip;", "trigger_type": "Archive"}
        assert pattern.confidence == 0.9
        assert pattern.auto_approved is True
        assert pattern.priority == 20

        conn.close()


class TestQueryPatterns:
    """Tests for pattern querying."""

    def test_query_by_signature(self, service, temp_db):
        """Test querying patterns by error signature."""
        conn = sqlite3.connect(str(temp_db))

        # Insert test patterns
        conn.execute("""
            INSERT INTO learned_patterns
            (family, pattern_type, error_signature, fix_template, fix_type, confidence, auto_approved, source)
            VALUES ('zip', 'compile_error', 'CS0246', 'Add using', 'using_directive', 0.9, TRUE, 'test')
        """)
        conn.execute("""
            INSERT INTO learned_patterns
            (family, pattern_type, error_signature, fix_template, fix_type, confidence, auto_approved, source)
            VALUES ('zip', 'compile_error', 'CS0103', 'Define var', 'template', 0.7, FALSE, 'test')
        """)
        conn.commit()
        conn.close()

        # Query CS0246 patterns
        patterns = service.query_patterns("CS0246", min_confidence=0.5)
        assert len(patterns) == 1
        assert patterns[0].error_signature == "CS0246"

    def test_query_respects_confidence(self, service, temp_db):
        """Test that min_confidence filter works."""
        conn = sqlite3.connect(str(temp_db))
        conn.execute("""
            INSERT INTO learned_patterns
            (family, pattern_type, error_signature, fix_template, fix_type, confidence, auto_approved, source)
            VALUES ('zip', 'compile_error', 'CS0246', 'Low conf', 'template', 0.3, TRUE, 'test')
        """)
        conn.execute("""
            INSERT INTO learned_patterns
            (family, pattern_type, error_signature, fix_template, fix_type, confidence, auto_approved, source)
            VALUES ('zip', 'compile_error', 'CS0246', 'High conf', 'template', 0.9, TRUE, 'test')
        """)
        conn.commit()
        conn.close()

        # Query with high confidence threshold
        patterns = service.query_patterns("CS0246", min_confidence=0.8)
        assert len(patterns) == 1
        assert patterns[0].confidence == 0.9

    def test_query_approved_only(self, service, temp_db):
        """Test approved_only filter."""
        conn = sqlite3.connect(str(temp_db))
        conn.execute("""
            INSERT INTO learned_patterns
            (family, pattern_type, error_signature, fix_template, fix_type, confidence, auto_approved, source)
            VALUES ('zip', 'compile_error', 'CS0246', 'Approved', 'template', 0.9, TRUE, 'test')
        """)
        conn.execute("""
            INSERT INTO learned_patterns
            (family, pattern_type, error_signature, fix_template, fix_type, confidence, auto_approved, source)
            VALUES ('zip', 'compile_error', 'CS0246', 'Not approved', 'template', 0.9, FALSE, 'test')
        """)
        conn.commit()
        conn.close()

        # Query approved only
        patterns = service.query_patterns("CS0246", approved_only=True)
        assert len(patterns) == 1
        assert patterns[0].auto_approved is True


class TestApplyPattern:
    """Tests for pattern application."""

    def test_apply_regex_replace(self, service):
        """Test regex replacement pattern."""
        pattern = LearnedPattern(
            id=1, family="zip", pattern_type="compile_error",
            error_signature="TEST", match_condition=None,
            fix_template="Replace Normal with Optimal",
            fix_type="regex_replace",
            fix_code={"pattern": r"CompressionLevel\.Normal", "replacement": "CompressionLevel.Optimal"},
            confidence=0.9, auto_approved=True, priority=50,
            requires_llm=False, example_before=None, example_after=None, source="test"
        )

        code = "var level = CompressionLevel.Normal;"
        fixed, success, desc = service.apply_pattern(pattern, code)

        assert success is True
        assert "CompressionLevel.Optimal" in fixed
        assert "CompressionLevel.Normal" not in fixed

    def test_apply_regex_no_match(self, service):
        """Test regex that doesn't match."""
        pattern = LearnedPattern(
            id=1, family="zip", pattern_type="compile_error",
            error_signature="TEST", match_condition=None,
            fix_template="No match",
            fix_type="regex_replace",
            fix_code={"pattern": r"SomethingNotPresent", "replacement": "Replacement"},
            confidence=0.9, auto_approved=True, priority=50,
            requires_llm=False, example_before=None, example_after=None, source="test"
        )

        code = "var x = 1;"
        fixed, success, desc = service.apply_pattern(pattern, code)

        assert success is False
        assert fixed == code

    def test_apply_using_directive(self, service):
        """Test using directive insertion."""
        pattern = LearnedPattern(
            id=1, family="zip", pattern_type="compile_error",
            error_signature="CS0246", match_condition=None,
            fix_template="Add Aspose.Zip using",
            fix_type="using_directive",
            fix_code={"directive": "using Aspose.Zip;", "trigger_type": "Archive"},
            confidence=0.9, auto_approved=True, priority=50,
            requires_llm=False, example_before=None, example_after=None, source="test"
        )

        code = """using System;

var archive = new Archive("test.zip");"""

        fixed, success, desc = service.apply_pattern(pattern, code)

        assert success is True
        assert "using Aspose.Zip;" in fixed
        # Should be inserted after existing using
        assert fixed.index("using Aspose.Zip;") > fixed.index("using System;")

    def test_apply_using_directive_already_present(self, service):
        """Test using directive that's already present."""
        pattern = LearnedPattern(
            id=1, family="zip", pattern_type="compile_error",
            error_signature="CS0246", match_condition=None,
            fix_template="Add Aspose.Zip using",
            fix_type="using_directive",
            fix_code={"directive": "using Aspose.Zip;"},
            confidence=0.9, auto_approved=True, priority=50,
            requires_llm=False, example_before=None, example_after=None, source="test"
        )

        code = """using System;
using Aspose.Zip;

var archive = new Archive("test.zip");"""

        fixed, success, desc = service.apply_pattern(pattern, code)

        assert success is False
        assert fixed == code

    def test_apply_template_not_executable(self, service):
        """Test that template patterns return not executable."""
        pattern = LearnedPattern(
            id=1, family="zip", pattern_type="compile_error",
            error_signature="CS0246", match_condition=None,
            fix_template="This is just a description",
            fix_type="template",
            fix_code=None,
            confidence=0.5, auto_approved=False, priority=50,
            requires_llm=False, example_before=None, example_after=None, source="test"
        )

        code = "var x = 1;"
        fixed, success, desc = service.apply_pattern(pattern, code)

        assert success is False
        assert "template-only" in desc.lower() or "not executable" in desc.lower()


class TestRecordApplication:
    """Tests for feedback tracking."""

    def test_record_successful_application(self, service, temp_db):
        """Test recording a successful pattern application."""
        conn = sqlite3.connect(str(temp_db))

        # Insert pattern and performance row
        conn.execute("""
            INSERT INTO learned_patterns
            (family, pattern_type, error_signature, fix_template, source)
            VALUES ('zip', 'compile_error', 'CS0246', 'Test', 'test')
        """)
        conn.execute("""
            INSERT INTO pattern_performance (pattern_id, family, times_applied, times_succeeded)
            VALUES (1, 'zip', 5, 3)
        """)
        conn.commit()
        conn.close()

        # Record successful application
        service.record_application(
            pattern_id=1,
            example_id="test_example_1",
            run_id="test_run_1",
            success=True,
        )

        # Verify
        conn = sqlite3.connect(str(temp_db))
        row = conn.execute("SELECT * FROM pattern_performance WHERE pattern_id = 1").fetchone()
        assert row[2] == 6  # times_applied
        assert row[3] == 4  # times_succeeded
        conn.close()

    def test_record_failed_application(self, service, temp_db):
        """Test recording a failed pattern application."""
        conn = sqlite3.connect(str(temp_db))

        conn.execute("""
            INSERT INTO learned_patterns
            (family, pattern_type, error_signature, fix_template, source)
            VALUES ('zip', 'compile_error', 'CS0246', 'Test', 'test')
        """)
        conn.execute("""
            INSERT INTO pattern_performance (pattern_id, family, times_applied, times_succeeded)
            VALUES (1, 'zip', 5, 3)
        """)
        conn.commit()
        conn.close()

        # Record failed application
        service.record_application(
            pattern_id=1,
            example_id="test_example_2",
            run_id="test_run_1",
            success=False,
        )

        # Verify
        conn = sqlite3.connect(str(temp_db))
        row = conn.execute("SELECT * FROM pattern_performance WHERE pattern_id = 1").fetchone()
        assert row[2] == 6  # times_applied
        assert row[3] == 3  # times_succeeded (unchanged)
        conn.close()


class TestRetireLowPerformers:
    """Tests for pattern retirement."""

    def test_retire_low_performer(self, service, temp_db):
        """Test retiring a low-performing pattern."""
        conn = sqlite3.connect(str(temp_db))

        # Insert pattern with low success rate after many uses
        conn.execute("""
            INSERT INTO learned_patterns
            (family, pattern_type, error_signature, fix_template, auto_approved, source)
            VALUES ('zip', 'compile_error', 'CS0246', 'Low performer', TRUE, 'test')
        """)
        conn.execute("""
            INSERT INTO pattern_performance
            (pattern_id, family, times_applied, times_succeeded, success_rate)
            VALUES (1, 'zip', 15, 2, 0.133)
        """)
        conn.commit()
        conn.close()

        # Retire low performers
        retired = service.retire_low_performers(max_success_rate=0.3, min_applications=10)

        assert retired == 1

        # Verify pattern is no longer auto_approved
        conn = sqlite3.connect(str(temp_db))
        row = conn.execute("SELECT auto_approved, source FROM learned_patterns WHERE id = 1").fetchone()
        assert row[0] == 0  # auto_approved = FALSE
        assert "retired_" in row[1]
        conn.close()

    def test_dont_retire_good_performer(self, service, temp_db):
        """Test that good performers are not retired."""
        conn = sqlite3.connect(str(temp_db))

        conn.execute("""
            INSERT INTO learned_patterns
            (family, pattern_type, error_signature, fix_template, auto_approved, source)
            VALUES ('zip', 'compile_error', 'CS0246', 'Good performer', TRUE, 'test')
        """)
        conn.execute("""
            INSERT INTO pattern_performance
            (pattern_id, family, times_applied, times_succeeded, success_rate)
            VALUES (1, 'zip', 15, 12, 0.8)
        """)
        conn.commit()
        conn.close()

        # Try to retire
        retired = service.retire_low_performers(max_success_rate=0.3, min_applications=10)

        assert retired == 0


class TestApprovePattern:
    """Tests for pattern approval."""

    def test_approve_pattern(self, service, temp_db):
        """Test approving a pending pattern."""
        conn = sqlite3.connect(str(temp_db))
        conn.execute("""
            INSERT INTO learned_patterns
            (family, pattern_type, error_signature, fix_template, auto_approved, source)
            VALUES ('zip', 'compile_error', 'CS0246', 'Test', FALSE, 'auto_learn')
        """)
        conn.commit()
        conn.close()

        result = service.approve_pattern(1)
        assert result is True

        conn = sqlite3.connect(str(temp_db))
        row = conn.execute("SELECT auto_approved FROM learned_patterns WHERE id = 1").fetchone()
        assert row[0] == 1  # TRUE
        conn.close()

    def test_approve_nonexistent_pattern(self, service):
        """Test approving a pattern that doesn't exist."""
        result = service.approve_pattern(9999)
        assert result is False

    def test_retire_pattern_with_reason(self, service, temp_db):
        """Test retiring a pattern with a reason."""
        conn = sqlite3.connect(str(temp_db))
        conn.execute("""
            INSERT INTO learned_patterns
            (family, pattern_type, error_signature, fix_template, auto_approved, source)
            VALUES ('zip', 'compile_error', 'CS0246', 'Test', TRUE, 'auto_learn')
        """)
        conn.commit()
        conn.close()

        result = service.retire_pattern(1, "low_performance")
        assert result is True

        conn = sqlite3.connect(str(temp_db))
        row = conn.execute("SELECT auto_approved, source FROM learned_patterns WHERE id = 1").fetchone()
        assert row[0] == 0  # FALSE
        assert row[1] == "retired_low_performance"
        conn.close()

    def test_retire_nonexistent_pattern(self, service):
        """Test retiring a pattern that doesn't exist."""
        result = service.retire_pattern(9999, "test")
        assert result is False

    def test_bulk_approve(self, service, temp_db):
        """Test bulk approving multiple patterns."""
        conn = sqlite3.connect(str(temp_db))
        for i in range(5):
            conn.execute("""
                INSERT INTO learned_patterns
                (family, pattern_type, error_signature, fix_template, auto_approved, source)
                VALUES ('zip', 'compile_error', 'CS0246', ?, FALSE, 'auto_learn')
            """, (f"Pattern {i}",))
        conn.commit()
        conn.close()

        result = service.bulk_approve([1, 2, 3])
        assert result == 3

        conn = sqlite3.connect(str(temp_db))
        approved = conn.execute(
            "SELECT COUNT(*) FROM learned_patterns WHERE auto_approved = TRUE"
        ).fetchone()[0]
        assert approved == 3
        not_approved = conn.execute(
            "SELECT COUNT(*) FROM learned_patterns WHERE auto_approved = FALSE"
        ).fetchone()[0]
        assert not_approved == 2
        conn.close()

    def test_bulk_approve_empty_list(self, service):
        """Test bulk approve with empty list."""
        result = service.bulk_approve([])
        assert result == 0


class TestStorePattern:
    """Tests for pattern storage."""

    def test_store_pattern(self, service, temp_db):
        """Test storing a new pattern."""
        pattern_id = service.store_pattern(
            error_signature="CS0246",
            pattern_type="compile_error",
            fix_type="using_directive",
            fix_code={"directive": "using Aspose.Zip;"},
            fix_template="Add Aspose.Zip using directive",
            confidence=0.9,
            auto_approved=True,
            source="test",
        )

        assert pattern_id == 1

        # Verify pattern was stored
        conn = sqlite3.connect(str(temp_db))
        row = conn.execute("SELECT * FROM learned_patterns WHERE id = 1").fetchone()
        assert row is not None
        assert row[3] == "CS0246"  # error_signature

        # Verify performance tracking was initialized
        perf_row = conn.execute("SELECT * FROM pattern_performance WHERE pattern_id = 1").fetchone()
        assert perf_row is not None
        conn.close()


class TestExtractErrorSignature:
    """Tests for error signature extraction."""

    def test_extract_cs_code(self):
        """Test extracting CS error codes."""
        errors = ["error CS0246: The type or namespace name 'Archive' could not be found"]
        assert extract_error_signature(errors) == "CS0246"

    def test_extract_multiple_cs_codes(self):
        """Test extracting from multiple errors (takes first)."""
        errors = [
            "error CS0246: Type not found",
            "error CS0103: Name not found",
        ]
        assert extract_error_signature(errors) == "CS0246"

    def test_extract_password_issue(self):
        """Test detecting password issues."""
        errors = ["The password is incorrect"]
        assert extract_error_signature(errors) == "PASSWORD_ISSUE"

    def test_extract_missing_file(self):
        """Test detecting missing file issues."""
        errors = ["File 'test.zip' was not found"]
        assert extract_error_signature(errors) == "MISSING_FILE"

    def test_extract_unclassified_runtime_error(self):
        """Test unclassified runtime errors return RUNTIME_ERROR."""
        errors = ["Some random error that doesn't match known patterns"]
        signature = extract_error_signature(errors)

        # Unclassified runtime errors (not CS codes, not exceptions, not known patterns)
        # are correctly classified as RUNTIME_ERROR
        assert signature == "RUNTIME_ERROR"


class TestDeduplication:
    """Tests for pattern deduplication guards."""

    def test_duplicate_template_blocked(self, temp_db):
        """Same (family, error_sig, template) inserted twice — second is skipped."""
        from scripts.patterns.auto_learn import _is_duplicate

        conn = sqlite3.connect(str(temp_db))
        conn.row_factory = sqlite3.Row

        # Insert first pattern
        conn.execute(
            """INSERT INTO learned_patterns
               (family, pattern_type, error_signature, fix_template, fix_type, source)
               VALUES ('zip', 'compile_error', 'CS0246', 'Add using directive', 'template', 'auto_learn')"""
        )
        conn.commit()

        # Check duplicate
        p = {
            "family": "zip",
            "error_signature": "CS0246",
            "fix_type": "template",
            "fix_code": None,
        }
        assert _is_duplicate(conn, p) is True
        conn.close()

    def test_duplicate_fix_code_blocked(self, temp_db):
        """Identical fix_code JSON for same triple = duplicate."""
        from scripts.patterns.auto_learn import _is_duplicate

        conn = sqlite3.connect(str(temp_db))
        conn.row_factory = sqlite3.Row

        fix_code = json.dumps({"directive": "using Aspose.Zip;", "trigger_type": "Archive"})
        conn.execute(
            """INSERT INTO learned_patterns
               (family, pattern_type, error_signature, fix_template, fix_type, fix_code, source)
               VALUES ('zip', 'compile_error', 'CS0246', 'Add using', 'using_directive', ?, 'auto_learn')""",
            (fix_code,),
        )
        conn.commit()

        p = {
            "family": "zip",
            "error_signature": "CS0246",
            "fix_type": "using_directive",
            "fix_code": {"directive": "using Aspose.Zip;", "trigger_type": "Archive"},
        }
        assert _is_duplicate(conn, p) is True
        conn.close()

    def test_different_fix_code_allowed(self, temp_db):
        """Different fix_code for same error sig = not a duplicate."""
        from scripts.patterns.auto_learn import _is_duplicate

        conn = sqlite3.connect(str(temp_db))
        conn.row_factory = sqlite3.Row

        fix_code = json.dumps({"directive": "using Aspose.Zip;", "trigger_type": "Archive"})
        conn.execute(
            """INSERT INTO learned_patterns
               (family, pattern_type, error_signature, fix_template, fix_type, fix_code, source)
               VALUES ('zip', 'compile_error', 'CS0246', 'Add using', 'using_directive', ?, 'auto_learn')""",
            (fix_code,),
        )
        conn.commit()

        p = {
            "family": "zip",
            "error_signature": "CS0246",
            "fix_type": "using_directive",
            "fix_code": {"directive": "using Aspose.Zip.Saving;", "trigger_type": "ParallelOptions"},
        }
        assert _is_duplicate(conn, p) is False
        conn.close()

    def test_retired_patterns_not_counted_as_duplicates(self, temp_db):
        """Retired patterns should not block new insertions."""
        from scripts.patterns.auto_learn import _is_duplicate

        conn = sqlite3.connect(str(temp_db))
        conn.row_factory = sqlite3.Row

        conn.execute(
            """INSERT INTO learned_patterns
               (family, pattern_type, error_signature, fix_template, fix_type, source)
               VALUES ('zip', 'compile_error', 'CS0246', 'Add using', 'template', 'retired_duplicate')"""
        )
        conn.commit()

        p = {
            "family": "zip",
            "error_signature": "CS0246",
            "fix_type": "template",
        }
        assert _is_duplicate(conn, p) is False
        conn.close()


class TestCrossFamilyPatterns:
    """Tests for cross-family global pattern sharing (Phase 2)."""

    def test_query_returns_global_patterns(self, temp_db):
        """Global-scope patterns are returned for any family."""
        conn = sqlite3.connect(str(temp_db))

        # Insert a global pattern (created for ZIP, scope=global)
        fix_code = json.dumps({"transformer": "fix_stream_disposal"})
        conn.execute(
            """INSERT INTO learned_patterns
               (family, pattern_type, error_signature, fix_template,
                fix_type, fix_code, confidence, auto_approved, scope, source)
               VALUES ('zip', 'runtime_error', 'DISPOSED_STREAM', 'Fix stream disposal',
                'code_transform', ?, 0.9, TRUE, 'global', 'auto_learn')""",
            (fix_code,),
        )
        conn.execute(
            "INSERT INTO pattern_performance (pattern_id, family) VALUES (1, 'zip')"
        )
        conn.commit()
        conn.close()

        # Query from a DIFFERENT family — should still find the global pattern
        svc = LearnedPatternsService("words", db_path=temp_db)
        patterns = svc.query_patterns("DISPOSED_STREAM", min_confidence=0.5)
        assert len(patterns) == 1
        assert patterns[0].scope == "global"
        assert patterns[0].family == "zip"  # Original family preserved
        svc.close()

    def test_family_pattern_not_leaked(self, temp_db):
        """Family-scoped patterns are NOT returned for other families."""
        conn = sqlite3.connect(str(temp_db))

        fix_code = json.dumps({"directive": "using Aspose.Zip;", "trigger_type": "Archive"})
        conn.execute(
            """INSERT INTO learned_patterns
               (family, pattern_type, error_signature, fix_template,
                fix_type, fix_code, confidence, auto_approved, scope, source)
               VALUES ('zip', 'compile_error', 'CS0246', 'Add using Aspose.Zip',
                'using_directive', ?, 0.9, TRUE, 'family', 'auto_learn')""",
            (fix_code,),
        )
        conn.execute(
            "INSERT INTO pattern_performance (pattern_id, family) VALUES (1, 'zip')"
        )
        conn.commit()
        conn.close()

        # Query from Words — should NOT see ZIP-family pattern
        svc = LearnedPatternsService("words", db_path=temp_db)
        patterns = svc.query_patterns("CS0246", min_confidence=0.5)
        assert len(patterns) == 0
        svc.close()

    def test_preload_includes_global(self, temp_db):
        """Preload cache includes both family-specific and global patterns."""
        conn = sqlite3.connect(str(temp_db))

        # Insert a family-specific pattern for Words
        fc1 = json.dumps({"directive": "using Aspose.Words;", "trigger_type": "Document"})
        conn.execute(
            """INSERT INTO learned_patterns
               (family, pattern_type, error_signature, fix_template,
                fix_type, fix_code, confidence, auto_approved, scope, source)
               VALUES ('words', 'compile_error', 'CS0246', 'Add Words using',
                'using_directive', ?, 0.9, TRUE, 'family', 'auto_learn')""",
            (fc1,),
        )
        conn.execute("INSERT INTO pattern_performance (pattern_id, family) VALUES (1, 'words')")

        # Insert a global pattern (from ZIP but global scope)
        fc2 = json.dumps({"transformer": "fix_stream_disposal"})
        conn.execute(
            """INSERT INTO learned_patterns
               (family, pattern_type, error_signature, fix_template,
                fix_type, fix_code, confidence, auto_approved, scope, source)
               VALUES ('zip', 'runtime_error', 'DISPOSED_STREAM', 'Fix disposal',
                'code_transform', ?, 0.9, TRUE, 'global', 'auto_learn')""",
            (fc2,),
        )
        conn.execute("INSERT INTO pattern_performance (pattern_id, family) VALUES (2, 'zip')")
        conn.commit()
        conn.close()

        # Preload for Words — should include both
        svc = LearnedPatternsService("words", db_path=temp_db)
        svc.preload_all_patterns()
        assert "CS0246" in svc._preloaded_cache
        assert "DISPOSED_STREAM" in svc._preloaded_cache
        svc.close()


class TestScopeClassification:
    """Tests for _determine_scope in auto_learn.py."""

    def test_generic_transformer_is_global(self):
        from scripts.patterns.auto_learn import _determine_scope
        p = {"fix_type": "code_transform", "fix_code": {"transformer": "fix_stream_disposal"}}
        assert _determine_scope(p) == "global"

    def test_family_transformer_is_family(self):
        from scripts.patterns.auto_learn import _determine_scope
        p = {"fix_type": "code_transform", "fix_code": {"transformer": "fix_rar_password"}}
        assert _determine_scope(p) == "family"

    def test_system_using_directive_is_global(self):
        from scripts.patterns.auto_learn import _determine_scope
        p = {"fix_type": "using_directive", "fix_code": {"directive": "using System.IO;"}}
        assert _determine_scope(p) == "global"

    def test_aspose_using_directive_is_family(self):
        from scripts.patterns.auto_learn import _determine_scope
        p = {"fix_type": "using_directive", "fix_code": {"directive": "using Aspose.Zip;"}}
        assert _determine_scope(p) == "family"

    def test_regex_replace_is_family(self):
        from scripts.patterns.auto_learn import _determine_scope
        p = {"fix_type": "regex_replace", "fix_code": {"pattern": "foo", "replacement": "bar"}}
        assert _determine_scope(p) == "family"

    def test_llm_prompt_is_family(self):
        from scripts.patterns.auto_learn import _determine_scope
        p = {"fix_type": "llm_prompt", "fix_code": {"prompt": "fix {code}"}}
        assert _determine_scope(p) == "family"

    def test_template_is_family(self):
        from scripts.patterns.auto_learn import _determine_scope
        p = {"fix_type": "template"}
        assert _determine_scope(p) == "family"


class TestPatternValidation:
    """Tests for pattern validation on store."""

    def test_valid_regex_passes(self):
        from scripts.patterns.auto_learn import _validate_pattern_on_store
        p = {"fix_type": "regex_replace", "fix_code": {"pattern": r"CompressionLevel\.\w+", "replacement": "CompressionLevel.Optimal"}}
        assert _validate_pattern_on_store(p) is None

    def test_invalid_regex_rejected(self):
        from scripts.patterns.auto_learn import _validate_pattern_on_store
        p = {"fix_type": "regex_replace", "fix_code": {"pattern": "[invalid(", "replacement": "fix"}}
        result = _validate_pattern_on_store(p)
        assert result is not None
        assert "Invalid regex" in result

    def test_non_regex_pattern_passes(self):
        from scripts.patterns.auto_learn import _validate_pattern_on_store
        p = {"fix_type": "using_directive", "fix_code": {"directive": "using System.IO;"}}
        assert _validate_pattern_on_store(p) is None


class TestConflictDetection:
    """Tests for detect_conflicts in LearnedPatternsService."""

    def test_conflicting_regex_detected(self, temp_db):
        """Two regex_replace with same pattern but different replacement = conflict."""
        conn = sqlite3.connect(str(temp_db))

        fc1 = json.dumps({"pattern": "Foo", "replacement": "Bar"})
        fc2 = json.dumps({"pattern": "Foo", "replacement": "Baz"})
        conn.execute(
            """INSERT INTO learned_patterns
               (family, pattern_type, error_signature, fix_template, fix_type, fix_code, confidence, auto_approved, source)
               VALUES ('zip', 'compile_error', 'CS0246', 'Fix1', 'regex_replace', ?, 0.8, TRUE, 'auto_learn')""",
            (fc1,),
        )
        conn.execute(
            """INSERT INTO learned_patterns
               (family, pattern_type, error_signature, fix_template, fix_type, fix_code, confidence, auto_approved, source)
               VALUES ('zip', 'compile_error', 'CS0246', 'Fix2', 'regex_replace', ?, 0.8, TRUE, 'auto_learn')""",
            (fc2,),
        )
        conn.execute("INSERT INTO pattern_performance (pattern_id, family) VALUES (1, 'zip')")
        conn.execute("INSERT INTO pattern_performance (pattern_id, family) VALUES (2, 'zip')")
        conn.commit()
        conn.close()

        svc = LearnedPatternsService("zip", db_path=temp_db)
        conflicts = svc.detect_conflicts("CS0246")
        assert len(conflicts) == 1
        assert "Same regex pattern" in conflicts[0][2]
        svc.close()

    def test_no_conflict_for_same_replacement(self, temp_db):
        """Two regex_replace with same pattern AND same replacement = no conflict."""
        conn = sqlite3.connect(str(temp_db))

        fc = json.dumps({"pattern": "Foo", "replacement": "Bar"})
        conn.execute(
            """INSERT INTO learned_patterns
               (family, pattern_type, error_signature, fix_template, fix_type, fix_code, confidence, auto_approved, source)
               VALUES ('zip', 'compile_error', 'CS0246', 'Fix1', 'regex_replace', ?, 0.8, TRUE, 'auto_learn')""",
            (fc,),
        )
        conn.execute(
            """INSERT INTO learned_patterns
               (family, pattern_type, error_signature, fix_template, fix_type, fix_code, confidence, auto_approved, source)
               VALUES ('zip', 'compile_error', 'CS0246', 'Fix2', 'regex_replace', ?, 0.8, TRUE, 'auto_learn')""",
            (fc,),
        )
        conn.execute("INSERT INTO pattern_performance (pattern_id, family) VALUES (1, 'zip')")
        conn.execute("INSERT INTO pattern_performance (pattern_id, family) VALUES (2, 'zip')")
        conn.commit()
        conn.close()

        svc = LearnedPatternsService("zip", db_path=temp_db)
        conflicts = svc.detect_conflicts("CS0246")
        assert len(conflicts) == 0
        svc.close()


class TestHistoricalBoost:
    """Tests for cross-run priority boosting."""

    def test_proven_pattern_boosted(self, temp_db):
        """Pattern with high success rate is reordered ahead of untested one."""
        conn = sqlite3.connect(str(temp_db))

        # Insert two patterns: untested (id=1) and proven (id=2)
        for i, (conf, prio) in enumerate([(0.8, 40), (0.7, 50)], 1):
            fc = json.dumps({"directive": f"using NS{i};", "trigger_type": f"Type{i}"})
            conn.execute(
                """INSERT INTO learned_patterns
                   (family, pattern_type, error_signature, fix_template, fix_type, fix_code,
                    confidence, auto_approved, priority, source, scope)
                   VALUES ('zip', 'compile_error', 'CS0246', ?, 'using_directive', ?, ?, TRUE, ?, 'auto_learn', 'family')""",
                (f"Fix {i}", fc, conf, prio),
            )
            conn.execute(
                "INSERT INTO pattern_performance (pattern_id, family, times_applied, times_succeeded, success_rate) VALUES (?, 'zip', ?, ?, ?)",
                (i, 0 if i == 1 else 10, 0 if i == 1 else 8, 0.0 if i == 1 else 0.8),
            )
        conn.commit()
        conn.close()

        svc = LearnedPatternsService("zip", db_path=temp_db)
        patterns = svc.query_patterns("CS0246", min_confidence=0.5)

        # Pattern 2 (proven, 80% success) should come before pattern 1 (untested)
        assert len(patterns) == 2
        assert patterns[0].id == 2  # Proven pattern first
        svc.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
