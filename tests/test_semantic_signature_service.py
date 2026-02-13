"""Tests for SemanticSignatureService (DRIFT-01)."""

import pytest

from src.services.semantic_signature_service import (
    SemanticSignatureService,
    SemanticSignature,
    SignatureDrift,
    CRITICAL_ENUM_FAMILIES,
)


class FakeCatalog:
    """Minimal catalog stub for testing."""

    is_loaded = True

    def __init__(self, enums=None, types=None):
        self._enums = enums or {}
        self._types = types or []

    def get_all_enums(self):
        return self._enums

    def get_all_types(self):
        return self._types


# ── Barcode catalog stub ──────────────────────────────────────────

BARCODE_ENUMS = {
    "DecodeType": ["Code39", "DataMatrix", "QR", "Code128", "Pdf417"],
    "EncodeTypes": ["Code39", "DataMatrix", "QR", "Code128", "Pdf417"],
    "BarcodeQualityMode": ["Default", "Fast", "Normal"],
}

BARCODE_TYPES = [
    "BarcodeGenerator", "BarCodeReader", "BarCodeResult",
    "BarcodeParameters", "ComplexBarcode",
]


def make_barcode_service():
    catalog = FakeCatalog(enums=BARCODE_ENUMS, types=BARCODE_TYPES)
    return SemanticSignatureService(family="barcode", api_catalog=catalog)


def make_empty_service():
    catalog = FakeCatalog()
    return SemanticSignatureService(family="test", api_catalog=catalog)


# ══════════════════════════════════════════════════════════════════
# Extraction Tests
# ══════════════════════════════════════════════════════════════════

class TestExtractSignature:

    def test_extract_enum_values(self):
        svc = make_barcode_service()
        code = 'var gen = new BarcodeGenerator(EncodeTypes.Code39, "12345");'
        sig = svc.extract_signature(code)
        assert "EncodeTypes" in sig.enum_values
        assert "Code39" in sig.enum_values["EncodeTypes"]

    def test_extract_multiple_enums(self):
        svc = make_barcode_service()
        code = """
        var gen = new BarcodeGenerator(EncodeTypes.DataMatrix, "data");
        var reader = new BarCodeReader("test.png", DecodeType.DataMatrix);
        """
        sig = svc.extract_signature(code)
        assert "EncodeTypes" in sig.enum_values
        assert "DataMatrix" in sig.enum_values["EncodeTypes"]
        assert "DecodeType" in sig.enum_values
        assert "DataMatrix" in sig.enum_values["DecodeType"]

    def test_extract_constructor_types(self):
        svc = make_barcode_service()
        code = 'var gen = new BarcodeGenerator(EncodeTypes.Code39, "12345");'
        sig = svc.extract_signature(code)
        assert "BarcodeGenerator" in sig.constructor_types

    def test_extract_method_calls(self):
        svc = make_barcode_service()
        code = """
        gen.Save("barcode.png", BarCodeImageFormat.Png);
        var results = reader.ReadBarCodes();
        """
        sig = svc.extract_signature(code)
        assert "Save" in sig.method_calls
        assert "ReadBarCodes" in sig.method_calls

    def test_extract_property_assignments(self):
        svc = make_barcode_service()
        code = """
        gen.Parameters.Barcode.BarColor = Color.Black;
        gen.Parameters.Barcode.BackColor = Color.White;
        gen.Parameters.Barcode.XDimension.Pixels = 2;
        """
        sig = svc.extract_signature(code)
        assert "BarColor" in sig.property_assignments
        assert "BackColor" in sig.property_assignments

    def test_empty_code(self):
        svc = make_barcode_service()
        sig = svc.extract_signature("")
        assert sig.enum_values == {}
        assert sig.method_calls == []
        assert sig.constructor_types == []
        assert sig.property_assignments == {}

    def test_comments_stripped(self):
        svc = make_barcode_service()
        code = """
        // var gen = new BarcodeGenerator(EncodeTypes.Code39, "old");
        var gen = new BarcodeGenerator(EncodeTypes.DataMatrix, "new");
        /* EncodeTypes.QR is not used here */
        """
        sig = svc.extract_signature(code)
        assert "EncodeTypes" in sig.enum_values
        # Only DataMatrix should be extracted (others in comments)
        assert "DataMatrix" in sig.enum_values["EncodeTypes"]
        # Code39 is in comment, should NOT appear
        assert "Code39" not in sig.enum_values.get("EncodeTypes", [])

    def test_non_catalog_enums_ignored(self):
        svc = make_barcode_service()
        code = 'var level = CompressionLevel.Optimal;'  # Not a barcode enum
        sig = svc.extract_signature(code)
        assert "CompressionLevel" not in sig.enum_values

    def test_non_catalog_types_ignored(self):
        svc = make_barcode_service()
        code = 'var obj = new SomeFakeClass();'
        sig = svc.extract_signature(code)
        assert "SomeFakeClass" not in sig.constructor_types


