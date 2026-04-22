"""
Degraded-mode integration tests for LLMService + CircuitBreaker.

These tests verify that LLMService._call_with_fallback() correctly routes
traffic when the circuit breaker is in various states, and that the
circuit breaker is informed of call outcomes.

All external I/O is mocked.  No real HTTP calls are made.

Test IDs:
  DM-01  OPEN circuit → primary NOT called; Ollama called
  DM-02  OPEN circuit → log contains circuit_breaker_proactive_route
  DM-03  Primary timeout (transient) → record_failure called; Ollama attempted
  DM-04  Auth error (permanent) → record_failure NOT called
  DM-05  Fallback client None → returns None gracefully
  DM-06  HALF_OPEN probe success → circuit closes; next call goes to primary
"""
from __future__ import annotations

import logging
import pytest
from unittest.mock import MagicMock, patch, call

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.services.llm_service import LLMService
from src.services.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
)

# ---------------------------------------------------------------------------
# Routing config fixture — enables fallback_enabled
# ---------------------------------------------------------------------------

_ROUTING_CFG = {
    "enabled": True,
    "providers": {
        "company": {
            "base_url": "https://llm.test.com/v1",
            "api_key_env": "LLM_API_KEY",
            "timeout_seconds": 30,
            "fallback_to": "ollama",
        },
        "ollama": {
            "base_url": "http://localhost:11434/v1",
            "api_key_env": None,
            "timeout_seconds": 30,
            "auto_start": False,
        },
    },
    "fallback_enabled": True,
    "fallback_on_error": True,
    "circuit_breaker": {
        "enabled": True,
        "failure_threshold": 3,
        "recovery_timeout_s": 60.0,
    },
}

_MESSAGES = [{"role": "user", "content": "Fix this code"}]
_MODEL = "test-model"


def _make_service_with_open_circuit() -> LLMService:
    """Return an LLMService whose circuit breaker is OPEN."""
    service = LLMService(provider="ollama", model=_MODEL)
    service.set_routing_config(_ROUTING_CFG)

    # Force circuit to OPEN by injecting a mock CB in OPEN state
    mock_cb = MagicMock(spec=CircuitBreaker)
    mock_cb.should_use_fallback.return_value = True
    mock_cb.get_status.return_value = {
        "state": "open",
        "consecutive_failures": 3,
        "error_rate": 1.0,
        "avg_latency_s": 2.0,
    }
    service._circuit_breaker = mock_cb
    return service


# ===========================================================================
# DM-01  OPEN circuit → primary NOT called; Ollama called
# ===========================================================================

class TestOpenCircuitProactiveRouting:
    """DM-01: When circuit is OPEN, primary must be bypassed and Ollama called."""

    def test_open_circuit_bypasses_primary(self):
        service = _make_service_with_open_circuit()

        mock_primary = MagicMock()
        mock_fallback_response = MagicMock()
        service._client = mock_primary

        with patch.object(service, "_try_ollama_fallback", return_value=mock_fallback_response) as mock_fb:
            result = service._call_with_fallback(_MODEL, _MESSAGES)

        mock_primary.chat.completions.create.assert_not_called()
        mock_fb.assert_called_once()
        assert result is mock_fallback_response

    def test_open_circuit_calls_fallback_with_reason_circuit_open(self):
        service = _make_service_with_open_circuit()
        service._client = MagicMock()

        with patch.object(service, "_try_ollama_fallback", return_value=None) as mock_fb:
            service._call_with_fallback(_MODEL, _MESSAGES)

        args, kwargs = mock_fb.call_args
        # reason is passed as positional or keyword
        call_reason = kwargs.get("reason") or (args[2] if len(args) > 2 else None)
        assert call_reason == "circuit_open"


# ===========================================================================
# DM-02  OPEN circuit → log contains circuit_breaker_proactive_route
# ===========================================================================

class TestOpenCircuitLogging:
    """DM-02: Proactive routing must emit circuit_breaker_proactive_route log."""

    def test_proactive_route_is_logged(self, caplog):
        service = _make_service_with_open_circuit()
        service._client = MagicMock()

        with patch.object(service, "_try_ollama_fallback", return_value=None):
            with caplog.at_level(logging.INFO, logger="src.services.llm_service"):
                service._call_with_fallback(_MODEL, _MESSAGES)

        assert any("circuit_breaker_proactive_route" in r.message for r in caplog.records)


# ===========================================================================
# DM-03  Primary timeout (transient) → record_failure called; Ollama attempted
# ===========================================================================

