# Scripts Documentation

This directory contains utility scripts for the Example Reviewer project.

## Static Import Analyzer

### Overview

`analyze_cli_imports.py` is an AST-based static analyzer that detects undefined names in Python code. It's specifically designed to catch import errors in CLI code that uses lazy imports (imports inside functions) to optimize startup time.

### Problem Statement

Static type checkers like mypy can't detect certain classes of import errors when using lazy imports:

1. **Names imported at module level but used inside functions** - CORRECT ✓
2. **Names NOT imported but used inside functions** - BUG (NameError at runtime) ✗
3. **TYPE_CHECKING imports used at runtime** - BUG (ImportError at runtime) ✗

The analyzer catches these issues before they reach users.

### Usage

#### Basic Usage

```bash
python scripts/analyze_cli_imports.py <file.py>
```

#### Examples

Analyze a single file:
```bash
python scripts/analyze_cli_imports.py src/cli/main.py
```

Analyze multiple files:
```bash
python scripts/analyze_cli_imports.py src/cli/*.py
```

### Exit Codes

- **0** - Success (no undefined names found)
- **1** - Failure (undefined names found or error)

### Output Format

#### Success Case
```
Analyzing src/cli/main.py for undefined names...
======================================================================
[PASS] No undefined names found!
```

#### Failure Case
```
Analyzing src/cli/main.py for undefined names...
======================================================================
[FAIL] Found 2 undefined names:

Function: run_command (line 145)
  - 'Database' used at line 150 (not imported in function scope)
  - 'logger' used at line 155 (not defined anywhere)
```

### How It Works

The analyzer uses Python's `ast` module to walk the syntax tree and track:

1. **Module-level scope**: All top-level imports and assignments
2. **Function scopes**: Parameters, local assignments, local imports, nested functions
3. **Closure scopes**: Parent function scopes accessible to inner functions
4. **Comprehension scopes**: Loop variables local to comprehensions
5. **TYPE_CHECKING scope**: Imports only available to static type checkers

#### Name Resolution Algorithm

For each name used in a function, the analyzer checks:

1. Function's local scope (parameters, assignments, imports)
2. Parent function scopes (closures)
3. Module-level scope
4. Python builtins (`open`, `print`, `len`, etc.)
5. Common typing names (`Dict`, `List`, `Optional`, etc.)

If a name is not found in any of these scopes, it's reported as undefined.

### Scope Types Handled

#### Module-level Imports
```python
import os
import sys

def my_function():
    os.path.exists('test')  # ✓ Available
    sys.exit(0)             # ✓ Available
```

#### Function-level Imports (Lazy Imports)
```python
def my_function():
    import json
    data = json.loads('{}')  # ✓ Available
```

#### Undefined Names
```python
def my_function():
    Database()        # ✗ Undefined (not imported)
    query_data()      # ✗ Undefined (not defined)
```

#### Closures
```python
def outer():
    x = 10

    def inner():
        return x + 5  # ✓ Available from outer scope

    return inner()
```

#### Comprehensions
```python
def process():
    result = [x * 2 for x in range(10)]  # ✓ x is local to comprehension
    return result
```

#### TYPE_CHECKING Imports
```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mypackage import Database

def my_function():
    db = Database()  # ✗ Undefined at runtime (TYPE_CHECKING only)
```

### Testing

#### Run Unit Tests
Tests for the import analyzer have been integrated into the main test suite. Run:
```bash
pytest tests/ -k import
```

Expected output:
```
======================================================================
Running Import Analyzer Unit Tests
======================================================================

[PASS] Module level import
[PASS] Undefined in function
[PASS] Local import
[PASS] Function parameter
[PASS] Local assignment
[PASS] Closure access
[PASS] Comprehension scope
[PASS] TYPE_CHECKING runtime
[PASS] Builtin names
[PASS] Nested function name
[PASS] For loop variable
[PASS] With statement alias
[PASS] Typing names
[PASS] Import as
[PASS] From import as

======================================================================
Results: 15 passed, 0 failed
======================================================================
```

### Implementation Details

#### Core Classes

**FunctionScope**
```python
@dataclass
class FunctionScope:
    name: str                              # Function name
    lineno: int                            # Start line
    qualified_name: str                    # e.g., "outer.inner"
    parameters: Set[str]                   # Function parameters
    local_assignments: Set[str]            # Local variables
    local_imports: Set[str]                # Local imports
    names_used: Dict[str, int]             # name -> first line used
    comprehension_vars: Set[str]           # Comprehension vars
    nested_function_names: Set[str]        # Nested functions
    parent_scope: Optional['FunctionScope'] # For closures
```

**ImportAnalyzer**
```python
class ImportAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.module_level_names: Set[str] = set()
        self.type_checking_names: Set[str] = set()
        self.function_scopes: List[FunctionScope] = []
        self.current_scope: Optional[FunctionScope] = None
        self.in_type_checking: bool = False
```

#### Key Methods

- `visit_Import` - Track import statements
- `visit_ImportFrom` - Track from imports
- `visit_If` - Detect TYPE_CHECKING blocks
- `visit_FunctionDef` - Create new function scope
- `visit_Name` - Record name usage
- `visit_Assign` - Track local assignments
- `visit_For` - Track loop variables
- `visit_With` - Track with aliases
- `visit_ExceptHandler` - Track exception names
- `visit_ListComp` / `visit_SetComp` / `visit_DictComp` - Track comprehension variables

### Performance

- Single-pass AST walk
- No expensive operations
- Typical CLI file (100-500 lines): < 1 second

### Limitations

1. **Star imports**: `from module import *` cannot be tracked precisely
2. **Dynamic imports**: `__import__()` or `importlib.import_module()` are not tracked
3. **Attribute access**: Only tracks name availability, not attribute existence
4. **Runtime modifications**: Cannot detect names added to globals/locals at runtime

### Integration

The analyzer can be integrated into:

1. **CI/CD pipelines**: Run as a pre-commit hook or CI check
2. **Pre-commit hooks**: Catch issues before committing
3. **IDE integration**: Run on save or as a linter
4. **Test suites**: Add as a test case

Example CI integration:
```bash
# In .github/workflows/ci.yml
- name: Check CLI imports
  run: python scripts/analyze_cli_imports.py src/cli/main.py
```

### Troubleshooting

#### False Positives

If you encounter false positives (names incorrectly flagged as undefined):

1. Check if the name is in `PYTHON_BUILTINS` or `COMMON_TYPING_NAMES`
2. If it's a common builtin or typing name, add it to the appropriate set
3. If it's imported via star import, consider using explicit imports

#### False Negatives

If you encounter false negatives (undefined names not caught):

1. Check if the name is in one of the whitelists (builtins, typing)
2. Report as an issue with the specific code example

### Contributing

When adding new features or fixing bugs:

1. Add unit tests in the main test suite (`tests/`)
2. Run tests to ensure all pass (`pytest tests/`)
3. Update this documentation
4. Test on real CLI files

### References

- Python AST docs: https://docs.python.org/3/library/ast.html
- Task spec: reports/TASK_BACKLOG.md lines 2621-2717
- Plan source: plans/healing/cli-testing-system.md lines 93-350
