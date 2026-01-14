"""
Manual test script for NamespaceValidator (without pytest).
"""

from src.namespace_validator import NamespaceValidator


def test_whitelist_exact_match():
    """Test exact namespace match passes in whitelist mode."""
    policy = {
        "mode": "whitelist",
        "allowed_namespaces": ["System", "System.IO", "Aspose.Words"],
        "blacklist": []
    }
    validator = NamespaceValidator(policy)

    code = """
using System;
using System.IO;
using Aspose.Words;

class MyClass {
    void Method() {
        Console.WriteLine("Hello");
    }
}
"""
    is_valid, violations = validator.validate(code)
    assert is_valid is True, f"Expected valid but got violations: {violations}"
    assert len(violations) == 0
    print("PASS: test_whitelist_exact_match")


def test_whitelist_wildcard():
    """Test wildcard patterns work correctly."""
    policy = {
        "mode": "whitelist",
        "allowed_namespaces": ["System", "Aspose.Words.*"],
        "blacklist": []
    }
    validator = NamespaceValidator(policy)

    code = """
using System;
using Aspose.Words.Tables;
using Aspose.Words.Drawing;
"""
    is_valid, violations = validator.validate(code)
    assert is_valid is True, f"Expected valid but got violations: {violations}"
    assert len(violations) == 0
    print("PASS: test_whitelist_wildcard")


def test_whitelist_violation():
    """Test non-allowed namespace fails in whitelist mode."""
    policy = {
        "mode": "whitelist",
        "allowed_namespaces": ["System", "Aspose.Words.*"],
        "blacklist": []
    }
    validator = NamespaceValidator(policy)

    code = """
using System;
using Aspose.Pdf;
using Aspose.Words.Tables;
"""
    is_valid, violations = validator.validate(code)
    assert is_valid is False, "Expected invalid but got valid"
    assert len(violations) == 1
    assert "Aspose.Pdf" in violations[0]
    print("PASS: test_whitelist_violation")


def test_extract_usings():
    """Test using directive extraction."""
    policy = {"mode": "permissive"}
    validator = NamespaceValidator(policy)

    code = """
using System;
using System.IO;
using Aspose.Words;

class MyClass {
    void Method() { }
}
"""
    usings = validator._extract_usings(code)
    assert len(usings) == 3, f"Expected 3 usings but got {len(usings)}: {usings}"
    assert "System" in usings
    assert "System.IO" in usings
    assert "Aspose.Words" in usings
    print("PASS: test_extract_usings passed")


def test_blacklist_mode():
    """Test blacklist mode."""
    policy = {
        "mode": "blacklist",
        "allowed_namespaces": [],
        "blacklist": ["Aspose.Pdf"]
    }
    validator = NamespaceValidator(policy)

    # Allowed code
    code1 = """
using System;
using Aspose.Words;
"""
    is_valid, violations = validator.validate(code1)
    assert is_valid is True, f"Expected valid but got violations: {violations}"
    print("PASS: test_blacklist_mode (allowed) passed")

    # Blacklisted code
    code2 = """
using System;
using Aspose.Pdf;
"""
    is_valid, violations = validator.validate(code2)
    assert is_valid is False, "Expected invalid but got valid"
    assert "Aspose.Pdf" in violations[0]
    print("PASS: test_blacklist_mode (blocked) passed")


def test_permissive_mode():
    """Test permissive mode allows everything."""
    policy = {
        "mode": "permissive",
        "allowed_namespaces": [],
        "blacklist": []
    }
    validator = NamespaceValidator(policy)

    code = """
using System;
using Aspose.Pdf;
using Aspose.Words;
using Some.Random.Namespace;
"""
    is_valid, violations = validator.validate(code)
    assert is_valid is True, f"Expected valid but got violations: {violations}"
    assert len(violations) == 0
    print("PASS: test_permissive_mode passed")


def test_integration_pdf_vs_words():
    """Test cross-domain namespace violation."""
    # PDF family policy
    pdf_policy = {
        "mode": "whitelist",
        "allowed_namespaces": [
            "Aspose.Pdf",
            "Aspose.Pdf.*",
            "System",
            "System.IO"
        ],
        "blacklist": []
    }
    pdf_validator = NamespaceValidator(pdf_policy)

    # Code using Words namespace in PDF family (violation)
    cross_domain_code = """
using System;
using Aspose.Pdf;
using Aspose.Words;

class Example {
    void Method() { }
}
"""
    is_valid, violations = pdf_validator.validate(cross_domain_code)
    assert is_valid is False, "Expected invalid for cross-domain usage"
    assert len(violations) == 1
    assert "Aspose.Words" in violations[0]
    print("PASS: test_integration_pdf_vs_words passed")


def test_policy_summary():
    """Test policy summary generation."""
    policy = {
        "mode": "whitelist",
        "allowed_namespaces": ["System", "Aspose.Words.*"],
        "blacklist": []
    }
    validator = NamespaceValidator(policy)
    summary = validator.get_policy_summary()
    assert "Whitelist mode" in summary
    assert "System" in summary
    print("PASS: test_policy_summary passed")


def run_all_tests():
    """Run all manual tests."""
    print("Running manual tests for NamespaceValidator...\n")

    tests = [
        test_whitelist_exact_match,
        test_whitelist_wildcard,
        test_whitelist_violation,
        test_extract_usings,
        test_blacklist_mode,
        test_permissive_mode,
        test_integration_pdf_vs_words,
        test_policy_summary
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"FAIL: {test.__name__} failed: {e}")
            failed += 1
        except Exception as e:
            print(f"FAIL: {test.__name__} error: {e}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed")
    print(f"{'='*60}")

    if failed == 0:
        print("PASS: All tests passed!")
        return 0
    else:
        print(f"FAIL: {failed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit(run_all_tests())
