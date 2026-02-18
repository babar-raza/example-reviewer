"""
Unit tests for commit message formatting.

Tests all 4 format options (minimal, compact, detailed, structured),
pluralization, zero-count line omission, percentage accuracy,
and dynamic fix name inclusion.
"""

import pytest
from unittest.mock import MagicMock, patch
from src.pipeline.orchestrator import PipelineOrchestrator as Orchestrator


# ── Helpers ───────────────────────────────────────────────────────────

def _make_example(example_id: str, file_path: str = "/repo/blog/post.md", topic: str = ""):
    """Create a mock ExampleRecord."""
    ex = MagicMock()
    ex.example_id = example_id
    ex.file_path = file_path
    ex.topic = topic
    return ex


def _make_orchestrator():
    """Create an Orchestrator with mocked dependencies."""
    orch = object.__new__(Orchestrator)
    orch.db = MagicMock()
    orch.config_manager = MagicMock()
    orch._llm_fixed_example_ids = set()
    return orch


def _default_commit_stats(**overrides):
    """Default commit stats with all zeros, overrideable."""
    stats = {
        "compile_first_try": 0,
        "compile_deterministic": 0,
        "compile_llm": 0,
        "runtime_first_try": 0,
        "runtime_deterministic": 0,
        "runtime_llm": 0,
        "runtime_fixture": 0,
        "runtime_total": 0,
        "fix_names": [],
    }
    stats.update(overrides)
    return stats


# ── Pluralization ─────────────────────────────────────────────────────

class TestPlural:
    """Test the _plural() static method."""

    def test_singular(self):
        assert Orchestrator._plural(1, "file") == "1 file"

    def test_plural_default(self):
        assert Orchestrator._plural(5, "file") == "5 files"

    def test_zero_uses_plural(self):
        assert Orchestrator._plural(0, "file") == "0 files"

    def test_custom_plural(self):
        assert Orchestrator._plural(1, "C# example") == "1 C# example"
        assert Orchestrator._plural(3, "C# example") == "3 C# examples"

    def test_custom_plural_form(self):
        assert Orchestrator._plural(1, "LLM fix", "LLM fixes") == "1 LLM fix"
        assert Orchestrator._plural(2, "LLM fix", "LLM fixes") == "2 LLM fixes"


# ── Format: Minimal ──────────────────────────────────────────────────

class TestFormatMinimal:
    """Test the minimal commit message format."""

    def test_basic_output(self):
        orch = _make_orchestrator()
        examples = [_make_example(f"ex{i}") for i in range(42)]
        staged = [f"/repo/blog/file{i}.md" for i in range(15)]
        stats = _default_commit_stats(compile_first_try=42, runtime_first_try=42, runtime_total=42)
        phase_results = {"discovery": {"examples_found": 50, "files_processed": 37}}

        msg = orch._build_commit_message(
            "zip", "abcdef1234567890ffff", examples, staged,
            stats, phase_results, {}, "minimal",
        )
        assert "fix(zip): verify 42 C# examples in 15 files" in msg
        assert "50 discovered, 42 committed" in msg
        assert "abcdef1234567890" in msg  # run_id truncated to 16
        assert "Co-Authored-By: Example Reviewer" in msg

    def test_single_file_pluralization(self):
        orch = _make_orchestrator()
        examples = [_make_example("ex1")]
        staged = ["/repo/blog/post.md"]
        stats = _default_commit_stats(compile_first_try=1, runtime_first_try=1, runtime_total=1)

        msg = orch._format_minimal(
            "words", "run123456789abcde", examples, staged,
            stats, {"discovery": {"examples_found": 5}}, {},
        )
        assert "1 C# example in 1 file" in msg
        assert "5 discovered, 1 committed" in msg

    def test_no_discovery_stats_graceful(self):
        orch = _make_orchestrator()
        examples = [_make_example("ex1")]
        staged = ["/repo/blog/post.md"]
        stats = _default_commit_stats(compile_first_try=1)

        msg = orch._format_minimal(
            "zip", "run1234567890abcd", examples, staged,
            stats, {}, {},
        )
        # Falls back to len(examples) when discovery not available
        assert "1 discovered, 1 committed" in msg


