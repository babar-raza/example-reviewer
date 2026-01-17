# CLI Testing System Healing Plan

## Context

**Problem Statement:**
The CLI uses lazy imports (to speed up `--help`) which creates hidden `NameError` or `ImportError` bugs that only surface at runtime when specific code paths execute. Static type checkers (mypy, pyright) don't catch these because the imports exist in the codebase - they're just not loaded in the right scope.

**Business Impact:**
- Runtime failures in production when users invoke specific CLI commands
- `--help` works but actual command execution fails with import errors
- No systematic way to validate all CLI option combinations before release
- Wasted developer time debugging import issues reported by users

**Strategic Value:**
A comprehensive CLI testing system catches these issues in CI/CD before they reach users, providing:
1. **Static Analysis** - AST-based detection of undefined names
2. **Smoke Tests** - Basic execution validation for all commands
3. **Matrix Tests** - Systematic testing of option combinations
4. **CI Integration** - Automated validation on every commit

**Reference:** See [specs/cli-testing-system.md](../../specs/cli-testing-system.md) for complete architecture

---

## Gap → Taskcard Mapping

| Gap/Blocker ID | Description | Taskcard ID(s) | Priority |
|----------------|-------------|----------------|----------|
| CT-GAP-01 | No static analysis for import errors in CLI code | CT-01 | 🔥 HIGH |
| CT-GAP-02 | No smoke tests for CLI command execution | CT-02 | 🔥 HIGH |
| CT-GAP-03 | No systematic testing of CLI option combinations | CT-03 | 🟡 MEDIUM |
| CT-GAP-04 | No CI/CD integration for CLI validation | CT-04 | 🟡 MEDIUM |

---

## Repo Reality Check

**Purpose**: Verify current CLI structure and identify what testing infrastructure exists before building the system.

### Validation Commands

```bash
# 1. Verify CLI entry point exists
[ -f src/cli/main.py ] && echo "EXISTS: CLI entry point" || echo "MISSING"
python -m src.cli.main --help  # Should work

# 2. Check for existing CLI tests
find tests/ -name "*cli*" -o -name "*test_cli*"
ls -la tests/test_cli*.py 2>/dev/null || echo "No existing CLI tests"

# 3. Verify scripts/ directory exists
[ -d scripts/ ] && echo "EXISTS: scripts/" || echo "MISSING: scripts/ directory"

# 4. Check for existing CI workflows
ls -la .github/workflows/*.yml 2>/dev/null || echo "No GitHub Actions workflows"

# 5. Verify CLI has multiple subcommands
python -m src.cli.main --help | grep -E "^\s+(run|discover|compile)" || echo "Verify subcommands"

# 6. Check for lazy imports in CLI
grep -n "def run\|def discover\|def compile" src/cli/main.py | head -5
# Look for imports inside function bodies (lazy loading pattern)

# 7. Check Python version for AST compatibility
python --version  # Need 3.8+ for ast.unparse, 3.9+ for ast features
```

### Reality Check Results

| Assumption | Status | Evidence |
|------------|--------|----------|
| CLI at `src/cli/main.py` exists | ✅ **CORRECT** | Entry point is `python -m src.cli.main` |
| CLI uses subcommands | ✅ **CORRECT** | `run`, `discover`, `compile`, `validate` commands |
| CLI uses lazy imports | ⚠️ **VERIFY** | Need to check for imports inside functions |
| No existing CLI tests | ⚠️ **VERIFY** | May have some tests in tests/ directory |
| No scripts/ directory | ⚠️ **VERIFY** | May need to create |
| No CI workflows | ⚠️ **VERIFY** | Check .github/workflows/ |

### Go/No-Go Decision

✅ **GO** - This is a net-new system to improve CLI quality and catch import errors.

**Implementation Approach**:
1. Start with **CT-01** (Static Analyzer) - highest impact, catches issues before runtime
2. Then **CT-02** (Smoke Tests) - validates basic execution
3. Then **CT-04** (CI Integration) - automates validation
4. Finally **CT-03** (Matrix Tests) - comprehensive coverage

**Estimated Reality Check Time**: 15 minutes

---

## Taskcard CT-01: Static Import Analyzer

**Status:** Not Started

**Gap Linkage:** Fixes CT-GAP-01 (No static analysis for import errors)

**Priority:** 🔥 **HIGH** - Catches issues before runtime

