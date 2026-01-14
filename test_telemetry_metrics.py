"""Tests for advanced telemetry metrics (gauges, histograms, percentiles)."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import sys
sys.path.insert(0, 'src')

from telemetry import TelemetryClient


class _Response:
    def __init__(self, status_code=200):
        self.status_code = status_code


def _read_events(path: Path):
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def test_record_gauge_latest_value():
    with tempfile.TemporaryDirectory() as tmpdir:
        client = TelemetryClient(Path(tmpdir))
        run_dir = client.start_run(1, "validation", "zip")

        client.record_gauge("memory_usage_mb", 128)
        client.record_gauge("memory_usage_mb", 256)
        client.save_metrics()

        metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
        gauges = metrics["metrics_json"]["gauges"]
        assert gauges["memory_usage_mb"] == 256.0


def test_record_gauge_ignores_empty_name():
    with tempfile.TemporaryDirectory() as tmpdir:
        client = TelemetryClient(Path(tmpdir))
        run_dir = client.start_run(10, "validation", "zip")

        client.record_gauge("", 128)
        client.save_metrics()

        metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
        gauges = metrics["metrics_json"]["gauges"]
        assert gauges == {}


def test_record_gauge_invalid_value_logs_event():
    with tempfile.TemporaryDirectory() as tmpdir:
        client = TelemetryClient(Path(tmpdir))
        run_dir = client.start_run(11, "validation", "zip")

        client.record_gauge("memory_usage_mb", "nope")

        events = _read_events(run_dir / "events.ndjson")
        assert any(event["event_type"] == "gauge_recorded_invalid" for event in events)


def test_record_histogram_buckets_values():
    with tempfile.TemporaryDirectory() as tmpdir:
        client = TelemetryClient(Path(tmpdir))
        run_dir = client.start_run(2, "validation", "zip")

        values = [5, 10, 11, 60, 600, 1500]
        for value in values:
            client.record_histogram("snippet_length", value)

        client.save_metrics()
        metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
        buckets = metrics["metrics_json"]["histograms"]["snippet_length"]["buckets"]

        assert buckets["10"] == 2
        assert buckets["50"] == 1
        assert buckets["100"] == 1
        assert buckets["500"] == 0
        assert buckets["1000"] == 1
        assert buckets[">1000"] == 1


def test_record_histogram_ignores_empty_name():
    with tempfile.TemporaryDirectory() as tmpdir:
        client = TelemetryClient(Path(tmpdir))
        run_dir = client.start_run(12, "validation", "zip")

        client.record_histogram("", 10)
        client.save_metrics()

        metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
        histograms = metrics["metrics_json"]["histograms"]
        assert histograms == {}


def test_record_histogram_invalid_value_logs_event():
    with tempfile.TemporaryDirectory() as tmpdir:
        client = TelemetryClient(Path(tmpdir))
        run_dir = client.start_run(13, "validation", "zip")

        client.record_histogram("snippet_length", "bad")

        events = _read_events(run_dir / "events.ndjson")
        assert any(event["event_type"] == "histogram_recorded_invalid" for event in events)


def test_record_timing_calculates_percentiles():
    with tempfile.TemporaryDirectory() as tmpdir:
        client = TelemetryClient(Path(tmpdir))
        run_dir = client.start_run(3, "validation", "zip")

        for value in [10, 20, 30, 40, 50]:
            client.record_timing("compile_duration", value)

        client.save_metrics()
        metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
        timing = metrics["metrics_json"]["timings"]["compile_duration"]

        assert timing["p50"] == 30.0
        assert timing["p90"] == 50.0
        assert timing["p95"] == 50.0
        assert timing["p99"] == 50.0


def test_percentile_empty_and_upper_bound():
    with tempfile.TemporaryDirectory() as tmpdir:
        client = TelemetryClient(Path(tmpdir))
        assert client._percentile([], 90) == 0.0
        assert client._percentile([10.0], 100) == 10.0


def test_build_timing_details_skips_empty_values():
    with tempfile.TemporaryDirectory() as tmpdir:
        client = TelemetryClient(Path(tmpdir))
        client._timing_metrics = {"empty": [], "present": [5.0]}

        details = client._build_timing_details()

        assert "empty" not in details
        assert details["present"]["count"] == 1


def test_build_histogram_details_skips_empty_entries():
    with tempfile.TemporaryDirectory() as tmpdir:
        client = TelemetryClient(Path(tmpdir))
        client._histograms = {
            "empty_values": {"values": [], "buckets": [10]},
            "no_buckets": {"values": [5], "buckets": []}
        }

        assert client._build_histogram_details() == {}


def test_metrics_json_serializable():
    with tempfile.TemporaryDirectory() as tmpdir:
        client = TelemetryClient(Path(tmpdir))
        client.start_run(4, "validation", "zip")

        client.increment_metric("pages_scanned", 2)
        client.record_gauge("memory_usage_mb", 128)
        client.record_histogram("snippet_length", 10)
        client.record_timing("compile_duration", 42)
        client.save_metrics()

        json.dumps(client.metrics_json)


def test_metrics_sent_to_api():
    with tempfile.TemporaryDirectory() as tmpdir:
        client = TelemetryClient(Path(tmpdir), telemetry_url="http://example.test")

        with patch("telemetry.requests.post", return_value=_Response(201)), \
             patch("telemetry.requests.patch", return_value=_Response(200)) as mock_patch:
            client.start_run(5, "validation", "zip")
            client.record_histogram("snippet_length", 10)
            client.record_gauge("memory_usage_mb", 64)
            client.save_metrics()

            _, kwargs = mock_patch.call_args
            payload = kwargs["json"]["metrics_json"]
            assert "histograms" in payload
            assert "gauges" in payload
