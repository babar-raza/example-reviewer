# CT-01: Static Import Analyzer - Implementation Plan

## Agent: Discovery & Architecture (Agent A)
**Run ID**: run_20260116_020000
**Priority**: P0 (CRITICAL)
**Estimated Time**: 8 hours

## Problem Analysis

The CLI uses lazy imports (imports inside functions) to optimize `--help` performance. However, this creates a class of bugs that static type checkers can't detect:

1. Names imported at module level but used inside functions (correct)
2. Names NOT imported but used inside functions (BUG - NameError at runtime)
3. TYPE_CHECKING imports used at runtime (ImportError)

Static analyzers like mypy don't catch these because they assume all imports are available everywhere.

## Solution Architecture

### Core Components

1. **ImportAnalyzer (AST-based)**
   - Walks the Python AST to track name definitions and usages
   - Maintains separate scopes: module, function, closure, comprehension, TYPE_CHECKING
   - Reports undefined names with precise location information

2. **Scope Tracking System**
   - Module-level scope: All top-level imports and assignments
   - Function scopes: Parameters, local assignments, local imports, nested functions
   - Closure support: Functions can access parent function scopes
   - Comprehension scopes: Loop variables are local to comprehension
   - TYPE_CHECKING scope: Excluded from runtime availability

3. **Name Resolution Algorithm**
   - For each name used in a function:
     1. Check function's local scope (parameters, assignments, imports)
     2. Check parent function scopes (closures)
     3. Check module-level scope
     4. Check Python builtins
     5. Check common typing names (Dict, List, Optional, etc.)
   - If not found in any scope: report as undefined

### Data Structures

```python
@dataclass
class FunctionScope:
    name: str                              # Function name
    lineno: int                            # Start line
    qualified_name: str                    # e.g., "outer.inner"
    parameters: Set[str]                   # Function parameters
    local_assignments: Set[str]            # a = 1, for x in ..., with f as x
    local_imports: Set[str]                # import X, from Y import Z
    names_used: Dict[str, int]             # name -> first line used
    comprehension_vars: Set[str]           # [x for x in ...]
    nested_function_names: Set[str]        # def inner(): ...
    parent_scope: Optional['FunctionScope'] # For closure resolution
```

### AST Visitor Methods

1. `visit_Import` - Track module-level and function-level imports
2. `visit_ImportFrom` - Handle from X import Y, including TYPE_CHECKING
3. `visit_FunctionDef` - Create new function scope, track parameters
4. `visit_Name` - Record name usage with line number
5. `visit_Assign` - Track local assignments
6. `visit_For` - Track loop variables
7. `visit_With` - Track with aliases
8. `visit_ExceptHandler` - Track exception names
9. `visit_ListComp` - Track comprehension variables in nested scope
10. `visit_SetComp` - Track set comprehension variables
11. `visit_DictComp` - Track dict comprehension variables
12. `visit_GeneratorExp` - Track generator comprehension variables

## Implementation Steps

### Phase 1: Core Analyzer (2 hours)
1. Create `scripts/analyze_cli_imports.py`
2. Implement `FunctionScope` dataclass
3. Implement `ImportAnalyzer` class skeleton
4. Add basic AST visitor methods

### Phase 2: Scope Tracking (3 hours)
1. Implement module-level import tracking
2. Implement function-level import tracking
3. Implement TYPE_CHECKING scope isolation
4. Implement closure support (parent scope chain)
5. Implement comprehension scope handling

### Phase 3: Name Resolution (2 hours)
1. Implement `resolve_name()` method
2. Add builtin detection (open, print, len, etc.)
3. Add typing names detection (Dict, List, Optional, etc.)
4. Add undefined name reporting
5. Implement CLI interface with exit codes

### Phase 4: Testing & Documentation (1 hour)
1. Create `tests/test_import_analyzer.py`
2. Write 10+ unit tests covering all scenarios
3. Update `scripts/README.md`
4. Run tests and validate outputs
5. Create evidence documentation

## Test Strategy

### Unit Tests (tests/test_import_analyzer.py)

1. **test_module_level_import** - Names imported at module level are available
2. **test_undefined_in_function** - Name used but not imported in function
3. **test_local_import** - Import inside function makes name available
4. **test_function_parameter** - Parameters are available in function
5. **test_local_assignment** - Local assignments are available
6. **test_closure_access** - Inner function can access outer function names
7. **test_comprehension_scope** - Loop vars in comprehension don't leak
8. **test_type_checking_runtime** - TYPE_CHECKING imports not available at runtime
9. **test_builtin_names** - Python builtins don't trigger false positives
10. **test_nested_functions** - Nested function names are available in parent
11. **test_for_loop_variable** - For loop variables are local assignments
12. **test_with_statement_alias** - With aliases are local assignments

### Integration Tests

Run analyzer on actual CLI files:
- `src/cli/main.py` - Main CLI entry point
- All files in `src/cli/` directory

## Expected Outputs

### Success Case (Exit 0)
```
Analyzing src/cli/main.py for undefined names...
======================================================================
✓ No undefined names found!

Exit code: 0
```

### Failure Case (Exit 1)
```
Analyzing src/cli/main.py for undefined names...
======================================================================
❌ Found 2 undefined names:

Function: run_command (line 145)
  - 'Database' used at line 150 (not imported in function scope)
  - 'logger' used at line 155 (not defined anywhere)

Exit code: 1
```

## Acceptance Criteria Checklist

- [ ] ImportAnalyzer class implemented with full scope tracking
- [ ] CLI usage: `python scripts/analyze_cli_imports.py src/cli/main.py`
- [ ] Exit codes: 0 for success, 1 for undefined names
- [ ] No false positives on Python builtins
- [ ] No false positives on TYPE_CHECKING imports
- [ ] 10+ unit tests passing
- [ ] Fast execution (< 1 second per file)
- [ ] Documentation in scripts/README.md
- [ ] All evidence files created

## Risk Mitigation

1. **Complex AST traversal** - Use ast.NodeVisitor pattern for clean separation
2. **Scope edge cases** - Comprehensive unit tests for all scope types
3. **False positives** - Whitelist for builtins and common typing names
4. **Performance** - Single-pass AST walk, no expensive operations

## Success Metrics

1. Analyzer completes in < 1 second for typical CLI file (100-500 lines)
2. All unit tests pass
3. Zero false positives on known good code
4. Catches all undefined name cases from manual review
5. Self-review scores ≥4/5 on all 12 dimensions

## References

- Task spec: reports/TASK_BACKLOG.md lines 2621-2717
- Plan source: plans/healing/cli-testing-system.md lines 93-350
- Python AST docs: https://docs.python.org/3/library/ast.html
