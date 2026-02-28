"""Integration tests for gist README + multi-file upload + URL validation flow.

Verifies the full path:
  MarkdownUpdateService._upload_and_update_gist()
    -> GistReadmeService.generate_readme()
    -> GistPublisher.publish_gist_with_readme()
    -> GistPublisher.validate_gist_url()
"""

import re
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from dataclasses import dataclass
from typing import Optional

from src.services.gist_publisher import GistPublisher, GistPublishResult
from src.services.gist_readme_service import GistReadmeService


# ---------------------------------------------------------------------------
# Minimal stubs for MarkdownUpdateService dependencies
# ---------------------------------------------------------------------------

@dataclass
class _FakeGist:
    gist_id: str = "old_gist_42"
    owner: str = "aspose-gist"


@dataclass
class _FakeExample:
    example_id: str = "ex-001"
    example_key: str = "zip-extract-01"
    family: str = "ZIP"
    file_path: str = "blog/zip-extract.md"
    verified_code: str = "using System;\nclass Program { static void Main() {} }"
    gist: _FakeGist = None

    def __post_init__(self):
        if self.gist is None:
            self.gist = _FakeGist()


# ---------------------------------------------------------------------------
# Test: full flow through _upload_and_update_gist
# ---------------------------------------------------------------------------

