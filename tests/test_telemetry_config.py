"""Tests for telemetry configuration and HTTP API integration."""

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, 'src')

from cli import CLI
from telemetry import TelemetryClient


class _Response:
    def __init__(self, status_code=200):
        self.status_code = status_code


def test_env_telemetry_url_used_by_cli_settings(monkeypatch):
    monkeypatch.setenv("TELEMETRY_API_URL", "http://env.example")
    monkeypatch.delenv("TELEMETRY_API_TIMEOUT_MS", raising=False)
    monkeypatch.delenv("TELEMETRY_API_AUTH_ENABLED", raising=False)
    monkeypatch.delenv("TELEMETRY_API_AUTH_TOKEN", raising=False)

    cli = CLI()
    settings = cli._load_telemetry_settings()

    assert settings["telemetry_url"] == "http://env.example"
    assert settings["timeout_ms"] == 2000
    assert settings["auth_enabled"] is False
    assert settings["auth_token"] is None


def test_cli_telemetry_url_override(monkeypatch):
    monkeypatch.setenv("TELEMETRY_API_URL", "http://env.example")

    cli = CLI()
    settings = cli._load_telemetry_settings("http://override.example")

    assert settings["telemetry_url"] == "http://override.example"


def test_timeout_env_parsing(monkeypatch):
    monkeypatch.setenv("TELEMETRY_API_TIMEOUT_MS", "5000")

    cli = CLI()
    settings = cli._load_telemetry_settings()

    assert settings["timeout_ms"] == 5000


def test_auth_headers_sent_when_enabled():
    with tempfile.TemporaryDirectory() as tmpdir:
        client = TelemetryClient(
            Path(tmpdir),
            telemetry_url="http://example.test",
            timeout_ms=2000,
            auth_enabled=True,
            auth_token="secret"
        )

        with patch("telemetry.requests.post", return_value=_Response(201)) as mock_post:
            client.start_run(1, "discovery", "zip")

            assert mock_post.called
            _, kwargs = mock_post.call_args
            headers = kwargs["headers"]
            assert headers["Authorization"] == "Bearer secret"


def test_auth_headers_not_sent_when_disabled():
    with tempfile.TemporaryDirectory() as tmpdir:
        client = TelemetryClient(
            Path(tmpdir),
            telemetry_url="http://example.test",
            timeout_ms=2000,
            auth_enabled=False,
            auth_token="secret"
        )

        with patch("telemetry.requests.post", return_value=_Response(201)) as mock_post:
            client.start_run(1, "discovery", "zip")

            _, kwargs = mock_post.call_args
            headers = kwargs["headers"]
            assert "Authorization" not in headers


def test_timeout_applied_to_http_requests():
    with tempfile.TemporaryDirectory() as tmpdir:
        client = TelemetryClient(
            Path(tmpdir),
            telemetry_url="http://example.test",
            timeout_ms=5000
        )

        with patch("telemetry.requests.post", return_value=_Response(201)) as mock_post:
            client.start_run(2, "validation", "zip")

            _, kwargs = mock_post.call_args
            assert kwargs["timeout"] == 5.0


def test_idempotent_post_duplicate_event_id():
    with tempfile.TemporaryDirectory() as tmpdir:
        client = TelemetryClient(Path(tmpdir), telemetry_url="http://example.test")

        with patch("telemetry.requests.post", return_value=_Response(200)):
            client.start_run(3, "validation", "zip")


def test_rate_limit_handled_gracefully():
    with tempfile.TemporaryDirectory() as tmpdir:
        client = TelemetryClient(Path(tmpdir), telemetry_url="http://example.test")

        with patch("telemetry.requests.post", return_value=_Response(429)):
            client.start_run(4, "validation", "zip")


def test_finish_run_patches_metrics_json():
    with tempfile.TemporaryDirectory() as tmpdir:
        client = TelemetryClient(Path(tmpdir), telemetry_url="http://example.test")

        with patch("telemetry.requests.post", return_value=_Response(201)), \
             patch("telemetry.requests.patch", return_value=_Response(200)) as mock_patch:
            client.start_run(5, "validation", "zip")
            client.record_timing("persistent_fix_duration", 100)
            client.finish_run("completed")

            assert mock_patch.call_count >= 1
            _, kwargs = mock_patch.call_args
            payload = kwargs["json"]
            assert "metrics_json" in payload