# ══════════════════════════════════════════════════════════════════
# Comparison Tests
# ══════════════════════════════════════════════════════════════════

class TestCompareSignatures:

    def test_identical_signatures(self):
        svc = make_barcode_service()
        code = 'var gen = new BarcodeGenerator(EncodeTypes.Code39, "12345");'
        sig = svc.extract_signature(code)
        drift = svc.compare_signatures(sig, sig)
        assert drift.drift_score == 0.0
        assert not drift.critical
        assert drift.enum_changes == {}

    def test_critical_enum_change(self):
        svc = make_barcode_service()
        orig = 'var gen = new BarcodeGenerator(EncodeTypes.Code39, "12345");'
        fixed = 'var gen = new BarcodeGenerator(EncodeTypes.DataMatrix, "12345");'
        orig_sig = svc.extract_signature(orig)
        fixed_sig = svc.extract_signature(fixed)
        drift = svc.compare_signatures(orig_sig, fixed_sig)
        assert drift.critical
        assert "EncodeTypes" in drift.enum_changes
        assert drift.drift_score >= 0.8

    def test_non_critical_enum_change_with_override(self):
        svc = make_barcode_service()
        orig = 'var gen = new BarcodeGenerator(EncodeTypes.Code39, "12345");'
        fixed = 'var gen = new BarcodeGenerator(EncodeTypes.DataMatrix, "12345");'
        orig_sig = svc.extract_signature(orig)
        fixed_sig = svc.extract_signature(fixed)
        # Pass empty critical_enums list = no critical detection
        drift = svc.compare_signatures(orig_sig, fixed_sig, critical_enums=[])
        assert not drift.critical
        assert drift.drift_score >= 0.8  # Still has drift score

    def test_constructor_type_change(self):
        svc = make_barcode_service()
        orig = 'var gen = new BarcodeGenerator(EncodeTypes.Code39, "12345");'
        fixed = 'var reader = new BarCodeReader("test.png", DecodeType.Code39);'
        orig_sig = svc.extract_signature(orig)
        fixed_sig = svc.extract_signature(fixed)
        drift = svc.compare_signatures(orig_sig, fixed_sig)
        assert len(drift.type_changes) > 0
        assert drift.drift_score >= 0.7

    def test_property_removal(self):
        svc = make_barcode_service()
        orig = """
        gen.Parameters.Barcode.BarColor = Color.Black;
        gen.Parameters.Barcode.BackColor = Color.White;
        gen.Save("out.png");
        """
        fixed = """
        gen.Parameters.Barcode.BarColor = Color.Black;
        gen.Save("out.png");
        """
        orig_sig = svc.extract_signature(orig)
        fixed_sig = svc.extract_signature(fixed)
        drift = svc.compare_signatures(orig_sig, fixed_sig)
        assert "BackColor" in drift.property_changes.get("removed", [])
        assert drift.drift_score > 0

    def test_adding_using_no_drift(self):
        svc = make_barcode_service()
        orig = 'var gen = new BarcodeGenerator(EncodeTypes.Code39, "12345");'
        fixed = """
        using Aspose.BarCode.Generation;
        var gen = new BarcodeGenerator(EncodeTypes.Code39, "12345");
        """
        orig_sig = svc.extract_signature(orig)
        fixed_sig = svc.extract_signature(fixed)
        drift = svc.compare_signatures(orig_sig, fixed_sig)
        assert not drift.critical
        # Enum values and constructor should be preserved
        assert drift.enum_changes == {}

    def test_method_added(self):
        svc = make_barcode_service()
        orig = 'gen.Save("out.png");'
        fixed = """
        gen.Save("out.png");
        gen.Dispose();
        """
        orig_sig = svc.extract_signature(orig)
        fixed_sig = svc.extract_signature(fixed)
        drift = svc.compare_signatures(orig_sig, fixed_sig)
        assert "Dispose" in drift.method_changes.get("added", [])


