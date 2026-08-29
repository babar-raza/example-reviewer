"""Tests for TC-EPIC1-06: HTTP fail-closed auth via PDP.

Covers the HTTP transport boundary in src/http_server.py: fail-closed auth
(replacing the old ``if not API_KEY: return await call_next(request)`` fail-open
default), constant-time bearer comparison, CORS wildcard+credentials rejection,
request-body size limits, in-process rate limiting, and bounded REQUEST_TIMEOUT
parsing. See
reports/investigation/20260829_124758_production_readiness/taskcards/TC-EPIC1-06.md
for the taskcard this file closes out.

tests/test_http_server.py's existing 155 lines of tool-call-plumbing coverage are
migrated separately (its ``client`` fixture now opts into
EXAMPLE_REVIEWER_DEV_MODE=true) -- this file owns all auth/CORS/rate-limit/body-size
coverage so that migration doesn't have to also become a security test suite.
"""

import logging
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from src.core.authority.policies.http_boundary import http_access_policy, validate_cors_config
from src.mcp_tools.tools import ToolResult


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Every TestClient in these tests shares the host "testclient" -> the same
    rate-limiter bucket key -- reset before each test so tests can't bleed into
    each other's rate-limit budget."""
    from src.http_server import _rate_limiter

    _rate_limiter.reset()
    yield


def _mocked_mcp_server():
    mock_server = patch("src.http_server.mcp_server")
    return mock_server


class TestFailClosedAuth:
    def test_no_api_key_configured_refuses_service(self):
        """The core fix: an unset API key with no dev-mode opt-in refuses service
        (503), not the old fail-open "serve everything" default."""
        with patch("src.http_server.API_KEY", ""), patch("src.http_server.DEV_MODE", False):
            with patch("src.http_server.mcp_server"):
                from fastapi.testclient import TestClient
                from src.http_server import app

                tc = TestClient(app)
                resp = tc.get("/api/v1/tools")
                assert resp.status_code == 503
                assert resp.json()["policy_id"] == "http.auth.no_key_configured"

    def test_dev_mode_escape_hatch_serves_but_logs_warning(self, caplog):
        with patch("src.http_server.API_KEY", ""), patch("src.http_server.DEV_MODE", True):
            with patch("src.http_server.mcp_server"):
                from fastapi.testclient import TestClient
                from src.http_server import app

                tc = TestClient(app)
                with caplog.at_level(logging.WARNING, logger="src.http_server"):
                    resp = tc.get("/api/v1/tools")
                assert resp.status_code == 200
                assert any("DEV_MODE" in record.message for record in caplog.records)

    def test_healthz_always_reachable_regardless_of_auth_state(self):
        for dev_mode in (False, True):
            with patch("src.http_server.API_KEY", ""), patch("src.http_server.DEV_MODE", dev_mode):
                with patch("src.http_server.mcp_server"):
                    from fastapi.testclient import TestClient
                    from src.http_server import app

                    tc = TestClient(app)
                    resp = tc.get("/healthz")
                    assert resp.status_code == 200

    def test_valid_bearer_token_allowed(self):
        with patch("src.http_server.API_KEY", "secret123"), patch("src.http_server.DEV_MODE", False):
            with patch("src.http_server.mcp_server"):
                from fastapi.testclient import TestClient
                from src.http_server import app

                tc = TestClient(app)
                resp = tc.get("/api/v1/tools", headers={"Authorization": "Bearer secret123"})
                assert resp.status_code == 200

    def test_invalid_bearer_token_rejected(self):
        with patch("src.http_server.API_KEY", "secret123"), patch("src.http_server.DEV_MODE", False):
            with patch("src.http_server.mcp_server"):
                from fastapi.testclient import TestClient
                from src.http_server import app

                tc = TestClient(app)
                resp = tc.get("/api/v1/tools", headers={"Authorization": "Bearer wrong"})
                assert resp.status_code == 401
                assert resp.json()["policy_id"] == "http.auth.invalid_key"


class TestConstantTimeComparison:
    def test_bearer_comparison_uses_constant_time(self):
        """The policy body calls hmac.compare_digest for the bearer comparison,
        not `==` -- patch it and assert it's on the call path."""
        with patch(
            "src.core.authority.policies.http_boundary.hmac.compare_digest", return_value=True
        ) as mock_compare:
            decision = http_access_policy(
                "/api/v1/tools",
                {"check": "auth", "api_key": "secret123", "auth_header": "Bearer secret123", "dev_mode": False},
            )
        mock_compare.assert_called_once_with("Bearer secret123", "Bearer secret123")
        assert decision.allow is True
        assert decision.policy_id == "http.auth.valid_key"

    def test_old_timing_unsafe_comparison_replaced(self):
        """NEGATIVE CONTROL: the literal `==`-based bearer comparison is gone from
        src/http_server.py, and hmac.compare_digest is present in the policy body
        that replaced it."""
        repo_root = Path(__file__).resolve().parent.parent
        http_server_src = (repo_root / "src" / "http_server.py").read_text(encoding="utf-8")
        assert "auth_header ==" not in http_server_src

        policy_src = (
            repo_root / "src" / "core" / "authority" / "policies" / "http_boundary.py"
        ).read_text(encoding="utf-8")
        assert "hmac.compare_digest" in policy_src


