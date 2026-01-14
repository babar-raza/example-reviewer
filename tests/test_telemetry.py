"""Telemetry module tests covering run lifecycle, events, and metrics."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from telemetry import TelemetryClient


class _Response:
    def __init__(self, status_code=200):
        self.status_code = status_code


def _read_events(path: Path):
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def _prepare_commit_client(temp_artifacts_dir, run_id=19):
    client = TelemetryClient(temp_artifacts_dir)
    run_dir = client.start_run(run_id, "validation", "zip")
    client.telemetry_url = "http://example.test"
    return client, run_dir


@pytest.fixture
def temp_artifacts_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def test_start_run_creates_artifacts_and_metadata(temp_artifacts_dir):
    client = TelemetryClient(temp_artifacts_dir)
    run_dir = client.start_run(1, "validation", "zip")

    assert run_dir.exists()
    metadata_path = run_dir / "metadata.json"
    assert metadata_path.exists()

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["run_id"] == 1
    assert metadata["run_type"] == "validation"
    assert metadata["family"] == "zip"
    assert metadata["event_id"]
    assert metadata["telemetry_run_id"]


def test_start_run_posts_to_api_with_schema(temp_artifacts_dir):
    client = TelemetryClient(temp_artifacts_dir, telemetry_url="http://example.test")

    def _fake_run(cmd, **kwargs):
        if "remote.origin.url" in cmd:
            return type("obj", (), {"stdout": "https://github.com/example/repo\n"})
        return type("obj", (), {"stdout": "main\n"})

    with patch("telemetry.subprocess.run", side_effect=_fake_run), \
         patch("telemetry.requests.post", return_value=_Response(201)) as mock_post:
        client.start_run(2, "discovery", "zip")

        _, kwargs = mock_post.call_args
        payload = kwargs["json"]
        assert payload["event_id"]
        assert payload["run_id"]
        assert payload["agent_name"] == "example-reviewer"
        assert payload["job_type"] == "discovery"
        assert payload["start_time"]
        assert payload["status"] == "running"
        assert payload["product_family"] == "zip"
        assert payload["git_repo"] == "https://github.com/example/repo"
        assert payload["git_branch"] == "main"


def test_log_event_writes_ndjson(temp_artifacts_dir):
    client = TelemetryClient(temp_artifacts_dir)
    run_dir = client.start_run(3, "validation", "zip")

    client.log_event("custom_event", "info", "hello", {"key": "value"})

    events = _read_events(run_dir / "events.ndjson")
    assert any(e["event_type"] == "custom_event" for e in events)


def test_log_event_http_failure_graceful(temp_artifacts_dir):
    client = TelemetryClient(temp_artifacts_dir, telemetry_url="http://example.test")
    run_dir = client.start_run(4, "validation", "zip")

    with patch("telemetry.requests.post", side_effect=Exception("fail")):
        client.log_event("custom_event", "info", "hello")

    events = _read_events(run_dir / "events.ndjson")
    assert any(e["event_type"] == "custom_event" for e in events)


def test_log_event_ndjson_write_failure_is_caught(temp_artifacts_dir):
    client = TelemetryClient(temp_artifacts_dir)
    run_dir = client.start_run(4, "validation", "zip")

    client.ndjson_path = run_dir
    client.log_event("custom_event", "info", "hello")


def test_track_page_success_updates_metrics(temp_artifacts_dir):
    client = TelemetryClient(temp_artifacts_dir)
    client.start_run(5, "validation", "zip")

    with client.track_page(1, "C:/tmp/file.md", "file.md", "docs", "zip"):
        pass

    metrics = client.get_metrics()
    assert metrics["pages_scanned"] == 1


def test_track_page_failure_updates_errors(temp_artifacts_dir):
    client = TelemetryClient(temp_artifacts_dir)
    client.start_run(6, "validation", "zip")

    with pytest.raises(RuntimeError):
        with client.track_page(2, "C:/tmp/file.md", "file.md", "docs", "zip"):
            raise RuntimeError("boom")

    metrics = client.get_metrics()
    assert metrics["errors"] == 1


def test_track_snippet_success(temp_artifacts_dir):
    client = TelemetryClient(temp_artifacts_dir)
    client.start_run(7, "validation", "zip")

    with client.track_snippet(10, 1, "page.md"):
        pass

    metrics = client.get_metrics()
    assert metrics["snippets_found"] == 1


def test_track_snippet_failure_updates_errors(temp_artifacts_dir):
    client = TelemetryClient(temp_artifacts_dir)
    client.start_run(7, "validation", "zip")

    with pytest.raises(RuntimeError):
        with client.track_snippet(10, 1, "page.md"):
            raise RuntimeError("boom")

    metrics = client.get_metrics()
    assert metrics["errors"] == 1


def test_track_validation_success(temp_artifacts_dir):
    client = TelemetryClient(temp_artifacts_dir)
    client.start_run(8, "validation", "zip")

    with client.track_validation(10, "zip"):
        pass

    metrics = client.get_metrics()
    assert metrics["snippets_validated"] == 1


def test_track_validation_failure_updates_errors(temp_artifacts_dir):
    client = TelemetryClient(temp_artifacts_dir)
    client.start_run(8, "validation", "zip")

    with pytest.raises(RuntimeError):
        with client.track_validation(10, "zip"):
            raise RuntimeError("boom")

    metrics = client.get_metrics()
    assert metrics["errors"] == 1


def test_track_fix_success_and_failure(temp_artifacts_dir):
    client = TelemetryClient(temp_artifacts_dir)
    client.start_run(9, "validation", "zip")

    with client.track_fix(11, "pattern"):
        pass

    with pytest.raises(ValueError):
        with client.track_fix(11, "pattern"):
            raise ValueError("fail")

    metrics = client.get_metrics()
    assert metrics["snippets_fixed"] == 1
    assert metrics["errors"] == 1


def test_track_patch_success(temp_artifacts_dir):
    client = TelemetryClient(temp_artifacts_dir)
    client.start_run(10, "patching", "zip")

    with client.track_patch(101, "patch-1"):
        pass

    metrics = client.get_metrics()
    assert metrics["patches_generated"] == 1


def test_track_patch_failure_updates_errors(temp_artifacts_dir):
    client = TelemetryClient(temp_artifacts_dir)
    client.start_run(10, "patching", "zip")

    with pytest.raises(RuntimeError):
        with client.track_patch(101, "patch-1"):
            raise RuntimeError("boom")

    metrics = client.get_metrics()
    assert metrics["errors"] == 1


def test_track_compilation_logs_events(temp_artifacts_dir):
    client = TelemetryClient(temp_artifacts_dir)
    run_dir = client.start_run(11, "validation", "zip")

    with client.track_compilation(5, 99, 1):
        pass

    events = _read_events(run_dir / "events.ndjson")
    event_types = {event["event_type"] for event in events}
    assert "compilation_started" in event_types
    assert "compilation_completed" in event_types


def test_track_compilation_failure_logs_event(temp_artifacts_dir):
    client = TelemetryClient(temp_artifacts_dir)
    run_dir = client.start_run(11, "validation", "zip")

    with pytest.raises(RuntimeError):
        with client.track_compilation(5, 99, 1):
            raise RuntimeError("boom")

    events = _read_events(run_dir / "events.ndjson")
    event_types = {event["event_type"] for event in events}
    assert "compilation_failed" in event_types


def test_record_timing_and_save_metrics(temp_artifacts_dir):
    client = TelemetryClient(temp_artifacts_dir)
    run_dir = client.start_run(12, "validation", "zip")

    client.record_timing("compile_duration", 100)
    client.record_timing("compile_duration", 200)
    client.save_metrics()

    metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["compile_duration_min"] == 100
    assert metrics["compile_duration_max"] == 200
    assert metrics["compile_duration_count"] == 2
    assert metrics["compile_duration_avg"] == 150.0


def test_record_timing_invalid_inputs(temp_artifacts_dir):
    client = TelemetryClient(temp_artifacts_dir)
    client.start_run(12, "validation", "zip")

    client.record_timing("", 10)
    client.record_timing("compile_duration", "bad")
    client.record_timing("compile_duration", -5)

    metrics = client._aggregate_timing_metrics()
    assert metrics["compile_duration_min"] == 0
    assert metrics["compile_duration_max"] == 0
    assert metrics["compile_duration_count"] == 1


def test_save_metrics_patches_http_when_configured(temp_artifacts_dir):
    client = TelemetryClient(temp_artifacts_dir, telemetry_url="http://example.test")

    with patch("telemetry.requests.post", return_value=_Response(201)), \
         patch("telemetry.requests.patch", return_value=_Response(200)) as mock_patch:
        client.start_run(13, "validation", "zip")
        client.record_timing("compile_duration", 123)
        client.save_metrics()

        assert mock_patch.called
        _, kwargs = mock_patch.call_args
        assert "metrics_json" in kwargs["json"]


def test_increment_metric_new_key(temp_artifacts_dir):
    client = TelemetryClient(temp_artifacts_dir)
    client.start_run(13, "validation", "zip")

    client.increment_metric("new_metric", 3)
    metrics = client.get_metrics()
    assert metrics["new_metric"] == 3


def test_finish_run_patches_status_and_metrics(temp_artifacts_dir):
    client = TelemetryClient(temp_artifacts_dir, telemetry_url="http://example.test")

    with patch("telemetry.requests.post", return_value=_Response(201)), \
         patch("telemetry.requests.patch", return_value=_Response(200)) as mock_patch:
        client.start_run(14, "validation", "zip")
        client.increment_metric("snippets_found")
        client.finish_run("completed")

        assert mock_patch.call_count >= 1
        _, kwargs = mock_patch.call_args
        payload = kwargs["json"]
        assert payload["status"] == "success"
        assert "end_time" in payload
        assert "duration_ms" in payload
        assert "metrics_json" in payload


def test_finish_run_without_start_does_not_raise(temp_artifacts_dir):
    client = TelemetryClient(temp_artifacts_dir)
    client.finish_run("completed")


def test_finish_run_records_error_in_metadata(temp_artifacts_dir):
    client = TelemetryClient(temp_artifacts_dir)
    run_dir = client.start_run(15, "validation", "zip")

    client.finish_run("failed", "boom")
    metadata = json.loads((run_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["error"] == "boom"


def test_post_run_start_skips_when_missing_config(temp_artifacts_dir):
    client = TelemetryClient(temp_artifacts_dir)
    client._post_run_start(1, "validation", "zip")


def test_post_run_start_rate_limited(temp_artifacts_dir):
    client = TelemetryClient(temp_artifacts_dir, telemetry_url="http://example.test")

    with patch("telemetry.requests.post", return_value=_Response(429)):
        client.start_run(16, "validation", "zip")


def test_post_run_start_non_200(temp_artifacts_dir):
    client = TelemetryClient(temp_artifacts_dir, telemetry_url="http://example.test")

    with patch("telemetry.requests.post", return_value=_Response(201)):
        client.start_run(17, "validation", "zip")

    with patch("telemetry.requests.post", return_value=_Response(500)):
        client._post_run_start(17, "validation", "zip")


def test_patch_run_update_handles_errors(temp_artifacts_dir):
    client = TelemetryClient(temp_artifacts_dir, telemetry_url="http://example.test")

    with patch("telemetry.requests.post", return_value=_Response(201)):
        client.start_run(18, "validation", "zip")

    with patch("telemetry.requests.patch", return_value=_Response(429)):
        client._patch_run_update({"status": "success"})

    with patch("telemetry.requests.patch", return_value=_Response(500)):
        client._patch_run_update({"status": "success"})

    with patch("telemetry.requests.patch", side_effect=Exception("boom")):
        client._patch_run_update({"status": "success"})


def test_patch_run_update_skips_without_config(temp_artifacts_dir):
    client = TelemetryClient(temp_artifacts_dir)
    client._patch_run_update({"status": "success"})


def test_send_metrics_update_skips_without_config(temp_artifacts_dir):
    client = TelemetryClient(temp_artifacts_dir)
    client._send_metrics_update({})


def test_aggregate_timing_metrics_skips_empty_values(temp_artifacts_dir):
    client = TelemetryClient(temp_artifacts_dir)
    client._timing_metrics = {"empty": []}
    assert client._aggregate_timing_metrics() == {}


def test_build_headers_with_auth(temp_artifacts_dir):
    client = TelemetryClient(
        temp_artifacts_dir,
        telemetry_url="http://example.test",
        auth_enabled=True,
        auth_token="token"
    )

    headers = client._build_headers()
    assert headers["Authorization"] == "Bearer token"


def test_associate_commit_skips_without_config(temp_artifacts_dir):
    client = TelemetryClient(temp_artifacts_dir)
    client.associate_commit("abc123", "auto", "bot", "2024-01-01T00:00:00Z")


def test_associate_commit_rate_limited_logs_event(temp_artifacts_dir):
    client, run_dir = _prepare_commit_client(temp_artifacts_dir, run_id=20)

    with patch("telemetry.requests.post", return_value=_Response(429)):
        client.associate_commit("abc123", "auto", "bot", "2024-01-01T00:00:00Z")

    events = _read_events(run_dir / "events.ndjson")
    assert any(event["event_type"] == "telemetry_rate_limited" for event in events)


def test_associate_commit_non_200_logs_event(temp_artifacts_dir):
    client, run_dir = _prepare_commit_client(temp_artifacts_dir, run_id=21)

    with patch("telemetry.requests.post", return_value=_Response(500)):
        client.associate_commit("abc123", "auto", "bot", "2024-01-01T00:00:00Z")

    events = _read_events(run_dir / "events.ndjson")
    assert any(event["event_type"] == "commit_association_failed" for event in events)


def test_associate_commit_success_logs_event(temp_artifacts_dir):
    client, run_dir = _prepare_commit_client(temp_artifacts_dir, run_id=22)

    with patch("telemetry.requests.post", return_value=_Response(201)):
        client.associate_commit("abc123", "auto", "bot", "2024-01-01T00:00:00Z")

    events = _read_events(run_dir / "events.ndjson")
    assert any(event["event_type"] == "commit_associated" for event in events)


def test_associate_commit_exception_logs_event(temp_artifacts_dir):
    client, run_dir = _prepare_commit_client(temp_artifacts_dir, run_id=23)

    with patch("telemetry.requests.post", side_effect=Exception("boom")):
        client.associate_commit("abc123", "auto", "bot", "2024-01-01T00:00:00Z")

    events = _read_events(run_dir / "events.ndjson")
    assert any(event["event_type"] == "commit_association_failed" for event in events)
