"""Tests for ModelDiscoveryService (TASK-4A)."""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock

from src.services.model_discovery_service import ModelDiscoveryService


class TestModelDiscoveryServiceInit:
    """Test ModelDiscoveryService initialization."""

    def test_init_with_api_key(self):
        """Test initialization with explicit API key."""
        svc = ModelDiscoveryService(
            base_url="https://api.example.com/v1",
            api_key="test-key-123"
        )
        assert svc.base_url == "https://api.example.com/v1"
        assert svc.api_key == "test-key-123"
        assert svc.timeout_seconds == 10

    def test_init_without_api_key_no_env(self):
        """Test initialization without API key when no env vars set."""
        with patch.dict(os.environ, {}, clear=True):
            svc = ModelDiscoveryService(base_url="https://api.example.com/v1")
            assert svc.api_key is None

    def test_init_strips_trailing_slash(self):
        """Test that trailing slash is removed from base_url."""
        svc = ModelDiscoveryService(
            base_url="https://api.example.com/v1/",
            api_key="test-key"
        )
        assert svc.base_url == "https://api.example.com/v1"

    def test_init_custom_timeout(self):
        """Test initialization with custom timeout."""
        svc = ModelDiscoveryService(
            base_url="https://api.example.com/v1",
            api_key="test-key",
            timeout_seconds=30
        )
        assert svc.timeout_seconds == 30


class TestModelDiscoveryServiceEnvVars:
    """Test environment variable handling."""

    def test_get_api_key_from_llm_api_key_env(self):
        """Test reading from LLM_API_KEY environment variable."""
        with patch.dict(os.environ, {"LLM_API_KEY": "from-llm-api-key"}):
            svc = ModelDiscoveryService(base_url="https://api.example.com/v1")
            assert svc.api_key == "from-llm-api-key"

    def test_get_api_key_from_litellm_key_env(self):
        """Test reading from LITELLM_KEY environment variable."""
        # Clear all potential API key env vars, then set only LITELLM_KEY
        env = {k: v for k, v in os.environ.items() if k not in ModelDiscoveryService.API_KEY_ENV_VARS}
        env["LITELLM_KEY"] = "from-litellm-key"
        with patch.dict(os.environ, env, clear=True):
            svc = ModelDiscoveryService(base_url="https://api.example.com/v1")
            assert svc.api_key == "from-litellm-key"

    def test_get_api_key_from_openai_api_key_env(self):
        """Test reading from OPENAI_API_KEY environment variable."""
        # Clear all potential API key env vars, then set only OPENAI_API_KEY
        env = {k: v for k, v in os.environ.items() if k not in ModelDiscoveryService.API_KEY_ENV_VARS}
        env["OPENAI_API_KEY"] = "from-openai-key"
        with patch.dict(os.environ, env, clear=True):
            svc = ModelDiscoveryService(base_url="https://api.example.com/v1")
            assert svc.api_key == "from-openai-key"

    def test_api_key_priority_order(self):
        """Test that LLM_API_KEY takes priority over others."""
        env = {
            "LLM_API_KEY": "priority-one",
            "LITELLM_KEY": "priority-two",
            "OPENAI_API_KEY": "priority-three"
        }
        with patch.dict(os.environ, env):
            svc = ModelDiscoveryService(base_url="https://api.example.com/v1")
            assert svc.api_key == "priority-one"

    def test_explicit_api_key_overrides_env(self):
        """Test that explicit API key parameter overrides environment variables."""
        with patch.dict(os.environ, {"LLM_API_KEY": "from-env"}):
            svc = ModelDiscoveryService(
                base_url="https://api.example.com/v1",
                api_key="explicit-key"
            )
            assert svc.api_key == "explicit-key"


