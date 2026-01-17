"""
Comprehensive test suite for NamespaceValidator.
Tests whitelist, blacklist, and permissive modes with various scenarios.
"""

import pytest
from src.namespace_validator import NamespaceValidator


class TestNamespaceValidatorWhitelist:
    """Tests for whitelist mode."""

    def test_whitelist_exact_match(self):
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
        assert is_valid is True
        assert len(violations) == 0

    def test_whitelist_wildcard(self):
        """Test wildcard patterns work correctly (e.g., Aspose.Words.*)."""
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
using Aspose.Words.Saving;

class MyClass {
    void Method() { }
}
"""
        is_valid, violations = validator.validate(code)
        assert is_valid is True
        assert len(violations) == 0

    def test_whitelist_violation(self):
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

class MyClass {
    void Method() { }
}
"""
        is_valid, violations = validator.validate(code)
        assert is_valid is False
        assert len(violations) == 1
        assert "Aspose.Pdf" in violations[0]

    def test_whitelist_multiple_violations(self):
        """Test multiple namespace violations are detected."""
        policy = {
            "mode": "whitelist",
            "allowed_namespaces": ["System"],
            "blacklist": []
        }
        validator = NamespaceValidator(policy)

        code = """
using System;
using Aspose.Pdf;
using Aspose.Words;
using Aspose.Cells;

class MyClass {
    void Method() { }
}
"""
        is_valid, violations = validator.validate(code)
        assert is_valid is False
        assert len(violations) == 3
        violation_text = ' '.join(violations)
        assert "Aspose.Pdf" in violation_text
        assert "Aspose.Words" in violation_text
        assert "Aspose.Cells" in violation_text

    def test_whitelist_base_namespace_and_wildcard(self):
        """Test that base namespace and wildcard both work."""
        policy = {
            "mode": "whitelist",
            "allowed_namespaces": ["Aspose.Words", "Aspose.Words.*"],
            "blacklist": []
        }
        validator = NamespaceValidator(policy)

        code = """
using Aspose.Words;
using Aspose.Words.Tables;

class MyClass {
    void Method() { }
}
"""
        is_valid, violations = validator.validate(code)
        assert is_valid is True
        assert len(violations) == 0


class TestNamespaceValidatorBlacklist:
    """Tests for blacklist mode."""

    def test_blacklist_allowed_namespace(self):
        """Test allowed namespace passes in blacklist mode."""
        policy = {
            "mode": "blacklist",
            "allowed_namespaces": [],
            "blacklist": ["Aspose.Pdf"]
        }
        validator = NamespaceValidator(policy)

        code = """
using System;
using Aspose.Words;
using Aspose.Cells;

class MyClass {
    void Method() { }
}
"""
        is_valid, violations = validator.validate(code)
        assert is_valid is True
        assert len(violations) == 0

    def test_blacklist_violation(self):
        """Test blacklisted namespace fails in blacklist mode."""
        policy = {
            "mode": "blacklist",
            "allowed_namespaces": [],
            "blacklist": ["Aspose.Pdf"]
        }
        validator = NamespaceValidator(policy)

        code = """
using System;
using Aspose.Pdf;
using Aspose.Words;

class MyClass {
    void Method() { }
}
"""
        is_valid, violations = validator.validate(code)
        assert is_valid is False
        assert len(violations) == 1
        assert "Aspose.Pdf" in violations[0]

    def test_blacklist_wildcard(self):
        """Test blacklist with wildcard blocks all sub-namespaces."""
        policy = {
            "mode": "blacklist",
            "allowed_namespaces": [],
            "blacklist": ["Aspose.Pdf.*"]
        }
        validator = NamespaceValidator(policy)

        code = """
using System;
using Aspose.Pdf.Text;
using Aspose.Pdf.Forms;
using Aspose.Words;

class MyClass {
    void Method() { }
}
"""
        is_valid, violations = validator.validate(code)
        assert is_valid is False
        assert len(violations) == 2
        violation_text = ' '.join(violations)
        assert "Aspose.Pdf.Text" in violation_text
        assert "Aspose.Pdf.Forms" in violation_text


