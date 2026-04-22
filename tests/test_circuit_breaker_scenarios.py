"""
Circuit breaker state machine scenario tests.

Tests every transition, threshold, and recovery path of the CircuitBreaker
passive health monitor.  All tests are pure unit tests: no I/O, no network,
no external services.  Clock-dependent recovery-timeout tests manipulate
``_open_since`` directly rather than sleeping.

Test IDs map to scenarios in docs/architecture.md Section 6.4:
  CB-01  CLOSED → OPEN via consecutive failures
  CB-02  CLOSED → OPEN via error-rate threshold
  CB-03  CLOSED → OPEN via latency threshold
  CB-04  CLOSED stays CLOSED below all thresholds
  CB-05  OPEN → HALF_OPEN after recovery timeout
  CB-06  OPEN blocks primary before recovery timeout
  CB-07  HALF_OPEN → CLOSED on probe success
  CB-08  HALF_OPEN → OPEN on probe failure (resets timer)
  CB-09  get_status returns all required fields
  CB-10  build_circuit_breaker_from_config: disabled when no fallback
  CB-11  build_circuit_breaker_from_config: custom thresholds respected
  CB-12  build_circuit_breaker_from_config: defaults applied for empty config
"""
from __future__ import annotations

import time
import pytest

from src.services.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    build_circuit_breaker_from_config,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_cb(**overrides) -> CircuitBreaker:
    """Create a CircuitBreaker with default config, overriding specific fields."""
    defaults = dict(
        failure_threshold=3,
        error_rate_threshold=0.5,
        window_size=10,
        latency_threshold_s=30.0,
        recovery_timeout_s=60.0,
    )
    defaults.update(overrides)
    cfg = CircuitBreakerConfig(enabled=True, **defaults)
    return CircuitBreaker(cfg)


def _trip_to_open(cb: CircuitBreaker, n: int = 3, latency_s: float = 1.0) -> None:
    """Record n consecutive failures to trip the breaker to OPEN."""
    for _ in range(n):
        cb.record_failure(latency_s=latency_s)


# ===========================================================================
# CB-01  CLOSED → OPEN via consecutive failures
# ===========================================================================

class TestClosedToOpenConsecutiveFailures:
    """CB-01: Three consecutive failures must trip the breaker to OPEN."""

    def test_three_consecutive_failures_trips_breaker(self):
        cb = _make_cb(failure_threshold=3)
        _trip_to_open(cb, n=3)
        assert cb._state == CircuitState.OPEN

    def test_open_since_is_set_after_trip(self):
        cb = _make_cb()
        _trip_to_open(cb, n=3)
        assert cb._open_since is not None

    def test_two_failures_do_not_trip(self):
        cb = _make_cb(failure_threshold=3)
        cb.record_failure(latency_s=1.0)
        cb.record_failure(latency_s=1.0)
        assert cb._state == CircuitState.CLOSED

    def test_single_failure_stays_closed(self):
        cb = _make_cb()
        cb.record_failure(latency_s=1.0)
        assert cb._state == CircuitState.CLOSED

    def test_success_resets_consecutive_counter(self):
        # Use error_rate_threshold=1.0 to disable the error-rate trip path,
        # so only the consecutive-failure threshold can open the circuit.
        cb = _make_cb(failure_threshold=3, error_rate_threshold=1.0)
        cb.record_failure(latency_s=1.0)
        cb.record_failure(latency_s=1.0)
        cb.record_success(latency_s=0.5)  # resets consecutive_failures to 0
        cb.record_failure(latency_s=1.0)
        cb.record_failure(latency_s=1.0)
        # Only 2 consecutive failures since last success (< threshold 3) → CLOSED
        assert cb._state == CircuitState.CLOSED


# ===========================================================================
# CB-02  CLOSED → OPEN via error-rate threshold
# ===========================================================================

class TestClosedToOpenErrorRate:
    """CB-02: Error rate > 50% in window must trip the breaker."""

    def test_error_rate_threshold_trips_breaker(self):
        # 6 failures + 4 successes = 60% error rate → OPEN
        cb = _make_cb(
            failure_threshold=100,  # disable consecutive threshold
            error_rate_threshold=0.5,
            window_size=10,
        )
        for _ in range(4):
            cb.record_success(latency_s=0.5)
        for _ in range(6):
            cb.record_failure(latency_s=1.0)
        assert cb._state == CircuitState.OPEN

    def test_below_error_rate_stays_closed(self):
        # 4 failures + 6 successes = 40% error rate → stays CLOSED
        cb = _make_cb(
            failure_threshold=100,
            error_rate_threshold=0.5,
            window_size=10,
        )
        for _ in range(6):
            cb.record_success(latency_s=0.5)
        for _ in range(4):
            cb.record_failure(latency_s=1.0)
        assert cb._state == CircuitState.CLOSED

    def test_insufficient_window_does_not_trip(self):
        # Only 1 failure in a window of 10 (need at least 5 data points)
        cb = _make_cb(
            failure_threshold=100,
            error_rate_threshold=0.5,
            window_size=10,
        )
        cb.record_failure(latency_s=1.0)
        assert cb._state == CircuitState.CLOSED