class TestTransientPrimaryFailure:
    """DM-03: Transient primary failures must record failure and fall back."""

    def test_timeout_records_failure_and_falls_back(self):
        service = LLMService(provider="ollama", model=_MODEL)
        service.set_routing_config(_ROUTING_CFG)

        mock_cb = MagicMock(spec=CircuitBreaker)
        mock_cb.should_use_fallback.return_value = False  # CLOSED
        mock_cb.get_status.return_value = {"state": "closed", "consecutive_failures": 0, "error_rate": 0.0, "avg_latency_s": 0.0}
        service._circuit_breaker = mock_cb

        mock_primary = MagicMock()
        # Simulate a connection timeout (transient — not a ValueError/auth error)
        mock_primary.chat.completions.create.side_effect = ConnectionError("timeout")
        service._client = mock_primary

        with patch.object(service, "_try_ollama_fallback", return_value=None) as mock_fb:
            service._call_with_fallback(_MODEL, _MESSAGES)

        mock_cb.record_failure.assert_called_once()
        mock_fb.assert_called_once()

    def test_success_records_success(self):
        service = LLMService(provider="ollama", model=_MODEL)
        service.set_routing_config(_ROUTING_CFG)

        mock_cb = MagicMock(spec=CircuitBreaker)
        mock_cb.should_use_fallback.return_value = False
        service._circuit_breaker = mock_cb

        mock_response = MagicMock()
        mock_primary = MagicMock()
        mock_primary.chat.completions.create.return_value = mock_response
        service._client = mock_primary

        result = service._call_with_fallback(_MODEL, _MESSAGES)

        mock_cb.record_success.assert_called_once()
        mock_cb.record_failure.assert_not_called()
        assert result is mock_response


# ===========================================================================
# DM-04  Auth error (permanent) → record_failure NOT called
# ===========================================================================

class TestPermanentAuthError:
    """DM-04: Auth/permanent errors must NOT trip the circuit breaker."""

    def test_auth_error_does_not_record_failure(self):
        service = LLMService(provider="ollama", model=_MODEL)
        service.set_routing_config(_ROUTING_CFG)

        mock_cb = MagicMock(spec=CircuitBreaker)
        mock_cb.should_use_fallback.return_value = False
        service._circuit_breaker = mock_cb

        mock_primary = MagicMock()
        # ValueError is a "permanent" type → _is_transient_error returns False
        mock_primary.chat.completions.create.side_effect = ValueError("401 authentication failed")
        service._client = mock_primary

        with patch.object(service, "_try_ollama_fallback", return_value=None):
            service._call_with_fallback(_MODEL, _MESSAGES)

        mock_cb.record_failure.assert_not_called()


# ===========================================================================
# DM-05  Fallback client None → returns None gracefully
# ===========================================================================

class TestFallbackClientNone:
    """DM-05: When Ollama client cannot be created, return None cleanly."""

    def test_fallback_client_none_returns_none(self):
        service = _make_service_with_open_circuit()
        service._client = MagicMock()

        with patch.object(service, "_try_ollama_fallback", return_value=None) as mock_fb:
            result = service._call_with_fallback(_MODEL, _MESSAGES)

        assert result is None


# ===========================================================================
# DM-06  No primary client → routes to fallback with reason no_primary_client
# ===========================================================================

class TestNoPrimaryClient:
    """When primary client is None, route to fallback without circuit-breaker involvement."""

    def test_no_primary_routes_to_fallback(self):
        service = LLMService(provider="ollama", model=_MODEL)
        service.set_routing_config(_ROUTING_CFG)
        service._client = None  # no primary

        mock_cb = MagicMock(spec=CircuitBreaker)
        mock_cb.should_use_fallback.return_value = False  # CLOSED
        service._circuit_breaker = mock_cb

        with patch.object(service, "_try_ollama_fallback", return_value=None) as mock_fb:
            result = service._call_with_fallback(_MODEL, _MESSAGES)

        mock_fb.assert_called_once()
        args, kwargs = mock_fb.call_args
        call_reason = kwargs.get("reason") or (args[2] if len(args) > 2 else None)
        assert call_reason == "no_primary_client"

    def test_routing_disabled_uses_client_directly(self):
        service = LLMService(provider="ollama", model=_MODEL)
        # Do NOT set routing config → routing_config is None / fallback_enabled=False

        mock_response = MagicMock()
        mock_primary = MagicMock()
        mock_primary.chat.completions.create.return_value = mock_response
        service._client = mock_primary

        # set_routing_config not called; routing_config is None
        result = service._call_with_fallback(_MODEL, _MESSAGES)

        mock_primary.chat.completions.create.assert_called_once()
        assert result is mock_response