class TestNamespaceValidatorPermissive:
    """Tests for permissive mode."""

    def test_permissive_allows_everything(self):
        """Test permissive mode allows all namespaces."""
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
using Aspose.Cells;
using Some.Random.Namespace;

class MyClass {
    void Method() { }
}
"""
        is_valid, violations = validator.validate(code)
        assert is_valid is True
        assert len(violations) == 0


class TestNamespaceExtraction:
    """Tests for using directive extraction."""

    def test_extract_usings_basic(self):
        """Test basic using directive extraction."""
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
        assert len(usings) == 3
        assert "System" in usings
        assert "System.IO" in usings
        assert "Aspose.Words" in usings

    def test_extract_usings_ignores_static(self):
        """Test that static usings are ignored."""
        policy = {"mode": "permissive"}
        validator = NamespaceValidator(policy)

        code = """
using System;
using static System.Math;
using Aspose.Words;

class MyClass {
    void Method() { }
}
"""
        usings = validator._extract_usings(code)
        assert len(usings) == 2
        assert "System" in usings
        assert "Aspose.Words" in usings
        assert "System.Math" not in usings

    def test_extract_usings_ignores_aliases(self):
        """Test that using aliases are ignored."""
        policy = {"mode": "permissive"}
        validator = NamespaceValidator(policy)

        code = """
using System;
using Word = Aspose.Words;
using Aspose.Pdf;

class MyClass {
    void Method() { }
}
"""
        usings = validator._extract_usings(code)
        assert len(usings) == 2
        assert "System" in usings
        assert "Aspose.Pdf" in usings

    def test_extract_usings_ignores_using_statements(self):
        """Test that using statements (not directives) are ignored."""
        policy = {"mode": "permissive"}
        validator = NamespaceValidator(policy)

        code = """
using System;
using System.IO;

class MyClass {
    void Method() {
        using (var stream = new FileStream("test.txt", FileMode.Open)) {
            // do something
        }
    }
}
"""
        usings = validator._extract_usings(code)
        assert len(usings) == 2
        assert "System" in usings
        assert "System.IO" in usings

    def test_extract_usings_nested_namespaces(self):
        """Test extraction of deeply nested namespaces."""
        policy = {"mode": "permissive"}
        validator = NamespaceValidator(policy)

        code = """
using System;
using Aspose.Words.Tables.PreferredWidth;
using Very.Deeply.Nested.Namespace.Here;

class MyClass {
    void Method() { }
}
"""
        usings = validator._extract_usings(code)
        assert len(usings) == 3
        assert "Aspose.Words.Tables.PreferredWidth" in usings
        assert "Very.Deeply.Nested.Namespace.Here" in usings


class TestIntegration:
    """Integration tests for real-world scenarios."""

    def test_integration_pdf_family(self):
        """Test PDF family config with whitelist."""
        policy = {
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
        validator = NamespaceValidator(policy)

        # Valid PDF code
        valid_code = """
using System;
using System.IO;
using Aspose.Pdf;
using Aspose.Pdf.Text;

class PdfExample {
    void CreatePdf() {
        Document doc = new Document();
        doc.Save("output.pdf");
    }
}
"""
        is_valid, violations = validator.validate(valid_code)
        assert is_valid is True
        assert len(violations) == 0

        # Invalid PDF code using Words namespace
        invalid_code = """
using System;
using Aspose.Pdf;
using Aspose.Words;

class PdfExample {
    void CreatePdf() {
        Document doc = new Document();
    }
}
"""
        is_valid, violations = validator.validate(invalid_code)
        assert is_valid is False
        assert len(violations) == 1
        assert "Aspose.Words" in violations[0]

    def test_integration_words_family(self):
        """Test Words family config with whitelist."""
        policy = {
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
        validator = NamespaceValidator(policy)

        # Invalid Words code using PDF namespace
        invalid_code = """
