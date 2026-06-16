"""
Smoke test: verify all src packages are importable.

Maps to RC-RATE-007: No package import smoke test.
Ensures no missing __init__.py or broken import chains.
"""
import importlib
import pkgutil
import pytest


def _discover_subpackages(package_path, package_name):
    """Yield all subpackage names under a top-level package."""
    results = []
    for importer, modname, ispkg in pkgutil.walk_packages(
        path=package_path, prefix=package_name + ".", onerror=lambda _: None
    ):
        results.append(modname)
    return results


def test_all_src_packages_importable():
    """Every __init__.py-bearing directory under src/ should be importable."""
    import src

    subpackages = _discover_subpackages(src.__path__, src.__name__)
    assert len(subpackages) > 0, "Expected at least one subpackage under src/"

    failures = []
    for pkg in subpackages:
        try:
            importlib.import_module(pkg)
        except Exception as exc:
            failures.append(f"{pkg}: {exc}")

    if failures:
        pytest.fail(
            f"{len(failures)} package(s) failed to import:\n"
            + "\n".join(failures)
        )


def test_utils_markdown_parser_importable():
    """Regression: src.utils.markdown_parser must be importable (RC-RATE-001)."""
    mod = importlib.import_module("src.utils.markdown_parser")
    assert hasattr(mod, "parse_fenced_blocks")
