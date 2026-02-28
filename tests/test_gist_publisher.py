"""Tests for GistPublisher multi-file upload and URL validation."""

import pytest
from unittest.mock import patch, MagicMock, PropertyMock

from src.services.gist_publisher import GistPublisher, GistPublishResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def publisher():
    """GistPublisher with a fake token (no real HTTP calls)."""
    return GistPublisher(
        target_account="test-account",
        token="ghp_FAKE",
        is_public=True,
        timeout_seconds=5,
    )


@pytest.fixture
def gist_api_response():
    """Standard GitHub gist API response body."""
    return {
        "id": "abc123",
        "html_url": "https://gist.github.com/test-account/abc123",
        "files": {
            "Example.cs": {
                "filename": "Example.cs",
                "raw_url": "https://gist.githubusercontent.com/raw/Example.cs",
            },
            "README.md": {
                "filename": "README.md",
                "raw_url": "https://gist.githubusercontent.com/raw/README.md",
            },
        },
    }


# ---------------------------------------------------------------------------
# publish_gist (existing, backward-compat)
# ---------------------------------------------------------------------------

class TestPublishGist:
    """publish_gist() should remain backward-compatible after refactor."""

    @patch("src.services.gist_publisher.requests")
    def test_create_single_file(self, mock_requests, publisher, gist_api_response):
        resp = MagicMock()
        resp.status_code = 201
        resp.json.return_value = gist_api_response
        mock_requests.post.return_value = resp

        result = publisher.publish_gist(
            code_content="using System;",
            filename="Example.cs",
            description="test",
        )

        assert result.success is True
        assert result.gist_id == "abc123"
        # Verify payload has one file
        call_kwargs = mock_requests.post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1]["json"]
        assert "Example.cs" in payload["files"]
        assert len(payload["files"]) == 1

    def test_empty_code_returns_error(self, publisher):
        result = publisher.publish_gist(
            code_content="",
            filename="Example.cs",
            description="test",
        )
        assert result.success is False
        assert "empty" in result.error.lower()

    def test_no_token_returns_error(self):
        pub = GistPublisher(target_account="x", token=None, token_env_var="NONEXISTENT_VAR_12345")
        result = pub.publish_gist("code", "f.cs", "d")
        assert result.success is False
        assert "token" in result.error.lower()

    @patch("src.services.gist_publisher.requests")
    def test_update_existing_gist(self, mock_requests, publisher, gist_api_response):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = gist_api_response
        mock_requests.patch.return_value = resp

        result = publisher.publish_gist(
            code_content="using System;",
            filename="Example.cs",
            description="update",
            old_gist_id="old123",
        )

        assert result.success is True
        mock_requests.patch.assert_called_once()

    def test_filename_gets_extension(self, publisher):
        """Filename without extension should get .cs appended."""
        with patch("src.services.gist_publisher.requests") as mock_req:
            resp = MagicMock()
            resp.status_code = 201
            resp.json.return_value = {"id": "x", "html_url": "u", "files": {}}
            mock_req.post.return_value = resp

            publisher.publish_gist("code", "NoExt", "desc")
            payload = mock_req.post.call_args.kwargs.get("json") or mock_req.post.call_args[1]["json"]
            assert "NoExt.cs" in payload["files"]


# ---------------------------------------------------------------------------
# publish_gist_with_readme (NEW)
# ---------------------------------------------------------------------------

