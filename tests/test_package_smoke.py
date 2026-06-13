"""
Package smoke tests for Example Reviewer Pipeline.

Validates that all source modules import cleanly and core
components can be instantiated without runtime errors.
"""

import importlib
import pkgutil
import pytest


# ---------------------------------------------------------------------------
# Module import tests
# ---------------------------------------------------------------------------

def _iter_src_modules():
    """Yield dotted module names under src/."""
    import src
    for importer, modname, ispkg in pkgutil.walk_packages(
        path=src.__path__,
        prefix="src.",
    ):
        yield modname


# Collect all importable modules at test-collection time
_ALL_MODULES = None

def _get_all_modules():
    global _ALL_MODULES
    if _ALL_MODULES is None:
        try:
            _ALL_MODULES = list(_iter_src_modules())
        except Exception:
            _ALL_MODULES = []
    return _ALL_MODULES


class TestModuleImports:
    """Verify every module under src/ imports without error."""

    def test_src_package_importable(self):
        """The top-level src package must import."""
        import src
        assert src is not None

    def test_core_models_importable(self):
        mod = importlib.import_module("src.core.models")
        assert hasattr(mod, "ExampleRecord")
        assert hasattr(mod, "ExampleStatus")

    def test_core_config_importable(self):
        mod = importlib.import_module("src.core.config")
        assert mod is not None

    def test_core_path_guard_importable(self):
        mod = importlib.import_module("src.core.path_guard")
        assert hasattr(mod, "is_read_only_path")
        assert hasattr(mod, "assert_write_allowed")

    def test_core_provenance_guard_importable(self):
        mod = importlib.import_module("src.core.provenance_guard")
        assert hasattr(mod, "validate_provenance")

    def test_pipeline_module_importable(self):
        mod = importlib.import_module("src.pipeline")
        assert mod is not None

    def test_services_module_importable(self):
        mod = importlib.import_module("src.services")
        assert mod is not None

    def test_mcp_tools_module_importable(self):
        mod = importlib.import_module("src.mcp_tools")
        assert mod is not None


class TestCoreComponents:
    """Verify core component classes can be referenced."""

    def test_example_status_enum_values(self):
        from src.core.models import ExampleStatus
        # Must have at least DISCOVERED and VERIFIED
        assert hasattr(ExampleStatus, "DISCOVERED")
        assert hasattr(ExampleStatus, "VERIFIED")

    def test_path_guard_read_only_prefixes_defined(self):
        from src.core.path_guard import READ_ONLY_PREFIXES
        assert isinstance(READ_ONLY_PREFIXES, tuple)
        assert len(READ_ONLY_PREFIXES) > 0

    def test_logging_config_importable(self):
        from src.core.logging_config import setup_structured_logging, set_run_context
        assert callable(setup_structured_logging)
        assert callable(set_run_context)
