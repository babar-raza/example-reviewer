"""
Test script to verify API pattern loading.
Verifies that new ASP.NET Core patterns are accessible to the validation system.
"""

import json
import sys
from pathlib import Path

def test_pattern_loading():
    """Test that API patterns load correctly from family config."""
    print("Testing pattern loading...")

    # Load family config
    config_path = Path("config/families/zip.json")
    if not config_path.exists():
        print(f"ERROR: Config file not found: {config_path}")
        return False

    with open(config_path, 'r') as f:
        family_config = json.load(f)

    # Verify api_patterns exists
    if 'api_patterns' not in family_config:
        print("ERROR: 'api_patterns' key not found in config")
        return False

    api_patterns = family_config['api_patterns']
    print(f"  Found {len(api_patterns)} patterns")

    # Verify specific patterns exist
    expected_patterns = [
        'compression_basic',
        'compression_static',
        'default_parameters',
        'aspnet_minimal_api_setup',
        'aspnet_file_response',
        'aspnet_http_context_response'
    ]

    all_found = True
    for pattern_name in expected_patterns:
        if pattern_name in api_patterns:
            pattern = api_patterns[pattern_name]
            has_description = 'description' in pattern
            has_code = 'code' in pattern
            code_length = len(pattern.get('code', ''))

            status = "OK" if (has_description and has_code and code_length > 0) else "INCOMPLETE"
            print(f"  [{status}] {pattern_name}: {code_length} chars")

            if status == "INCOMPLETE":
                all_found = False
        else:
            print(f"  [MISSING] {pattern_name}")
            all_found = False

    # Verify new ASP.NET patterns have required content
    print("\nVerifying ASP.NET Core patterns:")

    aspnet_checks = [
        ('aspnet_minimal_api_setup', ['using Microsoft.AspNetCore.Builder', 'WebApplication.CreateBuilder']),
        ('aspnet_file_response', ['Results.File', 'DeflateCompressionSettings()']),
        ('aspnet_http_context_response', ['HttpContext', 'SaveAsync does not exist'])
    ]

    for pattern_name, required_strings in aspnet_checks:
        pattern = api_patterns.get(pattern_name, {})
        code = pattern.get('code', '')

        all_present = all(s in code for s in required_strings)
        status = "OK" if all_present else "MISSING CONTENT"

        missing = [s for s in required_strings if s not in code]
        if missing:
            print(f"  [{status}] {pattern_name}")
            print(f"      Missing: {missing}")
        else:
            print(f"  [{status}] {pattern_name}")

    if not all_found:
        print("\nRESULT: FAILED - Some patterns missing or incomplete")
        return False

    print("\nRESULT: PASSED - All patterns loaded successfully")
    return True

if __name__ == '__main__':
    success = test_pattern_loading()
    sys.exit(0 if success else 1)
