"""
Unit tests for LLMService routing logic (TASK-4C).
Tests smart model routing based on error complexity.
"""

import pytest
import os
from unittest.mock import Mock, MagicMock, patch, call
from typing import Dict, Any, Optional, List

# Add parent directory to path
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.services.llm_service import LLMService, LLMResponse
from src.pipeline.error_complexity_classifier import ErrorComplexityClassifier


class TestLLMServiceRouting:
    """Tests for routing configuration and model selection."""

    def setup_method(self):
        """Setup test fixtures."""
        self.routing_config = {
            "enabled": True,
            "providers": {
                "company": {
                    "base_url": "https://llm.test.com/v1",
                    "api_key_env": "LLM_API_KEY",
                    "timeout_seconds": 120,
                    "fallback_to": "ollama"
                },
                "ollama": {
                    "base_url": "http://localhost:11434/v1",
                    "api_key_env": None,
                    "timeout_seconds": 120
                }
            },
            "model_tiers": {
                "small": "test-small-model",
                "medium": "test-medium-model",
                "large": "test-large-model"
            },
            "fallback_enabled": True,
            "track_cost": True
        }

    def test_set_routing_config(self):
        """Test setting routing configuration."""
        service = LLMService(provider="ollama", model="test-model")
        service.set_routing_config(self.routing_config)

        assert service.routing_enabled is True
        assert service.routing_config == self.routing_config

    def test_extract_error_code_from_logs(self):
        """Test extracting error code from error logs."""
        service = LLMService(provider="ollama", model="test-model")

        # Test CS0246 extraction
        logs = "error CS0246: The type or namespace name 'Archive' could not be found"
        error_code = service._extract_error_code_from_logs(logs)
        assert error_code == "CS0246"

        # Test CS0103 extraction
        logs = "error CS0103: The name 'x' does not exist in the current context"
        error_code = service._extract_error_code_from_logs(logs)
        assert error_code == "CS0103"

        # Test no error code
        logs = "Some generic error message"
        error_code = service._extract_error_code_from_logs(logs)
        assert error_code is None

        # Test multiple error codes (should get first)
        logs = "error CS0246: ... error CS0103: ..."
        error_code = service._extract_error_code_from_logs(logs)
        assert error_code == "CS0246"

    def test_select_model_for_error_simple(self):
        """Test model selection for simple errors."""
        service = LLMService(provider="ollama", model="default-model")
        service.set_routing_config(self.routing_config)

        # Simple error (missing type)
        model = service._select_model_for_error(
            "CS0246",
            "The type or namespace name 'Archive' could not be found"
        )
        assert model == "test-small-model"

    def test_select_model_for_error_medium(self):
        """Test model selection for medium complexity errors."""
        service = LLMService(provider="ollama", model="default-model")
        service.set_routing_config(self.routing_config)

        # Medium error (missing argument)
        model = service._select_model_for_error(
            "CS7036",
            "No overload for method 'Extract' takes 1 arguments"
        )
        assert model == "test-medium-model"

    def test_select_model_for_error_complex(self):
        """Test model selection for complex errors."""
        service = LLMService(provider="ollama", model="default-model")
        service.set_routing_config(self.routing_config)

        # Complex error (member not found)
        model = service._select_model_for_error(
            "CS1061",
            "Archive does not contain a definition for 'SaveAsync'"
        )
        assert model == "test-large-model"

    def test_get_tier_distribution(self):
        """Test tier distribution tracking."""
        service = LLMService(provider="ollama", model="default-model")
        service.set_routing_config(self.routing_config)

        # Simulate multiple routing decisions
        service._select_model_for_error("CS0246", "Missing type")
        service._select_model_for_error("CS7036", "Missing argument")
        service._select_model_for_error("CS1061", "Member not found")
        service._select_model_for_error("CS0246", "Missing type again")

        distribution = service.get_tier_distribution()
        assert distribution["small"] == 2
        assert distribution["medium"] == 1
        assert distribution["large"] == 1

    def test_get_routing_metadata(self):
        """Test getting routing metadata."""
        service = LLMService(provider="ollama", model="default-model")
        service.set_routing_config(self.routing_config)

        service._select_model_for_error("CS0246", "Missing type")
        service._select_model_for_error("CS1061", "Member not found")

        metadata = service.get_routing_metadata()
        assert metadata["routing_enabled"] is True
        assert "tier_distribution" in metadata
        assert "routed_models" in metadata
        assert metadata["routed_models"]["small"] == "test-small-model"
        assert metadata["routed_models"]["large"] == "test-large-model"

    def test_routing_disabled_uses_default_model(self):
        """Test that disabled routing uses default model."""
        service = LLMService(provider="ollama", model="default-model")
        # Don't enable routing

        model = service._select_model_for_error("CS0246", "Missing type")
        assert model == "default-model"

    def test_routing_without_config(self):
        """Test that routing without config uses default model."""
        service = LLMService(provider="ollama", model="default-model")
        service.routing_enabled = True
        service.routing_config = None

        model = service._select_model_for_error("CS0246", "Missing type")
        assert model == "default-model"


