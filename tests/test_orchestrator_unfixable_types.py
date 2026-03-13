from unittest.mock import Mock

from src.pipeline.orchestrator import PipelineOrchestrator


def _make_orchestrator() -> PipelineOrchestrator:
    """Create an orchestrator instance without running heavy initialization."""
    return object.__new__(PipelineOrchestrator)


def test_check_unfixable_types_skips_bcl_arraylist():
    orch = _make_orchestrator()
    catalog = Mock()
    catalog.has_type.return_value = False

    errors = [
        "error CS0246: The type or namespace name 'ArrayList' could not be found (are you missing a using directive or an assembly reference?)"
    ]

    result = orch._check_unfixable_types(errors, catalog_service=catalog, code="ArrayList pages = new ArrayList();")

    assert result == []
    catalog.has_type.assert_not_called()


def test_check_unfixable_types_skips_user_defined_type():
    orch = _make_orchestrator()
    catalog = Mock()
    catalog.has_type.return_value = False

    errors = [
        "error CS0246: The type or namespace name 'PageCollector' could not be found (are you missing a using directive or an assembly reference?)"
    ]
    code = """
class PageCollector
{
}

PageCollector collector = new PageCollector();
""".strip()

    result = orch._check_unfixable_types(errors, catalog_service=catalog, code=code)

    assert result == []
    catalog.has_type.assert_not_called()


def test_check_unfixable_types_reports_true_unknown_types():
    orch = _make_orchestrator()
    catalog = Mock()
    catalog.has_type.return_value = False

    errors = [
        "error CS0246: The type or namespace name 'DefinitelyMissingType' could not be found (are you missing a using directive or an assembly reference?)"
    ]

    result = orch._check_unfixable_types(errors, catalog_service=catalog, code="")

    assert result == ["DefinitelyMissingType"]
    catalog.has_type.assert_called_once_with("DefinitelyMissingType")