**Role:** Senior engineer delivering AST-based static analysis tool for detecting undefined names in Python CLI code.

---

### Scope

**Fix:**
- Create `scripts/analyze_cli_imports.py` - AST-based analyzer
- Detect undefined names in Python functions before runtime
- Track all accessible scopes (module, function, closure, builtins)
- Handle `TYPE_CHECKING` imports correctly (runtime vs type-check only)
- Support nested functions, comprehensions, closures
- Exit 0 if no issues, exit 1 if undefined names found

**Allowed paths:**
- `scripts/analyze_cli_imports.py` - new static analyzer script
- `tests/test_import_analyzer.py` - new test file for analyzer
- `scripts/README.md` - documentation for scripts

**Forbidden:** Any other file/path

---

### Acceptance Checks

**CLI:**
- Run `python scripts/analyze_cli_imports.py src/cli/main.py`
- Should exit 0 if no undefined names found
- Should exit 1 and print details if undefined names found
- Output shows function name, line number, and undefined variable name
- Example output:
  ```
  Analyzing src/cli/main.py for undefined names...
  ======================================================================
  ❌ Found 2 undefined names:

  Function: run_command (line 145)
    - 'Database' used at line 150 (not imported in function scope)
    - 'logger' used at line 155 (not defined anywhere)

  Exit code: 1
  ```

**Tests:**
- `pytest tests/test_import_analyzer.py -v` passes
- Test detects undefined module-level import usage
- Test detects undefined local variable usage
- Test handles `TYPE_CHECKING` imports correctly
- Test tracks closure scope correctly
- Test handles comprehension variables correctly
- Test handles nested functions correctly
- Test handles Python builtins correctly (no false positives)

**No mock data in production paths:**
- Analyzer parses real Python AST
- Tests use sample Python code snippets

---

### Deliverables

1. **New script `scripts/analyze_cli_imports.py` (500+ lines):**
   - Implement `ImportAnalyzer(ast.NodeVisitor)` class
   - Track module-level definitions (imports, classes, functions, assignments)
   - Track function-level definitions (parameters, local assignments, local imports)
   - Implement `FunctionScope` dataclass for scope tracking
   - Support nested functions with closure scope
   - Handle comprehension variables (list/dict/set comp, generators)
   - Handle `TYPE_CHECKING` imports (excluded from runtime scope)
   - Implement scope resolution algorithm
   - Generate detailed error reports with line numbers
   - Main entry point with CLI argument parsing

   Key classes:
   ```python
   from dataclasses import dataclass
   from typing import Set, Dict, Optional
   import ast

   @dataclass
   class FunctionScope:
       name: str
       lineno: int
       qualified_name: str  # e.g., "outer.inner"
       parameters: Set[str]
       local_assignments: Set[str]
       local_imports: Set[str]
       names_used: Dict[str, int]  # name -> first line used
       comprehension_vars: Set[str]
       nested_function_names: Set[str]
       parent_scope: Optional['FunctionScope']  # For closures

   class ImportAnalyzer(ast.NodeVisitor):
       def __init__(self):
           self.module_level_names: Set[str] = set()
           self.type_checking_names: Set[str] = set()
           self.function_scopes: List[FunctionScope] = []
           self.current_scope: Optional[FunctionScope] = None
           self.in_type_checking: bool = False

       def visit_Import(self, node): ...
       def visit_ImportFrom(self, node): ...
       def visit_FunctionDef(self, node): ...
       def visit_Name(self, node): ...
       def visit_ListComp(self, node): ...
       # ... other visitor methods
   ```

2. **Scope resolution algorithm:**
   - Names are available if they come from:
     1. Module-level imports/definitions
     2. Function parameters
     3. Local assignments (for loops, with aliases, except names)
     4. Local imports (inside function)
     5. Comprehension variables
     6. Nested function names
     7. Closure scope (parent function scopes)
     8. Python builtins (`open`, `print`, `len`, etc.)
     9. Common typing names (`Dict`, `List`, `Optional`, etc.)

3. **New test file `tests/test_import_analyzer.py`:**
   - Test undefined module import usage:
     ```python
     def test_undefined_module_import():
         code = '''
         def foo():
             db = Database()  # Database not imported
         '''
         analyzer = ImportAnalyzer()
         result = analyzer.analyze(code)
         assert len(result.undefined_names) == 1
         assert 'Database' in result.undefined_names[0]
     ```
   - Test closure scope tracking
   - Test comprehension variables
   - Test TYPE_CHECKING handling
   - Test nested functions
   - Test no false positives for builtins