# ── Format: Compact ──────────────────────────────────────────────────

class TestFormatCompact:
    """Test the compact commit message format."""

    def test_full_stats(self):
        orch = _make_orchestrator()
        examples = [_make_example(f"ex{i}") for i in range(42)]
        staged = [f"/repo/blog/file{i}.md" for i in range(15)]
        stats = _default_commit_stats(
            compile_first_try=35, compile_deterministic=4, compile_llm=3,
            runtime_first_try=38, runtime_deterministic=2, runtime_llm=1,
            runtime_fixture=1, runtime_total=42,
            fix_names=["stream disposal", "CS0246 using directives"],
        )
        phase_results = {"discovery": {"examples_found": 50}}

        msg = orch._format_compact(
            "zip", "abcdef1234567890", examples, staged,
            stats, phase_results, {},
        )
        assert "- Compile: 35 first-try, 4 deterministic, 3 LLM-fixed" in msg
        assert "- Runtime: 38 first-try, 2 deterministic, 1 LLM-fixed, 1 fixture-resolved" in msg
        assert "- Fixes: stream disposal, CS0246 using directives" in msg

    def test_no_llm_fixes_omitted(self):
        orch = _make_orchestrator()
        examples = [_make_example(f"ex{i}") for i in range(10)]
        staged = [f"/repo/file{i}.md" for i in range(5)]
        stats = _default_commit_stats(
            compile_first_try=8, compile_deterministic=2,
            runtime_first_try=10, runtime_total=10,
            fix_names=["stream disposal"],
        )

        msg = orch._format_compact(
            "zip", "run1234567890abcd", examples, staged,
            stats, {"discovery": {"examples_found": 10}}, {},
        )
        assert "- Compile: 8 first-try, 2 deterministic" in msg
        assert "LLM" not in msg.split("Runtime")[0].split("Compile")[1]  # No LLM in compile line

    def test_no_fixes_line_omitted(self):
        orch = _make_orchestrator()
        examples = [_make_example("ex1")]
        staged = ["/repo/file.md"]
        stats = _default_commit_stats(
            compile_first_try=1, runtime_first_try=1, runtime_total=1,
            fix_names=[],
        )

        msg = orch._format_compact(
            "zip", "run1234567890abcd", examples, staged,
            stats, {"discovery": {"examples_found": 1}}, {},
        )
        assert "Fixes" not in msg

    def test_categories_included(self):
        orch = _make_orchestrator()
        examples = [_make_example("ex1")]
        staged = ["/repo/file.md"]
        stats = _default_commit_stats(compile_first_try=1, runtime_first_try=1, runtime_total=1)
        categories = {"blog": ["compression", "encryption"], "kb": ["extraction"]}

        msg = orch._format_compact(
            "zip", "run1234567890abcd", examples, staged,
            stats, {"discovery": {"examples_found": 1}}, categories,
        )
        assert "Blog: 2 files (compression, encryption)" in msg
        assert "Kb: 1 file (extraction)" in msg


# ── Format: Detailed ─────────────────────────────────────────────────

