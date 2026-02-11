"""Tests for APICatalogService (HEAL-06)."""

import pytest
from pathlib import Path

from src.services.api_catalog_service import APICatalogService
from src.namespace_validator import NamespaceValidator


CATALOG_PATH = "config/families/zip_api_catalog.json"


class TestAPICatalogService:
    """Unit tests for APICatalogService."""

    def test_load_zip_catalog(self):
        svc = APICatalogService("zip")
        assert svc.is_loaded
        assert len(svc.get_all_types()) >= 130

    def test_load_with_explicit_path(self):
        svc = APICatalogService("zip", catalog_path=CATALOG_PATH)
        assert svc.is_loaded
        assert len(svc.get_all_types()) == 138

    def test_missing_family_graceful(self):
        svc = APICatalogService("nonexistent_family_xyzzy")
        assert not svc.is_loaded
        assert svc.get_all_types() == []
        assert svc.get_namespace_for_type("Archive") is None

    def test_get_namespace_for_type(self):
        svc = APICatalogService("zip")
        assert svc.get_namespace_for_type("Archive") == "Aspose.Zip"
        assert svc.get_namespace_for_type("RarArchive") == "Aspose.Zip.Rar"
        assert svc.get_namespace_for_type("FakeType") is None

    def test_get_using_directive(self):
        svc = APICatalogService("zip")
        assert svc.get_using_directive("Archive") == "using Aspose.Zip;"
        assert svc.get_using_directive("SevenZipArchive") == "using Aspose.Zip.SevenZip;"
        assert svc.get_using_directive("FakeType") is None

    def test_validate_symbol(self):
        svc = APICatalogService("zip")
        assert svc.validate_symbol("Archive")
        assert svc.validate_symbol("TarArchive")
        assert not svc.validate_symbol("BogusType")

    def test_ambiguous_types(self):
        svc = APICatalogService("zip")
        assert svc.is_ambiguous("CancelEntryEventArgs")
        assert not svc.is_ambiguous("Archive")
        ns = svc.get_ambiguous_namespaces("CancelEntryEventArgs")
        assert len(ns) >= 2

    def test_validate_namespace(self):
        svc = APICatalogService("zip")
        assert svc.validate_namespace("Aspose.Zip")
        assert svc.validate_namespace("Aspose.Zip.Rar")
        assert not svc.validate_namespace("Aspose.Fake")

    def test_get_namespace_set(self):
        svc = APICatalogService("zip")
        ns = svc.get_namespace_set()
        assert isinstance(ns, set)
        assert "Aspose.Zip" in ns
        assert len(ns) == 28

    def test_using_directive_map(self):
        svc = APICatalogService("zip")
        m = svc.get_using_directive_map()
        assert len(m) == 138
        assert "Archive" in m


class TestNamespaceValidatorCatalogIntegration:
    """Integration tests for NamespaceValidator + APICatalogService (HEAL-03)."""

    def test_without_catalog_rejects_aspose(self):
        v = NamespaceValidator({"mode": "whitelist", "allowed_namespaces": ["System.*"]})
        ok, violations = v.validate("using Aspose.Zip;\nusing System.IO;")
        assert not ok
        assert "Aspose.Zip" in violations

    def test_with_catalog_allows_aspose(self):
        catalog = APICatalogService("zip")
        v = NamespaceValidator(
            {"mode": "whitelist", "allowed_namespaces": ["System.*"]},
            catalog=catalog,
        )
        ok, violations = v.validate("using Aspose.Zip;\nusing System.IO;\nusing Aspose.Zip.Rar;")
        assert ok
        assert violations == []

    def test_with_catalog_rejects_unknown(self):
        catalog = APICatalogService("zip")
        v = NamespaceValidator(
            {"mode": "whitelist", "allowed_namespaces": ["System.*"]},
            catalog=catalog,
        )
        ok, violations = v.validate("using Aspose.Fake.Namespace;")
        assert not ok
        assert "Aspose.Fake.Namespace" in violations

    def test_family_isolation(self):
        """zip catalog should NOT affect a hypothetical 'words' validator."""
        fake_catalog = APICatalogService("words")  # nonexistent, not loaded
        v = NamespaceValidator(
            {"mode": "whitelist", "allowed_namespaces": ["System.*"]},
            catalog=fake_catalog,
        )
        ok, violations = v.validate("using Aspose.Zip;")
        assert not ok  # zip namespaces NOT in words catalog


class TestCatalogConfigIntegration:
    """Integration tests for config -> catalog -> service chain (HEAL-05)."""

    def test_config_loads_api_catalog(self):
        from src.core.config import ConfigurationManager
        cm = ConfigurationManager()
        fc = cm.load_family_config("zip")
        assert fc.api_catalog is not None
        assert fc.api_catalog.enabled is True
        assert fc.api_catalog.path == "config/families/zip_api_catalog.json"

    def test_config_path_loads_catalog(self):
        from src.core.config import ConfigurationManager
        cm = ConfigurationManager()
        fc = cm.load_family_config("zip")
        svc = APICatalogService("zip", catalog_path=fc.api_catalog.path)
        assert svc.is_loaded
        assert len(svc.get_all_types()) == 138


class TestSemanticMicrofixesIntegration:
    """Integration: semantic_microfixes uses catalog via service."""

    def test_catalog_directives_available_via_registry(self):
        """Test that catalog directives are accessible via FamilyServiceRegistry."""
        from pathlib import Path
        from src.pipeline.family_service_registry import FamilyServiceRegistry
        from src.core.config import ConfigurationManager
        from src.services.semantic_microfixes import USING_DIRECTIVE_ALLOWLIST

        config_manager = ConfigurationManager()
        registry = FamilyServiceRegistry(config_manager, artifacts_dir=Path("artifacts"))

        # Verify full catalog available through registry
        directives = registry.get_using_directives('zip')
        assert len(directives) >= 137
        assert "Archive" in directives
        assert "TarArchive" in directives

        # Verify static fallback still exists (for backwards compatibility)
        assert len(USING_DIRECTIVE_ALLOWLIST) >= 5  # Hardcoded fallback entries