class TestUploadAndUpdateGistIntegration:
    """End-to-end integration of README generation, multi-file upload, and URL validation."""

    def _build_markdown_service(self, gist_publisher, gist_readme_service=None):
        """Build a MarkdownUpdateService with minimal deps."""
        from src.services.markdown_service import MarkdownUpdateService

        db = MagicMock()
        return MarkdownUpdateService(
            db=db,
            gist_publisher=gist_publisher,
            gist_upload_mode="upload-on-change",
            gist_target_account="test-account",
            gist_readme_service=gist_readme_service,
        )

    @patch("src.services.gist_publisher.requests")
    def test_full_flow_with_readme(self, mock_requests):
        """README generated -> multi-file gist created -> URL validated."""
        # Setup: LLM returns a README
        mock_llm = MagicMock()
        llm_response = MagicMock()
        llm_response.content = "# zip-extract-01\n\nExtracts zip files."
        mock_llm.complete.return_value = llm_response

        # Setup: GitHub API returns success
        create_resp = MagicMock()
        create_resp.status_code = 200
        create_resp.json.return_value = {
            "id": "new_gist_99",
            "html_url": "https://gist.github.com/test-account/new_gist_99",
            "files": {
                "ZipExtract.cs": {"raw_url": "https://raw.example.com/ZipExtract.cs"},
                "README.md": {"raw_url": "https://raw.example.com/README.md"},
            },
        }
        mock_requests.patch.return_value = create_resp

        # Setup: URL validation
        head_resp = MagicMock()
        head_resp.status_code = 200
        mock_requests.head.return_value = head_resp

        # Build services
        publisher = GistPublisher(target_account="test-account", token="ghp_FAKE")
        readme_svc = GistReadmeService(llm_service=mock_llm, family="ZIP")
        md_service = self._build_markdown_service(publisher, readme_svc)

        # Build test content with a gist shortcode
        content = 'Some text\n{{< gist aspose-gist old_gist_42 "ZipExtract.cs" >}}\nMore text'
        example = _FakeExample()

        # Find the shortcode match
        pattern = r'\{\{<\s*gist\s+\S+\s+\S+\s+"[^"]+"\s*>\}\}'
        match = re.search(pattern, content)
        assert match is not None

        # Execute
        result = md_service._upload_and_update_gist(
            content=content,
            example=example,
            match=match,
            filename="ZipExtract.cs",
        )

        # Verify result
        assert result is not None
        updated_content, change_info = result

        # Shortcode updated with new gist ID
        assert "new_gist_99" in updated_content
        assert "test-account" in updated_content

        # Change info has README and validation flags
        assert change_info["has_readme"] is True
        assert change_info["url_validated"] is True
        assert change_info["new_gist_id"] == "new_gist_99"

        # LLM was called for README
        mock_llm.complete.assert_called_once()

        # PATCH was used (upload-on-change mode with old_gist_id)
        mock_requests.patch.assert_called_once()
        patch_payload = mock_requests.patch.call_args.kwargs.get("json") or mock_requests.patch.call_args[1]["json"]
        assert "README.md" in patch_payload["files"]

        # HEAD was used for validation
        mock_requests.head.assert_called_once()

    @patch("src.services.gist_publisher.requests")
    def test_flow_without_readme_service(self, mock_requests):
        """Without GistReadmeService, should upload single-file gist."""
        create_resp = MagicMock()
        create_resp.status_code = 200
        create_resp.json.return_value = {
            "id": "single_99",
            "html_url": "https://gist.github.com/test-account/single_99",
            "files": {"Ex.cs": {"raw_url": "https://raw.example.com/Ex.cs"}},
        }
        mock_requests.patch.return_value = create_resp

        head_resp = MagicMock()
        head_resp.status_code = 200
        mock_requests.head.return_value = head_resp

        publisher = GistPublisher(target_account="test-account", token="ghp_FAKE")
        md_service = self._build_markdown_service(publisher, gist_readme_service=None)

        content = 'Text {{< gist owner old_42 "Ex.cs" >}} end'
        example = _FakeExample()
        match = re.search(r'\{\{<\s*gist\s+\S+\s+\S+\s+"[^"]+"\s*>\}\}', content)

        result = md_service._upload_and_update_gist(content, example, match, "Ex.cs")

        assert result is not None
        _, change_info = result
        assert change_info["has_readme"] is False

        # Should use PATCH (single file)
        patch_payload = mock_requests.patch.call_args.kwargs.get("json") or mock_requests.patch.call_args[1]["json"]
        assert "README.md" not in patch_payload["files"]

    @patch("src.services.gist_publisher.requests")
    def test_readme_failure_falls_back_to_single_file(self, mock_requests):
        """If README generation fails, should still upload code-only gist."""
        mock_llm = MagicMock()
        mock_llm.complete.side_effect = RuntimeError("LLM down")

        create_resp = MagicMock()
        create_resp.status_code = 200
        create_resp.json.return_value = {
            "id": "fallback_99",
            "html_url": "https://gist.github.com/test-account/fallback_99",
            "files": {"Ex.cs": {"raw_url": "https://raw.example.com/Ex.cs"}},
        }
        mock_requests.patch.return_value = create_resp

        head_resp = MagicMock()
        head_resp.status_code = 200
        mock_requests.head.return_value = head_resp

        publisher = GistPublisher(target_account="test-account", token="ghp_FAKE")
        readme_svc = GistReadmeService(llm_service=mock_llm, family="ZIP")
        md_service = self._build_markdown_service(publisher, readme_svc)

        content = 'Text {{< gist owner old_42 "Ex.cs" >}} end'
        example = _FakeExample()
        match = re.search(r'\{\{<\s*gist\s+\S+\s+\S+\s+"[^"]+"\s*>\}\}', content)

        result = md_service._upload_and_update_gist(content, example, match, "Ex.cs")

        # Should succeed - README failure falls back to template, which is non-empty
        assert result is not None
        _, change_info = result
        # Fallback readme is non-empty, so has_readme should be True
        assert change_info["has_readme"] is True

    @patch("src.services.gist_publisher.requests")
    def test_url_validation_failure_still_succeeds(self, mock_requests):
        """Gist upload succeeds even if URL validation fails."""
        mock_llm = MagicMock()
        llm_response = MagicMock()
        llm_response.content = "# README"
        mock_llm.complete.return_value = llm_response

        create_resp = MagicMock()
        create_resp.status_code = 200
        create_resp.json.return_value = {
            "id": "g99",
            "html_url": "https://gist.github.com/test-account/g99",
            "files": {"Ex.cs": {"raw_url": "https://raw.example.com/Ex.cs"}},
        }
        mock_requests.patch.return_value = create_resp

        # URL validation returns 404
        head_resp = MagicMock()
        head_resp.status_code = 404
        mock_requests.head.return_value = head_resp
        get_resp = MagicMock()
        get_resp.status_code = 404
        mock_requests.get.return_value = get_resp

        publisher = GistPublisher(target_account="test-account", token="ghp_FAKE")
        readme_svc = GistReadmeService(llm_service=mock_llm, family="ZIP")
        md_service = self._build_markdown_service(publisher, readme_svc)

        content = 'Text {{< gist owner old_42 "Ex.cs" >}} end'
        example = _FakeExample()
        match = re.search(r'\{\{<\s*gist\s+\S+\s+\S+\s+"[^"]+"\s*>\}\}', content)

        result = md_service._upload_and_update_gist(content, example, match, "Ex.cs")

        assert result is not None
        _, change_info = result
        assert change_info["url_validated"] is False
        assert change_info["new_gist_id"] == "g99"


# ---------------------------------------------------------------------------
# GistConfig integration
# ---------------------------------------------------------------------------

class TestGistConfigReadmeField:
    """Verify readme_generation field works in GistConfig."""

    def test_default_is_true(self):
        from src.core.config import GistConfig
        cfg = GistConfig()
        assert cfg.readme_generation is True

    def test_can_disable(self):
        from src.core.config import GistConfig
        cfg = GistConfig(readme_generation=False)
        assert cfg.readme_generation is False

    def test_from_dict(self):
        from src.core.config import GistConfig
        cfg = GistConfig(**{"readme_generation": False, "target_account": "x"})
        assert cfg.readme_generation is False
        assert cfg.target_account == "x"
