"""
Unit tests for OllamaManager - Ollama process lifecycle management.
All tests use mocks; no real Ollama installation needed.
"""

import subprocess
from unittest.mock import Mock, patch, MagicMock

import pytest
import requests

from src.services.ollama_manager import OllamaManager, OllamaStatus


# ---------------------------------------------------------------------------
# Installation detection
# ---------------------------------------------------------------------------


class TestIsInstalled:
    def test_on_path(self):
        with patch("shutil.which", return_value="C:\\ollama\\ollama.exe"):
            mgr = OllamaManager()
            assert mgr.is_installed() is True

    def test_not_on_path(self):
        with patch("shutil.which", return_value=None):
            mgr = OllamaManager()
            assert mgr.is_installed() is False

    def test_cached_after_first_call(self):
        with patch("shutil.which", return_value="C:\\ollama\\ollama.exe") as mock_which:
            mgr = OllamaManager()
            mgr.is_installed()
            mgr.is_installed()
            assert mock_which.call_count == 1


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


class TestIsRunning:
    @patch("src.services.ollama_manager.requests.get")
    def test_healthy(self, mock_get):
        mock_get.return_value = Mock(status_code=200)
        mgr = OllamaManager()
        assert mgr.is_running() is True

    @patch("src.services.ollama_manager.requests.get")
    def test_connection_refused(self, mock_get):
        mock_get.side_effect = requests.ConnectionError("refused")
        mgr = OllamaManager()
        assert mgr.is_running() is False

    @patch("src.services.ollama_manager.requests.get")
    def test_timeout(self, mock_get):
        mock_get.side_effect = requests.Timeout("timeout")
        mgr = OllamaManager()
        assert mgr.is_running() is False

    @patch("src.services.ollama_manager.requests.get")
    def test_non_200(self, mock_get):
        mock_get.return_value = Mock(status_code=500)
        mgr = OllamaManager()
        assert mgr.is_running() is False


# ---------------------------------------------------------------------------
# ensure_running - already running
# ---------------------------------------------------------------------------


class TestEnsureRunningAlreadyRunning:
    @patch("src.services.ollama_manager.requests.get")
    def test_returns_running_no_subprocess(self, mock_get):
        """If Ollama is already running, no subprocess is started."""
        mock_get.return_value = Mock(
            status_code=200,
            json=lambda: {"models": [{"name": "qwen2.5-coder:7b"}]},
        )
        mgr = OllamaManager()
        status = mgr.ensure_running()
        assert status.is_running is True
        assert status.was_auto_started is False
        assert mgr._process is None


# ---------------------------------------------------------------------------
# ensure_running - auto-start disabled
# ---------------------------------------------------------------------------


class TestEnsureRunningAutoStartDisabled:
    @patch("src.services.ollama_manager.requests.get")
    def test_returns_error_when_disabled(self, mock_get):
        mock_get.side_effect = requests.ConnectionError("refused")
        mgr = OllamaManager(auto_start=False)
        status = mgr.ensure_running()
        assert status.is_running is False
        assert "auto_start disabled" in status.error


# ---------------------------------------------------------------------------
# ensure_running - not installed
# ---------------------------------------------------------------------------


class TestEnsureRunningNotInstalled:
    @patch("src.services.ollama_manager.requests.get")
    @patch("shutil.which", return_value=None)
    def test_returns_not_installed(self, mock_which, mock_get):
        mock_get.side_effect = requests.ConnectionError("refused")
        mgr = OllamaManager()
        status = mgr.ensure_running()
        assert status.is_running is False
        assert "not installed" in status.error

    @patch("src.services.ollama_manager.requests.get")
    @patch("shutil.which", return_value=None)
    def test_does_not_retry(self, mock_which, mock_get):
        mock_get.side_effect = requests.ConnectionError("refused")
        mgr = OllamaManager()
        mgr.ensure_running()
        status2 = mgr.ensure_running()
        assert "already attempted" in status2.error


# ---------------------------------------------------------------------------
# ensure_running - successful auto-start
# ---------------------------------------------------------------------------