# ══════════════════════════════════════════════════════════════════
# Drift Scoring Tests
# ══════════════════════════════════════════════════════════════════

class TestDriftScoring:

    def test_score_caps_at_1(self):
        svc = make_barcode_service()
        # Massive changes: enum + type + method + property
        orig = """
        var gen = new BarcodeGenerator(EncodeTypes.Code39, "12345");
        gen.Parameters.Barcode.BarColor = Color.Black;
        gen.Save("out.png");
        """
        fixed = """
        var reader = new BarCodeReader("test.png", DecodeType.DataMatrix);
        reader.ReadBarCodes();
        """
        orig_sig = svc.extract_signature(orig)
        fixed_sig = svc.extract_signature(fixed)
        drift = svc.compare_signatures(orig_sig, fixed_sig)
        assert drift.drift_score <= 1.0

    def test_score_zero_for_identical(self):
        svc = make_barcode_service()
        code = 'var gen = new BarcodeGenerator(EncodeTypes.Code39, "12345");'
        sig = svc.extract_signature(code)
        drift = svc.compare_signatures(sig, sig)
        assert drift.drift_score == 0.0


# ══════════════════════════════════════════════════════════════════
# Serialization Tests
# ══════════════════════════════════════════════════════════════════

class TestSerialization:

    def test_signature_to_dict(self):
        sig = SemanticSignature(
            enum_values={"DecodeType": ["Code39"]},
            method_calls=["Save"],
            constructor_types=["BarcodeGenerator"],
            property_assignments={"BarColor": "Color.Black"},
        )
        d = sig.to_dict()
        assert d["enum_values"]["DecodeType"] == ["Code39"]
        assert "Save" in d["method_calls"]

    def test_drift_to_dict(self):
        drift = SignatureDrift(
            drift_score=0.8,
            critical=True,
            critical_reason="Critical enum changed",
            enum_changes={"EncodeTypes": ({"Code39"}, {"DataMatrix"})},
        )
        d = drift.to_dict()
        assert d["drift_score"] == 0.8
        assert d["critical"] is True

    def test_signature_roundtrip(self):
        sig = SemanticSignature(
            enum_values={"DecodeType": ["Code39"]},
            method_calls=["Save"],
            constructor_types=["BarcodeGenerator"],
            property_assignments={"BarColor": "Color.Black"},
        )
        d = sig.to_dict()
        restored = SemanticSignature.from_dict(d)
        assert restored.enum_values == sig.enum_values
        assert restored.method_calls == sig.method_calls


# ══════════════════════════════════════════════════════════════════
# Module-Level Tests
# ══════════════════════════════════════════════════════════════════

class TestCriticalEnumFamilies:

    def test_barcode_critical_enums(self):
        assert "DecodeType" in CRITICAL_ENUM_FAMILIES["barcode"]
        assert "EncodeTypes" in CRITICAL_ENUM_FAMILIES["barcode"]

    def test_zip_critical_enums(self):
        assert "CompressionLevel" in CRITICAL_ENUM_FAMILIES["zip"]

    def test_words_critical_enums(self):
        assert "SaveFormat" in CRITICAL_ENUM_FAMILIES["words"]