using System;
using Aspose.Words;
using Aspose.Pdf;

class WordsExample {
    void CreateDoc() {
        Document doc = new Document();
    }
}
"""
        is_valid, violations = validator.validate(invalid_code)
        assert is_valid is False
        assert len(violations) == 1
        assert "Aspose.Pdf" in violations[0]

    def test_policy_summary_whitelist(self):
        """Test policy summary for whitelist mode."""
        policy = {
            "mode": "whitelist",
            "allowed_namespaces": ["System", "Aspose.Words.*"],
            "blacklist": []
        }
        validator = NamespaceValidator(policy)
        summary = validator.get_policy_summary()
        assert "Whitelist mode" in summary
        assert "System" in summary
        assert "Aspose.Words.*" in summary

    def test_policy_summary_blacklist(self):
        """Test policy summary for blacklist mode."""
        policy = {
            "mode": "blacklist",
            "allowed_namespaces": [],
            "blacklist": ["Aspose.Pdf"]
        }
        validator = NamespaceValidator(policy)
        summary = validator.get_policy_summary()
        assert "Blacklist mode" in summary
        assert "Aspose.Pdf" in summary

    def test_policy_summary_permissive(self):
        """Test policy summary for permissive mode."""
        policy = {
            "mode": "permissive",
            "allowed_namespaces": [],
            "blacklist": []
        }
        validator = NamespaceValidator(policy)
        summary = validator.get_policy_summary()
        assert "Permissive mode" in summary
        assert "All namespaces allowed" in summary


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_code(self):
        """Test validation of empty code."""
        policy = {
            "mode": "whitelist",
            "allowed_namespaces": ["System"],
            "blacklist": []
        }
        validator = NamespaceValidator(policy)

        code = ""
        is_valid, violations = validator.validate(code)
        assert is_valid is True
        assert len(violations) == 0

    def test_code_without_usings(self):
        """Test validation of code without using directives."""
        policy = {
            "mode": "whitelist",
            "allowed_namespaces": ["System"],
            "blacklist": []
        }
        validator = NamespaceValidator(policy)

        code = """
class MyClass {
    void Method() {
        System.Console.WriteLine("Hello");
    }
}
"""
        is_valid, violations = validator.validate(code)
        assert is_valid is True
        assert len(violations) == 0

    def test_default_mode_is_whitelist(self):
        """Test that default mode is whitelist."""
        policy = {
            "allowed_namespaces": ["System"]
        }
        validator = NamespaceValidator(policy)
        assert validator.mode == "whitelist"

    def test_empty_policy(self):
        """Test validator with empty policy."""
        policy = {}
        validator = NamespaceValidator(policy)
        assert validator.mode == "whitelist"
        assert validator.allowed == []
        assert validator.blacklist == []

        # Should block everything in whitelist mode with empty allowed list
        code = """
using System;

class MyClass {
    void Method() { }
}
"""
        is_valid, violations = validator.validate(code)
        assert is_valid is False
        assert len(violations) == 1

    def test_wildcard_exact_match(self):
        """Test that Aspose.Words.* allows Aspose.Words itself."""
        policy = {
            "mode": "whitelist",
            "allowed_namespaces": ["Aspose.Words.*"],
            "blacklist": []
        }
        validator = NamespaceValidator(policy)

        # Aspose.Words should NOT be allowed by Aspose.Words.* wildcard
        code = """
using Aspose.Words;

class MyClass {
    void Method() { }
}
"""
        is_valid, violations = validator.validate(code)
        # Aspose.Words is NOT matched by Aspose.Words.* (wildcard requires dot)
        assert is_valid is False


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=src.namespace_validator", "--cov-report=term-missing"])