class TestEnsureRunningAutoStart:
    @patch("subprocess.Popen")
    @patch("shutil.which", return_value="C:\\ollama\\ollama.exe")
    @patch("src.services.ollama_manager.requests.get")
    def test_starts_and_waits(self, mock_get, mock_which, mock_popen):
        """Auto-start Ollama, wait for readiness, verify status."""
        mock_proc = MagicMock()
        mock_proc.pid = 12345
        mock_proc.poll.return_value = None
        mock_popen.return_value = mock_proc

        call_count = [0]

        def get_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] <= 1:
                raise requests.ConnectionError("not yet")
            return Mock(
                status_code=200,
                json=lambda: {"models": [{"name": "qwen2.5-coder:7b"}]},
            )

        mock_get.side_effect = get_side_effect

        mgr = OllamaManager(startup_timeout_seconds=5, auto_pull_model=False)
        status = mgr.ensure_running()

        assert status.is_running is True
        assert status.was_auto_started is True
        assert status.startup_time_ms >= 0  # Can be 0 with mocked fast responses
        mock_popen.assert_called_once()

    @patch("subprocess.Popen")
    @patch("shutil.which", return_value="C:\\ollama\\ollama.exe")
    @patch("src.services.ollama_manager.requests.get")
    def test_process_dies_immediately(self, mock_get, mock_which, mock_popen):
        """If ollama serve exits immediately, report failure."""
        mock_proc = MagicMock()
        mock_proc.pid = 12345
        mock_proc.poll.return_value = 1  # Exited with error
        mock_proc.returncode = 1
        mock_popen.return_value = mock_proc

        mock_get.side_effect = requests.ConnectionError("refused")

        mgr = OllamaManager(startup_timeout_seconds=2, auto_pull_model=False)
        status = mgr.ensure_running()

        assert status.is_running is False
        assert "did not become ready" in status.error


# ---------------------------------------------------------------------------
# Model pulling
# ---------------------------------------------------------------------------


class TestEnsureModelAvailable:
    def test_skips_when_present(self):
        """If model already in list, no pull."""
        mgr = OllamaManager(model="qwen2.5-coder:7b")
        status = OllamaStatus(
            is_running=True,
            models_available=["qwen2.5-coder:7b"],
        )
        with patch("subprocess.run") as mock_run:
            mgr._ensure_model_available(status)
            mock_run.assert_not_called()

    def test_skips_with_substring_match(self):
        """Substring matching handles version suffixes."""
        mgr = OllamaManager(model="qwen2.5-coder:7b")
        status = OllamaStatus(
            is_running=True,
            models_available=["qwen2.5-coder:7b-instruct-q4_0"],
        )
        with patch("subprocess.run") as mock_run:
            mgr._ensure_model_available(status)
            mock_run.assert_not_called()

    @patch("src.services.ollama_manager.requests.get")
    def test_pulls_when_missing(self, mock_get):
        """If model not in list, runs ollama pull."""
        mock_get.return_value = Mock(
            status_code=200,
            json=lambda: {"models": [{"name": "qwen2.5-coder:7b"}]},
        )
        mgr = OllamaManager(model="qwen2.5-coder:7b")
        status = OllamaStatus(is_running=True, models_available=[])

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stderr="")
            mgr._ensure_model_available(status)
            mock_run.assert_called_once()
            assert "qwen2.5-coder:7b" in mock_run.call_args[0][0]

    def test_handles_pull_timeout(self):
        """Timeout during pull is handled gracefully."""
        mgr = OllamaManager(model="big-model:70b", pull_timeout_seconds=1)
        status = OllamaStatus(is_running=True, models_available=[])

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("ollama", 1)):
            mgr._ensure_model_available(status)  # Should not raise


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------


class TestCleanup:
    def test_terminates_running_process(self):
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.pid = 99999

        mgr = OllamaManager()
        mgr._process = mock_proc
        mgr._cleanup()

        mock_proc.terminate.assert_called_once()
        assert mgr._process is None

    def test_no_process_is_safe(self):
        mgr = OllamaManager()
        mgr._cleanup()  # Should not raise

    def test_kills_if_terminate_times_out(self):
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.pid = 99999
        mock_proc.wait.side_effect = subprocess.TimeoutExpired("ollama", 10)

        mgr = OllamaManager()
        mgr._process = mock_proc
        mgr._cleanup()

        mock_proc.terminate.assert_called_once()
        mock_proc.kill.assert_called_once()

    def test_skips_already_exited_process(self):
        mock_proc = MagicMock()
        mock_proc.poll.return_value = 0  # Already exited

        mgr = OllamaManager()
        mgr._process = mock_proc
        mgr._cleanup()

        mock_proc.terminate.assert_not_called()


# ---------------------------------------------------------------------------
# shutdown() public API
# ---------------------------------------------------------------------------


class TestShutdown:
    def test_delegates_to_cleanup(self):
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.pid = 11111

        mgr = OllamaManager()
        mgr._process = mock_proc
        mgr.shutdown()

        mock_proc.terminate.assert_called_once()
        assert mgr._process is None
