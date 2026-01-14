"""
Integration test for Code Pattern Detector with Persistent Fix Service.

Validates that pattern detection is properly integrated and affects context inference decisions.
"""

import sys
sys.path.insert(0, 'src')

from code_pattern_detector import CodePatternDetector, CodePattern
from persistent_fix_service import PersistentFixService
from unittest.mock import MagicMock


def test_pattern_detector_integration():
    """Test that pattern detector is integrated into PersistentFixService"""

    # Create mock dependencies
    workspace = MagicMock()
    ollama = MagicMock()
    db = MagicMock()
    telemetry = MagicMock()
    family_config = {
        'persistent_fix': {
            'max_iterations': 10,
            'iterations_per_model': 3,
            'enable_context_inference': True
        }
    }

    # Create service
    service = PersistentFixService(
        workspace=workspace,
        ollama=ollama,
        db=db,
        telemetry=telemetry,
        family_config=family_config
    )

    # Verify pattern detector is initialized
    assert hasattr(service, 'pattern_detector')
    assert isinstance(service.pattern_detector, CodePatternDetector)

    print("✓ Pattern detector properly integrated into PersistentFixService")


def test_needs_context_with_patterns():
    """Test that _needs_context uses pattern detector correctly"""

    workspace = MagicMock()
    ollama = MagicMock()
    db = MagicMock()
    telemetry = MagicMock()
    family_config = {
        'persistent_fix': {
            'enable_context_inference': True
        }
    }

    service = PersistentFixService(
        workspace=workspace,
        ollama=ollama,
        db=db,
        telemetry=telemetry,
        family_config=family_config
    )

    # Test complete program (should NOT need context)
    complete_program = """
class Program {
    static void Main(string[] args) {
        Console.WriteLine("Test");
    }
}
"""
    assert not service._needs_context(complete_program), "Complete program should not need context"
    print("✓ Complete program: No context needed")

    # Test top-level statements (should NOT need context)
    top_level = """
var x = 10;
Console.WriteLine(x);
"""
    assert not service._needs_context(top_level), "Top-level statements should not need context"
    print("✓ Top-level statements: No context needed")

    # Test method only (SHOULD need context)
    method_only = """
public void ProcessData(string input) {
    Console.WriteLine(input);
}
"""
    assert service._needs_context(method_only), "Method-only code should need context"
    print("✓ Method-only: Context needed")

    # Test fragment (SHOULD need context)
    fragment = """
var x = 10;
"""
    assert service._needs_context(fragment), "Fragment should need context"
    print("✓ Fragment: Context needed")

    # Test class only (should NOT need context)
    class_only = """
public class MyClass {
    public void Method() {
        Console.WriteLine("Test");
    }
}
"""
    assert not service._needs_context(class_only), "Class-only code should not need context"
    print("✓ Class-only: No context needed")


def test_telemetry_logging():
    """Test that pattern detection is logged to telemetry"""

    workspace = MagicMock()
    ollama = MagicMock()
    db = MagicMock()
    telemetry = MagicMock()
    family_config = {
        'persistent_fix': {
            'enable_context_inference': True
        }
    }

    service = PersistentFixService(
        workspace=workspace,
        ollama=ollama,
        db=db,
        telemetry=telemetry,
        family_config=family_config
    )

    # Test that telemetry is called
    code = "var x = 10;"
    service._needs_context(code)

    # Verify telemetry was called with pattern metric
    telemetry.increment_metric.assert_called()
    call_args = [call[0][0] for call in telemetry.increment_metric.call_args_list]

    # Should have called with pattern_detected_* metric
    pattern_metrics = [arg for arg in call_args if arg.startswith('pattern_detected_')]
    assert len(pattern_metrics) > 0, "Pattern detection should be logged to telemetry"
    print(f"✓ Telemetry logged: {pattern_metrics[0]}")


if __name__ == '__main__':
    print("Testing Pattern Detector Integration...")
    print()

    test_pattern_detector_integration()
    print()

    test_needs_context_with_patterns()
    print()

    test_telemetry_logging()
    print()

    print("=" * 60)
    print("All integration tests passed!")
    print("=" * 60)