4. **Documentation in `scripts/README.md`:**
   - Usage instructions for analyze_cli_imports.py
   - Explain scope resolution rules
   - Examples of caught issues
   - Integration with CI/CD

---

### Hard Rules

- ✅ No changes to production CLI code (analysis tool only)
- ✅ Exit codes: 0 = success, 1 = undefined names found
- ✅ Deterministic output (consistent ordering)
- ✅ No new runtime deps (uses stdlib ast module)
- ✅ Python 3.8+ compatible

---

### Review Dimensions (5/5 Criteria)

| Dimension | 5/5 Means |
|-----------|-----------|
| **Correctness** | Accurately detects all undefined names; no false positives for builtins, closures, comprehensions |
| **Completeness** | Handles all scope types (module, function, closure, comprehension, TYPE_CHECKING) |
| **Robustness** | Handles edge cases (nested functions, decorators, lambda, async); clear error messages |
| **Testability** | Comprehensive test suite; tests cover all scope types and edge cases |
| **Documentation** | Clear usage instructions; explains scope rules; examples provided |
| **Integration** | Easy to run manually and in CI; fast execution (< 1 second for typical CLI file) |

---

### Now (Runbook)

```bash
# 1. Create scripts directory if needed
mkdir -p scripts

# 2. Create analyzer script
cat > scripts/analyze_cli_imports.py << 'EOF'
#!/usr/bin/env python3
"""
Static analyzer for detecting undefined names in Python code.
Catches import errors before runtime by analyzing AST.
"""
import ast
import sys
from dataclasses import dataclass, field
from typing import Set, Dict, List, Optional

# BUILTINS list
BUILTINS = set(dir(__builtins__))
TYPING_NAMES = {'Dict', 'List', 'Optional', 'Union', 'Any', 'Tuple', 'Set', ...}

@dataclass
class FunctionScope:
    """Tracks names available in a function scope."""
    name: str
    lineno: int
    qualified_name: str
    parameters: Set[str] = field(default_factory=set)
    local_assignments: Set[str] = field(default_factory=set)
    local_imports: Set[str] = field(default_factory=set)
    names_used: Dict[str, int] = field(default_factory=dict)
    comprehension_vars: Set[str] = field(default_factory=set)
    nested_function_names: Set[str] = field(default_factory=set)
    parent_scope: Optional['FunctionScope'] = None

class ImportAnalyzer(ast.NodeVisitor):
    # Implementation here...
    pass

def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_cli_imports.py <python_file>")
        sys.exit(1)

    file_path = sys.argv[1]
    # ... implementation
EOF

chmod +x scripts/analyze_cli_imports.py

# 3. Test on CLI file
python scripts/analyze_cli_imports.py src/cli/main.py

# 4. Create tests
cat > tests/test_import_analyzer.py << 'EOF'
import pytest
from scripts.analyze_cli_imports import ImportAnalyzer, FunctionScope

def test_undefined_import():
    code = """
def foo():
    db = Database()
"""
    # Test implementation...
EOF

# 5. Run tests
pytest tests/test_import_analyzer.py -v

# 6. Document in README
cat >> scripts/README.md << 'EOF'
# Static Import Analyzer

Detects undefined names in Python code before runtime.

## Usage
python scripts/analyze_cli_imports.py src/cli/main.py
EOF
```

---

## Taskcard CT-02: Execution Smoke Tests

**Status:** Not Started

**Gap Linkage:** Fixes CT-GAP-02 (No smoke tests for CLI execution)

**Priority:** 🔥 **HIGH** - Validates basic CLI functionality

**Role:** Senior engineer delivering smoke tests for all CLI commands.

---

### Scope

**Fix:**
- Create `tests/test_cli_smoke.py` - smoke tests for all CLI commands
- Test `--help` for all subcommands
- Test basic execution of each command (with minimal args)
- Verify exit codes are correct
- Verify no import errors at runtime
- Use temporary directories and mock dependencies

**Allowed paths:**
- `tests/test_cli_smoke.py` - new smoke test file
- `tests/conftest.py` - shared fixtures for CLI testing

**Forbidden:** Any other file/path

---

### Acceptance Checks

