"""
Test namespace validator with cross-domain snippet.
Simulates a Words snippet using PDF namespace (should fail validation).
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from namespace_validator import NamespaceValidator


def test_cross_domain_pdf_in_words():
    """Test Words family rejecting PDF namespace."""
    print("Test 1: Words family rejecting PDF namespace")
    print("="*60)

    # Words family policy (from config/families/words.json)
    words_policy = {
        "mode": "whitelist",
        "allowed_namespaces": [
            "Aspose.Words",
            "Aspose.Words.*",
            "System",
            "System.IO",
            "System.Text",
            "System.Collections.Generic",
            "System.Linq"
        ],
        "blacklist": []
    }

    validator = NamespaceValidator(words_policy)

    # Cross-domain code: Words snippet using Aspose.Pdf
    code = """
using System;
using System.IO;
using Aspose.Words;
using Aspose.Pdf;

class WordsExample
{
    void ProcessDocument()
    {
        // This should fail namespace validation
        Document doc = new Document();
    }
}
"""

    is_valid, violations = validator.validate(code)

    print(f"Code snippet:\n{code}")
    print(f"\nValidation result: {'VALID' if is_valid else 'INVALID'}")
    print(f"Violations: {violations}")

    assert is_valid is False, "Expected cross-domain namespace to fail validation"
    assert len(violations) == 1, f"Expected 1 violation but got {len(violations)}"
    assert "Aspose.Pdf" in violations[0], f"Expected Aspose.Pdf violation but got: {violations}"

    print("\nPASS: Cross-domain namespace correctly rejected")
    print("="*60)


def test_cross_domain_words_in_pdf():
    """Test PDF family rejecting Words namespace."""
    print("\nTest 2: PDF family rejecting Words namespace")
    print("="*60)

    # PDF family policy (from config/families/pdf.json)
    pdf_policy = {
        "mode": "whitelist",
        "allowed_namespaces": [
            "Aspose.Pdf",
            "Aspose.Pdf.*",
            "System",
            "System.IO",
            "System.Text",
            "System.Collections.Generic",
            "System.Linq"
        ],
        "blacklist": []
    }

    validator = NamespaceValidator(pdf_policy)

    # Cross-domain code: PDF snippet using Aspose.Words
    code = """
using System;
using Aspose.Pdf;
using Aspose.Words;

class PdfExample
{
    void ProcessPdf()
    {
        // This should fail namespace validation
        Document doc = new Document();
    }
}
"""

    is_valid, violations = validator.validate(code)

    print(f"Code snippet:\n{code}")
    print(f"\nValidation result: {'VALID' if is_valid else 'INVALID'}")
    print(f"Violations: {violations}")

    assert is_valid is False, "Expected cross-domain namespace to fail validation"
    assert len(violations) == 1, f"Expected 1 violation but got {len(violations)}"
    assert "Aspose.Words" in violations[0], f"Expected Aspose.Words violation but got: {violations}"

    print("\nPASS: Cross-domain namespace correctly rejected")
    print("="*60)


def test_valid_pdf_snippet():
    """Test valid PDF snippet passes validation."""
    print("\nTest 3: Valid PDF snippet passes validation")
    print("="*60)

    pdf_policy = {
        "mode": "whitelist",
        "allowed_namespaces": [
            "Aspose.Pdf",
            "Aspose.Pdf.*",
            "System",
            "System.IO",
            "System.Text",
            "System.Collections.Generic",
            "System.Linq"
        ],
        "blacklist": []
    }

    validator = NamespaceValidator(pdf_policy)

    # Valid PDF code
    code = """
using System;
using System.IO;
using Aspose.Pdf;
using Aspose.Pdf.Text;
using Aspose.Pdf.Forms;

class PdfExample
{
    void CreatePdf()
    {
        Document doc = new Document();
        doc.Save("output.pdf");
    }
}
"""

    is_valid, violations = validator.validate(code)

    print(f"Code snippet:\n{code}")
    print(f"\nValidation result: {'VALID' if is_valid else 'INVALID'}")
    print(f"Violations: {violations}")

    assert is_valid is True, f"Expected valid PDF code to pass but got violations: {violations}"
    assert len(violations) == 0, f"Expected no violations but got: {violations}"

    print("\nPASS: Valid PDF snippet correctly accepted")
    print("="*60)


def main():
    """Run all cross-domain tests."""
    print("\nCross-Domain Namespace Validator Tests")
    print("="*60)
    print()

    tests = [
        test_cross_domain_pdf_in_words,
        test_cross_domain_words_in_pdf,
        test_valid_pdf_snippet
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"\nFAIL: {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"\nERROR: {test.__name__}: {e}")
            failed += 1

    print(f"\n\n{'='*60}")
    print(f"Summary: {passed} passed, {failed} failed")
    print(f"{'='*60}")

    if failed == 0:
        print("\nPASS: All cross-domain namespace tests passed!")
        print("\nNamespace validator successfully prevents cross-domain API usage.")
        return 0
    else:
        print(f"\nFAIL: {failed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit(main())
