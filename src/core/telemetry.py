"""
Telemetry module for Example Review System.
Provides dual-write (NDJSON + HTTP API) with context managers for tracking operations.
"""

import json
import time
import requests
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from contextlib import contextmanager


class TelemetryClient:
    """
    Telemetry client with dual-write pattern.
    Writes to NDJSON (crash-resilient) and HTTP API (if available).
    """

    def __init__(
        self,
        artifacts_dir: Path,
        telemetry_url: Optional[str] = None,
        timeout_ms: int = 2000,
        auth_enabled: bool = False,
        auth_token: Optional[str] = None
    ):
        """
        Initialize telemetry client.

        Args:
            artifacts_dir: Directory for storing run artifacts
            telemetry_url: Optional HTTP URL for telemetry service (e.g., http://localhost:8765/ingest)
            timeout_ms: HTTP timeout in milliseconds (unused, for compatibility)
            auth_enabled: Whether auth is enabled (unused, for compatibility)
            auth_token: Auth token (unused, for compatibility)
        """
        self.artifacts_dir = artifacts_dir
        self.telemetry_url = telemetry_url
        self.timeout_ms = timeout_ms
        self.auth_enabled = auth_enabled
        self.auth_token = auth_token
        self.current_run_dir: Optional[Path] = None
        self.ndjson_path: Optional[Path] = None
        self.metrics: Dict[str, int] = {}

    def start_run(self, run_id: int, run_type: str, family: str) -> Path:
        """
        Start a new run and create artifacts directory.

        Args:
            run_id: Database run ID
            run_type: Run type (discovery, validation, patching, verification)
            family: Product family

        Returns:
            Path to run artifacts directory
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        run_dir_name = f"run_{timestamp}_{run_id}"
        self.current_run_dir = self.artifacts_dir / "runs" / run_dir_name
        self.current_run_dir.mkdir(parents=True, exist_ok=True)

        # Create NDJSON event log
        self.ndjson_path = self.current_run_dir / "events.ndjson"

        # Create metadata file
        metadata = {
            "run_id": run_id,
            "run_type": run_type,
            "family": family,
            "started_at": datetime.utcnow().isoformat(),
            "artifacts_dir": str(self.current_run_dir)
        }
        metadata_path = self.current_run_dir / "metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)

        # Reset metrics
        self.metrics = {
            "pages_scanned": 0,
            "snippets_found": 0,
            "snippets_validated": 0,
            "snippets_verified": 0,
            "snippets_fixed": 0,
            "patches_generated": 0,
            "patches_applied": 0,
            "errors": 0
        }

        # Log run start event
        self.log_event("run_started", "info", f"{run_type.capitalize()} run started for {family}", {
            "run_id": run_id,
            "run_type": run_type,
            "family": family
        })

        return self.current_run_dir

    def log_event(self, event_type: str, severity: str, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Log an event to NDJSON and HTTP API.

        Args:
            event_type: Event type identifier
            severity: 'debug', 'info', 'warning', 'error'
            message: Event message
            details: Optional details dictionary
        """
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "severity": severity,
            "message": message,
            "source": "example-reviewer"
        }

        if details:
            event["details"] = details

        # Write 1: NDJSON (crash-resilient)
        if self.ndjson_path:
            try:
                with open(self.ndjson_path, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(event) + '\n')
            except Exception as e:
                print(f"[!] Failed to write to NDJSON: {e}")

        # Write 2: HTTP API (best effort)
        if self.telemetry_url:
            try:
                requests.post(
                    self.telemetry_url,
                    json=event,
                    timeout=2
                )
            except Exception:
                # Non-critical, NDJSON is source of truth
                pass

    @contextmanager
    def track_page(self, page_id: int, file_path: str, relative_path: str, site: str, family: str):
        """
        Context manager for tracking page scanning operations.

        Args:
            page_id: Database page ID
            file_path: Absolute file path
            relative_path: Relative path from content root
            site: Site name
            family: Product family

        Yields:
            page_id
        """
        start_time = time.time()

        self.log_event("page_scan_started", "debug", f"Scanning {relative_path}", {
            "page_id": page_id,
            "file_path": file_path,
            "site": site,
            "family": family
        })

        try:
            yield page_id
            duration_ms = int((time.time() - start_time) * 1000)
            self.metrics["pages_scanned"] += 1

            self.log_event("page_scan_completed", "info", f"Scanned {relative_path}", {
                "page_id": page_id,
                "duration_ms": duration_ms,
                "status": "success"
            })

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            self.metrics["errors"] += 1

            self.log_event("page_scan_failed", "error", f"Failed to scan {relative_path}: {str(e)}", {
                "page_id": page_id,
                "duration_ms": duration_ms,
                "error": str(e),
                "status": "error"
            })
            raise

    @contextmanager
    def track_snippet(self, snippet_id: int, snippet_ordinal: int, page_path: str):
        """
        Context manager for tracking snippet operations.

        Args:
            snippet_id: Database snippet ID
            snippet_ordinal: Position on page
            page_path: Page file path

        Yields:
            snippet_id
        """
        start_time = time.time()

        self.log_event("snippet_processing_started", "debug", f"Processing snippet {snippet_ordinal} in {page_path}", {
            "snippet_id": snippet_id,
            "snippet_ordinal": snippet_ordinal
        })

        try:
            yield snippet_id
            duration_ms = int((time.time() - start_time) * 1000)
            self.metrics["snippets_found"] += 1

            self.log_event("snippet_processing_completed", "info", f"Processed snippet {snippet_ordinal}", {
                "snippet_id": snippet_id,
                "duration_ms": duration_ms,
                "status": "success"
            })

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            self.metrics["errors"] += 1

            self.log_event("snippet_processing_failed", "error", f"Failed to process snippet {snippet_ordinal}: {str(e)}", {
                "snippet_id": snippet_id,
                "duration_ms": duration_ms,
                "error": str(e),
                "status": "error"
            })
            raise

    @contextmanager
    def track_validation(self, snippet_id: int, family: str):
        """
        Context manager for tracking validation operations.

        Args:
            snippet_id: Database snippet ID
            family: Product family

        Yields:
            None
        """
        start_time = time.time()

        self.log_event("validation_started", "debug", f"Validating snippet {snippet_id}", {
            "snippet_id": snippet_id,
            "family": family
        })

        try:
            yield
            duration_ms = int((time.time() - start_time) * 1000)
            self.metrics["snippets_validated"] += 1

            self.log_event("validation_completed", "info", f"Validated snippet {snippet_id}", {
                "snippet_id": snippet_id,
                "duration_ms": duration_ms,
                "status": "success"
            })

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            self.metrics["errors"] += 1

            self.log_event("validation_failed", "error", f"Validation failed for snippet {snippet_id}: {str(e)}", {
                "snippet_id": snippet_id,
                "duration_ms": duration_ms,
                "error": str(e),
                "status": "error"
            })
            raise

    @contextmanager
    def track_compilation(self, snippet_id: int, version_id: int, attempt_number: int):
        """
        Context manager for tracking compilation attempts.

        Args:
            snippet_id: Database snippet ID
            version_id: Snippet version ID being compiled
            attempt_number: Compilation attempt number

        Yields:
            None
        """
        start_time = time.time()

        self.log_event("compilation_started", "debug", f"Compiling snippet {snippet_id} (attempt {attempt_number})", {
            "snippet_id": snippet_id,
            "version_id": version_id,
            "attempt_number": attempt_number
        })

        try:
            yield
            duration_ms = int((time.time() - start_time) * 1000)

            self.log_event("compilation_completed", "info", f"Compilation completed for snippet {snippet_id}", {
                "snippet_id": snippet_id,
                "version_id": version_id,
                "attempt_number": attempt_number,
                "duration_ms": duration_ms,
                "status": "success"
            })

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)

            self.log_event("compilation_failed", "warning", f"Compilation failed for snippet {snippet_id}: {str(e)}", {
                "snippet_id": snippet_id,
                "version_id": version_id,
                "attempt_number": attempt_number,
                "duration_ms": duration_ms,
                "error": str(e),
                "status": "error"
            })
            raise

    @contextmanager
    def track_fix(self, snippet_id: int, fix_type: str):
        """
        Context manager for tracking fix operations.

        Args:
            snippet_id: Database snippet ID
            fix_type: Type of fix ('pattern', 'ollama', 'manual')

        Yields:
            None
        """
        start_time = time.time()

        self.log_event("fix_started", "debug", f"Applying {fix_type} fix to snippet {snippet_id}", {
            "snippet_id": snippet_id,
            "fix_type": fix_type
        })

        try:
            yield
            duration_ms = int((time.time() - start_time) * 1000)
            self.metrics["snippets_fixed"] += 1

            self.log_event("fix_completed", "info", f"Applied {fix_type} fix to snippet {snippet_id}", {
                "snippet_id": snippet_id,
                "fix_type": fix_type,
                "duration_ms": duration_ms,
                "status": "success"
            })

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            self.metrics["errors"] += 1

            self.log_event("fix_failed", "error", f"Fix failed for snippet {snippet_id}: {str(e)}", {
                "snippet_id": snippet_id,
                "fix_type": fix_type,
                "duration_ms": duration_ms,
                "error": str(e),
                "status": "error"
            })
            raise

    @contextmanager
    def track_patch(self, page_id: int, patch_id: str):
        """
        Context manager for tracking patch operations.

        Args:
            page_id: Database page ID
            patch_id: Patch identifier

        Yields:
            None
        """
        start_time = time.time()

        self.log_event("patch_started", "debug", f"Generating patch {patch_id} for page {page_id}", {
            "page_id": page_id,
            "patch_id": patch_id
        })

        try:
            yield
            duration_ms = int((time.time() - start_time) * 1000)
            self.metrics["patches_generated"] += 1

            self.log_event("patch_completed", "info", f"Generated patch {patch_id}", {
                "page_id": page_id,
                "patch_id": patch_id,
                "duration_ms": duration_ms,
                "status": "success"
            })

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            self.metrics["errors"] += 1

            self.log_event("patch_failed", "error", f"Patch generation failed: {str(e)}", {
                "page_id": page_id,
                "patch_id": patch_id,
                "duration_ms": duration_ms,
                "error": str(e),
                "status": "error"
            })
            raise

    def increment_metric(self, metric_name: str, amount: int = 1):
        """Increment a metric counter."""
        if metric_name in self.metrics:
            self.metrics[metric_name] += amount
        else:
            self.metrics[metric_name] = amount

    def get_metrics(self) -> Dict[str, int]:
        """Get current metrics snapshot."""
        return self.metrics.copy()

    def save_metrics(self):
        """Save metrics to file in artifacts directory."""
        if self.current_run_dir:
            metrics_path = self.current_run_dir / "metrics.json"
            with open(metrics_path, 'w', encoding='utf-8') as f:
                json.dump(self.metrics, f, indent=2)

    def finish_run(self, status: str = "completed", error: Optional[str] = None):
        """
        Finish the current run and save final metrics.

        Args:
            status: Final status ('completed', 'failed', 'cancelled')
            error: Optional error message if failed
        """
        self.log_event("run_finished", "info" if status == "completed" else "error",
                      f"Run finished with status: {status}", {
                          "status": status,
                          "error": error,
                          "metrics": self.metrics
                      })

        # Save final metrics
        self.save_metrics()

        # Update metadata with completion info
        if self.current_run_dir:
            metadata_path = self.current_run_dir / "metadata.json"
            if metadata_path.exists():
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)

                metadata["completed_at"] = datetime.utcnow().isoformat()
                metadata["status"] = status
                metadata["metrics"] = self.metrics
                if error:
                    metadata["error"] = error

                with open(metadata_path, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2)
