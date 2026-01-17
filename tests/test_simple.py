#!/usr/bin/env python3
"""
Simple test to verify the code analysis improvements.
"""

import re

# Reproduce the API namespace mapping
API_NAMESPACE_MAP = {
    'Archive': 'Aspose.Zip',
    'ArchiveEntry': 'Aspose.Zip',
    'ArchiveEntrySettings': 'Aspose.Zip.Saving',
    'DeflateCompressionSettings': 'Aspose.Zip.Saving',
    'SevenZipArchive': 'Aspose.Zip.SevenZip',
    'RarArchive': 'Aspose.Zip.Rar',
}

def analyze_code(code):
    """Analyze code to detect APIs and structure."""
    has_usings = bool(re.search(r'^\s*using\s+[\w\.]+\s*;', code, re.MULTILINE))
    has_namespace = bool(re.search(r'\bnamespace\s+[\w\.]+', code))
    has_class = bool(re.search(r'\bclass\s+\w+', code))
    has_main = bool(re.search(r'\bstatic\s+(?:async\s+)?(?:void|Task|Task<int>|int)\s+Main\s*\(', code))
    is_async = bool(re.search(r'\bawait\s+', code)) or bool(re.search(r'\basync\s+', code))

    detected_apis = []
    for api_class in API_NAMESPACE_MAP.keys():
        patterns = [
            rf'\bnew\s+{api_class}\b',
            rf'\b{api_class}\.',
            rf'\b{api_class}<',
            rf'<{api_class}>',
            rf'\({api_class}\s+\w+\)',
        ]
        if any(re.search(pattern, code) for pattern in patterns):
            detected_apis.append(api_class)

    return {
        'has_usings': has_usings,
        'has_namespace': has_namespace,
        'has_class': has_class,
        'has_main': has_main,
        'is_async': is_async,
        'detected_apis': detected_apis,
    }

def categorize_errors(errors):
    """Categorize compilation errors."""
    ERROR_PATTERNS = {
        r"CS0246.*type.*'(\w+)'": "missing_type",  # Matches "could not be found" or "not found"
        r"CS0103.*name.*'(\w+)'.*does not exist": "undefined_variable",
        r"CS1002.*;.*expected": "missing_semicolon",
        r"CS1513.*}.*expected": "missing_brace",
        r"CS8803.*Top-level statements": "top_level_statements_error",
    }

    categorized = {}
    for error in errors:
        for pattern, category in ERROR_PATTERNS.items():
            if re.search(pattern, error, re.IGNORECASE):
                if category not in categorized:
                    categorized[category] = []
                categorized[category].append(error)
                break

    return categorized


print("=" * 70)
print("Testing Enhanced Code Analysis")
print("=" * 70)

# Test 1: Simple Archive usage
print("\n--- Test 1: Simple Archive Usage ---")
code1 = '''var archive = new Archive("input.zip");
archive.Save("output.zip");'''

result1 = analyze_code(code1)
print(f"Code: {code1[:40]}...")
print(f"Detected APIs: {result1['detected_apis']}")
print(f"Has class: {result1['has_class']}")
print(f"Has Main: {result1['has_main']}")
assert 'Archive' in result1['detected_apis'], "Failed to detect Archive API"
print("PASS - Archive API detected")

# Test 2: Multiple API types
print("\n--- Test 2: Multiple API Types ---")
code2 = '''var settings = new DeflateCompressionSettings();
using (var archive = new Archive(settings))
{
    var entry = archive.CreateEntry("file.txt", "source.txt");
}'''

result2 = analyze_code(code2)
print(f"Detected APIs: {result2['detected_apis']}")
assert 'Archive' in result2['detected_apis'], "Failed to detect Archive"
assert 'DeflateCompressionSettings' in result2['detected_apis'], "Failed to detect DeflateCompressionSettings"
print("PASS - Multiple APIs detected")

# Test 3: Code with class
print("\n--- Test 3: Class Detection ---")
code3 = '''public class ArchiveProcessor
{
    public void Process()
    {
        var archive = new Archive();
    }
}'''

result3 = analyze_code(code3)
print(f"Has class: {result3['has_class']}")
assert result3['has_class'], "Failed to detect class"
print("PASS - Class detected")

# Test 4: Complete code with namespace
print("\n--- Test 4: Namespace Detection ---")
code4 = '''using Aspose.Zip;
namespace MyApp
{
    class Program { }
}'''

result4 = analyze_code(code4)
print(f"Has namespace: {result4['has_namespace']}")
print(f"Has usings: {result4['has_usings']}")
assert result4['has_namespace'], "Failed to detect namespace"
assert result4['has_usings'], "Failed to detect usings"
print("PASS - Namespace and usings detected")

# Test 5: Error categorization
print("\n--- Test 5: Error Categorization ---")
errors = [
    "Program.cs(10,17): error CS0246: The type or namespace name 'Archive' could not be found",
    "Program.cs(12,9): error CS0103: The name 'myVar' does not exist in the current context",
    "Program.cs(15,20): error CS1002: ; expected",
    "Program.cs(18,1): error CS8803: Top-level statements must precede namespace and type declarations",
]

categorized = categorize_errors(errors)
print(f"Error categories: {list(categorized.keys())}")
assert 'missing_type' in categorized, "Failed to categorize missing_type"
assert 'undefined_variable' in categorized, "Failed to categorize undefined_variable"
assert 'missing_semicolon' in categorized, "Failed to categorize missing_semicolon"
assert 'top_level_statements_error' in categorized, "Failed to categorize top_level_statements_error"
print("PASS - All error categories detected correctly")

print("\n" + "=" * 70)
print("SUCCESS - All tests passed!")
print("=" * 70)
print("\nSummary of enhancements verified:")
print("+ API detection from code patterns")
print("+ Code structure analysis (class, Main, namespace, usings)")
print("+ Error pattern recognition and categorization")
print("+ Support for multiple Aspose.Zip API types")
