"""
Configuration utilities for Example Review System.
Handles family config normalization and validation.
"""

from typing import Dict, Any, List


def normalize_family_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize family configuration to canonical format.

    Handles backward compatibility by converting legacy flat format
    to the canonical nested format defined in specs/family_config_schema.md.

    Args:
        config: Raw config dictionary (may be legacy or canonical format)

    Returns:
        Normalized config in canonical format

    Examples:
        Legacy format:
            {
                "name": "test",
                "package_id": "Newtonsoft.Json",
                "version": "latest_stable",
                "target_framework": "net6.0"
            }

        Canonical format:
            {
                "family": "test",
                "nuget_config": {
                    "primary_package": {
                        "name": "Newtonsoft.Json",
                        "version_strategy": "latest_stable"
                    },
                    "target_frameworks": ["net6.0"]
                },
                "code_defaults": {
                    "default_usings": []
                }
            }
    """
    # If already in canonical format, return as-is (with defaults)
    if 'nuget_config' in config and 'family' in config:
        return _apply_defaults(config)

    # Convert legacy format to canonical
    normalized = {}

    # family: use 'family' if present, else 'name'
    normalized['family'] = config.get('family') or config.get('name', '')

    # display_name: optional
    if 'display_name' in config:
        normalized['display_name'] = config['display_name']

    # content_pattern: optional
    if 'content_pattern' in config:
        normalized['content_pattern'] = config['content_pattern']

    # nuget_config: convert flat fields to nested structure
    nuget_config = {}

    primary_package = {}

    # package_id -> primary_package.name
    if 'package_id' in config:
        primary_package['name'] = config['package_id']
    elif 'nuget_config' in config and 'primary_package' in config['nuget_config']:
        primary_package = config['nuget_config']['primary_package'].copy()
    else:
        # Default to Newtonsoft.Json for test configs
        primary_package['name'] = 'Newtonsoft.Json'

    # version -> version_strategy
    if 'version' in config:
        if config['version'] in ['latest_stable', 'pinned']:
            primary_package['version_strategy'] = config['version']
        else:
            # Assume it's a pinned version
            primary_package['version_strategy'] = 'pinned'
            primary_package['pinned_version'] = config['version']
    elif 'version_strategy' not in primary_package:
        primary_package['version_strategy'] = 'latest_stable'

    nuget_config['primary_package'] = primary_package

    # additional_packages: preserve if present
    if 'additional_packages' in config:
        nuget_config['additional_packages'] = config['additional_packages']
    else:
        nuget_config['additional_packages'] = []

    # target_framework (singular) -> target_frameworks (array)
    if 'target_framework' in config:
        nuget_config['target_frameworks'] = [config['target_framework']]
    elif 'target_frameworks' in config:
        nuget_config['target_frameworks'] = config['target_frameworks']
    else:
        nuget_config['target_frameworks'] = ['net8.0']

    normalized['nuget_config'] = nuget_config

    # code_defaults: preserve if present, else empty
    if 'code_defaults' in config:
        normalized['code_defaults'] = config['code_defaults']
    else:
        normalized['code_defaults'] = {'default_usings': []}

    # patterns: preserve if present
    normalized['patterns'] = config.get('patterns', [])

    # non_existent_apis: preserve if present
    normalized['non_existent_apis'] = config.get('non_existent_apis', [])

    return normalized


def _apply_defaults(config: Dict[str, Any]) -> Dict[str, Any]:
    """Apply default values to canonical config."""
    config = config.copy()

    # Ensure code_defaults exists
    if 'code_defaults' not in config:
        config['code_defaults'] = {}

    if 'default_usings' not in config['code_defaults']:
        config['code_defaults']['default_usings'] = []

    # Ensure patterns and non_existent_apis exist
    if 'patterns' not in config:
        config['patterns'] = []

    if 'non_existent_apis' not in config:
        config['non_existent_apis'] = []

    # Ensure nuget_config has additional_packages
    if 'additional_packages' not in config['nuget_config']:
        config['nuget_config']['additional_packages'] = []

    # Ensure target_frameworks is an array
    if 'target_frameworks' not in config['nuget_config']:
        config['nuget_config']['target_frameworks'] = ['net8.0']

    return config


def validate_family_config(config: Dict[str, Any]) -> tuple[bool, List[str]]:
    """
    Validate family configuration.

    Args:
        config: Normalized config dictionary

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    # Required fields
    if not config.get('family'):
        errors.append("Missing required field: 'family'")

    # Validate family name format (lowercase alphanumeric + hyphens)
    family = config.get('family', '')
    if family and not all(c.isalnum() or c == '-' for c in family):
        errors.append(f"Invalid family name '{family}': must contain only lowercase alphanumeric and hyphens")

    if family and not family.islower():
        errors.append(f"Invalid family name '{family}': must be lowercase")

    # nuget_config validation
    if 'nuget_config' not in config:
        errors.append("Missing required field: 'nuget_config'")
    else:
        nuget = config['nuget_config']

        if 'primary_package' not in nuget:
            errors.append("Missing required field: 'nuget_config.primary_package'")
        else:
            primary = nuget['primary_package']

            if 'name' not in primary:
                errors.append("Missing required field: 'nuget_config.primary_package.name'")

            if 'version_strategy' not in primary:
                errors.append("Missing required field: 'nuget_config.primary_package.version_strategy'")
            elif primary['version_strategy'] not in ['latest_stable', 'pinned']:
                errors.append(f"Invalid version_strategy: '{primary['version_strategy']}' (must be 'latest_stable' or 'pinned')")

            if primary.get('version_strategy') == 'pinned' and 'pinned_version' not in primary:
                errors.append("Missing required field 'pinned_version' when version_strategy is 'pinned'")

        if 'target_frameworks' not in nuget or not nuget['target_frameworks']:
            errors.append("Missing or empty field: 'nuget_config.target_frameworks'")

    return (len(errors) == 0, errors)