class TestModelDiscoveryServiceDiscoverModels:
    """Test model discovery from endpoint."""

    @patch("src.services.model_discovery_service.requests.get")
    def test_discover_models_success(self, mock_get):
        """Test successful model discovery."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"id": "qwen2.5-coder:7b", "object": "model"},
                {"id": "qwen2.5:13b", "object": "model"},
                {"id": "qwen2.5:70b", "object": "model"},
            ]
        }
        mock_get.return_value = mock_response

        svc = ModelDiscoveryService(
            base_url="https://api.example.com/v1",
            api_key="test-key"
        )
        models = svc.discover_models()

        assert len(models) == 3
        assert models[0]["id"] == "qwen2.5-coder:7b"
        mock_get.assert_called_once()

    @patch("src.services.model_discovery_service.requests.get")
    def test_discover_models_caching(self, mock_get):
        """Test that models are cached after first discovery."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"id": "model-1", "object": "model"}]
        }
        mock_get.return_value = mock_response

        svc = ModelDiscoveryService(
            base_url="https://api.example.com/v1",
            api_key="test-key"
        )

        # First call should query endpoint
        models1 = svc.discover_models()
        assert len(models1) == 1

        # Second call should use cache (mock not called again)
        models2 = svc.discover_models()
        assert len(models2) == 1
        assert mock_get.call_count == 1  # Only called once

    @patch("src.services.model_discovery_service.requests.get")
    def test_discover_models_force_refresh(self, mock_get):
        """Test force_refresh bypasses cache."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"id": "model-1", "object": "model"}]
        }
        mock_get.return_value = mock_response

        svc = ModelDiscoveryService(
            base_url="https://api.example.com/v1",
            api_key="test-key"
        )

        svc.discover_models()
        svc.discover_models(force_refresh=True)

        assert mock_get.call_count == 2

    @patch("src.services.model_discovery_service.requests.get")
    def test_discover_models_auth_failure_401(self, mock_get):
        """Test handling of 401 Unauthorized response."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        svc = ModelDiscoveryService(
            base_url="https://api.example.com/v1",
            api_key="bad-key"
        )
        models = svc.discover_models()

        assert models == []

    @patch("src.services.model_discovery_service.requests.get")
    def test_discover_models_forbidden_403(self, mock_get):
        """Test handling of 403 Forbidden response."""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_get.return_value = mock_response

        svc = ModelDiscoveryService(
            base_url="https://api.example.com/v1",
            api_key="insufficient-perms-key"
        )
        models = svc.discover_models()

        assert models == []

    @patch("src.services.model_discovery_service.requests.get")
    def test_discover_models_not_found_404(self, mock_get):
        """Test handling of 404 Not Found response."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        svc = ModelDiscoveryService(
            base_url="https://api.example.com/v1",
            api_key="test-key"
        )
        models = svc.discover_models()

        assert models == []

    @patch("src.services.model_discovery_service.requests.get")
    def test_discover_models_service_unavailable_503(self, mock_get):
        """Test handling of 503 Service Unavailable response."""
        mock_response = Mock()
        mock_response.status_code = 503
        mock_get.return_value = mock_response

        svc = ModelDiscoveryService(
            base_url="https://api.example.com/v1",
            api_key="test-key"
        )
        models = svc.discover_models()

        assert models == []

    @patch("src.services.model_discovery_service.requests.get")
    def test_discover_models_timeout(self, mock_get):
        """Test handling of request timeout."""
        import requests
        mock_get.side_effect = requests.exceptions.Timeout()

        svc = ModelDiscoveryService(
            base_url="https://api.example.com/v1",
            api_key="test-key"
        )
        models = svc.discover_models()

        assert models == []

    @patch("src.services.model_discovery_service.requests.get")
    def test_discover_models_connection_error(self, mock_get):
        """Test handling of connection error."""
        import requests
        mock_get.side_effect = requests.exceptions.ConnectionError()

        svc = ModelDiscoveryService(
            base_url="https://api.example.com/v1",
            api_key="test-key"
        )
        models = svc.discover_models()

        assert models == []

    @patch("src.services.model_discovery_service.requests.get")
    def test_discover_models_invalid_json(self, mock_get):
        """Test handling of invalid JSON response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response

        svc = ModelDiscoveryService(
            base_url="https://api.example.com/v1",
            api_key="test-key"
        )
        models = svc.discover_models()

        assert models == []

    def test_discover_models_no_api_key(self):
        """Test that discovery fails gracefully without API key."""
        svc = ModelDiscoveryService(
            base_url="https://api.example.com/v1",
            api_key=None
        )
        models = svc.discover_models()

        assert models == []


