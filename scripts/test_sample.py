"""Sample file with undefined names for testing."""

import os

def function_with_issues():
    """This function uses names that aren't imported."""
    # os is fine - imported at module level
    os.path.exists('test')

    # These are NOT imported - should be detected
    db = Database()
    result = query_data()

    return result


def function_with_lazy_import():
    """This function uses lazy imports correctly."""
    from pathlib import Path

    p = Path('test')
    return p


def function_with_type_checking():
    """Uses TYPE_CHECKING import incorrectly."""
    # This would fail at runtime because MyType is TYPE_CHECKING only
    obj = MyType()
    return obj


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mymodule import MyType
