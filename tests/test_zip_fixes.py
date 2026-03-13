"""
Unit tests for src/services/family_fixes/zip_fixes.py

Covers:
- detect_identical_default_constructed_objects (detector)
- get_synthesis_harness (ZIP harness)
- CATALOG_VERIFIED completeness
"""
import pytest
from src.services.family_fixes.zip_fixes import (
    detect_identical_default_constructed_objects,
    get_synthesis_harness,
    CATALOG_VERIFIED,
    COMPRESSION_SETTINGS_TYPES,
)


class TestCatalogVerified:
    def test_required_types_present(self):
        required = {
            'DeflateCompressionSettings',
            'Bzip2CompressionSettings',
            'LzmaCompressionSettings',
            'StoreCompressionSettings',
        }
        assert required.issubset(CATALOG_VERIFIED.keys())

    def test_all_values_true(self):
        assert all(CATALOG_VERIFIED.values()), "All CATALOG_VERIFIED entries must be True"


class TestCompressionSettingsTypes:
    def test_contains_core_types(self):
        assert 'DeflateCompressionSettings' in COMPRESSION_SETTINGS_TYPES
        assert 'Bzip2CompressionSettings' in COMPRESSION_SETTINGS_TYPES
        assert 'LzmaCompressionSettings' in COMPRESSION_SETTINGS_TYPES
        assert 'StoreCompressionSettings' in COMPRESSION_SETTINGS_TYPES


class TestDetectIdenticalDefaultConstructedObjects:
    """Tests for the identical-object detector."""

    IDENTICAL_DEFLATE_CODE = """
using Aspose.Zip.Saving;
var fastest = new DeflateCompressionSettings();      // fastest, larger files
var balanced = new DeflateCompressionSettings();     // default balance
var smallest = new DeflateCompressionSettings();     // slowest, smallest files
"""

    DIFFERENT_ALGORITHMS_CODE = """
using Aspose.Zip.Saving;
var deflate = new DeflateCompressionSettings();
var bzip2 = new Bzip2CompressionSettings();
var lzma = new LzmaCompressionSettings();
var store = new StoreCompressionSettings();
"""

    SINGLE_INSTANCE_CODE = """
using Aspose.Zip.Saving;
var settings = new DeflateCompressionSettings();
var entrySettings = new ArchiveEntrySettings(settings);
"""

    NON_COMPRESSION_DUPLICATE_CODE = """
var a = new ArchiveEntry();
var b = new ArchiveEntry();
"""

    def test_detects_3_identical_deflate_instances(self):
        """3 identical DeflateCompressionSettings() — detector should return None (no code change)."""
        result = detect_identical_default_constructed_objects(
            self.IDENTICAL_DEFLATE_CODE, ""
        )
        # Detector returns None (no code mutation; logging only)
        assert result is None, "Detector must not mutate code; should return None"

    def test_different_algorithms_not_flagged(self):
        """Different sibling types — no pattern match."""
        result = detect_identical_default_constructed_objects(
            self.DIFFERENT_ALGORITHMS_CODE, ""
        )
        assert result is None

    def test_single_instance_not_flagged(self):
        """Single DeflateCompressionSettings — count < 2, no flag."""
        result = detect_identical_default_constructed_objects(
            self.SINGLE_INSTANCE_CODE, ""
        )
        assert result is None

    def test_non_compression_duplicates_not_flagged(self):
        """Duplicate non-CompressionSettings types — outside our COMPRESSION_SETTINGS_TYPES set."""
        result = detect_identical_default_constructed_objects(
            self.NON_COMPRESSION_DUPLICATE_CODE, ""
        )
        assert result is None

    def test_returns_none_always_regardless_of_error_text(self):
        """Detector ignores error_text entirely (it's a structural detector)."""
        result = detect_identical_default_constructed_objects(
            self.IDENTICAL_DEFLATE_CODE,
            "System.InvalidOperationException: Some error"
        )
        assert result is None

    def test_two_identical_bzip2_instances(self):
        """2 identical Bzip2CompressionSettings — also matches."""
        code = """
var a = new Bzip2CompressionSettings();
var b = new Bzip2CompressionSettings();
"""
        result = detect_identical_default_constructed_objects(code, "")
        assert result is None  # Returns None (detector only)

    def test_empty_code_no_crash(self):
        """Empty code should not raise."""
        result = detect_identical_default_constructed_objects("", "")
        assert result is None


class TestGetSynthesisHarness:
    def test_harness_contains_body(self):
        body = "var archive = new Archive();\narchive.Save(\"out.zip\");"
        harness = get_synthesis_harness(body)
        assert "new Archive()" in harness
        assert "archive.Save" in harness

    def test_harness_includes_aspose_usings(self):
        harness = get_synthesis_harness("")
        assert "using Aspose.Zip;" in harness
        assert "using Aspose.Zip.Saving;" in harness

    def test_harness_has_main(self):
        harness = get_synthesis_harness("")
        assert "static void Main()" in harness

    def test_extra_usings_injected(self):
        harness = get_synthesis_harness("", extra_usings="using System.Threading;")
        assert "using System.Threading;" in harness

    def test_data_dir_injected(self):
        harness = get_synthesis_harness("", data_dir="/tmp/test")
        assert "/tmp/test" in harness

    def test_body_indented(self):
        harness = get_synthesis_harness("var x = 1;")
        # Body should be inside Main, indented
        assert "        var x = 1;" in harness


class TestAPICatalogServiceHierarchy:
    """Integration tests for APICatalogService hierarchy methods with the ZIP catalog."""

    @pytest.fixture
    def catalog(self):
        from src.services.api_catalog_service import APICatalogService
        c = APICatalogService('zip')
        if not c.is_loaded:
            pytest.skip("ZIP API catalog not available")
        if not c.has_hierarchy():
            pytest.skip("ZIP API catalog does not have hierarchy data (run with --full to regenerate)")
        return c

    def test_get_base_class_deflate(self, catalog):
        base = catalog.get_base_class('DeflateCompressionSettings')
        assert base == 'CompressionSettings', f"Expected CompressionSettings, got {base}"

    def test_get_sibling_types_deflate(self, catalog):
        siblings = catalog.get_sibling_types('DeflateCompressionSettings')
        assert 'Bzip2CompressionSettings' in siblings
        assert 'LzmaCompressionSettings' in siblings
        assert 'StoreCompressionSettings' in siblings
        assert 'DeflateCompressionSettings' not in siblings, "Sibling list must not include the type itself"

    def test_get_type_group_deflate(self, catalog):
        group = catalog.get_type_group('DeflateCompressionSettings')
        assert 'DeflateCompressionSettings' in group
        assert 'Bzip2CompressionSettings' in group
        assert len(group) >= 4, f"Expected at least 4 CompressionSettings types, got {group}"

    def test_get_type_group_by_base_class(self, catalog):
        """get_type_group works when called with the base class name directly."""
        group = catalog.get_type_group('CompressionSettings')
        assert 'DeflateCompressionSettings' in group

    def test_get_type_kind_deflate(self, catalog):
        kind = catalog.get_type_kind('DeflateCompressionSettings')
        assert kind in ('class', 'sealed class'), f"Unexpected kind: {kind}"

    def test_has_hierarchy_true(self, catalog):
        assert catalog.has_hierarchy()

    def test_get_base_class_unknown_type_returns_none(self, catalog):
        assert catalog.get_base_class('NonExistentType') is None

    def test_get_sibling_types_no_base_returns_empty(self, catalog):
        # Archive has no exported base class in Aspose namespace
        siblings = catalog.get_sibling_types('Archive')
        assert isinstance(siblings, list)