class TestModelDiscoveryServiceMapToTiers:
    """Test model tier mapping."""

    def test_map_to_tiers_basic(self):
        """Test basic tier mapping with clear patterns."""
        models = [
            {"id": "mistral-7b", "object": "model"},
            {"id": "llama2-13b", "object": "model"},
            {"id": "falcon-70b", "object": "model"},
        ]

        svc = ModelDiscoveryService(
            base_url="https://api.example.com/v1",
            api_key="test-key"
        )
        tiers = svc.map_to_tiers(models)

        assert tiers.get("small") == "mistral-7b"
        assert tiers.get("medium") == "llama2-13b"
        assert tiers.get("large") == "falcon-70b"

    def test_map_to_tiers_with_descriptive_names(self):
        """Test tier mapping with descriptive model names."""
        models = [
            {"id": "compact-small-model", "object": "model"},
            {"id": "balanced-medium-model", "object": "model"},
            {"id": "powerful-large-model", "object": "model"},
        ]

        svc = ModelDiscoveryService(
            base_url="https://api.example.com/v1",
            api_key="test-key"
        )
        tiers = svc.map_to_tiers(models)

        assert tiers.get("small") == "compact-small-model"
        assert tiers.get("medium") == "balanced-medium-model"
        assert tiers.get("large") == "powerful-large-model"

    def test_map_to_tiers_with_mini_pattern(self):
        """Test tier mapping with 'mini' pattern for small."""
        models = [
            {"id": "tinyllm-mini", "object": "model"},
        ]

        svc = ModelDiscoveryService(
            base_url="https://api.example.com/v1",
            api_key="test-key"
        )
        tiers = svc.map_to_tiers(models)

        assert tiers.get("small") == "tinyllm-mini"

    def test_map_to_tiers_with_xl_pattern(self):
        """Test tier mapping with 'xl' pattern for large."""
        models = [
            {"id": "gigantictransformer-xl", "object": "model"},
        ]

        svc = ModelDiscoveryService(
            base_url="https://api.example.com/v1",
            api_key="test-key"
        )
        tiers = svc.map_to_tiers(models)

        assert tiers.get("large") == "gigantictransformer-xl"

    def test_map_to_tiers_partial_matches(self):
        """Test that only available tiers are returned."""
        models = [
            {"id": "model-7b", "object": "model"},
        ]

        svc = ModelDiscoveryService(
            base_url="https://api.example.com/v1",
            api_key="test-key"
        )
        tiers = svc.map_to_tiers(models)

        assert len(tiers) == 1
        assert "small" in tiers
        assert "medium" not in tiers
        assert "large" not in tiers

    def test_map_to_tiers_empty_models(self):
        """Test mapping with empty model list."""
        svc = ModelDiscoveryService(
            base_url="https://api.example.com/v1",
            api_key="test-key"
        )
        tiers = svc.map_to_tiers([])

        assert tiers == {}

    def test_map_to_tiers_no_matching_patterns(self):
        """Test mapping when no models match tier patterns."""
        models = [
            {"id": "custom-model-abc", "object": "model"},
            {"id": "other-model-xyz", "object": "model"},
        ]

        svc = ModelDiscoveryService(
            base_url="https://api.example.com/v1",
            api_key="test-key"
        )
        tiers = svc.map_to_tiers(models)

        assert tiers == {}

    def test_map_to_tiers_case_insensitive(self):
        """Test that pattern matching is case-insensitive."""
        models = [
            {"id": "Model-7B", "object": "model"},
            {"id": "Model-13B", "object": "model"},
            {"id": "Model-70B", "object": "model"},
        ]

        svc = ModelDiscoveryService(
            base_url="https://api.example.com/v1",
            api_key="test-key"
        )
        tiers = svc.map_to_tiers(models)

        assert "small" in tiers
        assert "medium" in tiers
        assert "large" in tiers

    def test_map_to_tiers_first_match_wins(self):
        """Test that first matching model is selected for each tier."""
        models = [
            {"id": "first-7b", "object": "model"},
            {"id": "second-7b", "object": "model"},
        ]

        svc = ModelDiscoveryService(
            base_url="https://api.example.com/v1",
            api_key="test-key"
        )
        tiers = svc.map_to_tiers(models)

        # First 7b model should be selected
        assert tiers.get("small") == "first-7b"


