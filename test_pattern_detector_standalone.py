"""
Standalone test for Code Pattern Detector without external dependencies.

Tests core pattern detection functionality.
"""

import sys
sys.path.insert(0, 'src')

from code_pattern_detector import CodePatternDetector, CodePattern


def test_all_patterns():
    """Test detection of all pattern types"""

    detector = CodePatternDetector()

    test_cases = [
        # Complete Program
        (
            """
class Program {
    static void Main(string[] args) {
        Console.WriteLine("Hello World");
    }
}
""",
            CodePattern.COMPLETE_PROGRAM,
            0.95,
            "Complete Program"
        ),

        # Top-level statements
        (
            """
using System;

var message = "Hello World";
Console.WriteLine(message);
return 0;
""",
            CodePattern.TOP_LEVEL_STATEMENTS,
            0.85,
            "Top-level Statements"
        ),

        # Minimal API
        (
            """
var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

app.MapGet("/", () => "Hello World");
app.Run();
""",
            CodePattern.MINIMAL_API,
            0.90,
            "Minimal API"
        ),

        # Class Only
        (
            """
public class MyClass {
    public string Name { get; set; }

    public void DoSomething() {
        Console.WriteLine(Name);
    }
}
""",
            CodePattern.CLASS_ONLY,
            0.80,
            "Class Only"
        ),

        # Method Only
        (
            """
public void ProcessData(string input) {
    Console.WriteLine(input);
}

private int Calculate(int x, int y) {
    return x + y;
}
""",
            CodePattern.METHOD_ONLY,
            0.75,
            "Method Only"
        ),

        # Fragment
        (
            """
var x = 10;
""",
            CodePattern.FRAGMENT,
            0.60,
            "Fragment"
        ),

        # With Comments
        (
            """
// This is a complete program
using System;

class Program {
    /* Main entry point */
    static void Main(string[] args) {
        Console.WriteLine("Hello World"); // Print message
    }
}
""",
            CodePattern.COMPLETE_PROGRAM,
            0.95,
            "Complete Program with Comments"
        ),

        # Empty Code
        (
            "",
            CodePattern.FRAGMENT,
            0.60,
            "Empty Code"
        ),

        # Namespace with Class
        (
            """
namespace MyApp {
    public class MyClass {
        public void Method() {
            Console.WriteLine("Test");
        }
    }
}
""",
            CodePattern.CLASS_ONLY,
            0.80,
            "Namespace with Class"
        ),

        # Complex Top-level with Control Flow
        (
            """
using System;

var numbers = new[] { 1, 2, 3, 4, 5 };
for (int i = 0; i < numbers.Length; i++) {
    if (numbers[i] % 2 == 0) {
        Console.WriteLine(numbers[i]);
    }
}
""",
            CodePattern.TOP_LEVEL_STATEMENTS,
            0.85,
            "Complex Top-level Statements"
        ),
    ]

    passed = 0
    failed = 0

    print("Running Pattern Detection Tests...")
    print("=" * 70)

    for code, expected_pattern, expected_confidence, description in test_cases:
        pattern, confidence = detector.detect(code)

        if pattern == expected_pattern and confidence == expected_confidence:
            print(f"[PASS] {description:40} [{pattern.value}] {confidence:.2f}")
            passed += 1
        else:
            print(f"[FAIL] {description:40} Expected: {expected_pattern.value} ({expected_confidence}), Got: {pattern.value} ({confidence})")
            failed += 1

    print("=" * 70)
    print(f"Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("[OK] All tests passed!")
        return True
    else:
        print(f"[X] {failed} tests failed")
        return False


def test_confidence_hierarchy():
    """Test that confidence scores follow expected hierarchy"""

    detector = CodePatternDetector()

    patterns_to_test = [
        ("class Program { static void Main() {} }", CodePattern.COMPLETE_PROGRAM),
        ("var builder = WebApplication.CreateBuilder(args); var app = builder.Build(); app.Run();", CodePattern.MINIMAL_API),
        ("var x = 10; Console.WriteLine(x);", CodePattern.TOP_LEVEL_STATEMENTS),
        ("class MyClass { public void Method() {} }", CodePattern.CLASS_ONLY),
        ("public void Method() { Console.WriteLine(\"Test\"); }", CodePattern.METHOD_ONLY),
        ("var x = 10;", CodePattern.FRAGMENT),
    ]

    confidences = []
    print("\nTesting Confidence Hierarchy...")
    print("=" * 70)

    for code, expected_pattern in patterns_to_test:
        pattern, confidence = detector.detect(code)
        confidences.append((pattern.value, confidence))
        status = "[OK]" if pattern == expected_pattern else "[X]"
        print(f"{status} {expected_pattern.value:30} confidence: {confidence:.2f}")

    # Check hierarchy (should be descending)
    print("=" * 70)

    if confidences[0][1] >= confidences[1][1] >= confidences[2][1] >= confidences[3][1] >= confidences[4][1] >= confidences[5][1]:
        print("[OK] Confidence hierarchy is correct (descending order)")
        return True
    else:
        print("[X] Confidence hierarchy is incorrect")
        return False


def test_context_inference_decisions():
    """Test which patterns should need context wrapping"""

    detector = CodePatternDetector()

    # Patterns that should NOT need context
    no_context_needed = [
        ("class Program { static void Main() {} }", "Complete Program"),
        ("var x = 10; Console.WriteLine(x);", "Top-level Statements"),
        ("var builder = WebApplication.CreateBuilder(args); var app = builder.Build(); app.Run();", "Minimal API"),
        ("class MyClass { public void Method() {} }", "Class Only"),
    ]

    # Patterns that SHOULD need context
    context_needed = [
        ("public void Method() {}", "Method Only"),
        ("var x = 10;", "Fragment"),
    ]

    print("\nTesting Context Inference Decisions...")
    print("=" * 70)

    all_passed = True

    print("Patterns that should NOT need context:")
    for code, description in no_context_needed:
        pattern, confidence = detector.detect(code)
        needs_context = pattern in [CodePattern.METHOD_ONLY, CodePattern.FRAGMENT]

        if not needs_context:
            print(f"  [OK] {description:30} [{pattern.value}]")
        else:
            print(f"  [X] {description:30} [{pattern.value}] (incorrectly needs context)")
            all_passed = False

    print("\nPatterns that SHOULD need context:")
    for code, description in context_needed:
        pattern, confidence = detector.detect(code)
        needs_context = pattern in [CodePattern.METHOD_ONLY, CodePattern.FRAGMENT]

        if needs_context:
            print(f"  [OK] {description:30} [{pattern.value}]")
        else:
            print(f"  [X] {description:30} [{pattern.value}] (incorrectly doesn't need context)")
            all_passed = False

    print("=" * 70)

    if all_passed:
        print("[OK] All context inference decisions are correct")
    else:
        print("[X] Some context inference decisions are incorrect")

    return all_passed


if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("CODE PATTERN DETECTOR - STANDALONE TEST SUITE")
    print("=" * 70)
    print()

    results = []

    results.append(("Pattern Detection", test_all_patterns()))
    print()

    results.append(("Confidence Hierarchy", test_confidence_hierarchy()))
    print()

    results.append(("Context Inference", test_context_inference_decisions()))
    print()

    print("=" * 70)
    print("FINAL RESULTS")
    print("=" * 70)

    for test_name, passed in results:
        status = "[OK] PASS" if passed else "[X] FAIL"
        print(f"{status:10} {test_name}")

    print("=" * 70)

    all_passed = all(passed for _, passed in results)
    if all_passed:
        print("\n[OK][OK][OK] ALL TESTS PASSED [OK][OK][OK]\n")
        sys.exit(0)
    else:
        print("\n[X][X][X] SOME TESTS FAILED [X][X][X]\n")
        sys.exit(1)