class TestPublishGistWithReadme:
    """Tests for multi-file gist upload (code + README.md)."""

    @patch("src.services.gist_publisher.requests")
    def test_creates_two_file_gist(self, mock_requests, publisher, gist_api_response):
        resp = MagicMock()
        resp.status_code = 201
        resp.json.return_value = gist_api_response
        mock_requests.post.return_value = resp

        result = publisher.publish_gist_with_readme(
            code_content="using Aspose.Zip;",
            filename="ZipExample.cs",
            readme_content="# ZipExample\nOverview text.",
            description="test multi-file",
        )

        assert result.success is True
        assert result.gist_id == "abc123"

        payload = mock_requests.post.call_args.kwargs.get("json") or mock_requests.post.call_args[1]["json"]
        assert "ZipExample.cs" in payload["files"]
        assert "README.md" in payload["files"]
        assert payload["files"]["README.md"]["content"] == "# ZipExample\nOverview text."

    @patch("src.services.gist_publisher.requests")
    def test_updates_existing_with_readme(self, mock_requests, publisher, gist_api_response):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = gist_api_response
        mock_requests.patch.return_value = resp

        result = publisher.publish_gist_with_readme(
            code_content="code",
            filename="Ex.cs",
            readme_content="# Readme",
            description="update",
            old_gist_id="existing_123",
        )

        assert result.success is True
        mock_requests.patch.assert_called_once()
        payload = mock_requests.patch.call_args.kwargs.get("json") or mock_requests.patch.call_args[1]["json"]
        assert "Ex.cs" in payload["files"]
        assert "README.md" in payload["files"]

    def test_empty_readme_still_included(self, publisher):
        """Empty readme_content should produce a README.md with empty string."""
        with patch("src.services.gist_publisher.requests") as mock_req:
            resp = MagicMock()
            resp.status_code = 201
            resp.json.return_value = {"id": "x", "html_url": "u", "files": {}}
            mock_req.post.return_value = resp

            publisher.publish_gist_with_readme("code", "f.cs", "", "desc")
            payload = mock_req.post.call_args.kwargs.get("json") or mock_req.post.call_args[1]["json"]
            assert "README.md" in payload["files"]

    def test_empty_code_returns_error(self, publisher):
        result = publisher.publish_gist_with_readme(
            code_content="  ",
            filename="f.cs",
            readme_content="# Title",
            description="desc",
        )
        assert result.success is False
        assert "empty" in result.error.lower()

    def test_no_token_returns_error(self):
        pub = GistPublisher(target_account="x", token=None, token_env_var="NONEXISTENT_VAR_12345")
        result = pub.publish_gist_with_readme("code", "f.cs", "# Readme", "d")
        assert result.success is False

    @patch("src.services.gist_publisher.requests")
    def test_api_error_returns_failure(self, mock_requests, publisher):
        resp = MagicMock()
        resp.status_code = 422
        resp.text = "Validation failed"
        mock_requests.post.return_value = resp

        result = publisher.publish_gist_with_readme("code", "f.cs", "readme", "desc")
        assert result.success is False
        assert "422" in result.error

    @patch("src.services.gist_publisher.requests")
    def test_timeout_returns_failure(self, mock_requests, publisher):
        import requests as real_requests
        mock_requests.exceptions = real_requests.exceptions
        mock_requests.post.side_effect = real_requests.exceptions.Timeout("timeout")

        result = publisher.publish_gist_with_readme("code", "f.cs", "readme", "desc")
        assert result.success is False
        assert "timed out" in result.error.lower()


# ---------------------------------------------------------------------------
# validate_gist_url (NEW)
# ---------------------------------------------------------------------------

class TestValidateGistUrl:
    """Tests for HEAD/GET URL validation."""

    @patch("src.services.gist_publisher.requests")
    def test_head_200_returns_valid(self, mock_requests, publisher):
        resp = MagicMock()
        resp.status_code = 200
        mock_requests.head.return_value = resp

        valid, code, msg = publisher.validate_gist_url("https://gist.github.com/abc123")

        assert valid is True
        assert code == 200
        assert msg == "OK"
        mock_requests.head.assert_called_once()

    @patch("src.services.gist_publisher.requests")
    def test_head_405_falls_back_to_get(self, mock_requests, publisher):
        head_resp = MagicMock()
        head_resp.status_code = 405
        mock_requests.head.return_value = head_resp

        get_resp = MagicMock()
        get_resp.status_code = 200
        mock_requests.get.return_value = get_resp

        valid, code, msg = publisher.validate_gist_url("https://gist.github.com/abc123")

        assert valid is True
        mock_requests.head.assert_called_once()
        mock_requests.get.assert_called_once()

    @patch("src.services.gist_publisher.requests")
    def test_head_500_falls_back_to_get(self, mock_requests, publisher):
        head_resp = MagicMock()
        head_resp.status_code = 500
        mock_requests.head.return_value = head_resp

        get_resp = MagicMock()
        get_resp.status_code = 200
        mock_requests.get.return_value = get_resp

        valid, code, msg = publisher.validate_gist_url("https://example.com")
        assert valid is True

    @patch("src.services.gist_publisher.requests")
    def test_both_fail_returns_invalid(self, mock_requests, publisher):
        head_resp = MagicMock()
        head_resp.status_code = 404
        mock_requests.head.return_value = head_resp

        get_resp = MagicMock()
        get_resp.status_code = 404
        mock_requests.get.return_value = get_resp

        valid, code, msg = publisher.validate_gist_url("https://example.com/missing")

        assert valid is False
        assert code == 404

    @patch("src.services.gist_publisher.requests")
    def test_timeout_returns_invalid(self, mock_requests, publisher):
        import requests as real_requests
        mock_requests.exceptions = real_requests.exceptions
        mock_requests.head.side_effect = real_requests.exceptions.Timeout("timeout")

        valid, code, msg = publisher.validate_gist_url("https://example.com")

        assert valid is False
        assert code == 0
        assert "timed out" in msg.lower()

    @patch("src.services.gist_publisher.requests")
    def test_connection_error_returns_invalid(self, mock_requests, publisher):
        import requests as real_requests
        mock_requests.exceptions = real_requests.exceptions
        mock_requests.head.side_effect = real_requests.exceptions.ConnectionError("dns fail")

        valid, code, msg = publisher.validate_gist_url("https://example.com")

        assert valid is False
        assert "failed" in msg.lower()

    def test_no_requests_lib_returns_invalid(self, publisher):
        with patch("src.services.gist_publisher.REQUESTS_AVAILABLE", False):
            valid, code, msg = publisher.validate_gist_url("https://example.com")
            assert valid is False
            assert "not available" in msg.lower()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

