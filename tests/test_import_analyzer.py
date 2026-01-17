"""
Unit tests for the static import analyzer.

Tests cover all scope types and edge cases:
- Module-level imports
- Function-level imports (lazy imports)
- TYPE_CHECKING blocks
- Closures
- Comprehensions
- Nested functions
- Builtins
"""

import ast
import pytest
from pathlib import Path
import sys

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

from analyze_cli_imports import ImportAnalyzer, PYTHON_BUILTINS, COMMON_TYPING_NAMES


def analyze_code(code: str) -> ImportAnalyzer:
    """Helper to parse and analyze code."""
    tree = ast.parse(code)
    analyzer = ImportAnalyzer()
    analyzer.visit(tree)
    return analyzer


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
    assert undefined == {}


def test_undefined_in_function():
    """Names used but not imported should be detected as undefined."""
    code = """
def my_function():
    Database()  # Not imported anywhere
    result = query_data()  # Not defined
"""
    analyzer = analyze_code(code)
    undefined = analyzer.find_undefined_names()

    assert 'my_function' in undefined
    names = [name for name, _ in undefined['my_function']]
    assert 'Database' in names
    assert 'query_data' in names


def test_local_import():
    """Import inside function makes name available in that function."""
    code = """
def my_function():
    import json
    data = json.loads('{}')
"""
    analyzer = analyze_code(code)
    undefined = analyzer.find_undefined_names()
    assert undefined == {}


def test_local_import_from():
    """From imports inside function should work."""
    code = """
def my_function():
    from pathlib import Path
    p = Path('test')
"""
    analyzer = analyze_code(code)
    undefined = analyzer.find_undefined_names()
    assert undefined == {}


def test_function_parameter():
    """Function parameters should be available in function body."""
    code = """
def process(data, config=None):
    return data.strip() + str(config)
"""
    analyzer = analyze_code(code)
    undefined = analyzer.find_undefined_names()
    assert undefined == {}


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
    assert undefined == {}


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
    assert undefined == {}


def test_nested_closure():
    """Deeply nested closures should work."""
    code = """
def outer():
    a = 1

    def middle():
        b = 2

        def inner():
            return a + b

        return inner()

    return middle()
"""
    analyzer = analyze_code(code)
    undefined = analyzer.find_undefined_names()
    assert undefined == {}


def test_comprehension_scope():
    """Comprehension variables should be available in comprehension."""
    code = """
def process():
    result = [x * 2 for x in range(10)]
    return result
"""
    analyzer = analyze_code(code)
    undefined = analyzer.find_undefined_names()
    assert undefined == {}


def test_comprehension_nested():
    """Nested comprehensions should work."""
    code = """
def matrix():
    return [[x + y for x in range(3)] for y in range(3)]
"""
    analyzer = analyze_code(code)
    undefined = analyzer.find_undefined_names()
    assert undefined == {}


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

    assert 'my_function' in undefined
    names = [name for name, _ in undefined['my_function']]
    assert 'Database' in names


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
    assert undefined == {}


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
    assert undefined == {}


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
    assert undefined == {}


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
    assert undefined == {}


def test_exception_handler():
    """Exception handler names should be available in handler."""
    code = """
def safe_operation():
    try:
        risky_code()
    except Exception as e:
        print(e)
"""
    analyzer = analyze_code(code)
    undefined = analyzer.find_undefined_names()

    # risky_code is not defined, but e should be fine
    assert 'safe_operation' in undefined
    names = [name for name, _ in undefined['safe_operation']]
    assert 'risky_code' in names
    assert 'e' not in names  # e should be available in except block


def test_tuple_unpacking():
    """Tuple unpacking in assignments should work."""
    code = """
def unpack():
    a, b, c = (1, 2, 3)
    return a + b + c
"""
    analyzer = analyze_code(code)
    undefined = analyzer.find_undefined_names()
    assert undefined == {}


def test_starred_assignment():
    """Starred assignment should work."""
    code = """
def starred():
    a, *rest, b = [1, 2, 3, 4, 5]
    return a + b + len(rest)
"""
    analyzer = analyze_code(code)
    undefined = analyzer.find_undefined_names()
    assert undefined == {}


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
    assert undefined == {}


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
    assert undefined == {}


def test_from_import_as():
    """From import with 'as' should use the alias."""
    code = """
from pathlib import Path as P

def create_path():
    return P('test')
"""
    analyzer = analyze_code(code)
    undefined = analyzer.find_undefined_names()
    assert undefined == {}


def test_multiple_undefined():
    """Should detect multiple undefined names."""
    code = """
def complex_function():
    a = Undefined1()
    b = Undefined2()
    c = Undefined3()
    return a + b + c
"""
    analyzer = analyze_code(code)
    undefined = analyzer.find_undefined_names()

    assert 'complex_function' in undefined
    names = [name for name, _ in undefined['complex_function']]
    assert 'Undefined1' in names
    assert 'Undefined2' in names
    assert 'Undefined3' in names


def test_class_definitions():
    """Class definitions at module level should be available."""
    code = """
class MyClass:
    pass

def use_class():
    return MyClass()
"""
    analyzer = analyze_code(code)
    undefined = analyzer.find_undefined_names()
    assert undefined == {}


def test_mixed_scopes():
    """Complex code with multiple scope types."""
    code = """
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mymodule import TypeOnly

def outer(param1, param2):
    local_var = 10

    def inner():
        from json import loads
        data = loads('{}')

        # param1, param2 from outer
        # local_var from outer
        # data from local
        result = param1 + param2 + local_var + len(data)

        # os from module level
        os.path.exists('test')

        return result

    return inner()
"""
    analyzer = analyze_code(code)
    undefined = analyzer.find_undefined_names()
    assert undefined == {}


def test_augmented_assignment():
    """Augmented assignments (+=, etc.) should track variables."""
    code = """
def accumulate():
    total = 0
    total += 10
    total *= 2
    return total
"""
    analyzer = analyze_code(code)
    undefined = analyzer.find_undefined_names()
    assert undefined == {}


def test_annotated_assignment():
    """Annotated assignments should track variables."""
    code = """
def annotated():
    count: int = 0
    name: str = "test"
    return count + len(name)
"""
    analyzer = analyze_code(code)
    undefined = analyzer.find_undefined_names()
    assert undefined == {}


def test_async_function():
    """Async functions should work like regular functions."""
    code = """
import asyncio

async def fetch_data():
    await asyncio.sleep(1)
    return "data"
"""
    analyzer = analyze_code(code)
    undefined = analyzer.find_undefined_names()
    assert undefined == {}


def test_set_dict_comprehensions():
    """Set and dict comprehensions should work."""
    code = """
def comprehensions():
    s = {x for x in range(10)}
    d = {k: v for k, v in enumerate(range(5))}
    return s, d
"""
    analyzer = analyze_code(code)
    undefined = analyzer.find_undefined_names()
    assert undefined == {}


def test_generator_expression():
    """Generator expressions should work."""
    code = """
def generator():
    gen = (x * 2 for x in range(10))
    return list(gen)
"""
    analyzer = analyze_code(code)
    undefined = analyzer.find_undefined_names()
    assert undefined == {}


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
