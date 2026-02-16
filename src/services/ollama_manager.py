"""
Ollama process manager for auto-starting and managing the Ollama server.

Handles health checking, auto-start, model pulling, and cleanup.
Designed for Windows (CREATE_NO_WINDOW) with cross-platform fallback.
"""

import atexit
import logging
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from typing import Optional, List

import requests

logger = logging.getLogger(__name__)

# Windows-specific: suppress console window for background processes
CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0


@dataclass
class OllamaStatus:
    """Status of Ollama server after ensure_running()."""
    is_running: bool = False
    base_url: str = "http://localhost:11434"
    models_available: List[str] = field(default_factory=list)
    was_auto_started: bool = False
    error: Optional[str] = None
    startup_time_ms: int = 0


class OllamaManager:
    """
    Manages the Ollama server lifecycle.

    - Health check (is Ollama running?)
    - Auto-start (launch 'ollama serve' as background subprocess)
    - Model availability (is the configured model pulled?)
    - Auto-pull (pull model if not available)
    - Cleanup (terminate subprocess on exit, only if we started it)
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "qwen2.5-coder:7b",
        auto_start: bool = True,
        startup_timeout_seconds: int = 30,
        auto_pull_model: bool = True,
        pull_timeout_seconds: int = 600,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.auto_start = auto_start
        self.startup_timeout_seconds = startup_timeout_seconds
        self.auto_pull_model = auto_pull_model
        self.pull_timeout_seconds = pull_timeout_seconds

        self._process: Optional[subprocess.Popen] = None
        self._auto_start_attempted: bool = False
        self._installed: Optional[bool] = None  # None = not checked yet

    def is_installed(self) -> bool:
        """Check if ollama CLI is available on PATH. Result is cached."""
        if self._installed is not None:
            return self._installed
        self._installed = shutil.which("ollama") is not None
        if not self._installed:
            logger.warning(
                "Ollama is not installed or not on PATH. "
                "Fallback LLM will be unavailable. "
                "Install from https://ollama.ai"
            )
        return self._installed

    def is_running(self) -> bool:
        """Check if Ollama server is responding to health checks."""
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return resp.status_code == 200
        except (requests.ConnectionError, requests.Timeout):
            return False
        except Exception as e:
            logger.debug(f"Ollama health check error: {e}")
            return False

    def ensure_running(self) -> OllamaStatus:
        """
        Ensure Ollama is running. Auto-start if configured and needed.

        Returns:
            OllamaStatus with current state after all checks/actions.
        """
        status = OllamaStatus(base_url=self.base_url)

        # Step 1: Check if already running
        if self.is_running():
            status.is_running = True
            status.models_available = self._list_models()
            logger.info(f"Ollama already running at {self.base_url}")
            if self.auto_pull_model:
                self._ensure_model_available(status)
            return status

        # Step 2: Auto-start disabled?
        if not self.auto_start:
            status.error = "Ollama not running and auto_start disabled"
            logger.warning(status.error)
            return status

        # Step 3: Already tried and failed?
        if self._auto_start_attempted:
            status.error = "Auto-start already attempted and failed"
            logger.warning(status.error)
            return status

        # Step 4: Check if installed
        if not self.is_installed():
            self._auto_start_attempted = True
            status.error = "Ollama not installed"
            return status

        # Step 5: Start Ollama
        logger.info("Ollama not running. Attempting auto-start...")
        start_time = time.time()

        try:
            popen_kwargs = {
                "stdout": subprocess.DEVNULL,
                "stderr": subprocess.DEVNULL,
            }
            if sys.platform == "win32":
                popen_kwargs["creationflags"] = CREATE_NO_WINDOW

            self._process = subprocess.Popen(
                ["ollama", "serve"],
                **popen_kwargs,
            )

            # Register cleanup so we terminate on exit
            atexit.register(self._cleanup)

            logger.info(f"Started 'ollama serve' (PID: {self._process.pid})")

        except FileNotFoundError:
            self._auto_start_attempted = True
            self._installed = False
            status.error = "ollama command not found"
            logger.error(status.error)
            return status
        except OSError as e:
            self._auto_start_attempted = True
            status.error = f"Failed to start ollama: {e}"
            logger.error(status.error)
            return status

        # Step 6: Wait for readiness
        if not self._wait_for_ready():
            self._auto_start_attempted = True
            status.error = f"Ollama did not become ready within {self.startup_timeout_seconds}s"
            logger.error(status.error)
            self._cleanup()
            return status

        elapsed_ms = int((time.time() - start_time) * 1000)
        status.is_running = True
        status.was_auto_started = True
        status.startup_time_ms = elapsed_ms
        logger.info(f"Ollama ready in {elapsed_ms}ms")

        # Step 7: Ensure model is available
        status.models_available = self._list_models()
        if self.auto_pull_model:
            self._ensure_model_available(status)

        return status

    def _wait_for_ready(self) -> bool:
        """Poll Ollama until it responds or timeout expires."""
        deadline = time.time() + self.startup_timeout_seconds
        poll_interval = 0.5

        while time.time() < deadline:
            # Check if process died early
            if self._process and self._process.poll() is not None:
                logger.error(
                    f"Ollama process exited with code {self._process.returncode}"
                )
                return False

            if self.is_running():
                return True

            time.sleep(poll_interval)
            poll_interval = min(poll_interval * 1.5, 2.0)

        return False

    def _list_models(self) -> List[str]:
        """Get list of locally available model names."""
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return [m.get("name", "") for m in data.get("models", [])]
        except Exception as e:
            logger.debug(f"Failed to list Ollama models: {e}")
        return []

    def _ensure_model_available(self, status: OllamaStatus) -> None:
        """Pull the configured model if not already available locally."""
        for available in status.models_available:
            if self.model in available or available in self.model:
                logger.info(f"Model '{self.model}' is available")
                return

        logger.info(f"Model '{self.model}' not found locally. Pulling...")
        try:
            result = subprocess.run(
                ["ollama", "pull", self.model],
                capture_output=True,
                text=True,
                timeout=self.pull_timeout_seconds,
            )
            if result.returncode == 0:
                logger.info(f"Successfully pulled model '{self.model}'")
                status.models_available = self._list_models()
            else:
                logger.error(
                    f"Failed to pull model '{self.model}': {result.stderr[:300]}"
                )
        except subprocess.TimeoutExpired:
            logger.error(
                f"Model pull timed out after {self.pull_timeout_seconds}s"
            )
        except Exception as e:
            logger.error(f"Error pulling model: {e}")

    def _cleanup(self) -> None:
        """Terminate the Ollama process if we started it."""
        if self._process is not None:
            try:
                if self._process.poll() is None:
                    logger.info(
                        f"Terminating auto-started Ollama (PID: {self._process.pid})"
                    )
                    self._process.terminate()
                    try:
                        self._process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        logger.warning("Ollama did not terminate gracefully, killing")
                        self._process.kill()
            except Exception as e:
                logger.debug(f"Error during Ollama cleanup: {e}")
            finally:
                self._process = None

    def shutdown(self) -> None:
        """Public shutdown method for explicit cleanup."""
        self._cleanup()
