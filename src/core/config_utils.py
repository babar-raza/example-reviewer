"""Compatibility helpers for family config normalization and validation."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple


def normalize_family_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize legacy family config into canonical format."""
    result: Dict[str, Any] = dict(config or {})

    if "family" not in result and "name" in result:
        result["family"] = result.pop("name")

    # Legacy flat fields -> canonical nuget_config
    if any(key in result for key in ("package_id", "version", "target_framework")):
        nuget = result.get("nuget_config", {})
        primary = nuget.get("primary_package", {})

        if "package_id" in result and "name" not in primary:
            primary["name"] = result.get("package_id")

        version = result.get("version")
        if version:
            if version == "latest_stable":
                primary["version_strategy"] = "latest_stable"
            elif version == "pinned":
                primary["version_strategy"] = "pinned"
            else:
                primary["version_strategy"] = "pinned"
                primary["pinned_version"] = version

        primary.setdefault("version_strategy", "latest_stable")
        nuget["primary_package"] = primary

        target_framework = result.get("target_framework")
        if target_framework:
            nuget["target_frameworks"] = [target_framework]
        nuget.setdefault("target_frameworks", ["net8.0"])
        result["nuget_config"] = nuget

    if "nuget_config" in result:
        nuget = result.get("nuget_config", {})
        primary = nuget.get("primary_package", {})
        primary.setdefault("version_strategy", "latest_stable")
        nuget["primary_package"] = primary
        if "target_frameworks" not in nuget:
            nuget["target_frameworks"] = ["net8.0"]
        result["nuget_config"] = nuget

    code_defaults = result.get("code_defaults", {})
    code_defaults.setdefault("default_usings", [])
    result["code_defaults"] = code_defaults

    return result


def validate_family_config(config: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate canonical family config fields."""
    errors: List[str] = []
    if not config:
        return False, ["family is required"]

    family = config.get("family", "")
    if not family:
        errors.append("family is required")
    else:
        if family.lower() != family:
            errors.append("family name must be lowercase")
        if not re.fullmatch(r"[a-z0-9-]+", family):
            errors.append("family name must be lowercase alphanumeric or hyphenated")

    nuget = config.get("nuget_config", {})
    primary = nuget.get("primary_package", {})
    version_strategy = primary.get("version_strategy", "latest_stable")

    if version_strategy not in ("latest_stable", "pinned"):
        errors.append("version_strategy must be 'latest_stable' or 'pinned'")
    if version_strategy == "pinned" and not primary.get("pinned_version"):
        errors.append("pinned_version is required when version_strategy is pinned")

    target_frameworks = nuget.get("target_frameworks", [])
    if not target_frameworks:
        errors.append("target_frameworks must contain at least one framework")

    return len(errors) == 0, errors
