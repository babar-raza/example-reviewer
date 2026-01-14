"""Tests for auto-commit configuration hierarchy."""

import sys

sys.path.insert(0, 'src')

from cli import CLI


def test_cli_flag_overrides_family_config_and_env(monkeypatch):
    monkeypatch.setenv("AUTO_COMMIT_ENABLED", "true")
    cli = CLI()
    family_config = {"auto_commit": False}

    assert cli._resolve_auto_commit(True, family_config) is True
    assert cli._resolve_auto_commit(False, family_config) is False


def test_family_config_overrides_env(monkeypatch):
    monkeypatch.setenv("AUTO_COMMIT_ENABLED", "false")
    cli = CLI()
    family_config = {"auto_commit": True}

    assert cli._resolve_auto_commit(None, family_config) is True


def test_env_var_used_as_fallback(monkeypatch):
    monkeypatch.setenv("AUTO_COMMIT_ENABLED", "true")
    cli = CLI()

    assert cli._resolve_auto_commit(None, {}) is True


def test_default_is_false(monkeypatch):
    monkeypatch.delenv("AUTO_COMMIT_ENABLED", raising=False)
    cli = CLI()

    assert cli._resolve_auto_commit(None, {}) is False