class TestLLMServiceFallback:
    """Tests for fallback chain implementation."""

    def setup_method(self):
        """Setup test fixtures."""
        self.routing_config = {
            "enabled": True,
            "providers": {
                "company": {
                    "base_url": "https://llm.test.com/v1",
                    "api_key_env": "LLM_API_KEY",
                    "timeout_seconds": 120,
                    "fallback_to": "ollama"
                },
                "ollama": {
                    "base_url": "http://localhost:11434/v1",
                    "api_key_env": None,
                    "timeout_seconds": 120
                }
            },
            "fallback_enabled": True
        }

    @patch('src.services.llm_service.OpenAI')
    def test_fallback_client_initialization(self, mock_openai):
        """Test fallback client initialization."""
        service = LLMService(provider="ollama", model="test-model")
        service.set_routing_config(self.routing_config)

        mock_openai_instance = MagicMock()
        mock_openai.return_value = mock_openai_instance

        fallback_client = service._get_fallback_client()

        assert fallback_client is not None
        mock_openai.assert_called_once()
        call_kwargs = mock_openai.call_args[1]
        assert call_kwargs["base_url"] == "http://localhost:11434/v1"
        assert call_kwargs["api_key"] == "ollama"

    @patch('src.services.llm_service.OpenAI')
    def test_fallback_client_caching(self, mock_openai):
        """Test fallback client caching."""
        service = LLMService(provider="ollama", model="test-model")
        service.set_routing_config(self.routing_config)

        mock_openai_instance = MagicMock()
        mock_openai.return_value = mock_openai_instance

        # First call
        client1 = service._get_fallback_client()
        # Second call (should be cached)
        client2 = service._get_fallback_client()

        # Should only initialize once
        assert mock_openai.call_count == 1
        assert client1 is client2

    def test_fallback_client_no_config(self):
        """Test fallback client with no routing config."""
        service = LLMService(provider="ollama", model="test-model")

        fallback_client = service._get_fallback_client()
        assert fallback_client is None

    def test_fallback_client_no_ollama_config(self):
        """Test fallback client when Ollama not in config."""
        service = LLMService(provider="ollama", model="test-model")

        config = {"enabled": True, "providers": {}}
        service.set_routing_config(config)

        fallback_client = service._get_fallback_client()
        assert fallback_client is None


class TestCompleteMethodRouting:
    """Tests for routing integration in complete method."""

    def setup_method(self):
        """Setup test fixtures."""
        self.routing_config = {
            "enabled": True,
            "providers": {
                "company": {
                    "base_url": "https://llm.test.com/v1",
                    "api_key_env": "LLM_API_KEY",
                    "timeout_seconds": 120,
                    "fallback_to": "ollama"
                },
                "ollama": {
                    "base_url": "http://localhost:11434/v1",
                    "api_key_env": None,
                    "timeout_seconds": 120
                }
            },
            "model_tiers": {
                "small": "test-small-model",
                "medium": "test-medium-model",
                "large": "test-large-model"
            },
            "fallback_enabled": True
        }

    @patch('src.services.llm_service.OpenAI')
    def test_complete_with_error_logs_and_routing(self, mock_openai):
        """Test complete method with error logs and routing enabled."""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        service = LLMService(provider="ollama", model="default-model")
        service.set_routing_config(self.routing_config)

        # Mock the response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "fixed code"
        mock_response.choices[0].finish_reason = "stop"
        mock_response.model = "test-small-model"
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50
        mock_response.usage.total_tokens = 150

        mock_client.chat.completions.create.return_value = mock_response

        # Call complete with error logs (simple error)
        error_logs = "error CS0246: The type or namespace name 'Archive' could not be found"
        response = service.complete(
            prompt="Fix this code",
            error_logs=error_logs
        )

        assert response.success is True
        assert response.content == "fixed code"
        # Verify the small model was used
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "test-small-model"

    @patch('src.services.llm_service.OpenAI')
    def test_complete_without_routing(self, mock_openai):
        """Test complete method without routing uses default model."""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        service = LLMService(provider="ollama", model="default-model")
        # Don't enable routing

        # Mock the response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "fixed code"
        mock_response.choices[0].finish_reason = "stop"
        mock_response.model = "default-model"
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50
        mock_response.usage.total_tokens = 150

        mock_client.chat.completions.create.return_value = mock_response

        error_logs = "error CS0246: The type or namespace name 'Archive' could not be found"
        response = service.complete(
            prompt="Fix this code",
            error_logs=error_logs
        )

        assert response.success is True
        # Verify the default model was used (no routing)
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "default-model"


class TestTelemetryIntegration:
    """Tests for telemetry tracking of routing decisions."""

    def test_tier_distribution_tracking(self):
        """Test that tier distribution is tracked correctly."""
        service = LLMService(provider="ollama", model="test-model")

        routing_config = {
            "enabled": True,
            "model_tiers": {
                "small": "small-model",
                "medium": "medium-model",
                "large": "large-model"
            }
        }
        service.set_routing_config(routing_config)

        # Simulate various errors
        errors = [
            ("CS0246", "Missing type"),                      # small
            ("CS0246", "Missing type 2"),                    # small
            ("CS7036", "Missing argument"),                  # medium
            ("CS1061", "Member not found"),                  # large
            ("CS1061", "Another member error"),              # large
            ("CS1061", "Yet another"),                       # large
        ]

        for error_code, error_msg in errors:
            service._select_model_for_error(error_code, error_msg)

        dist = service.get_tier_distribution()
        assert dist["small"] == 2
        assert dist["medium"] == 1
        assert dist["large"] == 3

    def test_routed_models_tracking(self):
        """Test that routed models are tracked."""
        service = LLMService(provider="ollama", model="test-model")

        routing_config = {
            "enabled": True,
            "model_tiers": {
                "small": "gpt-3.5-turbo",
                "medium": "gpt-4",
                "large": "gpt-4-turbo"
            }
        }
        service.set_routing_config(routing_config)

        service._select_model_for_error("CS0246", "Missing type")
        service._select_model_for_error("CS1061", "Member not found")

        metadata = service.get_routing_metadata()
        assert metadata["routed_models"]["small"] == "gpt-3.5-turbo"
        assert metadata["routed_models"]["large"] == "gpt-4-turbo"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
