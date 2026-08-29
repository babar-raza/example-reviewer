"""Tests for scripts/validation/check_no_raw_status_writes.py (TC-EPIC2-01).

Uses fixture directories under a temp dir (not the real repo tree) for the
planted-violation / clean-tree tests, so this file's assertions don't depend on
the real codebase's current migration state (see test_state_authority.py's
test_lint_script_flags_current_error_router_dead_code for the real-tree check).
"""

from pathlib import Path

from scripts.validation.check_no_raw_status_writes import main, scan


def _write(tmp_path: Path, relative: str, content: str) -> Path:
    path = tmp_path / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


class TestScan:
    def test_script_flags_known_violations(self, tmp_path):
        _write(
            tmp_path,
            "src/pipeline/bad_writer.py",
            'def write(conn):\n'
            '    conn.execute("""\n'
            "        UPDATE example_run_state\n"
            "        SET status = ?\n"
            '    """, (status,))\n',
        )

        violations = scan(tmp_path)

        assert len(violations) == 1
        assert violations[0].path == tmp_path / "src" / "pipeline" / "bad_writer.py"
        assert violations[0].line == 3  # the "UPDATE example_run_state" line itself

    def test_script_passes_clean_tree(self, tmp_path):
        _write(
            tmp_path,
            "src/pipeline/fine.py",
            "def do_something():\n"
            "    return 1 + 1\n",
        )

        violations = scan(tmp_path)

        assert violations == []

    def test_flags_direct_update_example_status_call(self, tmp_path):
        _write(
            tmp_path,
            "src/pipeline/orchestrator_like.py",
            "def foo(self):\n"
            "    self.db.update_example_status(example_id, ExampleStatus.VERIFIED, run_id=run_id)\n",
        )

        violations = scan(tmp_path)

        assert len(violations) == 1
        assert violations[0].line == 2
        assert "update_example_status" in violations[0].message

    def test_flags_direct_status_assignment(self, tmp_path):
        _write(
            tmp_path,
            "src/pipeline/error_router_like.py",
            "def escalate(example):\n"
            "    example.status = ExampleStatus.NEEDS_REVIEW\n",
        )

        violations = scan(tmp_path)

        assert len(violations) == 1
        assert violations[0].line == 2

    def test_flags_dead_writer_call(self, tmp_path):
        _write(
            tmp_path,
            "src/pipeline/dead_caller.py",
            "def foo(self):\n"
            "    self.db.update_example_run_state_status(example_id, status, run_id=run_id)\n",
        )

        violations = scan(tmp_path)

        assert len(violations) == 1
        assert "update_example_run_state_status" in violations[0].message

    def test_status_comparison_is_not_flagged(self, tmp_path):
        """A `==` comparison against ExampleStatus must not be mistaken for the
        assignment pattern -- only `=` (single) is a violation."""
        _write(
            tmp_path,
            "src/pipeline/reader.py",
            "def check(example):\n"
            "    if example.status == ExampleStatus.VERIFIED:\n"
            "        return True\n"
            "    return False\n",
        )

        violations = scan(tmp_path)

        assert violations == []

    def test_exempt_files_are_never_flagged(self, tmp_path):
        _write(
            tmp_path,
            "src/core/database.py",
            'def update_example_status(self):\n'
            '    conn.execute("UPDATE example_run_state SET status = ?", (x,))\n',
        )
        _write(
            tmp_path,
            "src/core/state_authority.py",
            "def transition(self):\n"
            "    self.db.update_example_status(example_id, status, run_id=run_id)\n",
        )

        violations = scan(tmp_path)

        assert violations == []


class TestMain:
    def test_main_warn_only_exits_zero_with_violations(self, tmp_path, capsys):
        _write(
            tmp_path,
            "src/pipeline/bad.py",
            "def foo(example):\n"
            "    example.status = ExampleStatus.NEEDS_REVIEW\n",
        )

        exit_code = main([str(tmp_path)])

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "violation(s) found" in captured.out

    def test_main_strict_exits_nonzero_with_violations(self, tmp_path):
        _write(
            tmp_path,
            "src/pipeline/bad.py",
            "def foo(example):\n"
            "    example.status = ExampleStatus.NEEDS_REVIEW\n",
        )

        exit_code = main([str(tmp_path), "--strict"])

        assert exit_code == 1

    def test_main_exits_zero_on_clean_tree_even_strict(self, tmp_path):
        _write(tmp_path, "src/pipeline/fine.py", "def f():\n    return 1\n")

        assert main([str(tmp_path), "--strict"]) == 0