class TestFormatDetailed:
    """Test the detailed commit message format."""

    def test_full_output(self):
        orch = _make_orchestrator()
        examples = [_make_example(f"ex{i}") for i in range(42)]
        staged = [f"/repo/blog/file{i}.md" for i in range(15)]
        stats = _default_commit_stats(
            compile_first_try=35, compile_deterministic=4, compile_llm=3,
            runtime_first_try=38, runtime_deterministic=2, runtime_llm=1,
            runtime_fixture=1, runtime_total=42,
            fix_names=["stream disposal", "CS0246 using directives", "CS1503 constructor"],
        )
        phase_results = {
            "discovery": {"examples_found": 50, "files_processed": 37}
        }

        msg = orch._format_detailed(
            "zip", "abcdef1234567890", examples, staged,
            stats, phase_results, {},
        )

        # Title
        assert "fix(zip): verify 42 C# examples in 15 files" in msg
        # Discovery
        assert "Discovery: 50 found in 37 files, 42 committed (84%)" in msg
        # Compilation section
        assert "Compilation (42 processed):" in msg
        assert "  35 first-try (83%)" in msg
        assert "  4 deterministic: stream disposal, CS0246 using directives, CS1503 constructor" in msg
        assert "  3 LLM fixes" in msg
        # Runtime section
        assert "Runtime (42 processed):" in msg
        assert "  38 first-try (90%)" in msg
        assert "  2 deterministic fixes" in msg
        assert "  1 fixture-resolved" in msg
        assert "  1 LLM fix" in msg

    def test_percentages_truncated_not_rounded(self):
        orch = _make_orchestrator()
        # 1/3 = 33.33... should truncate to 33%, not round to 33%
        examples = [_make_example(f"ex{i}") for i in range(3)]
        staged = ["/repo/file.md"]
        stats = _default_commit_stats(
            compile_first_try=1, compile_deterministic=1, compile_llm=1,
            runtime_first_try=3, runtime_total=3,
        )
        phase_results = {"discovery": {"examples_found": 3, "files_processed": 1}}

        msg = orch._format_detailed(
            "zip", "run1234567890abcd", examples, staged,
            stats, phase_results, {},
        )
        assert "  1 first-try (33%)" in msg

    def test_100_percent_runtime_collapses(self):
        orch = _make_orchestrator()
        examples = [_make_example(f"ex{i}") for i in range(10)]
        staged = [f"/repo/file{i}.md" for i in range(5)]
        stats = _default_commit_stats(
            compile_first_try=10,
            runtime_first_try=10, runtime_total=10,
        )
        phase_results = {"discovery": {"examples_found": 10, "files_processed": 5}}

        msg = orch._format_detailed(
            "zip", "run1234567890abcd", examples, staged,
            stats, phase_results, {},
        )
        # All first-try should collapse to single line
        assert "Runtime: 10 first-try (100%)" in msg
        assert "Runtime (10 processed):" not in msg

    def test_no_runtime_section_when_zero(self):
        orch = _make_orchestrator()
        examples = [_make_example("ex1")]
        staged = ["/repo/file.md"]
        stats = _default_commit_stats(compile_first_try=1, runtime_total=0)
        phase_results = {"discovery": {"examples_found": 1}}

        msg = orch._format_detailed(
            "zip", "run1234567890abcd", examples, staged,
            stats, phase_results, {},
        )
        assert "Runtime" not in msg

    def test_discovery_without_files_processed(self):
        orch = _make_orchestrator()
        examples = [_make_example(f"ex{i}") for i in range(5)]
        staged = ["/repo/file.md"]
        stats = _default_commit_stats(compile_first_try=5, runtime_first_try=5, runtime_total=5)
        phase_results = {"discovery": {"examples_found": 8}}

        msg = orch._format_detailed(
            "zip", "run1234567890abcd", examples, staged,
            stats, phase_results, {},
        )
        # No files_processed → simpler discovery line
        assert "Discovery: 8 found, 5 committed (62%)" in msg

    def test_single_llm_fix_singular(self):
        orch = _make_orchestrator()
        examples = [_make_example("ex1")]
        staged = ["/repo/file.md"]
        stats = _default_commit_stats(compile_llm=1, runtime_total=0)
        phase_results = {"discovery": {"examples_found": 1}}

        msg = orch._format_detailed(
            "zip", "run1234567890abcd", examples, staged,
            stats, phase_results, {},
        )
        assert "  1 LLM fix" in msg
        assert "  1 LLM fixes" not in msg

    def test_multiple_llm_fixes_plural(self):
        orch = _make_orchestrator()
        examples = [_make_example(f"ex{i}") for i in range(5)]
        staged = ["/repo/file.md"]
        stats = _default_commit_stats(compile_first_try=2, compile_llm=3, runtime_total=0)
        phase_results = {"discovery": {"examples_found": 5}}

        msg = orch._format_detailed(
            "zip", "run1234567890abcd", examples, staged,
            stats, phase_results, {},
        )
        assert "  3 LLM fixes" in msg

    def test_zero_compile_deterministic_omitted(self):
        orch = _make_orchestrator()
        examples = [_make_example(f"ex{i}") for i in range(10)]
        staged = ["/repo/file.md"]
        stats = _default_commit_stats(
            compile_first_try=8, compile_llm=2,
            runtime_first_try=10, runtime_total=10,
        )
        phase_results = {"discovery": {"examples_found": 10}}

        msg = orch._format_detailed(
            "zip", "run1234567890abcd", examples, staged,
            stats, phase_results, {},
        )
        assert "deterministic" not in msg.split("Runtime")[0]  # Not in compilation section


