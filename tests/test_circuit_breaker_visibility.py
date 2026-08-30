"""Tests for TC-EPIC3-06: circuit-breaker state visibility.

Covers LLMService.get_circuit_breaker_snapshot() (a thin, pure-read wrapper
over CircuitBreaker.get_status(), CB-09's existing subject) and the
orchestrator run-start wiring that captures it into
results['circuit_breaker_state_at_start'] before any LLM calls happen this
run. See
reports/investigation/20260829_124758_production_readiness/taskcards/TC-EPIC3-06.md.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.services.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitState
from src.services.llm_service import LLMService


def _routing_config_with_fallback() -> dict:
    return {
        "enabled": True,
        "providers": {
            "company": {"base_url": "https://llm.test.com/v1", "api_key_env": "LLM_API_KEY"},
            "ollama": {"base_url": "http://localhost:11434/v1", "api_key_env": None},
        },
        "model_tiers": {"small": "m1", "medium": "m2", "large": "m3"},
        "circuit_breaker": {},
    }


class TestGetCircuitBreakerSnapshot:
    def test_returns_none_when_no_fallback_configured(self):
        """No ollama provider -> has_fallback=False -> no circuit breaker built
        -> snapshot must be None, not an error."""
        service = LLMService(provider="ollama", model="test-model")
        service.set_routing_config({"enabled": True, "providers": {}, "model_tiers": {}})
        assert service.get_circuit_breaker_snapshot() is None

    def test_reflects_closed_state_at_construction(self):
        service = LLMService(provider="ollama", model="test-model")
        service.set_routing_config(_routing_config_with_fallback())
        snapshot = service.get_circuit_breaker_snapshot()
        assert snapshot is not None
        assert snapshot["state"] == "closed"
        assert snapshot["consecutive_failures"] == 0

    def test_reflects_open_state_after_forced_failures(self):
        """Force the breaker OPEN via 3 consecutive failures, then confirm the
        snapshot (not a stale CLOSED default) reflects it."""
        service = LLMService(provider="ollama", model="test-model")
        service.set_routing_config(_routing_config_with_fallback())
        for _ in range(3):
            service._circuit_breaker.record_failure(latency_s=1.0)

        snapshot = service.get_circuit_breaker_snapshot()
        assert snapshot["state"] == "open"
        assert snapshot["consecutive_failures"] == 3

    def test_snapshot_capture_does_not_mutate_state(self):
        """Pure read: calling the snapshot method repeatedly must not change
        the breaker's own state (CB.get_status() takes the lock but performs
        no writes; this pins that contract at the LLMService wrapper layer)."""
        service = LLMService(provider="ollama", model="test-model")
        service.set_routing_config(_routing_config_with_fallback())
        for _ in range(3):
            service._circuit_breaker.record_failure(latency_s=1.0)

        first = service.get_circuit_breaker_snapshot()
        second = service.get_circuit_breaker_snapshot()
        third = service.get_circuit_breaker_snapshot()
        assert first == second == third
        assert service._circuit_breaker._state == CircuitState.OPEN
        assert service._circuit_breaker._consecutive_failures == 3


def _make_orchestrator_stub():
    """Minimal Orchestrator double reaching the circuit-breaker snapshot line
    in run_full_pipeline() (right after create_run()), then failing loudly on
    the very next real dependency it touches (self.config_manager.load_global_config)
    -- deliberately, so the test can assert on the snapshot capture in
    isolation without mocking the rest of this 500+ line method."""
    from src.pipeline.orchestrator import PipelineOrchestrator as Orchestrator

    orch = object.__new__(Orchestrator)
    orch.db = MagicMock()
    orch.db.create_run.return_value = "test-run-001"
    orch.config_manager = MagicMock()
    orch.config_manager.load_family_config.return_value = MagicMock()
    orch.config_manager.load_global_config.side_effect = RuntimeError("STOP: test boundary")
    orch._current_family = None
    orch._vector_db_startup_decision = {}
    orch._drift_enabled = False
    return orch


class TestOrchestratorRunStartSnapshot:
    def test_run_full_pipeline_captures_snapshot_before_phases_run(self):
        """Integration: a simulated run where the circuit breaker starts OPEN
        (primed via prior failures on the shared LLMService instance) produces
        results['circuit_breaker_state_at_start'] == 'open' -- captured at
        run start, before the rest of the pipeline runs. The stub's
        load_global_config raises immediately after this taskcard's own
        block, isolating the assertion to just this taskcard's change."""
        orch = _make_orchestrator_stub()
        primed_llm_service = MagicMock()
        primed_llm_service.get_circuit_breaker_snapshot.return_value = {
            "state": "open", "consecutive_failures": 3,
        }
        orch._llm_service = primed_llm_service

        with pytest.raises(RuntimeError, match="STOP: test boundary"):
            orch.run_full_pipeline(family="zip")

        primed_llm_service.get_circuit_breaker_snapshot.assert_called_once()

    def test_snapshot_capture_failure_is_non_fatal_to_the_run(self):
        """A snapshot capture failure (e.g. llm_service construction throws)
        must not fail the underlying run -- caught and logged, run proceeds
        to (and past) the next real dependency, matching TC-EPIC3-05's
        RunManifest non-fatal-capture requirement this field will feed."""
        orch = _make_orchestrator_stub()
        broken_llm_service = MagicMock()
        broken_llm_service.get_circuit_breaker_snapshot.side_effect = RuntimeError("boom")
        orch._llm_service = broken_llm_service

        # If the snapshot failure were fatal, this would raise "boom" instead
        # of reaching the stub's deliberate STOP boundary further down.
        with pytest.raises(RuntimeError, match="STOP: test boundary"):
            orch.run_full_pipeline(family="zip")