# ===========================================================================
# CB-03  CLOSED → OPEN via latency threshold
# ===========================================================================

class TestClosedToOpenLatency:
    """CB-03: Average latency > 30s must trip the breaker."""

    def test_high_latency_trips_breaker(self):
        # _evaluate() is only called from record_failure(); use failures with
        # high latency so the avg_latency check fires.
        # error_rate_threshold=1.0 means only 100% failure rate trips that path,
        # and with 2 items (< window_size/2=5) the error-rate check is skipped anyway.
        cb = _make_cb(
            failure_threshold=100,
            error_rate_threshold=1.0,   # disable error-rate trip path
            latency_threshold_s=30.0,
        )
        # Two failures both above threshold; avg = 35.5s > 30s → OPEN
        cb.record_failure(latency_s=35.0)
        cb.record_failure(latency_s=36.0)
        assert cb._state == CircuitState.OPEN

    def test_latency_below_threshold_stays_closed(self):
        cb = _make_cb(latency_threshold_s=30.0)
        cb.record_success(latency_s=25.0)
        cb.record_success(latency_s=20.0)
        assert cb._state == CircuitState.CLOSED

    def test_single_data_point_not_enough_for_latency_check(self):
        # Need at least 2 data points for latency threshold
        cb = _make_cb(
            failure_threshold=100,
            error_rate_threshold=1.0,
            latency_threshold_s=30.0,
        )
        cb.record_success(latency_s=35.0)
        # Only 1 point — latency check requires >= 2
        assert cb._state == CircuitState.CLOSED


# ===========================================================================
# CB-05  OPEN → HALF_OPEN after recovery timeout
# ===========================================================================

class TestOpenToHalfOpen:
    """CB-05: Recovery timeout elapsed → OPEN becomes HALF_OPEN; probe allowed."""

    def test_recovery_timeout_transitions_to_half_open(self):
        cb = _make_cb(recovery_timeout_s=60.0)
        _trip_to_open(cb, n=3)
        assert cb._state == CircuitState.OPEN

        # Simulate 61 seconds elapsed since open
        cb._open_since = time.time() - 61.0

        result = cb.should_use_fallback()
        assert result is False, "HALF_OPEN: probe call should go to primary"
        assert cb._state == CircuitState.HALF_OPEN

    def test_open_before_timeout_uses_fallback(self):
        cb = _make_cb(recovery_timeout_s=60.0)
        _trip_to_open(cb, n=3)

        # Do NOT advance the clock — still within recovery timeout
        result = cb.should_use_fallback()
        assert result is True, "OPEN: should route to fallback"
        assert cb._state == CircuitState.OPEN


# ===========================================================================
# CB-07  HALF_OPEN → CLOSED on probe success
# ===========================================================================

class TestHalfOpenToClosedOnSuccess:
    """CB-07: Successful probe call in HALF_OPEN closes the circuit."""

    def test_probe_success_closes_circuit(self):
        cb = _make_cb(recovery_timeout_s=60.0)
        _trip_to_open(cb, n=3)
        cb._open_since = time.time() - 61.0  # advance past timeout

        cb.should_use_fallback()  # → HALF_OPEN
        assert cb._state == CircuitState.HALF_OPEN

        cb.record_success(latency_s=0.5)
        assert cb._state == CircuitState.CLOSED

    def test_closed_after_probe_success_clears_open_since(self):
        cb = _make_cb(recovery_timeout_s=60.0)
        _trip_to_open(cb, n=3)
        cb._open_since = time.time() - 61.0

        cb.should_use_fallback()
        cb.record_success(latency_s=0.5)

        assert cb._open_since is None

    def test_should_use_fallback_returns_false_after_close(self):
        cb = _make_cb(recovery_timeout_s=60.0)
        _trip_to_open(cb, n=3)
        cb._open_since = time.time() - 61.0

        cb.should_use_fallback()
        cb.record_success(latency_s=0.5)

        assert cb.should_use_fallback() is False


