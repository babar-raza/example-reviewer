"""Lightweight telemetry client for legacy tests."""

from __future__ import annotations

import json
import logging
import subprocess
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


class TelemetryClient:
    """Local telemetry recorder with optional HTTP API updates."""

    def __init__(
        self,
        artifacts_dir: Path,
        telemetry_url: Optional[str] = None,
        timeout_ms: int = 2000,
        auth_enabled: bool = False,
        auth_token: Optional[str] = None,
    ):
        self.artifacts_dir = Path(artifacts_dir)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.telemetry_url = telemetry_url
        self.timeout_ms = timeout_ms
        self.auth_enabled = auth_enabled
        self.auth_token = auth_token

        self.run_id: Optional[int] = None
        self.run_type: Optional[str] = None
        self.family: Optional[str] = None
        self.event_id: Optional[str] = None
        self.telemetry_run_id: Optional[str] = None
        self.run_dir: Optional[Path] = None
        self.ndjson_path: Optional[Path] = None
        self._run_start_time: Optional[datetime] = None

        self.metrics: Dict[str, int] = {"errors": 0}
        self._timing_metrics: Dict[str, List[float]] = {}
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, Dict[str, Any]] = {}
        self.metrics_json: Dict[str, Any] = {}

    def start_run(self, run_id: int, run_type: str, family: str) -> Path:
        self.run_id = run_id
        self.run_type = run_type
        self.family = family
        self.event_id = str(uuid.uuid4())
        self.telemetry_run_id = str(uuid.uuid4())
        self._run_start_time = datetime.now(timezone.utc)

        self.run_dir = self.artifacts_dir / f"run_{run_id}_{family}"
        self.run_dir.mkdir(parents=True, exist_ok=True)

        self.ndjson_path = self.run_dir / "events.ndjson"
        if not self.ndjson_path.exists():
            self.ndjson_path.write_text("", encoding="utf-8")

        metadata = {
            "run_id": run_id,
            "run_type": run_type,
            "family": family,
            "event_id": self.event_id,
            "telemetry_run_id": self.telemetry_run_id,
        }
        (self.run_dir / "metadata.json").write_text(
            json.dumps(metadata, indent=2),
            encoding="utf-8",
        )

        if self.telemetry_url:
            self._post_run_start(run_id, run_type, family)

        return self.run_dir

    def log_event(self, event_type: str, level: str, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        if not self.ndjson_path:
            return
        event = {
            "event_type": event_type,
            "level": level,
            "message": message,
            "details": details or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        try:
            with self.ndjson_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(event) + "\n")
        except Exception:
            logger.debug("Failed to write telemetry event", exc_info=True)

    def increment_metric(self, name: str, value: int = 1) -> None:
        if not name:
            return
        self.metrics[name] = self.metrics.get(name, 0) + value

    def get_metrics(self) -> Dict[str, int]:
        return dict(self.metrics)

    def record_timing(self, metric_name: str, duration_ms: Any) -> None:
        if not metric_name:
            return
        try:
            value = float(duration_ms)
        except (TypeError, ValueError):
            return
        if value < 0:
            value = 0.0
        self._timing_metrics.setdefault(metric_name, []).append(value)
        self.log_event(
            "timing_recorded",
            "info",
            "",
            {"metric_name": metric_name, "duration_ms": int(value)},
        )

    def record_gauge(self, metric_name: str, value: Any) -> None:
        if not metric_name:
            return
        try:
            self._gauges[metric_name] = float(value)
        except (TypeError, ValueError):
            self.log_event("gauge_recorded_invalid", "warning", "", {"metric_name": metric_name})

    def record_histogram(self, metric_name: str, value: Any) -> None:
        if not metric_name:
            return
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            self.log_event("histogram_recorded_invalid", "warning", "", {"metric_name": metric_name})
            return
        entry = self._histograms.setdefault(metric_name, {"values": [], "buckets": [10, 50, 100, 500, 1000]})
        entry["values"].append(numeric)

    def save_metrics(self) -> None:
        if not self.run_dir:
            return
        timing_metrics = self._aggregate_timing_metrics()
        self.metrics_json = {
            **self.metrics,
            **timing_metrics,
            "gauges": self._gauges,
            "histograms": self._build_histogram_details(),
            "timings": self._build_timing_details(),
        }
        payload = {**timing_metrics, "metrics_json": self.metrics_json}
        (self.run_dir / "metrics.json").write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )
        self._send_metrics_update(payload)

    def finish_run(self, status: str, error: Optional[str] = None) -> None:
        if not self.run_dir or not self.event_id:
            return
        end_time = datetime.now(timezone.utc)
        duration_ms = 0
        if self._run_start_time:
            duration_ms = int((end_time - self._run_start_time).total_seconds() * 1000)
        if error:
            metadata_path = self.run_dir / "metadata.json"
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            metadata["error"] = error
            metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

        self.save_metrics()

        status_value = "success" if status == "completed" else "failure" if status == "failed" else status
        update = {
            "status": status_value,
            "end_time": end_time.isoformat(),
            "duration_ms": duration_ms,
            "metrics_json": self.metrics_json,
        }
        self._patch_run_update(update)

    def _aggregate_timing_metrics(self) -> Dict[str, Any]:
        aggregated: Dict[str, Any] = {}
        for name, values in self._timing_metrics.items():
            if not values:
                continue
            min_v = min(values)
            max_v = max(values)
            count = len(values)
            avg = sum(values) / count if count else 0.0
            aggregated[f"{name}_min"] = int(min_v)
            aggregated[f"{name}_max"] = int(max_v)
            aggregated[f"{name}_count"] = count
            aggregated[f"{name}_avg"] = float(avg)
        return aggregated

    def _build_timing_details(self) -> Dict[str, Any]:
        details: Dict[str, Any] = {}
        for name, values in self._timing_metrics.items():
            if not values:
                continue
            sorted_vals = sorted(values)
            details[name] = {
                "count": len(sorted_vals),
                "min": float(sorted_vals[0]),
                "max": float(sorted_vals[-1]),
                "avg": float(sum(sorted_vals) / len(sorted_vals)),
                "p50": self._percentile(sorted_vals, 50),
                "p90": self._percentile(sorted_vals, 90),
                "p95": self._percentile(sorted_vals, 95),
                "p99": self._percentile(sorted_vals, 99),
            }
        return details

    def _build_histogram_details(self) -> Dict[str, Any]:
        details: Dict[str, Any] = {}
        for name, entry in self._histograms.items():
            values = entry.get("values", [])
            buckets = entry.get("buckets", [])
            if not values or not buckets:
                continue
            bucket_counts = {str(b): 0 for b in buckets}
            bucket_counts[">1000"] = 0
            for value in values:
                placed = False
                for bucket in buckets:
                    if value <= bucket:
                        bucket_counts[str(bucket)] += 1
                        placed = True
                        break
                if not placed:
                    bucket_counts[">1000"] += 1
            details[name] = {"buckets": bucket_counts}
        return details

    @staticmethod
    def _percentile(values: List[float], percentile: int) -> float:
        if not values:
            return 0.0
        if percentile >= 100:
            return float(values[-1])
        k = int(round((percentile / 100) * (len(values) - 1)))
        return float(values[min(k, len(values) - 1)])

    def _build_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.auth_enabled and self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers

    def _post_run_start(self, run_id: int, run_type: str, family: str) -> None:
        if not self.telemetry_url:
            return
        git_repo, git_branch = self._get_git_info()
        payload = {
            "event_id": self.event_id,
            "run_id": run_id,
            "agent_name": "example-reviewer",
            "job_type": run_type,
            "start_time": self._run_start_time.isoformat() if self._run_start_time else "",
            "status": "running",
            "product_family": family,
            "git_repo": git_repo,
            "git_branch": git_branch,
        }
        try:
            response = requests.post(
                f"{self.telemetry_url}/api/v1/runs",
                json=payload,
                headers=self._build_headers(),
                timeout=self.timeout_ms / 1000,
            )
            if response.status_code == 429:
                self.log_event("telemetry_rate_limited", "warning", "rate limited")
        except Exception:
            self.log_event("telemetry_post_failed", "warning", "post failed")

    def _patch_run_update(self, payload: Dict[str, Any]) -> None:
        if not self.telemetry_url or not self.event_id:
            return
        try:
            response = requests.patch(
                f"{self.telemetry_url}/api/v1/runs/{self.event_id}",
                json=payload,
                headers=self._build_headers(),
                timeout=self.timeout_ms / 1000,
            )
            if response.status_code == 429:
                self.log_event("telemetry_rate_limited", "warning", "rate limited")
        except Exception:
            self.log_event("telemetry_patch_failed", "warning", "patch failed")

    def _send_metrics_update(self, payload: Dict[str, Any]) -> None:
        if not self.telemetry_url:
            return
        if not self.event_id:
            return
        try:
            requests.patch(
                f"{self.telemetry_url}/api/v1/runs/{self.event_id}",
                json={"metrics_json": payload.get("metrics_json", {})},
                headers=self._build_headers(),
                timeout=self.timeout_ms / 1000,
            )
        except Exception:
            self.log_event("telemetry_metrics_failed", "warning", "metrics patch failed")

    def associate_commit(self, commit_hash: str, commit_source: str, commit_author: str, commit_timestamp: str) -> None:
        if not self.telemetry_url or not self.event_id:
            return
        payload = {
            "commit_hash": commit_hash,
            "commit_source": commit_source,
            "commit_author": commit_author,
            "commit_timestamp": commit_timestamp,
        }
        try:
            response = requests.post(
                f"{self.telemetry_url}/api/v1/runs/{self.event_id}/associate-commit",
                json=payload,
                headers=self._build_headers(),
                timeout=self.timeout_ms / 1000,
            )
            if response.status_code == 429:
                self.log_event("telemetry_rate_limited", "warning", "rate limited")
            elif response.status_code >= 300:
                self.log_event("commit_association_failed", "warning", "commit association failed")
            else:
                self.log_event("commit_associated", "info", "commit associated")
        except Exception:
            self.log_event("commit_association_failed", "warning", "commit association failed")

    @contextmanager
    def track_page(self, page_id: int, file_path: str, relative_path: str, site: str, family: str):
        try:
            yield
            self.increment_metric("pages_scanned", 1)
        except Exception:
            self.increment_metric("errors", 1)
            raise

    @contextmanager
    def track_snippet(self, snippet_id: int, page_id: int, file_path: str):
        try:
            yield
            self.increment_metric("snippets_found", 1)
        except Exception:
            self.increment_metric("errors", 1)
            raise

    @contextmanager
    def track_validation(self, snippet_id: int, family: str):
        try:
            yield
            self.increment_metric("snippets_validated", 1)
        except Exception:
            self.increment_metric("errors", 1)
            raise

    @contextmanager
    def track_fix(self, snippet_id: int, fix_type: str):
        try:
            yield
            self.increment_metric("snippets_fixed", 1)
        except Exception:
            self.increment_metric("errors", 1)
            raise

    @contextmanager
    def track_patch(self, snippet_id: int, patch_id: str):
        try:
            yield
            self.increment_metric("patches_generated", 1)
        except Exception:
            self.increment_metric("errors", 1)
            raise

    @contextmanager
    def track_compilation(self, run_id: int, snippet_id: int, attempt: int):
        self.log_event("compilation_started", "info", "", {"snippet_id": snippet_id, "attempt": attempt})
        try:
            yield
            self.log_event("compilation_completed", "info", "", {"snippet_id": snippet_id, "attempt": attempt})
        except Exception:
            self.log_event("compilation_failed", "error", "", {"snippet_id": snippet_id, "attempt": attempt})
            self.increment_metric("errors", 1)
            raise

    def _get_git_info(self) -> Tuple[str, str]:
        repo = ""
        branch = ""
        try:
            result = subprocess.run(
                ["git", "config", "--get", "remote.origin.url"],
                capture_output=True,
                text=True,
            )
            if result.stdout:
                repo = result.stdout.strip()
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
            )
            if result.stdout:
                branch = result.stdout.strip()
        except Exception:
            pass
        return repo, branch