class TestModelDiscoveryServiceGetBestModelForTier:
    """Test getting best model for specific tier."""

    def test_get_best_model_for_tier_small(self):
        """Test getting small tier model."""
        models = [
            {"id": "model-7b", "object": "model"},
            {"id": "model-13b", "object": "model"},
            {"id": "model-70b", "object": "model"},
        ]

        svc = ModelDiscoveryService(
            base_url="https://api.example.com/v1",
            api_key="test-key"
        )
        model = svc.get_best_model_for_tier("small", models)

        assert model == "model-7b"

    def test_get_best_model_for_tier_medium(self):
        """Test getting medium tier model."""
        models = [
            {"id": "model-7b", "object": "model"},
            {"id": "model-13b", "object": "model"},
            {"id": "model-70b", "object": "model"},
        ]

        svc = ModelDiscoveryService(
            base_url="https://api.example.com/v1",
            api_key="test-key"
        )
        model = svc.get_best_model_for_tier("medium", models)

        assert model == "model-13b"

    def test_get_best_model_for_tier_large(self):
        """Test getting large tier model."""
        models = [
            {"id": "model-7b", "object": "model"},
            {"id": "model-13b", "object": "model"},
            {"id": "model-70b", "object": "model"},
        ]

        svc = ModelDiscoveryService(
            base_url="https://api.example.com/v1",
            api_key="test-key"
        )
        model = svc.get_best_model_for_tier("large", models)

        assert model == "model-70b"

    def test_get_best_model_for_tier_not_found(self):
        """Test when tier is not found."""
        models = [
            {"id": "model-7b", "object": "model"},
        ]

        svc = ModelDiscoveryService(
            base_url="https://api.example.com/v1",
            api_key="test-key"
        )
        model = svc.get_best_model_for_tier("medium", models)

        assert model is None


class TestModelDiscoveryServiceValidateEndpoint:
    """Test endpoint validation."""

    @patch("src.services.model_discovery_service.requests.get")
    def test_validate_endpoint_success(self, mock_get):
        """Test successful endpoint validation."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        svc = ModelDiscoveryService(
            base_url="https://api.example.com/v1",
            api_key="test-key"
        )
        is_valid = svc.validate_endpoint()

        assert is_valid is True

    @patch("src.services.model_discovery_service.requests.get")
    def test_validate_endpoint_auth_failure(self, mock_get):
        """Test endpoint validation with auth failure."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        svc = ModelDiscoveryService(
            base_url="https://api.example.com/v1",
            api_key="bad-key"
        )
        is_valid = svc.validate_endpoint()

        assert is_valid is False

    @patch("src.services.model_discovery_service.requests.get")
    def test_validate_endpoint_connection_error(self, mock_get):
        """Test endpoint validation with connection error."""
        import requests
        mock_get.side_effect = requests.exceptions.ConnectionError()

        svc = ModelDiscoveryService(
            base_url="https://api.example.com/v1",
            api_key="test-key"
        )
        is_valid = svc.validate_endpoint()

        assert is_valid is False

    def test_validate_endpoint_no_api_key(self):
        """Test endpoint validation fails without API key."""
        svc = ModelDiscoveryService(
            base_url="https://api.example.com/v1",
            api_key=None
        )
        is_valid = svc.validate_endpoint()

        assert is_valid is False


class TestModelDiscoveryServiceCacheManagement:
    """Test cache management."""

    def test_clear_cache(self):
        """Test clearing the cache."""
        svc = ModelDiscoveryService(
            base_url="https://api.example.com/v1",
            api_key="test-key"
        )

        # Manually set cache
        svc._models = [{"id": "test", "object": "model"}]
        svc._tiers = {"small": "test"}

        # Clear and verify
        svc.clear_cache()
        assert svc._models is None
        assert svc._tiers is None
