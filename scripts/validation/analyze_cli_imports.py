#!/usr/bin/env python3
"""
Static Import Analyzer for Python CLI Code

Detects undefined names in Python code that uses lazy imports (imports inside functions).
This prevents NameError and ImportError at runtime that static type checkers can't catch.

Usage:
    python scripts/analyze_cli_imports.py <file.py>
    python scripts/analyze_cli_imports.py src/cli/main.py

Exit Codes:
    0 - No undefined names found
    1 - Undefined names found
"""

import ast
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set


# Common Python builtins that should not trigger false positives
PYTHON_BUILTINS = {
    'abs', 'all', 'any', 'ascii', 'bin', 'bool', 'bytearray', 'bytes',
    'callable', 'chr', 'classmethod', 'compile', 'complex', 'delattr',
    'dict', 'dir', 'divmod', 'enumerate', 'eval', 'exec', 'filter',
    'float', 'format', 'frozenset', 'getattr', 'globals', 'hasattr',
    'hash', 'help', 'hex', 'id', 'input', 'int', 'isinstance',
    'issubclass', 'iter', 'len', 'list', 'locals', 'map', 'max',
    'memoryview', 'min', 'next', 'object', 'oct', 'open', 'ord', 'pow',
    'print', 'property', 'range', 'repr', 'reversed', 'round', 'set',
    'setattr', 'slice', 'sorted', 'staticmethod', 'str', 'sum', 'super',
    'tuple', 'type', 'vars', 'zip', '__import__', '__name__', '__file__',
    '__doc__', '__package__', '__loader__', '__spec__', '__annotations__',
    '__builtins__', '__cached__', '__dict__', '__class__',
    # Common exception types
    'Exception', 'BaseException', 'StopIteration', 'GeneratorExit',
    'KeyboardInterrupt', 'SystemExit', 'ValueError', 'TypeError',
    'AttributeError', 'KeyError', 'IndexError', 'NameError',
    'RuntimeError', 'NotImplementedError', 'OSError', 'IOError',
    'ImportError', 'ModuleNotFoundError', 'FileNotFoundError',
    'ConnectionError', 'TimeoutError',
    # Common constants
    'True', 'False', 'None', 'NotImplemented', 'Ellipsis',
}

# Common typing names that may be imported conditionally
COMMON_TYPING_NAMES = {
    'Any', 'Dict', 'List', 'Set', 'Tuple', 'Optional', 'Union',
    'Callable', 'Iterable', 'Iterator', 'Sequence', 'Mapping',
    'MutableMapping', 'Type', 'TypeVar', 'Generic', 'Protocol',
    'Literal', 'Final', 'ClassVar', 'cast', 'overload', 'TYPE_CHECKING',
}


@dataclass
class FunctionScope:
    """Represents a function's scope with all defined and used names."""

    name: str                                      # Function name
    lineno: int                                    # Start line number
    qualified_name: str                            # e.g., "outer.inner"
    parameters: Set[str] = field(default_factory=set)  # Function parameters
    local_assignments: Set[str] = field(default_factory=set)  # Local variables
    local_imports: Set[str] = field(default_factory=set)  # Local imports
    names_used: Dict[str, int] = field(default_factory=dict)  # name -> first line
    comprehension_vars: Set[str] = field(default_factory=set)  # Comprehension vars
    nested_function_names: Set[str] = field(default_factory=set)  # Nested functions
    parent_scope: Optional['FunctionScope'] = None  # For closures

    def is_name_available(self, name: str) -> bool:
        """Check if a name is available in this scope or parent scopes."""
        if name in self.parameters:
            return True
        if name in self.local_assignments:
            return True
        if name in self.local_imports:
            return True
        if name in self.nested_function_names:
            return True
        # Check parent scope (closure)
        if self.parent_scope:
            return self.parent_scope.is_name_available(name)
        return False


