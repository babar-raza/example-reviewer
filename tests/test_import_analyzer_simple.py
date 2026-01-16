"""
Simple unit tests for the static import analyzer (no pytest required).

Run with: python tests/test_import_analyzer_simple.py
"""

import ast
from pathlib import Path
import sys

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

from analyze_cli_imports import ImportAnalyzer


def analyze_code(code: str) -> ImportAnalyzer:
    """Helper to parse and analyze code."""
    tree = ast.parse(code)
    analyzer = ImportAnalyzer()
    analyzer.visit(tree)
    return analyzer


def run_test(test_name: str, test_func):
    """Run a single test and report results."""
    try:
        test_func()
        print(f"[PASS] {test_name}")
        return True
    except AssertionError as e:
        print(f"[FAIL] {test_name}: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] {test_name}: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_module_level_import():
    """Module-level imports should be available in functions."""
    code = """
import os
import sys

def my_function():
    os.path.exists('test')
    sys.exit(0)
"""
    analyzer = analyze_code(code)
    undefined = analyzer.find_undefined_names()
    assert undefined == {}, f"Expected no undefined names, got {undefined}"


def test_undefined_in_function():
    """Names used but not imported should be detected as undefined."""
    code = """
def my_function():
    Database()  # Not imported anywhere
    result = query_data()  # Not defined
"""
    analyzer = analyze_code(code)
    undefined = analyzer.find_undefined_names()

    assert 'my_function' in undefined, "Expected undefined names in my_function"
    names = [name for name, _ in undefined['my_function']]
    assert 'Database' in names, "Expected Database to be undefined"
    assert 'query_data' in names, "Expected query_data to be undefined"


def test_local_import():
    """Import inside function makes name available in that function."""
    code = """
def my_function():
    import json
    data = json.loads('{}')
"""
    analyzer = analyze_code(code)
    undefined = analyzer.find_undefined_names()
    assert undefined == {}, f"Expected no undefined names, got {undefined}"


def test_function_parameter():
    """Function parameters should be available in function body."""
    code = """
def process(data, config=None):
    return data.strip() + str(config)
"""
    analyzer = analyze_code(code)
    undefined = analyzer.find_undefined_names()
    assert undefined == {}, f"Expected no undefined names, got {undefined}"


def test_local_assignment():
    """Local assignments should be available in function."""
    code = """
def calculate():
    x = 10
    y = 20
    return x + y
"""
    analyzer = analyze_code(code)
    undefined = analyzer.find_undefined_names()
    assert undefined == {}, f"Expected no undefined names, got {undefined}"


def test_closure_access():
    """Inner function should access outer function variables."""
    code = """
def outer():
    x = 10

    def inner():
        return x + 5

    return inner()
"""
    analyzer = analyze_code(code)
    undefined = analyzer.find_undefined_names()
    assert undefined == {}, f"Expected no undefined names, got {undefined}"


def test_comprehension_scope():
    """Comprehension variables should be available in comprehension."""
    code = """
def process():
    result = [x * 2 for x in range(10)]
    return result
"""
    analyzer = analyze_code(code)
    undefined = analyzer.find_undefined_names()
    assert undefined == {}, f"Expected no undefined names, got {undefined}"


def test_type_checking_runtime():
    """TYPE_CHECKING imports should not be available at runtime."""
    code = """
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mypackage import Database

def my_function():
    db = Database()  # Should be undefined at runtime
"""
    analyzer = analyze_code(code)
    undefined = analyzer.find_undefined_names()

    assert 'my_function' in undefined, "Expected undefined names in my_function"
    names = [name for name, _ in undefined['my_function']]
    assert 'Database' in names, "Expected Database to be undefined at runtime"


def test_builtin_names():
    """Python builtins should not trigger false positives."""
    code = """
def process_file():
    with open('test.txt') as f:
        data = f.read()

    result = len(data)
    print(result)

    items = list(range(10))
    total = sum(items)

    return isinstance(total, int)
"""
    analyzer = analyze_code(code)
    undefined = analyzer.find_undefined_names()
    assert undefined == {}, f"Expected no undefined names, got {undefined}"


def test_nested_function_name():
    """Nested function names should be available in parent scope."""
    code = """
def outer():
    def inner():
        return 42

    result = inner()
    return result
"""
    analyzer = analyze_code(code)
    undefined = analyzer.find_undefined_names()
    assert undefined == {}, f"Expected no undefined names, got {undefined}"


def test_for_loop_variable():
    """For loop variables should be available in function."""
    code = """
def iterate():
    for i in range(10):
        print(i)

    for x, y in [(1, 2), (3, 4)]:
        print(x + y)
"""
    analyzer = analyze_code(code)
    undefined = analyzer.find_undefined_names()
    assert undefined == {}, f"Expected no undefined names, got {undefined}"


def test_with_statement_alias():
    """With statement aliases should be available."""
    code = """
def read_file():
    with open('test.txt') as f:
        content = f.read()
    return content
"""
    analyzer = analyze_code(code)
    undefined = analyzer.find_undefined_names()
    assert undefined == {}, f"Expected no undefined names, got {undefined}"


def test_typing_names():
    """Common typing names should not trigger false positives."""
    code = """
def typed_function(data: Dict[str, Any]) -> Optional[List[str]]:
    if not data:
        return None
    return list(data.keys())
"""
    analyzer = analyze_code(code)
    undefined = analyzer.find_undefined_names()
    assert undefined == {}, f"Expected no undefined names, got {undefined}"


def test_import_as():
    """Import with 'as' should use the alias."""
    code = """
import numpy as np

def compute():
    arr = np.array([1, 2, 3])
    return arr
"""
    analyzer = analyze_code(code)
    undefined = analyzer.find_undefined_names()
    assert undefined == {}, f"Expected no undefined names, got {undefined}"


def test_from_import_as():
    """From import with 'as' should use the alias."""
    code = """
from pathlib import Path as P

def create_path():
    return P('test')
"""
    analyzer = analyze_code(code)
    undefined = analyzer.find_undefined_names()
    assert undefined == {}, f"Expected no undefined names, got {undefined}"


def main():
    """Run all tests."""
    print("=" * 70)
    print("Running Import Analyzer Unit Tests")
    print("=" * 70)
    print()

    tests = [
        ("Module level import", test_module_level_import),
        ("Undefined in function", test_undefined_in_function),
        ("Local import", test_local_import),
        ("Function parameter", test_function_parameter),
        ("Local assignment", test_local_assignment),
        ("Closure access", test_closure_access),
        ("Comprehension scope", test_comprehension_scope),
        ("TYPE_CHECKING runtime", test_type_checking_runtime),
        ("Builtin names", test_builtin_names),
        ("Nested function name", test_nested_function_name),
        ("For loop variable", test_for_loop_variable),
        ("With statement alias", test_with_statement_alias),
        ("Typing names", test_typing_names),
        ("Import as", test_import_as),
        ("From import as", test_from_import_as),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        if run_test(test_name, test_func):
            passed += 1
        else:
            failed += 1

    print()
    print("=" * 70)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 70)

    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