class TestCorsHardening:
    def test_wildcard_cors_with_credentials_rejected_at_startup(self):
        with pytest.raises(RuntimeError):
            validate_cors_config(["*"], True)

    def test_wildcard_cors_without_credentials_allowed(self):
        validate_cors_config(["*"], False)  # must not raise

    def test_explicit_allowlist_with_credentials_allowed(self):
        validate_cors_config(["https://example.com"], True)  # must not raise


class TestRequestTimeoutParsing:
    def test_request_timeout_env_malformed_does_not_crash_process(self, caplog):
        from src.http_server import _parse_bounded_int_env

        with patch.dict(os.environ, {"EXAMPLE_REVIEWER_REQUEST_TIMEOUT": "not_a_number"}):
            with caplog.at_level(logging.WARNING):
                value = _parse_bounded_int_env("EXAMPLE_REVIEWER_REQUEST_TIMEOUT", 300, 1, 3600)
        assert value == 300
        assert any("not a valid integer" in record.message for record in caplog.records)

    def test_request_timeout_out_of_bounds_clamped_or_rejected(self, caplog):
        from src.http_server import _parse_bounded_int_env

        with patch.dict(os.environ, {"EXAMPLE_REVIEWER_REQUEST_TIMEOUT": "999999"}):
            with caplog.at_level(logging.WARNING):
                value = _parse_bounded_int_env("EXAMPLE_REVIEWER_REQUEST_TIMEOUT", 300, 1, 3600)
        assert value == 3600

        with patch.dict(os.environ, {"EXAMPLE_REVIEWER_REQUEST_TIMEOUT": "-5"}):
            value = _parse_bounded_int_env("EXAMPLE_REVIEWER_REQUEST_TIMEOUT", 300, 1, 3600)
        assert value == 1


class TestBodySizeLimit:
    def test_oversized_body_rejected(self):
        with patch("src.http_server.MAX_BODY_BYTES", 10):
            with patch("src.http_server.mcp_server"):
                from fastapi.testclient import TestClient
                from src.http_server import app

                tc = TestClient(app)
                resp = tc.post("/api/v1/tools/status", json={"family": "zip-family-name-longer-than-10-bytes"})
                assert resp.status_code == 413
                assert resp.json()["policy_id"] == "http.body_size.exceeded"

    def test_small_body_allowed(self):
        with patch("src.http_server.API_KEY", ""), patch("src.http_server.DEV_MODE", True):
            with patch("src.http_server.mcp_server") as mock_server:
                mock_server.call_tool.return_value = ToolResult(success=True, data={})

                from fastapi.testclient import TestClient
                from src.http_server import app

                tc = TestClient(app)
                resp = tc.post("/api/v1/tools/status", json={"family": "zip"})
                assert resp.status_code == 200


class TestRateLimit:
    def test_rate_limit_triggers_on_burst(self):
        from src.http_server import _TokenBucket

        with patch("src.http_server.API_KEY", ""), patch("src.http_server.DEV_MODE", True):
            with patch("src.http_server._rate_limiter", _TokenBucket(capacity=2, refill_per_second=0)):
                with patch("src.http_server.mcp_server"):
                    from fastapi.testclient import TestClient
                    from src.http_server import app

                    tc = TestClient(app)
                    resp1 = tc.get("/api/v1/tools")
                    resp2 = tc.get("/api/v1/tools")
                    resp3 = tc.get("/api/v1/tools")

        assert resp1.status_code == 200
        assert resp2.status_code == 200
        assert resp3.status_code == 429
        assert resp3.json()["policy_id"] == "http.rate_limit.exceeded"

    def test_healthz_exempt_from_rate_limit(self):
        """/healthz bypasses every boundary check (including rate limiting) --
        operational necessity for the container healthcheck."""
        from src.http_server import _TokenBucket

        with patch("src.http_server._rate_limiter", _TokenBucket(capacity=1, refill_per_second=0)):
            with patch("src.http_server.mcp_server"):
                from fastapi.testclient import TestClient
                from src.http_server import app

                tc = TestClient(app)
                for _ in range(5):
                    resp = tc.get("/healthz")
                    assert resp.status_code == 200


class TestOldFailOpenBehaviorRejected:
    def test_old_fail_open_behavior_is_rejected(self):
        """NEGATIVE CONTROL: reconstruct the exact pre-fix condition
        (EXAMPLE_REVIEWER_API_KEY="", no dev-mode flag) and prove a real
        tool-invoking route no longer returns 200 -- the "empty key means every
        route is open" behavior documented in FINDINGS_REGISTER.md no longer
        holds. This assertion fails against the pre-TC-EPIC1-06 http_server.py
        (which returned 200 here)."""
        with patch("src.http_server.API_KEY", ""), patch("src.http_server.DEV_MODE", False):
            with patch("src.http_server.mcp_server") as mock_server:
                mock_server.call_tool.return_value = ToolResult(success=True, data={})

                from fastapi.testclient import TestClient
                from src.http_server import app

                tc = TestClient(app)
                resp = tc.post("/api/v1/tools/status", json={"family": "zip"})
                assert resp.status_code != 200
                assert resp.status_code == 503