# ── Format: Structured ───────────────────────────────────────────────

class TestFormatStructured:
    """Test the structured (machine-parseable) commit message format."""

    def test_basic_output(self):
        orch = _make_orchestrator()
        examples = [_make_example(f"ex{i}") for i in range(42)]
        staged = [f"/repo/blog/file{i}.md" for i in range(15)]
        stats = _default_commit_stats(
            compile_first_try=35, compile_deterministic=4, compile_llm=3,
            runtime_first_try=38, runtime_deterministic=2, runtime_llm=1,
            runtime_fixture=1, runtime_total=42,
            fix_names=["stream disposal", "CS0246 using directives"],
        )
        phase_results = {"discovery": {"examples_found": 50}}

        msg = orch._format_structured(
            "zip", "abcdef1234567890", examples, staged,
            stats, phase_results, {"blog": ["compression"], "kb": ["extraction"]},
        )

        assert "compile: 35/42 first-try, 4/42 deterministic, 3/42 llm" in msg
        assert "runtime: 38/42 first-try, 2/42 deterministic, 1/42 llm, 1/42 fixture" in msg
        assert "fixes: [stream_disposal, cs0246_using_directives]" in msg
        assert "files: blog=1, kb=1" in msg

    def test_no_fixture_when_zero(self):
        orch = _make_orchestrator()
        examples = [_make_example(f"ex{i}") for i in range(10)]
        staged = ["/repo/file.md"]
        stats = _default_commit_stats(
            compile_first_try=10,
            runtime_first_try=10, runtime_total=10,
        )

        msg = orch._format_structured(
            "zip", "run1234567890abcd", examples, staged,
            stats, {"discovery": {"examples_found": 10}}, {},
        )
        assert "fixture" not in msg

    def test_no_runtime_when_zero(self):
        orch = _make_orchestrator()
        examples = [_make_example("ex1")]
        staged = ["/repo/file.md"]
        stats = _default_commit_stats(compile_first_try=1, runtime_total=0)

        msg = orch._format_structured(
            "zip", "run1234567890abcd", examples, staged,
            stats, {"discovery": {"examples_found": 1}}, {},
        )
        assert "runtime:" not in msg


# ── _compute_commit_stats ────────────────────────────────────────────

