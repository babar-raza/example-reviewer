"""Tests for TelemetryClient timing metrics."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import sys
sys.path.insert(0, 'src')

from telemetry import TelemetryClient


def test_record_timing_writes_ndjson():
    with tempfile.TemporaryDirectory() as tmpdir:
        client = TelemetryClient(Path(tmpdir))
        run_dir = client.start_run(1, "validation", "zip")

        client.record_timing("persistent_fix_duration", 120)

        ndjson_path = run_dir / "events.ndjson"
        assert ndjson_path.exists()

        lines = ndjson_path.read_text(encoding="utf-8").strip().splitlines()
        assert lines

        event = json.loads(lines[-1])
        assert event["event_type"] == "timing_recorded"
        assert event["details"]["metric_name"] == "persistent_fix_duration"
        assert event["details"]["duration_ms"] == 120


def test_record_timing_aggregates_metrics():
    with tempfile.TemporaryDirectory() as tmpdir:
        client = TelemetryClient(Path(tmpdir))
        run_dir = client.start_run(2, "validation", "zip")

        client.record_timing("persistent_fix_duration", 100)
        client.record_timing("persistent_fix_duration", 200)
        client.save_metrics()

        metrics_path = run_dir / "metrics.json"
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))

        assert metrics["persistent_fix_duration_min"] == 100
        assert metrics["persistent_fix_duration_max"] == 200
        assert metrics["persistent_fix_duration_count"] == 2
        assert metrics["persistent_fix_duration_avg"] == 150.0


def test_record_timing_sends_metrics_json_patch():
    with tempfile.TemporaryDirectory() as tmpdir:
        client = TelemetryClient(Path(tmpdir), telemetry_url="http://example.test")
        client.start_run(3, "validation", "zip")
        client.event_id = "event-123"

        with patch("telemetry.requests.post"), patch("telemetry.requests.patch") as mock_patch:
            client.record_timing("persistent_fix_duration", 50)
            client.save_metrics()

            mock_patch.assert_called_once()
            args, kwargs = mock_patch.call_args
            assert args[0] == "http://example.test/api/v1/runs/event-123"
            assert "metrics_json" in kwargs["json"]
            assert kwargs["json"]["metrics_json"]["persistent_fix_duration_count"] == 1


def test_record_timing_http_failure_does_not_raise():
    with tempfile.TemporaryDirectory() as tmpdir:
        client = TelemetryClient(Path(tmpdir), telemetry_url="http://example.test")
        client.start_run(4, "validation", "zip")
        client.event_id = "event-456"

        with patch("telemetry.requests.post"), patch("telemetry.requests.patch", side_effect=Exception("timeout")):
            client.record_timing("persistent_fix_duration", 75)
            client.save_metrics()
