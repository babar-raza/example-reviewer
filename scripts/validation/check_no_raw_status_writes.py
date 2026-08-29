#!/usr/bin/env python3
"""
Detect code that bypasses StateAuthority (TC-EPIC2-01) to write an example's
status directly, instead of through src/core/state_authority.py's validated
transition() method.

Root cause (Root Cause 2, FINDINGS_REGISTER.md): Database.update_example_status()
issues a raw ``UPDATE example_run_state SET status = ...`` with no prior-status
read and no legality check. StateAuthority wraps it with a real, validating
transition table (reused from src/core/models.py's ExampleRecord.can_transition_to()),
but nothing stops a future call site from calling the raw primitive directly, or
resurrecting one of the other raw-write paths this investigation found. This
script is that enforcement.

Checks (scans tracked .py files under the given root, excluding
src/core/database.py and src/core/state_authority.py -- the two files
sanctioned to contain these patterns):
  (a) any literal ``UPDATE example_run_state SET ... status`` raw SQL fragment
      (a future module embedding this SQL directly, bypassing both
      update_example_status() and StateAuthority entirely).
  (b) any call to ``.update_example_status(`` -- the sanctioned low-level
      writer, but ONLY sanctioned to be called from within StateAuthority
      itself. TC-EPIC2-02 mechanically replaced every previously-flagged call
      site (54 in orchestrator.py, 2 in markdown_service.py, 1 in
      timeout_manager.py) with a StateAuthority call.
  (c) any direct ``.status = ExampleStatus.<MEMBER>`` attribute assignment --
      bypasses transition_to()/can_transition_to() at the Python-object level
      (the src/pipeline/error_router.py:300 pattern this investigation found).
  (d) any call to ``.update_example_run_state_status(`` -- a second,
      structurally identical, currently-uncalled raw-SQL writer
      (database.py's dead ``update_example_run_state_status()``) that must
      never gain a caller outside StateAuthority.

Explicitly NOT implemented as a separate static check (disclosed scope
decision, per this taskcard's own text permitting the implementer to pick
whichever approach is reliably enforceable): "any save_example(...) call that
passes run_id= where the example argument's .status was mutated since
construction". Check (c) above is a strict superset of this for every
currently-known instance -- it flags the mutating assignment itself,
unconditionally, regardless of whether a save_example() call follows it. A
prior-mutation-tracking dataflow check would need real control-flow analysis
to be reliable (a per-line/per-file heuristic here would either miss real
cases separated across functions or produce noisy false positives on
unrelated .status assignments in test fixtures), so it is left out rather than
shipped as an unreliable check.

Only scans src/ by default (not tests/) -- tests/test_state_authority.py's own
negative control (test_raw_update_example_status_bypasses_authority_by_design)
deliberately calls the raw primitive directly to document the shape of the bug
this script's ecosystem closes; flagging that intentional test would be a false
positive, not a real violation.

Modes:
  (default) Emit violations and exit 0 (non-blocking).
  --strict  Emit violations and exit 1 if any are found -- the mode CI runs in
            since TC-EPIC2-02 migrated all known call sites (see
            .gitlab-ci.yml's state-authority-lint job).

Usage:
    python scripts/validation/check_no_raw_status_writes.py
    python scripts/validation/check_no_raw_status_writes.py --strict
    python scripts/validation/check_no_raw_status_writes.py path/to/dir --strict
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List

_REPO_ROOT = Path(__file__).resolve().parents[2]

# The two files sanctioned to contain these patterns: database.py defines the
# low-level primitives, state_authority.py is their one validated caller.
_EXEMPT_SUFFIXES = ("src/core/database.py", "src/core/state_authority.py")

_UPDATE_CALL_RE = re.compile(r"\.update_example_status\s*\(")
_DEAD_WRITER_CALL_RE = re.compile(r"\.update_example_run_state_status\s*\(")
_DIRECT_ASSIGN_RE = re.compile(r"\.status\s*=\s*ExampleStatus\.\w+")
_RAW_SQL_UPDATE_RE = re.compile(r"UPDATE\s+example_run_state\b", re.IGNORECASE)
_RAW_SQL_SET_STATUS_RE = re.compile(r"SET\s+status\b", re.IGNORECASE)
_SQL_WINDOW_LINES = 4


@dataclass(frozen=True)
class Violation:
    path: Path
    line: int
    message: str

    def format(self, root: Path) -> str:
        try:
            display_path = self.path.relative_to(root)
        except ValueError:
            display_path = self.path
        return f"{display_path}:{self.line}: {self.message}"


def _is_exempt(path: Path) -> bool:
    normalized = str(path).replace("\\", "/")
    return any(normalized.endswith(suffix) for suffix in _EXEMPT_SUFFIXES)


def _scan_file(path: Path) -> List[Violation]:
    violations: List[Violation] = []
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return violations
    lines = text.splitlines()

    for i, line in enumerate(lines):
        line_no = i + 1

        if _UPDATE_CALL_RE.search(line):
            violations.append(Violation(
                path, line_no,
                "Direct call to update_example_status() outside StateAuthority -- "
                "use src/core/state_authority.py's StateAuthority.transition() "
                "(or a mark_*() convenience method) instead.",
            ))

        if _DEAD_WRITER_CALL_RE.search(line):
            violations.append(Violation(
                path, line_no,
                "Call to update_example_run_state_status() -- a dead, unvalidated "
                "second status writer with zero sanctioned callers. Route through "
                "StateAuthority instead.",
            ))

        if _DIRECT_ASSIGN_RE.search(line):
            violations.append(Violation(
                path, line_no,
                "Direct '.status = ExampleStatus.X' assignment bypasses "
                "ExampleRecord.transition_to()/can_transition_to() entirely -- "
                "route the change through StateAuthority.transition() instead.",
            ))

        if _RAW_SQL_UPDATE_RE.search(line):
            window = " ".join(lines[i:i + _SQL_WINDOW_LINES])
            if _RAW_SQL_SET_STATUS_RE.search(window):
                violations.append(Violation(
                    path, line_no,
                    "Raw 'UPDATE example_run_state SET status' SQL fragment outside "
                    "database.py -- route the change through StateAuthority instead.",
                ))

    return violations


def scan(root: Path) -> List[Violation]:
    """Scan every tracked-looking .py file under root, excluding the exempt files."""
    violations: List[Violation] = []
    for path in sorted(root.rglob("*.py")):
        if _is_exempt(path):
            continue
        violations.extend(_scan_file(path))
    return violations


def main(argv: List[str] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "root", nargs="?", default=str(_REPO_ROOT / "src"),
        help="Directory to scan (default: src/)",
    )
    parser.add_argument(
        "--strict", action="store_true",
        help="Exit non-zero if any violation is found (default: warn-only, exit 0).",
    )
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    violations = scan(root)

    if not violations:
        print(f"check_no_raw_status_writes: clean ({root})")
        return 0

    print(f"check_no_raw_status_writes: {len(violations)} violation(s) found in {root}:")
    for violation in violations:
        print("  " + violation.format(root))

    if args.strict:
        return 1

    print(
        "\nRunning in warn-only mode (pass --strict to fail CI on these). "
        "All known call sites were migrated in TC-EPIC2-02 -- a violation here "
        "means a new bypass was introduced; route it through StateAuthority."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