**Tests:**
- `pytest tests/test_cli_smoke.py -v` passes
- Test `python -m src.cli.main --help` returns exit 0
- Test `python -m src.cli.main run --help` returns exit 0
- Test `python -m src.cli.main discover --help` returns exit 0
- Test `python -m src.cli.main compile --help` returns exit 0
- Test `python -m src.cli.main validate --help` returns exit 0
- Test basic execution: `python -m src.cli.main run --family zip --dry-run` works
- Test no import errors raised during execution
- All tests complete in < 30 seconds

**No mock data in production paths:**
- Tests use temporary directories
- Tests mock expensive operations (LLM calls, network requests)

---

### Deliverables

1. **New test file `tests/test_cli_smoke.py`:**
   ```python
   import subprocess
   import pytest
   from pathlib import Path

   def test_main_help():
       """Test main --help works without import errors."""
       result = subprocess.run(
           ['python', '-m', 'src.cli.main', '--help'],
           capture_output=True, text=True
       )
       assert result.returncode == 0
       assert '--help' in result.stdout

   def test_run_help():
       """Test run --help works."""
       result = subprocess.run(
           ['python', '-m', 'src.cli.main', 'run', '--help'],
           capture_output=True, text=True
       )
       assert result.returncode == 0
       assert '--family' in result.stdout

   def test_run_dry_run():
       """Test run command executes without errors in dry-run mode."""
       result = subprocess.run(
           ['python', '-m', 'src.cli.main', 'run',
            '--family', 'zip', '--dry-run', '--max-examples', '1'],
           capture_output=True, text=True, timeout=30
       )
       # Should complete without import errors
       assert 'NameError' not in result.stderr
       assert 'ImportError' not in result.stderr

   # More tests for each command...
   ```

2. **Fixtures in `tests/conftest.py`:**
   ```python
   import pytest
   import tempfile
   from pathlib import Path

   @pytest.fixture
   def temp_workspace():
       """Create temporary workspace for CLI tests."""
       with tempfile.TemporaryDirectory() as tmpdir:
           workspace = Path(tmpdir)
           # Create minimal config structure
           (workspace / 'config').mkdir()
           (workspace / 'config' / 'global.json').write_text('{}')
           yield workspace
   ```

---

### Hard Rules

- ✅ No changes to CLI production code
- ✅ Tests use subprocess to invoke CLI (real execution)
- ✅ Mock expensive operations (LLM, network, file I/O)
- ✅ Tests complete quickly (< 30 seconds total)
- ✅ Tests use temporary directories (no pollution)

---

### Now (Runbook)

```bash
# 1. Create smoke test file
cat > tests/test_cli_smoke.py << 'EOF'
"""Smoke tests for CLI commands - catch import errors and basic execution issues."""
import subprocess
import pytest

# Test implementations...
EOF

# 2. Run smoke tests
pytest tests/test_cli_smoke.py -v

# 3. Verify all help commands work
python -m src.cli.main --help
python -m src.cli.main run --help
python -m src.cli.main discover --help

# 4. Test basic execution with dry-run
python -m src.cli.main run --family zip --dry-run --max-examples 1
```

---

## Taskcard CT-03: Runtime Matrix Tests

**Status:** Not Started

**Gap Linkage:** Fixes CT-GAP-03 (No systematic option combination testing)

**Priority:** 🟡 **MEDIUM** - Comprehensive coverage

**Role:** Senior engineer delivering systematic testing of CLI option combinations.

---

### Scope

**Fix:**
- Create `tests/test_cli_matrix.py` - matrix tests for option combinations
- Test common option combinations for each command
- Verify incompatible options are rejected correctly
- Test flag combinations (boolean flags)
- Test value parameter combinations
- Use parameterized tests for efficiency

**Allowed paths:**
- `tests/test_cli_matrix.py` - new matrix test file

**Forbidden:** Any other file/path

---

### Acceptance Checks

**Tests:**
- `pytest tests/test_cli_matrix.py -v` passes
- Test `run` command with various combinations:
  - `--family zip --dry-run`
  - `--family zip --max-examples 5`
  - `--family zip --dry-run --max-examples 1`
  - `--family zip --enable-git-commit --dry-run` (should not commit in dry-run)
- Test incompatible options are rejected:
  - `--enable-git-commit --disable-git-commit` (mutually exclusive)
- All tests complete in < 2 minutes

---

### Deliverables

