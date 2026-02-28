"""Tests for GistReadmeService - LLM README generation with template fallback."""

import pytest
from unittest.mock import MagicMock

from src.services.gist_readme_service import GistReadmeService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_llm():
    """LLM service mock that returns a response with .content attribute."""
    llm = MagicMock()
    response = MagicMock()
    response.content = "# Example\n\nOverview of the code.\n\n## Usage\n\nRun it."
    llm.complete.return_value = response
    return llm


@pytest.fixture
def service(mock_llm):
    """GistReadmeService with mocked LLM."""
    return GistReadmeService(llm_service=mock_llm, family="ZIP")


@pytest.fixture
def sample_code():
    return (
        "using System;\n"
        "using Aspose.Zip;\n"
        "\n"
        "class Program {\n"
        "    static void Main() {\n"
        '        using var archive = new Archive("input.zip");\n'
        '        archive.ExtractToDirectory("output");\n'
        "    }\n"
        "}\n"
    )


# ---------------------------------------------------------------------------
# generate_readme - LLM path
# ---------------------------------------------------------------------------

class TestGenerateReadme:

    def test_returns_llm_content(self, service, mock_llm, sample_code):
        readme = service.generate_readme(
            code=sample_code,
            example_key="zip-extract-01",
            family="ZIP",
            file_path="blog/zip-extract.md",
        )

        assert "# Example" in readme
        assert "Overview" in readme
        mock_llm.complete.assert_called_once()

    def test_passes_code_snippet_to_llm(self, service, mock_llm, sample_code):
        service.generate_readme(
            code=sample_code,
            example_key="test",
            family="ZIP",
            file_path="path.md",
        )

        call_kwargs = mock_llm.complete.call_args.kwargs
        assert "csharp" in call_kwargs["prompt"]
        assert "Aspose.Zip" in call_kwargs["prompt"]

    def test_truncates_long_code_to_1500(self, service, mock_llm):
        long_code = "x" * 3000
        service.generate_readme(
            code=long_code,
            example_key="test",
            family="ZIP",
            file_path="path.md",
        )

        call_kwargs = mock_llm.complete.call_args.kwargs
        # The prompt should contain at most 1500 chars of code
        code_in_prompt = call_kwargs["prompt"]
        # Between ```csharp\n and \n``` there should be <= 1500 chars
        assert "x" * 1501 not in code_in_prompt

    def test_includes_description_when_provided(self, service, mock_llm, sample_code):
        service.generate_readme(
            code=sample_code,
            example_key="test",
            family="ZIP",
            file_path="path.md",
            description="Extract files from a zip archive",
        )

        call_kwargs = mock_llm.complete.call_args.kwargs
        assert "Extract files" in call_kwargs["prompt"]

    def test_system_prompt_includes_family(self, service, mock_llm, sample_code):
        service.generate_readme(
            code=sample_code,
            example_key="test",
            family="Words",
            file_path="path.md",
        )

        call_kwargs = mock_llm.complete.call_args.kwargs
        assert "Words" in call_kwargs["system_prompt"]

    def test_llm_params(self, service, mock_llm, sample_code):
        service.generate_readme(
            code=sample_code,
            example_key="test",
            family="ZIP",
            file_path="path.md",
        )

        call_kwargs = mock_llm.complete.call_args.kwargs
        assert call_kwargs["max_tokens"] == 1024
        assert call_kwargs["temperature"] == 0.3


# ---------------------------------------------------------------------------
# generate_readme - fallback path
# ---------------------------------------------------------------------------

class TestGenerateReadmeFallback:

    def test_llm_exception_triggers_fallback(self, mock_llm, sample_code):
        mock_llm.complete.side_effect = RuntimeError("LLM unavailable")
        svc = GistReadmeService(llm_service=mock_llm, family="ZIP")

        readme = svc.generate_readme(
            code=sample_code,
            example_key="zip-extract-01",
            family="ZIP",
            file_path="path.md",
        )

        assert "# zip-extract-01" in readme
        assert "Aspose.ZIP" in readme
        assert "NuGet" in readme

    def test_fallback_contains_all_sections(self, mock_llm, sample_code):
        mock_llm.complete.side_effect = Exception("fail")
        svc = GistReadmeService(llm_service=mock_llm, family="Words")

        readme = svc.generate_readme(
            code=sample_code,
            example_key="doc-convert",
            family="Words",
            file_path="path.md",
        )

        assert "## Overview" in readme
        assert "## Usage" in readme
        assert "## Prerequisites" in readme
        assert "## License" in readme

    def test_fallback_uses_correct_family(self, mock_llm, sample_code):
        mock_llm.complete.side_effect = Exception("fail")
        svc = GistReadmeService(llm_service=mock_llm, family="OCR")

        readme = svc.generate_readme(
            code=sample_code,
            example_key="ocr-01",
            family="OCR",
            file_path="path.md",
        )

        assert "Aspose.OCR" in readme


# ---------------------------------------------------------------------------
# _strip_links
# ---------------------------------------------------------------------------

class TestStripLinks:

    def test_removes_regular_links(self, service):
        md = "See [Aspose docs](https://docs.aspose.com) for details."
        result = service._strip_links(md)
        assert result == "See Aspose docs for details."

    def test_preserves_mailto_links(self, service):
        md = "Contact [support](mailto:support@aspose.com) for help."
        result = service._strip_links(md)
        assert "mailto:" in result

    def test_handles_multiple_links(self, service):
        md = "[A](http://a.com) and [B](https://b.com) but [C](mailto:c@c.com)"
        result = service._strip_links(md)
        assert "A and B" in result
        assert "mailto:" in result

    def test_no_links_unchanged(self, service):
        md = "No links here."
        result = service._strip_links(md)
        assert result == "No links here."

    def test_empty_string(self, service):
        assert service._strip_links("") == ""


# ---------------------------------------------------------------------------
# _fallback_readme
# ---------------------------------------------------------------------------

class TestFallbackReadme:

    def test_structure(self, service):
        readme = service._fallback_readme("code", "my-example", "ZIP")
        lines = readme.split("\n")
        assert lines[0] == "# my-example"
        assert "Aspose.ZIP" in readme

    def test_different_families(self, service):
        for family in ["ZIP", "Words", "OCR", "BarCode", "PDF"]:
            readme = service._fallback_readme("code", "ex", family)
            assert f"Aspose.{family}" in readme