class TestComputeCommitStats:
    """Test the _compute_commit_stats() method."""

    def _make_compile_attempt(self, success=True):
        a = MagicMock()
        a.success = success
        return a

    def _make_runtime_attempt(self, success=True, scenario="first_try"):
        a = MagicMock()
        a.success = success
        a.scenario = scenario
        return a

    def test_first_try_compile(self):
        orch = _make_orchestrator()
        ex = _make_example("ex1")
        orch.db.get_compile_attempts.return_value = [self._make_compile_attempt(True)]
        orch.db.get_runtime_attempts.return_value = [self._make_runtime_attempt(True, "first_try")]

        stats = orch._compute_commit_stats([ex], "run1")
        assert stats["compile_first_try"] == 1
        assert stats["compile_llm"] == 0
        assert stats["compile_deterministic"] == 0
        assert stats["runtime_first_try"] == 1

    def test_llm_fixed_compile(self):
        orch = _make_orchestrator()
        orch._llm_fixed_example_ids = {"ex1"}
        ex = _make_example("ex1")
        orch.db.get_compile_attempts.return_value = [
            self._make_compile_attempt(False),
            self._make_compile_attempt(False),
            self._make_compile_attempt(True),
        ]
        orch.db.get_runtime_attempts.return_value = []

        stats = orch._compute_commit_stats([ex], "run1")
        assert stats["compile_llm"] == 1
        assert stats["compile_first_try"] == 0
        assert stats["compile_deterministic"] == 0

    def test_deterministic_fixed_compile(self):
        orch = _make_orchestrator()
        # NOT in _llm_fixed_example_ids
        ex = _make_example("ex1")
        orch.db.get_compile_attempts.return_value = [
            self._make_compile_attempt(False),
            self._make_compile_attempt(True),
        ]
        orch.db.get_runtime_attempts.return_value = []

        stats = orch._compute_commit_stats([ex], "run1")
        assert stats["compile_deterministic"] == 1
        assert stats["compile_llm"] == 0
        assert stats["compile_first_try"] == 0

    def test_runtime_fixture_resolved(self):
        orch = _make_orchestrator()
        ex = _make_example("ex1")
        orch.db.get_compile_attempts.return_value = [self._make_compile_attempt(True)]
        orch.db.get_runtime_attempts.return_value = [
            self._make_runtime_attempt(False, "first_try"),
            self._make_runtime_attempt(True, "fixture_resolved_missing_file"),
        ]

        stats = orch._compute_commit_stats([ex], "run1")
        assert stats["runtime_fixture"] == 1
        assert stats["runtime_first_try"] == 0
        assert stats["runtime_total"] == 1

    def test_runtime_deterministic_fix(self):
        orch = _make_orchestrator()
        ex = _make_example("ex1")
        orch.db.get_compile_attempts.return_value = [self._make_compile_attempt(True)]
        orch.db.get_runtime_attempts.return_value = [
            self._make_runtime_attempt(False, "first_try"),
            self._make_runtime_attempt(True, "deterministic_fix_missing_directory"),
        ]

        stats = orch._compute_commit_stats([ex], "run1")
        assert stats["runtime_deterministic"] == 1

    def test_runtime_llm_fix(self):
        orch = _make_orchestrator()
        ex = _make_example("ex1")
        orch.db.get_compile_attempts.return_value = [self._make_compile_attempt(True)]
        orch.db.get_runtime_attempts.return_value = [
            self._make_runtime_attempt(False, "first_try"),
            self._make_runtime_attempt(True, "llm_fix_attempt_1"),
        ]

        stats = orch._compute_commit_stats([ex], "run1")
        assert stats["runtime_llm"] == 1

    def test_no_runtime_attempts(self):
        orch = _make_orchestrator()
        ex = _make_example("ex1")
        orch.db.get_compile_attempts.return_value = [self._make_compile_attempt(True)]
        orch.db.get_runtime_attempts.return_value = []

        stats = orch._compute_commit_stats([ex], "run1")
        assert stats["runtime_total"] == 0
        assert stats["runtime_first_try"] == 0

    def test_mixed_examples(self):
        orch = _make_orchestrator()
        orch._llm_fixed_example_ids = {"ex3"}

        examples = [_make_example(f"ex{i}") for i in range(1, 4)]

        def mock_compile(eid, run_id=None):
            if eid == "ex1":
                return [self._make_compile_attempt(True)]  # first-try
            elif eid == "ex2":
                return [self._make_compile_attempt(False), self._make_compile_attempt(True)]  # deterministic
            else:
                return [self._make_compile_attempt(False), self._make_compile_attempt(False),
                        self._make_compile_attempt(True)]  # llm

        def mock_runtime(eid, run_id=None):
            if eid == "ex1":
                return [self._make_runtime_attempt(True, "first_try")]
            elif eid == "ex2":
                return [self._make_runtime_attempt(False, "first_try"),
                        self._make_runtime_attempt(True, "fixture_resolved_missing")]
            else:
                return [self._make_runtime_attempt(True, "first_try")]

        orch.db.get_compile_attempts.side_effect = mock_compile
        orch.db.get_runtime_attempts.side_effect = mock_runtime

        stats = orch._compute_commit_stats(examples, "run1")
        assert stats["compile_first_try"] == 1
        assert stats["compile_deterministic"] == 1
        assert stats["compile_llm"] == 1
        assert stats["runtime_first_try"] == 2
        assert stats["runtime_fixture"] == 1
        assert stats["runtime_total"] == 3

    def test_fix_names_collected(self):
        orch = _make_orchestrator()
        ex = _make_example("ex1")
        orch.db.get_compile_attempts.return_value = [self._make_compile_attempt(True)]
        orch.db.get_runtime_attempts.return_value = []

        # Mock the telemetry query
        mock_conn = MagicMock()
        mock_rows = [
            {"metadata": '{"fixes": ["stream disposal", "CS0246 added using"]}'},
            {"metadata": '{"fixes": ["stream disposal"]}'},
        ]
        mock_conn.execute.return_value.fetchall.return_value = mock_rows
        orch.db.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        orch.db.get_connection.return_value.__exit__ = MagicMock(return_value=False)

        stats = orch._compute_commit_stats([ex], "run1")
        assert "CS0246 added using" in stats["fix_names"]
        assert "stream disposal" in stats["fix_names"]
        assert len(stats["fix_names"]) == 2  # deduplicated


