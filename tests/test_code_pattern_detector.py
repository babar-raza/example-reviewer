"""
Tests for Code Pattern Detector

Verifies pattern detection for all C# code styles:
- Complete programs
- Top-level statements
- Minimal APIs
- Class-only code
- Method-only code
- Fragments
"""

import pytest
from src.code_pattern_detector import CodePatternDetector, CodePattern


@pytest.fixture
def detector():
    """Create a detector instance for tests"""
    return CodePatternDetector()


def test_complete_program(detector):
    """Test detection of complete Program class with Main method"""
    code = """
using System;

class Program
{
    static void Main(string[] args)
    {
        Console.WriteLine("Hello World");
    }
}
"""
    pattern, confidence = detector.detect(code)
    assert pattern == CodePattern.COMPLETE_PROGRAM
    assert confidence == 0.95


def test_top_level_statements(detector):
    """Test detection of C# 9+ top-level statements"""
    code = """
using System;

var message = "Hello World";
Console.WriteLine(message);
return 0;
"""
    pattern, confidence = detector.detect(code)
    assert pattern == CodePattern.TOP_LEVEL_STATEMENTS
    assert confidence == 0.85


def test_minimal_api(detector):
    """Test detection of ASP.NET minimal API pattern"""
    code = """
using Microsoft.AspNetCore.Builder;

var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

app.MapGet("/", () => "Hello World");
app.Run();
"""
    pattern, confidence = detector.detect(code)
    assert pattern == CodePattern.MINIMAL_API
    assert confidence == 0.90


def test_class_only(detector):
    """Test detection of class-only code"""
    code = """
using System;

public class MyClass
{
    public string Name { get; set; }

    public void DoSomething()
    {
        Console.WriteLine(Name);
    }
}
"""
    pattern, confidence = detector.detect(code)
    assert pattern == CodePattern.CLASS_ONLY
    assert confidence == 0.80


def test_method_only(detector):
    """Test detection of standalone method"""
    code = """
public void ProcessData(string input)
{
    Console.WriteLine(input);
}

private int Calculate(int x, int y)
{
    return x + y;
}
"""
    pattern, confidence = detector.detect(code)
    assert pattern == CodePattern.METHOD_ONLY
    assert confidence == 0.75


def test_fragment(detector):
    """Test detection of incomplete code fragment"""
    code = """
var x = 10;
"""
    pattern, confidence = detector.detect(code)
    assert pattern == CodePattern.FRAGMENT
    assert confidence == 0.60


def test_with_comments(detector):
    """Test handling of code with comments"""
    code = """
// This is a complete program
using System;

class Program
{
    /* Main entry point */
    static void Main(string[] args)
    {
        Console.WriteLine("Hello World"); // Print message
    }
}
"""
    pattern, confidence = detector.detect(code)
    assert pattern == CodePattern.COMPLETE_PROGRAM
    assert confidence == 0.95


def test_confidence_scores(detector):
    """Test that confidence scores follow expected hierarchy"""

    # Complete program has highest confidence
    complete_program = """
class Program {
    static void Main(string[] args) {
        Console.WriteLine("Test");
    }
}
"""
    _, conf_complete = detector.detect(complete_program)

    # Minimal API is high confidence
    minimal_api = """
var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();
app.Run();
"""
    _, conf_minimal = detector.detect(minimal_api)

    # Top-level statements
    top_level = """
var x = 10;
Console.WriteLine(x);
"""
    _, conf_top_level = detector.detect(top_level)

    # Class only
    class_only = """
class MyClass {
    public void Method() { }
}
"""
    _, conf_class = detector.detect(class_only)

    # Method only
    method_only = """
public void Method() {
    Console.WriteLine("Test");
}
"""
    _, conf_method = detector.detect(method_only)

    # Fragment has lowest confidence
    fragment = """
var x = 10;
"""
    _, conf_fragment = detector.detect(fragment)

    # Verify hierarchy
    assert conf_complete >= conf_minimal >= conf_top_level >= conf_class >= conf_method >= conf_fragment
    assert conf_complete == 0.95
    assert conf_fragment == 0.60


def test_empty_code(detector):
    """Test handling of empty code"""
    pattern, confidence = detector.detect("")
    assert pattern == CodePattern.FRAGMENT
    assert confidence == 0.60

    pattern, confidence = detector.detect("   \n  \n  ")
    assert pattern == CodePattern.FRAGMENT
    assert confidence == 0.60


def test_namespace_with_class(detector):
    """Test code with namespace wrapper"""
    code = """
namespace MyApp
{
    public class MyClass
    {
        public void Method()
        {
            Console.WriteLine("Test");
        }
    }
}
"""
    pattern, confidence = detector.detect(code)
    assert pattern == CodePattern.CLASS_ONLY
    assert confidence == 0.80


def test_complex_top_level_statements(detector):
    """Test complex top-level statements with control flow"""
    code = """
using System;

var numbers = new[] { 1, 2, 3, 4, 5 };
for (int i = 0; i < numbers.Length; i++)
{
    if (numbers[i] % 2 == 0)
    {
        Console.WriteLine(numbers[i]);
    }
}
"""
    pattern, confidence = detector.detect(code)
    assert pattern == CodePattern.TOP_LEVEL_STATEMENTS
    assert confidence == 0.85


def test_multiline_comment_removal(detector):
    """Test that multiline comments are properly removed"""
    code = """
/*
 * This looks like it might have class Program
 * but it's just a comment
 */
var x = 10;
Console.WriteLine(x);
"""
    pattern, confidence = detector.detect(code)
    assert pattern == CodePattern.TOP_LEVEL_STATEMENTS
    assert confidence == 0.85


def test_method_with_various_modifiers(detector):
    """Test method detection with different modifiers"""
    test_cases = [
        "public void Method() { }",
        "private int GetValue() { return 0; }",
        "protected string GetName() { return \"\"; }",
        "internal void Process() { }",
        "static void StaticMethod() { }",
    ]

    for code in test_cases:
        pattern, confidence = detector.detect(code)
        assert pattern == CodePattern.METHOD_ONLY
        assert confidence == 0.75
