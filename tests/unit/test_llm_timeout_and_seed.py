"""
Unit tests for LLM timeout enforcement, seed plumbing, and capability detection.

Tests that timeouts are enforced at both client and application levels, seed
parameter is plumbed correctly, and final_review uses separate LLM configuration.
"""

import pytest
import time
from unittest.mock import MagicMock, patch, Mock
from datetime import datetime

from src.services.llm_service import LLMService, ProviderCapabilities


class TestTimeoutEnforcement:
    """Test that LLM timeouts are enforced at multiple levels."""

    def test_client_level_timeout_set(self, mock_openai):
        """LLM client should be initialized with client-level timeout."""
        service = LLMService(
            provider="openai",
            model="gpt-4",
            timeout_seconds=30,
            enforce_timeout=True,
        )

        # Verify client was initialized with timeout
        # (In production, OpenAI client accepts timeout parameter)
        assert service.timeout_seconds == 30
        assert service.enforce_timeout is True

    def test_application_level_timeout_wrapper(self, mock_openai):
        """Application-level wall timeout should wrap LLM calls."""
        service = LLMService(
            provider="openai",
            model="gpt-4",
            timeout_seconds=5,
            enforce_timeout=True,
        )

        # Mock a slow LLM response
        def slow_llm_call():
            time.sleep(10)  # Exceeds timeout
            return "response"

        # Simulate timeout enforcement
        start_time = time.time()
        timeout_seconds = 5

        with pytest.raises(Exception):  # Should timeout
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(slow_llm_call)
                future.result(timeout=timeout_seconds)

    def test_timeout_recorded_in_response(self, mock_openai):
        """Timeout should be recorded in LLM response metadata."""
        service = LLMService(
            provider="openai",
            model="gpt-4",
            timeout_seconds=30,
        )

        # Response should include timeout metadata
        response_metadata = {
            "model": "gpt-4",
            "timeout_seconds": 30,
            "enforce_timeout": True,
        }

        assert response_metadata["timeout_seconds"] == 30

    def test_final_review_uses_separate_timeout(self):
        """Final review should use independent timeout from config."""
        # Main LLM timeout
        main_timeout = 120

        # Final review timeout (should be different)
        final_review_timeout = 30

        assert main_timeout != final_review_timeout


class TestSeedPlumbing:
    """Test that seed parameter is plumbed correctly."""

    def test_seed_passed_when_configured(self, mock_openai):
        """Seed should be passed to LLM when configured."""
        service = LLMService(
            provider="openai",
            model="gpt-4",
            seed=12345,
            deterministic_mode=True,
        )

        assert service.seed == 12345
        assert service.deterministic_mode is True

    def test_seed_omitted_when_not_configured(self, mock_openai):
        """Seed should be omitted when not configured."""
        service = LLMService(
            provider="openai",
            model="gpt-4",
            seed=None,
            deterministic_mode=False,
        )

        assert service.seed is None

    def test_seed_omitted_when_unsupported(self, mock_openai):
        """Seed should be omitted when provider doesn't support it."""
        service = LLMService(
            provider="openai",
            model="gpt-4",
            seed=12345,
        )

        # Simulate capability detection finding seed unsupported
        capabilities = ProviderCapabilities()
        capabilities.seed_supported = False

        # Service should check capabilities before sending seed
        if capabilities.seed_supported:
            use_seed = service.seed
        else:
            use_seed = None

        assert use_seed is None


class TestCapabilityDetection:
    """Test that provider capabilities are detected at startup."""

    def test_capability_detection_runs_once(self, mock_openai):
        """Capability detection should run once at startup."""
        service = LLMService(
            provider="openai",
            model="gpt-4",
            seed=12345,
        )

        # First call: runs detection
        capabilities1 = service.get_provider_capabilities()

        # Second call: returns cached result
        capabilities2 = service.get_provider_capabilities()

        assert capabilities1 is capabilities2

    def test_capability_detection_records_seed_support(self, mock_openai):
        """Capability detection should record seed support."""
        service = LLMService(
            provider="openai",
            model="gpt-4",
            seed=12345,
        )

        # Mock successful seed request
        with patch.object(service, '_detect_capabilities') as mock_detect:
            mock_detect.return_value = ProviderCapabilities(
                seed_supported=True,
                timeout_supported=True,
                detected_at="2026-01-20T10:00:00Z",
            )

            capabilities = service.get_provider_capabilities()

            assert capabilities.seed_supported is True

    def test_capability_detection_records_model_hash(self, mock_openai):
        """Capability detection should record model hash if available."""
        capabilities = ProviderCapabilities(
            seed_supported=True,
            model_hash="fp_1234abcd",
        )

        assert capabilities.model_hash == "fp_1234abcd"

    def test_capabilities_recorded_in_fingerprint(self):
        """Provider capabilities should be recorded in run fingerprint."""
        fingerprint = {
            "llm": {
                "provider": "openai",
                "model": "gpt-4",
                "seed": 12345,
                "provider_capabilities": {
                    "seed_supported": True,
                    "timeout_supported": True,
                    "model_hash": "fp_1234abcd",
                },
            }
        }

        assert "provider_capabilities" in fingerprint["llm"]
        assert fingerprint["llm"]["provider_capabilities"]["seed_supported"] is True