# ── _build_commit_message dispatch ───────────────────────────────────

class TestBuildCommitMessage:
    """Test the _build_commit_message() dispatch."""

    def test_defaults_to_compact(self):
        orch = _make_orchestrator()
        examples = [_make_example("ex1")]
        staged = ["/repo/file.md"]
        stats = _default_commit_stats(compile_first_try=1, runtime_first_try=1, runtime_total=1)

        msg = orch._build_commit_message(
            "zip", "run1234567890abcd", examples, staged,
            stats, {"discovery": {"examples_found": 1}}, {},
            "unknown_format",
        )
        # Should fall back to compact
        assert "- Compile:" in msg
        assert "Co-Authored-By:" in msg

    def test_co_author_always_present(self):
        orch = _make_orchestrator()
        examples = [_make_example("ex1")]
        staged = ["/repo/file.md"]
        stats = _default_commit_stats(compile_first_try=1)

        for fmt in ("minimal", "compact", "detailed", "structured"):
            msg = orch._build_commit_message(
                "zip", "run1234567890abcd", examples, staged,
                stats, {}, {}, fmt,
            )
            assert "Co-Authored-By: Example Reviewer <example-reviewer@aspose.net>" in msg


# ── Category topic building ──────────────────────────────────────────

class TestCategorizeFiles:
    """Test _categorize_staged_files() and _format_category_lines()."""

    def test_format_category_lines_singular(self):
        lines = Orchestrator._format_category_lines({"blog": ["compression"]})
        assert lines == ["Blog: 1 file (compression)"]

    def test_format_category_lines_plural(self):
        lines = Orchestrator._format_category_lines({"blog": ["compression", "encryption"]})
        assert lines == ["Blog: 2 files (compression, encryption)"]

    def test_empty_categories_omitted(self):
        lines = Orchestrator._format_category_lines({
            "blog": ["compression"],
            "kb": [],
            "docs": ["tables"],
        })
        # kb is empty, should not appear
        assert len(lines) == 2
        assert any("Blog" in l for l in lines)
        assert any("Docs" in l for l in lines)
        assert not any("Kb" in l for l in lines)
