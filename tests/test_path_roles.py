from pathlib import Path

from src.core.path_roles import (
    PathOperation,
    PathRole,
    classify_path_role,
    sanitize_file_aliases,
    validate_path_role_preservation,
)
from src.services.fixture_resolver_service import FixtureResolverService
from src.services.runtime_service import RuntimeService


def test_classify_path_role_distinguishes_output_and_template():
    assert classify_path_role("output.docx") == PathRole.OUTPUT
    assert classify_path_role("Blank.docx") == PathRole.TEMPLATE
    assert classify_path_role("input.docx") == PathRole.INPUT
    assert classify_path_role("sample.docx") == PathRole.FIXTURE
    assert classify_path_role("anything.docx", PathOperation.WRITE) == PathRole.OUTPUT


def test_sanitize_file_aliases_drops_output_to_template_mapping():
    aliases = {
        "Blank.docx": ["template.docx", "output.docx"],
        "sample.zip": ["input.zip"],
    }

    sanitized, warnings = sanitize_file_aliases(aliases)

    assert sanitized["Blank.docx"] == ["template.docx"]
    assert sanitized["sample.zip"] == ["input.zip"]
    assert any("output.docx" in warning for warning in warnings)


def test_validate_path_role_preservation_rejects_output_to_template_rewrite():
    original = 'var doc = new Document(); doc.Save("output.docx");'
    fixed = 'var doc = new Document(); doc.Save("Blank.docx");'

    result = validate_path_role_preservation(original, fixed)

    assert not result.valid
    assert any(issue.fixed_literal == "Blank.docx" for issue in result.issues)


def test_validate_path_role_preservation_allows_output_to_output_rename():
    original = 'var doc = new Document(); doc.Save("output.docx");'
    fixed = 'var doc = new Document(); doc.Save("result.docx");'

    result = validate_path_role_preservation(original, fixed)

    assert result.valid


def test_fixture_resolver_skips_output_alias_even_if_config_contains_it(tmp_path):
    test_data_dir = tmp_path / "test-data"
    test_data_dir.mkdir()
    (test_data_dir / "Blank.docx").write_bytes(b"PK\x03\x04" + b"\x00" * 50)

    resolver = FixtureResolverService(
        family="words",
        test_data_dir=test_data_dir,
        file_aliases={"Blank.docx": ["template.docx", "output.docx"]},
        registry_path=tmp_path / "fixture-registry.json",
    )

    result = resolver.resolve_missing_file("output.docx")

    assert not result.resolved
    assert result.method == "skipped"


def test_runtime_find_test_file_does_not_treat_output_name_as_fixture_alias(tmp_path):
    test_data_dir = tmp_path / "test-data"
    test_data_dir.mkdir()
    (test_data_dir / "Blank.docx").write_bytes(b"PK\x03\x04" + b"\x00" * 50)

    found = RuntimeService.find_test_file(
        required_name="output.docx",
        source_dir=test_data_dir,
        file_aliases={"Blank.docx": ["output.docx"]},
    )

    assert found is None