# ===========================================================================
# CB-08  HALF_OPEN → OPEN on probe failure
# ===========================================================================

class TestHalfOpenToOpenOnFailure:
    """CB-08: Failed probe in HALF_OPEN re-opens the circuit and resets timer."""

    def test_probe_failure_reopens_circuit(self):
        cb = _make_cb(recovery_timeout_s=60.0)
        _trip_to_open(cb, n=3)
        cb._open_since = time.time() - 61.0

        cb.should_use_fallback()  # → HALF_OPEN
        cb.record_failure(latency_s=1.0)  # probe fails → OPEN

        assert cb._state == CircuitState.OPEN

    def test_probe_failure_resets_open_since(self):
        cb = _make_cb(recovery_timeout_s=60.0)
        _trip_to_open(cb, n=3)
        old_open_since = cb._open_since
        cb._open_since = time.time() - 61.0

        cb.should_use_fallback()
        t_before = time.time()
        cb.record_failure(latency_s=1.0)
        t_after = time.time()

        assert cb._open_since is not None
        assert cb._open_since >= t_before
        assert cb._open_since <= t_after

    def test_should_use_fallback_true_after_probe_failure(self):
        cb = _make_cb(recovery_timeout_s=60.0)
        _trip_to_open(cb, n=3)
        cb._open_since = time.time() - 61.0

        cb.should_use_fallback()
        cb.record_failure(latency_s=1.0)

        # Now back in OPEN with a fresh timer — should block primary
        assert cb.should_use_fallback() is True


# ===========================================================================
# CB-09  get_status returns all required fields
# ===========================================================================

class TestGetStatus:
    """CB-09: get_status must return all required diagnostic fields."""

    def test_get_status_returns_required_fields(self):
        cb = _make_cb()
        status = cb.get_status()
        required = {"state", "consecutive_failures", "window_size",
                    "window_capacity", "open_since", "error_rate", "avg_latency_s"}
        assert required <= set(status.keys()), (
            f"Missing keys: {required - set(status.keys())}"
        )

    def test_get_status_reflects_closed_state(self):
        cb = _make_cb()
        status = cb.get_status()
        assert status["state"] == "closed"
        assert status["consecutive_failures"] == 0
        assert status["open_since"] is None

    def test_get_status_reflects_open_state(self):
        cb = _make_cb()
        _trip_to_open(cb, n=3)
        status = cb.get_status()
        assert status["state"] == "open"
        assert status["consecutive_failures"] == 3
        assert status["open_since"] is not None


# ===========================================================================
# CB-10/11/12  build_circuit_breaker_from_config factory
# ===========================================================================

class TestBuildCircuitBreakerFromConfig:
    """CB-10/11/12: Factory creates correct CircuitBreaker or returns None."""

    def test_disabled_when_no_fallback(self):
        """CB-10: No fallback → circuit breaker disabled → returns None."""
        cb = build_circuit_breaker_from_config({}, has_fallback=False)
        assert cb is None

    def test_disabled_explicitly(self):
        cb = build_circuit_breaker_from_config({"enabled": False}, has_fallback=True)
        assert cb is None

    def test_enabled_when_fallback_available(self):
        """CB-11: Fallback present + default config → circuit breaker created."""
        cb = build_circuit_breaker_from_config({}, has_fallback=True)
        assert cb is not None
        assert isinstance(cb, CircuitBreaker)

    def test_custom_thresholds_respected(self):
        """CB-11: Custom config overrides defaults."""
        cfg = {
            "failure_threshold": 5,
            "error_rate_threshold": 0.3,
            "window_size": 20,
            "latency_threshold_s": 15.0,
            "recovery_timeout_s": 120.0,
        }
        cb = build_circuit_breaker_from_config(cfg, has_fallback=True)
        assert cb._config.failure_threshold == 5
        assert cb._config.error_rate_threshold == 0.3
        assert cb._config.window_size == 20
        assert cb._config.latency_threshold_s == 15.0
        assert cb._config.recovery_timeout_s == 120.0

    def test_defaults_for_empty_config(self):
        """CB-12: Empty config dict uses default values."""
        cb = build_circuit_breaker_from_config({}, has_fallback=True)
        assert cb._config.failure_threshold == 3
        assert cb._config.error_rate_threshold == 0.5
        assert cb._config.window_size == 10
        assert cb._config.latency_threshold_s == 30.0
        assert cb._config.recovery_timeout_s == 60.0