1. **New test file `tests/test_cli_matrix.py`:**
   ```python
   import pytest
   import subprocess

   @pytest.mark.parametrize("family,max_examples", [
       ("zip", 1),
       ("zip", 5),
       ("pdf", 1),
   ])
   def test_run_family_combinations(family, max_examples):
       """Test run command with various family/max_examples combinations."""
       result = subprocess.run(
           ['python', '-m', 'src.cli.main', 'run',
            '--family', family, '--max-examples', str(max_examples), '--dry-run'],
           capture_output=True, text=True, timeout=60
       )
       assert 'NameError' not in result.stderr
       assert 'ImportError' not in result.stderr

   # More matrix tests...
   ```

---

### Now (Runbook)

```bash
# 1. Create matrix test file
cat > tests/test_cli_matrix.py << 'EOF'
"""Matrix tests for CLI option combinations."""
import pytest
import subprocess

# Test implementations...
EOF

# 2. Run matrix tests
pytest tests/test_cli_matrix.py -v
```

---

## Taskcard CT-04: CI Integration

**Status:** Not Started

**Gap Linkage:** Fixes CT-GAP-04 (No CI/CD validation)

**Priority:** 🟡 **MEDIUM** - Automates validation

**Role:** Senior engineer delivering GitHub Actions workflow for automated CLI testing.

---

### Scope

**Fix:**
- Create `.github/workflows/cli_tests.yml` - GitHub Actions workflow
- Run static analyzer on every commit
- Run smoke tests on every commit
- Run matrix tests on pull requests
- Report results as GitHub status checks
- Cache dependencies for fast execution

**Allowed paths:**
- `.github/workflows/cli_tests.yml` - new CI workflow

**Forbidden:** Any other file/path

---

### Deliverables

1. **New workflow `.github/workflows/cli_tests.yml`:**
   ```yaml
   name: CLI Tests

   on:
     push:
       branches: [main, develop]
     pull_request:
       branches: [main]

   jobs:
     static-analysis:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v3
         - uses: actions/setup-python@v4
           with:
             python-version: '3.10'
         - name: Run static import analyzer
           run: python scripts/analyze_cli_imports.py src/cli/main.py

     smoke-tests:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v3
         - uses: actions/setup-python@v4
         - name: Install dependencies
           run: pip install -r requirements.txt
         - name: Run smoke tests
           run: pytest tests/test_cli_smoke.py -v

     matrix-tests:
       if: github.event_name == 'pull_request'
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v3
         - uses: actions/setup-python@v4
         - name: Install dependencies
           run: pip install -r requirements.txt
         - name: Run matrix tests
           run: pytest tests/test_cli_matrix.py -v
   ```

---

## Summary

**4 Taskcards Created for CLI Testing System:**

| Priority | Taskcard | Impact | Effort | Dependencies |
|----------|----------|--------|--------|--------------|
| 🔥 HIGH | **CT-01**: Static Import Analyzer | Catches import errors pre-runtime | 8h | None |
| 🔥 HIGH | **CT-02**: Execution Smoke Tests | Validates basic CLI execution | 4h | None |
| 🟡 MEDIUM | **CT-03**: Runtime Matrix Tests | Systematic option coverage | 6h | CT-02 |
| 🟡 MEDIUM | **CT-04**: CI Integration | Automates validation | 2h | CT-01, CT-02 |

**Implementation Order:**
```
1. CT-01: Static Analyzer      (8h) - Catch issues statically
2. CT-02: Smoke Tests          (4h) - Validate basic execution
3. CT-04: CI Integration       (2h) - Automate validation
4. CT-03: Matrix Tests         (6h) - Comprehensive coverage
```

**Key Deliverables:**
- `scripts/analyze_cli_imports.py` - AST-based static analyzer
- `tests/test_cli_smoke.py` - Smoke tests for all commands
- `tests/test_cli_matrix.py` - Matrix tests for option combinations
- `.github/workflows/cli_tests.yml` - CI automation

**Expected Outcomes:**
- **Zero import errors in production** - Static analysis catches all undefined names
- **Faster debugging** - Issues caught in CI, not by users
- **Confident refactoring** - Tests catch regressions immediately
- **Systematic validation** - All option combinations tested

**Total Estimated Effort:** 20 hours (~2.5 days)

**Risk Assessment:**
- **Low Risk**: All taskcards are testing/tooling (no production code changes)
- **High Value**: Prevents user-facing import errors
- **Quick Win**: CT-01 + CT-02 (12h) provides immediate value