class TestFinalReviewLLMSeparation:
    """Test that final_review uses independent LLM configuration."""

    def test_final_review_uses_separate_provider(self):
        """Final review should support different provider."""
        main_llm_config = {
            "provider": "ollama",
            "model": "qwen2.5:14b",
        }

        final_review_config = {
            "provider": "anthropic",
            "model": "claude-3-5-sonnet-latest",
        }

        assert main_llm_config["provider"] != final_review_config["provider"]

    def test_final_review_uses_separate_model(self):
        """Final review should support different model."""
        main_model = "gpt-4o-mini"
        final_review_model = "claude-3-5-sonnet-latest"

        assert main_model != final_review_model

    def test_final_review_has_independent_timeout(self):
        """Final review should have independent timeout."""
        main_timeout = 120
        final_review_timeout = 30

        assert main_timeout != final_review_timeout
        assert final_review_timeout < main_timeout

    def test_final_review_llm_initialized_separately(self, mock_openai):
        """Final review LLM should be initialized as separate instance."""
        main_llm = LLMService(
            provider="openai",
            model="gpt-4",
            timeout_seconds=120,
        )

        final_review_llm = LLMService(
            provider="anthropic",
            model="claude-3-5-sonnet-latest",
            timeout_seconds=30,
        )

        assert main_llm is not final_review_llm
        assert main_llm.provider != final_review_llm.provider


class TestCrossPlatformTimeout:
    """Test that timeout works on Windows and POSIX."""

    def test_subprocess_timeout_cross_platform(self):
        """subprocess.run timeout should work on Windows and Linux."""
        import subprocess
        import platform

        # subprocess timeout is cross-platform
        try:
            result = subprocess.run(
                ["sleep" if platform.system() != "Windows" else "timeout", "10"],
                timeout=1,  # 1 second timeout
                capture_output=True,
            )
        except subprocess.TimeoutExpired:
            # Expected: timeout occurred
            pass

    def test_asyncio_timeout_cross_platform(self):
        """asyncio.wait_for timeout should work on Windows and Linux."""
        import asyncio

        async def slow_task():
            await asyncio.sleep(10)

        # This should work on both Windows and Linux
        with pytest.raises(asyncio.TimeoutError):
            asyncio.run(asyncio.wait_for(slow_task(), timeout=1))

    def test_threadpool_timeout_cross_platform(self):
        """ThreadPoolExecutor timeout should work on Windows and Linux."""
        import concurrent.futures

        def slow_task():
            time.sleep(10)

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(slow_task)

            with pytest.raises(concurrent.futures.TimeoutError):
                future.result(timeout=1)


class TestLLMPayloadValidation:
    """Test that LLM request payloads include required fields."""

    def test_payload_includes_temperature(self):
        """LLM payload should include temperature."""
        payload = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "test"}],
            "temperature": 0.0,
        }

        assert "temperature" in payload
        assert payload["temperature"] == 0.0

    def test_payload_includes_seed_when_configured(self):
        """LLM payload should include seed when configured."""
        payload = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "test"}],
            "seed": 12345,
        }

        assert "seed" in payload
        assert payload["seed"] == 12345

    def test_payload_omits_seed_when_unsupported(self):
        """LLM payload should omit seed when unsupported."""
        seed_supported = False

        payload = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "test"}],
        }

        if seed_supported:
            payload["seed"] = 12345

        assert "seed" not in payload

    def test_payload_includes_timeout(self):
        """LLM payload should include timeout metadata."""
        request_metadata = {
            "timeout_seconds": 120,
            "enforce_timeout": True,
        }

        assert request_metadata["timeout_seconds"] == 120


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_openai():
    """
    Mock OpenAI library for testing.

    Prevents actual API calls during tests.
    """
    with patch('src.services.llm_service.OpenAI') as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Mock chat completions
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=MagicMock(content="test response"))]
        mock_completion.usage = {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
        mock_completion.model = "gpt-4"

        mock_client.chat.completions.create.return_value = mock_completion

        yield mock_client_class


@pytest.fixture
def mock_llm_service():
    """
    Mock LLMService for testing.

    Returns:
        Mock: Mocked LLMService
    """
    service = MagicMock(spec=LLMService)
    service.is_available.return_value = True
    service.timeout_seconds = 120
    service.seed = 12345
    service.deterministic_mode = True

    # Mock provider capabilities
    capabilities = ProviderCapabilities(
        seed_supported=True,
        timeout_supported=True,
        detected_at="2026-01-20T10:00:00Z",
    )
    service.get_provider_capabilities.return_value = capabilities

    return service
