"""
Tests for GistPublisher service.
"""

import pytest
from unittest.mock import patch, MagicMock
import requests

from src.services.gist_publisher import (
    GistPublisher,
    GistPublishResult,
)


class TestGistPublishResult:
    """Tests for GistPublishResult dataclass."""

    def test_success_result(self):
        """Test successful publish result."""
        result = GistPublishResult(
            success=True,
            gist_id="abc123",
            html_url="https://gist.github.com/user/abc123",
            raw_url="https://gist.githubusercontent.com/user/abc123/raw/file.cs",
        )
        assert result.success is True
        assert result.gist_id == "abc123"
        assert result.error is None

    def test_failure_result(self):
        """Test failed publish result."""
        result = GistPublishResult(
            success=False,
            error="Authentication failed",
        )
        assert result.success is False
        assert result.gist_id is None
        assert result.error == "Authentication failed"


class TestGistPublisher:
    """Tests for GistPublisher service."""

    def test_init_with_token(self):
        """Test initialization with explicit token."""
        publisher = GistPublisher(
            target_account="test-account",
            token="test-token",
            is_public=False,
        )
        assert publisher.target_account == "test-account"
        assert publisher.token == "test-token"
        assert publisher.is_public is False

    @patch.dict('os.environ', {'GIST_PAT': 'env-token'})
    def test_init_from_env(self):
        """Test token loaded from environment variable."""
        publisher = GistPublisher(
            target_account="test-account",
        )
        assert publisher.token == "env-token"

    def test_is_available_with_token(self):
        """Test is_available returns True with token."""
        publisher = GistPublisher(
            target_account="test-account",
            token="test-token",
        )
        assert publisher.is_available() is True

    def test_is_available_without_token(self):
        """Test is_available returns False without token."""
        publisher = GistPublisher(
            target_account="test-account",
            token=None,
        )
        # Clear any env token
        with patch.dict('os.environ', {}, clear=True):
            publisher = GistPublisher(
                target_account="test-account",
            )
            assert publisher.is_available() is False

    def test_publish_gist_without_token(self):
        """Test publish fails gracefully without token."""
        publisher = GistPublisher(
            target_account="test-account",
            token=None,
        )
        publisher.token = None  # Force no token

        result = publisher.publish_gist(
            code_content="// test code",
            filename="test.cs",
            description="Test gist",
        )

        assert result.success is False
        assert "No authentication token" in result.error

    @patch('requests.post')
    def test_create_gist_success(self, mock_post):
        """Test successful gist creation."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            'id': 'new-gist-id',
            'html_url': 'https://gist.github.com/user/new-gist-id',
            'files': {
                'test.cs': {
                    'raw_url': 'https://gist.githubusercontent.com/user/new-gist-id/raw/test.cs'
                }
            }
        }
        mock_post.return_value = mock_response

        publisher = GistPublisher(
            target_account="test-account",
            token="test-token",
        )

        result = publisher.publish_gist(
            code_content="// test code",
            filename="test.cs",
            description="Test gist",
        )

        assert result.success is True
        assert result.gist_id == "new-gist-id"
        assert result.html_url == "https://gist.github.com/user/new-gist-id"

        # Verify API call
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "Authorization" in call_args.kwargs['headers']
        assert call_args.kwargs['json']['public'] is True

    @patch('requests.post')
    def test_create_gist_failure(self, mock_post):
        """Test gist creation failure handling."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Bad credentials"
        mock_response.raise_for_status.side_effect = requests.HTTPError("401 Unauthorized")
        mock_post.return_value = mock_response

        publisher = GistPublisher(
            target_account="test-account",
            token="bad-token",
        )

        result = publisher.publish_gist(
            code_content="// test code",
            filename="test.cs",
            description="Test gist",
        )

        assert result.success is False
        assert result.error is not None

    @patch('requests.patch')
    def test_update_gist_success(self, mock_patch):
        """Test successful gist update."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': 'existing-gist-id',
            'html_url': 'https://gist.github.com/user/existing-gist-id',
            'files': {
                'test.cs': {
                    'raw_url': 'https://gist.githubusercontent.com/user/existing-gist-id/raw/test.cs'
                }
            }
        }
        mock_patch.return_value = mock_response

        publisher = GistPublisher(
            target_account="test-account",
            token="test-token",
        )

        result = publisher.publish_gist(
            code_content="// updated code",
            filename="test.cs",
            description="Updated gist",
            old_gist_id="existing-gist-id",
        )

        assert result.success is True
        assert result.gist_id == "existing-gist-id"

        # Verify PATCH was used, not POST
        mock_patch.assert_called_once()
        assert "existing-gist-id" in mock_patch.call_args.args[0]

    @patch('requests.post')
    def test_create_private_gist(self, mock_post):
        """Test creating a private (secret) gist."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            'id': 'private-gist-id',
            'html_url': 'https://gist.github.com/user/private-gist-id',
            'files': {}
        }
        mock_post.return_value = mock_response

        publisher = GistPublisher(
            target_account="test-account",
            token="test-token",
            is_public=False,
        )

        publisher.publish_gist(
            code_content="// secret code",
            filename="secret.cs",
            description="Secret gist",
        )

        # Verify public=False in request
        call_args = mock_post.call_args
        assert call_args.kwargs['json']['public'] is False

    @patch('requests.post')
    def test_network_timeout(self, mock_post):
        """Test network timeout handling."""
        mock_post.side_effect = requests.Timeout("Connection timed out")

        publisher = GistPublisher(
            target_account="test-account",
            token="test-token",
        )

        result = publisher.publish_gist(
            code_content="// test code",
            filename="test.cs",
            description="Test gist",
        )

        assert result.success is False
        assert "timeout" in result.error.lower() or "timed out" in result.error.lower()

    @patch('requests.post')
    def test_rate_limit_handling(self, mock_post):
        """Test rate limit error handling."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "API rate limit exceeded"
        mock_response.raise_for_status.side_effect = requests.HTTPError("403 Forbidden")
        mock_post.return_value = mock_response

        publisher = GistPublisher(
            target_account="test-account",
            token="test-token",
        )

        result = publisher.publish_gist(
            code_content="// test code",
            filename="test.cs",
            description="Test gist",
        )

        assert result.success is False
        assert "403" in result.error or "rate limit" in result.error.lower()


class TestGistPublisherFromConfig:
    """Tests for creating GistPublisher from config."""

    def test_from_config(self):
        """Test creating publisher from config object."""
        config = MagicMock()
        config.target_account = "config-account"
        config.pat_env_var = "CUSTOM_PAT"
        config.is_public = False

        with patch.dict('os.environ', {'CUSTOM_PAT': 'config-token'}):
            publisher = GistPublisher.from_config(config)

        assert publisher.target_account == "config-account"
        assert publisher.token == "config-token"
        assert publisher.is_public is False

    def test_from_config_missing_token(self):
        """Test creating publisher when token env var not set."""
        config = MagicMock()
        config.target_account = "config-account"
        config.pat_env_var = "MISSING_PAT"
        config.is_public = True

        with patch.dict('os.environ', {}, clear=True):
            publisher = GistPublisher.from_config(config)

        assert publisher.target_account == "config-account"
        assert publisher.is_available() is False
