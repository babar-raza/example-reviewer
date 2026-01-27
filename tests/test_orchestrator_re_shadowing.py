"""
Regression test for orchestrator UnboundLocalError on 're' module.

This test ensures that the runtime phase in orchestrator.py does not attempt
to use 're' before it's imported, which would cause:
  UnboundLocalError: cannot access local variable 're' where it is not associated with a value

The bug was caused by a conditional `import re` inside the _run_runtime_phase function,
which made `re` a local variable, but the function also used `re.search()` earlier in the
same scope before the import statement was executed.

Fix: Removed the inner `import re` and rely only on module-level import.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path
from src.pipeline.orchestrator import PipelineOrchestrator
from src.core.models import ExampleStatus
from src.services.runtime_service import RuntimeResult


def test_orchestrator_re_not_shadowed():
    """
    Test that orchestrator can use 're' module without UnboundLocalError.

    This regression test verifies the fix for the issue where:
    1. Runtime phase encounters a compile error (CS####) in runtime output
    2. Code uses re.search() to detect compile errors (line ~1603)
    3. Later code had a conditional `import re` (was at line ~1707)
    4. Even later code uses re.search() to extract RAR filename (line ~1711)

    Before the fix, step 2 would raise UnboundLocalError because step 3's
    conditional `import re` made 're' a local variable for the entire function,
    but step 2 tried to use it before it was imported.

    Fix: Removed the inner `import re` and rely only on module-level import.
    """
    import src.pipeline.orchestrator as orch_module
    import inspect

    # Get the source code of _run_runtime_phase
    source = inspect.getsource(orch_module.PipelineOrchestrator._run_runtime_phase)

    # Verify there's no inner "import re" in the function
    # (allowing for whitespace but must be indented, not at module level)
    lines = source.split('\n')
    inner_import_re = [
        (i, line) for i, line in enumerate(lines)
        if 'import re' in line and line.strip().startswith('import re') and line.startswith(' ')
    ]

    assert len(inner_import_re) == 0, \
        f"Found {len(inner_import_re)} inner 'import re' statement(s) in _run_runtime_phase:\n" \
        + '\n'.join(f"  Line {i}: {line}" for i, line in inner_import_re) + \
        "\nThis causes UnboundLocalError. Should use module-level import only."


def test_re_module_available_at_module_level():
    """Verify that 're' is imported at module level in orchestrator.py"""
    import src.pipeline.orchestrator as orch_module

    # Verify 're' is available at module level
    assert hasattr(orch_module, 're'), "Module 're' should be imported at module level"
    assert orch_module.re.__name__ == 're', "Should be the actual 're' module"


def test_compile_error_pattern_detection():
    """
    Test that the compile error pattern (CS####) detection works.
    This is the code path that was failing with UnboundLocalError.
    """
    import re

    # Test the pattern used in orchestrator
    compile_error_pattern = r'\bCS\d{4}\b'

    # Test cases
    assert re.search(compile_error_pattern, "error CS0246: Type not found")
    assert re.search(compile_error_pattern, "CS1234 is an error")
    assert not re.search(compile_error_pattern, "This has no compile errors")
    assert not re.search(compile_error_pattern, "XCS0246 is not a match")  # Must be word boundary

    # Test findall pattern
    runtime_output = """
    error CS0246: The type or namespace name 'Foo' could not be found
    error CS0103: The name 'bar' does not exist
    """
    errors = re.findall(r'error CS\d{4}:.*', runtime_output)
    assert len(errors) == 2
    assert "CS0246" in errors[0]
    assert "CS0103" in errors[1]


def test_rar_filename_extraction_pattern():
    """
    Test the RAR filename extraction pattern.
    This is the later code path that was causing 're' to be shadowed.
    """
    import re

    # Test the pattern used for RAR file extraction
    # Note: The pattern expects quoted filenames or simple filenames without spaces
    test_cases = [
        ("Could not find 'archive.rar' in directory", "archive.rar"),
        ('Missing file "data.rar" required', "data.rar"),
        ("'file.rar' for processing", "file.rar"),  # Quoted version
        ("'path/to/nested.rar' not found", "nested.rar"),  # Full path - extracts basename
    ]

    for error_text, expected_filename in test_cases:
        rar_match = re.search(r'(["\']?)([^"\']+\.rar)\1', error_text, re.IGNORECASE)
        assert rar_match is not None, f"Should match RAR file in: {error_text}"
        extracted = rar_match.group(2).replace('\\', '/').split('/')[-1]
        assert extracted == expected_filename, \
            f"Expected {expected_filename}, got {extracted} from {error_text}"
