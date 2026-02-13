"""Tests for BarCodeDriftValidator (DRIFT-04)."""

import pytest

from src.services.family_drift_validators.base import (
    FamilyDriftValidator,
    DriftValidationResult,
    DriftIssue,
)
from src.services.family_drift_validators.barcode_validator import (
    BarCodeDriftValidator,
)


class TestBarCodeDriftValidator:

    def setup_method(self):
        self.validator = BarCodeDriftValidator()

    # ── Barcode Type Preservation ─────────────────────────────────

    def test_barcode_type_preserved_valid(self):
        orig = 'var gen = new BarcodeGenerator(EncodeTypes.Code39, "12345");'
        fixed = """
        using Aspose.BarCode.Generation;
        var gen = new BarcodeGenerator(EncodeTypes.Code39, "12345");
        """
        result = self.validator.validate(orig, fixed, {})
        assert result.valid

    def test_barcode_type_changed_critical(self):
        orig = 'var gen = new BarcodeGenerator(EncodeTypes.Code39, "12345");'
        fixed = 'var gen = new BarcodeGenerator(EncodeTypes.DataMatrix, "12345");'
        result = self.validator.validate(orig, fixed, {})
        assert not result.valid
        assert any(i.severity == "critical" for i in result.issues)
        assert any(i.category == "barcode_type_change" for i in result.issues)

    def test_decode_type_changed_critical(self):
        orig = 'var reader = new BarCodeReader("test.png", DecodeType.Code39);'
        fixed = 'var reader = new BarCodeReader("test.png", DecodeType.QR);'
        result = self.validator.validate(orig, fixed, {})
        assert not result.valid
        assert any(i.category == "barcode_type_change" for i in result.issues)

    def test_barcode_type_added_not_removed_ok(self):
        orig = 'var gen = new BarcodeGenerator(EncodeTypes.Code39, "12345");'
        fixed = """
        var gen = new BarcodeGenerator(EncodeTypes.Code39, "12345");
        var gen2 = new BarcodeGenerator(EncodeTypes.DataMatrix, "67890");
        """
        result = self.validator.validate(orig, fixed, {})
        # Added types (not removed) is valid
        assert result.valid

    # ── Mode Detection ────────────────────────────────────────────

    def test_mode_change_generation_to_recognition(self):
        orig = """
        BarcodeGenerator gen = new BarcodeGenerator(EncodeTypes.Code39, "12345");
        gen.Save("barcode.png");
        """
        fixed = """
        BarCodeReader reader = new BarCodeReader("barcode.png", DecodeType.Code39);
        var results = reader.ReadBarCodes();
        """
        result = self.validator.validate(orig, fixed, {})
        assert not result.valid
        assert any(i.category == "api_mode_change" for i in result.issues)

    def test_same_mode_valid(self):
        orig = """
        BarcodeGenerator gen = new BarcodeGenerator(EncodeTypes.Code39, "12345");
        gen.Save("barcode.png");
        """
        fixed = """
        using Aspose.BarCode.Generation;
        BarcodeGenerator gen = new BarcodeGenerator(EncodeTypes.Code39, "12345");
        gen.Save("barcode.png", BarCodeImageFormat.Png);
        """
        result = self.validator.validate(orig, fixed, {})
        assert result.valid

    def test_both_mode_preserved(self):
        orig = """
        BarcodeGenerator gen = new BarcodeGenerator(EncodeTypes.Code39, "12345");
        gen.Save("barcode.png");
        BarCodeReader reader = new BarCodeReader("barcode.png");
        reader.ReadBarCodes();
        """
        fixed = """
        using Aspose.BarCode.Generation;
        BarcodeGenerator gen = new BarcodeGenerator(EncodeTypes.Code39, "12345");
        gen.Save("barcode.png", BarCodeImageFormat.Png);
        BarCodeReader reader = new BarCodeReader("barcode.png");
        var results = reader.ReadBarCodes();
        """
        result = self.validator.validate(orig, fixed, {})
        assert result.valid

    # ── Customization Preservation ────────────────────────────────

    def test_critical_property_removed_high(self):
        orig = """
        gen.Parameters.Barcode.BarColor = Color.Black;
        gen.Parameters.Barcode.BackColor = Color.White;
        gen.Save("out.png");
        """
        fixed = """
        gen.Parameters.Barcode.BarColor = Color.Black;
        gen.Save("out.png");
        """
        result = self.validator.validate(orig, fixed, {})
        # BackColor is in CRITICAL_PROPERTIES
        assert any(i.severity == "high" for i in result.issues)
        assert any(i.category == "critical_property_loss" for i in result.issues)

    def test_multiple_noncritical_properties_removed(self):
        orig = """
        gen.Height = 50;
        gen.Width = 200;
        gen.Margin = 10;
        gen.Save("out.png");
        """
        fixed = """
        gen.Save("out.png");
        """
        result = self.validator.validate(orig, fixed, {})
        assert any(i.severity == "high" for i in result.issues)
        assert any(i.category == "customization_loss" for i in result.issues)

    def test_single_noncritical_property_removed_ok(self):
        orig = """
        gen.Height = 50;
        gen.Save("out.png");
        """
        fixed = """
        gen.Save("out.png");
        """
        result = self.validator.validate(orig, fixed, {})
        # Only 1 non-critical property removed, under threshold
        assert not any(i.category == "customization_loss" for i in result.issues)

    def test_properties_preserved_valid(self):
        orig = """
        gen.Parameters.Barcode.BarColor = Color.Black;
        gen.Parameters.Barcode.BackColor = Color.White;
        gen.Save("out.png");
        """
        fixed = """
        using Aspose.Drawing;
        gen.Parameters.Barcode.BarColor = Aspose.Drawing.Color.Black;
        gen.Parameters.Barcode.BackColor = Aspose.Drawing.Color.White;
        gen.Save("out.png");
        """
        result = self.validator.validate(orig, fixed, {})
        assert result.valid

    # ── Edge Cases ────────────────────────────────────────────────

    def test_empty_code(self):
        result = self.validator.validate("", "", {})
        assert result.valid

    def test_no_barcode_apis(self):
        orig = 'Console.WriteLine("Hello World");'
        fixed = 'Console.WriteLine("Hello World!");'
        result = self.validator.validate(orig, fixed, {})
        assert result.valid

    def test_unknown_mode_no_issue(self):
        orig = 'Console.WriteLine("Hello");'
        fixed = 'Console.WriteLine("World");'
        result = self.validator.validate(orig, fixed, {})
        assert result.valid  # Both unknown - no mode change

    # ── get_critical_patterns ─────────────────────────────────────

    def test_get_critical_patterns(self):
        patterns = self.validator.get_critical_patterns()
        assert "DecodeType" in patterns
        assert "EncodeTypes" in patterns
        assert "BarcodeType" in patterns

    # ── DriftValidationResult ─────────────────────────────────────

    def test_result_to_dict(self):
        result = DriftValidationResult(
            valid=False,
            issues=[
                DriftIssue(
                    severity="critical",
                    category="barcode_type_change",
                    message="Barcode type changed"
                )
            ],
            drift_score=0.3,
        )
        d = result.to_dict()
        assert d["valid"] is False
        assert len(d["issues"]) == 1
        assert d["issues"][0]["severity"] == "critical"

    # ── Drift Score ───────────────────────────────────────────────

    def test_drift_score_increases_with_issues(self):
        orig = 'var gen = new BarcodeGenerator(EncodeTypes.Code39, "12345");'
        fixed = 'var reader = new BarCodeReader("test.png", DecodeType.DataMatrix);'
        result = self.validator.validate(orig, fixed, {})
        assert result.drift_score > 0

    def test_no_issues_zero_drift(self):
        code = 'var gen = new BarcodeGenerator(EncodeTypes.Code39, "12345");'
        result = self.validator.validate(code, code, {})
        assert result.drift_score == 0.0


class TestFamilyDriftValidatorBase:

    def test_abstract_cannot_instantiate(self):
        with pytest.raises(TypeError):
            FamilyDriftValidator()

    def test_drift_issue_to_dict(self):
        issue = DriftIssue(
            severity="critical",
            category="test",
            message="test message",
        )
        d = issue.to_dict()
        assert d["severity"] == "critical"
        assert d["category"] == "test"