class TestInternalHelpers:

    def test_get_headers(self, publisher):
        headers = publisher._get_headers()
        assert "Authorization" in headers
        assert "ghp_FAKE" in headers["Authorization"]

    def test_parse_gist_response(self, publisher, gist_api_response):
        result = publisher._parse_gist_response(gist_api_response, 201)
        assert result.success is True
        assert result.gist_id == "abc123"
        assert result.html_url == "https://gist.github.com/test-account/abc123"
        assert result.raw_url is not None

    def test_from_config(self):
        mock_config = MagicMock()
        mock_config.target_account = "acme"
        mock_config.pat_env_var = "MY_PAT"
        mock_config.is_public = False

        pub = GistPublisher.from_config(mock_config)
        assert pub.target_account == "acme"
        assert pub.is_public is False

    @patch("src.services.gist_publisher.requests")
    def test_update_404_falls_back_to_create(self, mock_requests, publisher, gist_api_response):
        """When PATCH returns 404, _update_gist falls back to _create_gist."""
        patch_resp = MagicMock()
        patch_resp.status_code = 404
        mock_requests.patch.return_value = patch_resp

        create_resp = MagicMock()
        create_resp.status_code = 201
        create_resp.json.return_value = gist_api_response
        mock_requests.post.return_value = create_resp

        result = publisher.publish_gist(
            code_content="code",
            filename="f.cs",
            description="desc",
            old_gist_id="nonexistent",
        )

        assert result.success is True
        mock_requests.patch.assert_called_once()
        mock_requests.post.assert_called_once()

    @patch("src.services.gist_publisher.requests")
    def test_update_403_falls_back_to_create(self, mock_requests, publisher, gist_api_response):
        """When PATCH returns 403 (different owner), _update_gist falls back to _create_gist."""
        patch_resp = MagicMock()
        patch_resp.status_code = 403
        mock_requests.patch.return_value = patch_resp

        create_resp = MagicMock()
        create_resp.status_code = 201
        create_resp.json.return_value = gist_api_response
        mock_requests.post.return_value = create_resp

        result = publisher.publish_gist(
            code_content="code",
            filename="f.cs",
            description="desc",
            old_gist_id="other_owner_gist",
        )

        assert result.success is True
        mock_requests.patch.assert_called_once()
        mock_requests.post.assert_called_once()

    @patch("src.services.gist_publisher.requests")
    def test_update_403_with_readme_falls_back_to_create(self, mock_requests, publisher, gist_api_response):
        """403 fallback also works for publish_gist_with_readme."""
        patch_resp = MagicMock()
        patch_resp.status_code = 403
        mock_requests.patch.return_value = patch_resp

        create_resp = MagicMock()
        create_resp.status_code = 201
        create_resp.json.return_value = gist_api_response
        mock_requests.post.return_value = create_resp

        result = publisher.publish_gist_with_readme(
            code_content="code",
            filename="f.cs",
            readme_content="# README",
            description="desc",
            old_gist_id="other_owner_gist",
        )

        assert result.success is True
        assert mock_requests.patch.call_count == 1
        assert mock_requests.post.call_count == 1