class ImportAnalyzer(ast.NodeVisitor):
    """AST visitor that tracks imports and name usage to detect undefined names."""

    def __init__(self):
        self.module_level_names: Set[str] = set()
        self.type_checking_names: Set[str] = set()
        self.function_scopes: List[FunctionScope] = []
        self.current_scope: Optional[FunctionScope] = None
        self.in_type_checking: bool = False
        self.scope_stack: List[FunctionScope] = []

    def visit_Import(self, node: ast.Import) -> None:
        """Track import statements: import foo, import bar as baz."""
        for alias in node.names:
            # Use the alias if provided, otherwise the module name
            name = alias.asname if alias.asname else alias.name.split('.')[0]

            if self.in_type_checking:
                self.type_checking_names.add(name)
            elif self.current_scope:
                self.current_scope.local_imports.add(name)
            else:
                self.module_level_names.add(name)

        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Track from imports: from foo import bar, from baz import qux as q."""
        # Check if we're entering TYPE_CHECKING block
        if node.module == 'typing' and any(
            alias.name == 'TYPE_CHECKING' for alias in node.names
        ):
            self.module_level_names.add('TYPE_CHECKING')
            self.generic_visit(node)
            return

        for alias in node.names:
            if alias.name == '*':
                # We can't track star imports precisely
                continue

            # Use the alias if provided, otherwise the imported name
            name = alias.asname if alias.asname else alias.name

            if self.in_type_checking:
                self.type_checking_names.add(name)
            elif self.current_scope:
                self.current_scope.local_imports.add(name)
            else:
                self.module_level_names.add(name)

        self.generic_visit(node)

    def visit_If(self, node: ast.If) -> None:
        """Track if TYPE_CHECKING blocks."""
        # Check if this is "if TYPE_CHECKING:"
        is_type_checking_block = False
        if isinstance(node.test, ast.Name) and node.test.id == 'TYPE_CHECKING':
            is_type_checking_block = True

        if is_type_checking_block:
            old_in_type_checking = self.in_type_checking
            self.in_type_checking = True
            for child in node.body:
                self.visit(child)
            self.in_type_checking = old_in_type_checking

            # Visit else clause normally
            for child in node.orelse:
                self.visit(child)
        else:
            self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Track function definitions and create new scope."""
        # Determine qualified name
        if self.current_scope:
            qualified_name = f"{self.current_scope.qualified_name}.{node.name}"
            parent_scope = self.current_scope
            # Add this function name to parent's nested functions
            self.current_scope.nested_function_names.add(node.name)
        else:
            qualified_name = node.name
            parent_scope = None
            # Module-level function
            self.module_level_names.add(node.name)

        # Create new function scope
        scope = FunctionScope(
            name=node.name,
            lineno=node.lineno,
            qualified_name=qualified_name,
            parent_scope=parent_scope,
        )

        # Track parameters (including *args, **kwargs, annotations)
        for arg in node.args.args:
            scope.parameters.add(arg.arg)
        if node.args.vararg:
            scope.parameters.add(node.args.vararg.arg)
        if node.args.kwarg:
            scope.parameters.add(node.args.kwarg.arg)
        for arg in node.args.posonlyargs:
            scope.parameters.add(arg.arg)
        for arg in node.args.kwonlyargs:
            scope.parameters.add(arg.arg)

        # Add decorators to module-level if at module level
        if not self.current_scope:
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Name):
                    # Don't add decorator names to module level, they need to exist already
                    pass

        self.function_scopes.append(scope)
        old_scope = self.current_scope
        self.current_scope = scope
        self.scope_stack.append(scope)

        # Visit function body
        for child in node.body:
            self.visit(child)

        self.current_scope = old_scope
        self.scope_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Track async function definitions (same as regular functions)."""
        self.visit_FunctionDef(node)  # Reuse the same logic

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Track class definitions as available names."""
        if self.current_scope:
            self.current_scope.local_assignments.add(node.name)
        else:
            self.module_level_names.add(node.name)

        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        """Track name usage."""
        if self.current_scope and isinstance(node.ctx, ast.Load):
            # Only track names being loaded (used), not stored (assigned)
            if node.id not in self.current_scope.names_used:
                self.current_scope.names_used[node.id] = node.lineno

        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        """Track local assignments: a = 1, x, y = 2, 3."""
        if self.current_scope:
            for target in node.targets:
                self._extract_assignment_names(target, self.current_scope.local_assignments)
        else:
            # Module-level assignments
            for target in node.targets:
                self._extract_assignment_names(target, self.module_level_names)

        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        """Track annotated assignments: a: int = 1."""
        if self.current_scope:
            self._extract_assignment_names(node.target, self.current_scope.local_assignments)
        else:
            self._extract_assignment_names(node.target, self.module_level_names)

        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        """Track augmented assignments: a += 1."""
        if self.current_scope:
            self._extract_assignment_names(node.target, self.current_scope.local_assignments)
        else:
            self._extract_assignment_names(node.target, self.module_level_names)

        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        """Track for loop variables: for x in ..., for i, j in ..."""
        if self.current_scope:
            self._extract_assignment_names(node.target, self.current_scope.local_assignments)
        else:
            self._extract_assignment_names(node.target, self.module_level_names)

        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:
        """Track with statement aliases: with open() as f."""
        if self.current_scope:
            for item in node.items:
                if item.optional_vars:
                    self._extract_assignment_names(
                        item.optional_vars,
                        self.current_scope.local_assignments
                    )
        else:
            for item in node.items:
                if item.optional_vars:
                    self._extract_assignment_names(item.optional_vars, self.module_level_names)

        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        """Track exception handler names: except Exception as e."""
        if self.current_scope and node.name:
            self.current_scope.local_assignments.add(node.name)

        self.generic_visit(node)

    def visit_ListComp(self, node: ast.ListComp) -> None:
        """Track list comprehension scope."""
        self._visit_comprehension(node)

    def visit_SetComp(self, node: ast.SetComp) -> None:
        """Track set comprehension scope."""
        self._visit_comprehension(node)

    def visit_DictComp(self, node: ast.DictComp) -> None:
        """Track dict comprehension scope."""
        self._visit_comprehension(node)

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> None:
        """Track generator expression scope."""
        self._visit_comprehension(node)

    def _visit_comprehension(self, node) -> None:
        """Visit comprehension and track loop variables in nested scope."""
        # Comprehension variables are local to the comprehension
        # They don't leak to the enclosing scope in Python 3

        # For now, we'll track them in the current function scope
        # but mark them as comprehension vars
        if self.current_scope:
            for generator in node.generators:
                self._extract_assignment_names(
                    generator.target,
                    self.current_scope.comprehension_vars
                )

        self.generic_visit(node)

    def _extract_assignment_names(self, target, name_set: Set[str]) -> None:
        """Extract variable names from assignment target."""
        if isinstance(target, ast.Name):
            name_set.add(target.id)
        elif isinstance(target, (ast.Tuple, ast.List)):
            for elt in target.elts:
                self._extract_assignment_names(elt, name_set)
        elif isinstance(target, ast.Starred):
            self._extract_assignment_names(target.value, name_set)
        # Ignore attribute assignments (a.b = c) and subscript (a[b] = c)

    def is_name_available(self, name: str, scope: FunctionScope) -> bool:
        """Check if a name is available in the given scope."""
        # Check function scope first
        if scope.is_name_available(name):
            return True

        # Check comprehension vars
        if name in scope.comprehension_vars:
            return True

        # Check module-level names
        if name in self.module_level_names:
            return True

        # Check builtins
        if name in PYTHON_BUILTINS:
            return True

        # Check common typing names
        if name in COMMON_TYPING_NAMES:
            return True

        # TYPE_CHECKING names are NOT available at runtime
        # (they're only for static type checkers)

        return False

    def find_undefined_names(self) -> Dict[str, List[tuple]]:
        """
        Find undefined names in all function scopes.

        Returns:
            Dict mapping function qualified_name to list of (name, lineno) tuples
        """
        undefined = {}

        for scope in self.function_scopes:
            scope_undefined = []

            for name, lineno in scope.names_used.items():
                if not self.is_name_available(name, scope):
                    scope_undefined.append((name, lineno))

            if scope_undefined:
                undefined[scope.qualified_name] = sorted(scope_undefined, key=lambda x: x[1])

        return undefined


