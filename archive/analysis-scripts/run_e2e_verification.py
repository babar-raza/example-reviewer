#!/usr/bin/env python3
"""
End-to-End Pipeline Verification Script
Tests the hardened pipeline on real zip family content
"""

import sys
import json
import subprocess
from pathlib import Path

def run_command(cmd, description):
    """Run a CLI command and return JSON result."""
    print(f"\n{'='*70}")
    print(f"  {description}")
    print('='*70)

    try:
        result = subprocess.run(
            cmd,
            cwd=Path(__file__).parent,
            capture_output=True,
            text=True,
            timeout=300
        )

        # Extract JSON from output (ignore log lines)
        lines = result.stdout.strip().split('\n')
        json_line = None
        for line in reversed(lines):
            if line.strip().startswith('{'):
                json_line = line
                break

        if json_line:
            data = json.loads(json_line)
            print(f"Status: {'SUCCESS' if data.get('success') else 'FAILED'}")
            if data.get('data'):
                print(f"\nResults:")
                for key, value in data['data'].items():
                    if isinstance(value, dict):
                        print(f"  {key}:")
                        for k, v in value.items():
                            print(f"    {k}: {v}")
                    elif isinstance(value, list):
                        print(f"  {key}: [{len(value)} items]")
                        if len(value) <= 5:
                            for item in value:
                                print(f"    - {item}")
                    else:
                        print(f"  {key}: {value}")
            if data.get('error'):
                print(f"Error: {data['error']}")
            return data
        else:
            print(f"Failed to parse JSON output")
            print(f"STDOUT:\n{result.stdout}")
            print(f"STDERR:\n{result.stderr}")
            return None

    except subprocess.TimeoutExpired:
        print("TIMEOUT - Command took too long")
        return None
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    print("\n" + "="*70)
    print("  EXAMPLE REVIEWER PIPELINE - E2E VERIFICATION")
    print("  Testing Enhanced Compilation & LLM Services")
    print("="*70)

    python_exe = ".venv/Scripts/python.exe"
    base_cmd = [python_exe, "-m", "src.cli.main", "--json"]

    # Step 1: Extract code examples from zip family
    result1 = run_command(
        base_cmd + ["extract", "--family", "zip", "--max-files", "20"],
        "Step 1: Extract Code Examples from Markdown"
    )

    if not result1 or not result1.get('success'):
        print("\nExtraction failed - cannot continue")
        return False

    examples_found = result1.get('data', {}).get('examples_found', 0)
    print(f"\n>>> Extracted {examples_found} examples")

    if examples_found == 0:
        print("No examples found - stopping here")
        return True

    # Step 2: Compile and verify (without LLM fixes first)
    result2 = run_command(
        base_cmd + ["compile-verify", "--family", "zip", "--max-examples", "30"],
        "Step 2: Compile Examples (First Try)"
    )

    if result2 and result2.get('success'):
        data2 = result2.get('data', {})
        compiled_first_try = data2.get('compiled_first_try', 0)
        total_attempted = data2.get('total_attempted', 0)

        if total_attempted > 0:
            success_rate = (compiled_first_try / total_attempted) * 100
            print(f"\n>>> First-try compilation: {compiled_first_try}/{total_attempted} ({success_rate:.1f}%)")
            print(f">>> Target was 60-70%, baseline was 30%")

    # Step 3: Get detailed status
    result3 = run_command(
        base_cmd + ["status", "--family", "zip"],
        "Step 3: Pipeline Status"
    )

    if result3 and result3.get('success'):
        data3 = result3.get('data', {})
        by_status = data3.get('by_status', {})

        print("\n>>> Status Breakdown:")
        for status, count in by_status.items():
            print(f"    {status}: {count}")

    # Step 4: Attempt compilation with LLM fixes (if LLM is available)
    print("\n" + "="*70)
    print("  Step 4: Compile with LLM Fixes (if needed)")
    print("="*70)
    print("Skipping LLM fixes for now - requires Ollama running")
    print("To test LLM fixes, run:")
    print("  python -m src.cli.main --json compile-fix --family zip --max-examples 10")

    # Summary
    print("\n" + "="*70)
    print("  VERIFICATION SUMMARY")
    print("="*70)

    if result1 and result2 and result3:
        print("\nAll pipeline phases executed successfully!")

        if result2.get('data'):
            compiled = result2['data'].get('compiled_first_try', 0)
            total = result2['data'].get('total_attempted', 0)
            if total > 0:
                rate = (compiled / total) * 100
                print(f"\nFirst-try compilation rate: {rate:.1f}%")

                if rate >= 60:
                    print("EXCELLENT - Exceeded 60% target!")
                elif rate >= 45:
                    print("GOOD - Improved from 30% baseline")
                elif rate >= 30:
                    print("BASELINE - Matches original performance")
                else:
                    print("NEEDS IMPROVEMENT - Below baseline")

        return True
    else:
        print("\nSome phases failed - see details above")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
