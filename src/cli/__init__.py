"""Compatibility CLI helpers."""

import os

__version__ = "0.1.0"


class CLI:
    """Compatibility CLI wrapper for config resolution helpers."""

    def _resolve_auto_commit(self, cli_flag, family_config):
        if cli_flag is not None:
            return bool(cli_flag)
        if family_config and "auto_commit" in family_config:
            return bool(family_config.get("auto_commit"))
        env_value = os.getenv("AUTO_COMMIT_ENABLED", "").lower()
        if env_value in {"true", "1", "yes"}:
            return True
        if env_value in {"false", "0", "no"}:
            return False
        return False

    def _load_telemetry_settings(self, override_url: str | None = None):
        telemetry_url = override_url or os.getenv("TELEMETRY_API_URL", "")
        timeout_raw = os.getenv("TELEMETRY_API_TIMEOUT_MS", "")
        timeout_ms = int(timeout_raw) if timeout_raw.isdigit() else 2000
        auth_enabled = os.getenv("TELEMETRY_API_AUTH_ENABLED", "").lower() in {"true", "1", "yes"}
        auth_token = os.getenv("TELEMETRY_API_AUTH_TOKEN") if auth_enabled else None
        return {
            "telemetry_url": telemetry_url,
            "timeout_ms": timeout_ms,
            "auth_enabled": auth_enabled,
            "auth_token": auth_token,
        }


__all__ = ["CLI", "__version__"]