def analyze_file(file_path: Path) -> int:
    """
    Analyze a Python file for undefined names.

    Args:
        file_path: Path to Python file

    Returns:
        Exit code (0 = success, 1 = undefined names found)
    """
    print(f"Analyzing {file_path} for undefined names...")
    print("=" * 70)

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()

        tree = ast.parse(source, filename=str(file_path))

        analyzer = ImportAnalyzer()
        analyzer.visit(tree)

        undefined = analyzer.find_undefined_names()

        if not undefined:
            print("[PASS] No undefined names found!")
            print()
            return 0

        print(f"[FAIL] Found {sum(len(names) for names in undefined.values())} undefined names:")
        print()

        for func_name, names in sorted(undefined.items()):
            # Extract function line number from scope
            scope = next(s for s in analyzer.function_scopes if s.qualified_name == func_name)
            print(f"Function: {func_name} (line {scope.lineno})")

            for name, lineno in names:
                print(f"  - '{name}' used at line {lineno}")
            print()

        return 1

    except SyntaxError as e:
        print(f"[ERROR] Syntax error in {file_path}: {e}")
        return 1
    except Exception as e:
        print(f"[ERROR] Error analyzing {file_path}: {e}")
        import traceback
        traceback.print_exc()
        return 1


def main() -> int:
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/analyze_cli_imports.py <file.py>")
        print()
        print("Example:")
        print("  python scripts/analyze_cli_imports.py src/cli/main.py")
        return 1

    file_path = Path(sys.argv[1])

    if not file_path.exists():
        print(f"[ERROR] File not found: {file_path}")
        return 1

    if not file_path.is_file():
        print(f"[ERROR] Not a file: {file_path}")
        return 1

    if file_path.suffix != '.py':
        print(f"[ERROR] Not a Python file: {file_path}")
        return 1

    return analyze_file(file_path)


if __name__ == '__main__':
    sys.exit(main())
