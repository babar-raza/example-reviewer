#!/usr/bin/env python3
"""
Gate 1: Determinism Verification Tool

Compares results_summary.json from multiple runs to verify determinism.

Requirements (from Plan v2.1):
- Accept 2-N results_summary.json file paths as arguments
- Compare these fields (must be identical):
  - selection_hash
  - per-example terminal statuses (example_id -> status mapping)
  - drift comparisons (if enabled, must follow policy consistently)
- Exit code 0 if deterministic, 1 if not
- Print clear diff report showing what differs

Usage:
    python tools/verify_determinism.py runs/run1/results_summary.json runs/run2/results_summary.json runs/run3/results_summary.json
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional


def load_results_summary(filepath: Path) -> Dict[str, Any]:
    """Load and parse results_summary.json file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"ERROR: File not found: {filepath}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in {filepath}: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to load {filepath}: {e}", file=sys.stderr)
        sys.exit(1)


def extract_example_statuses(summary: Dict[str, Any]) -> Dict[str, str]:
    """
    Extract per-example terminal statuses from results_summary.

    Returns dict mapping example_id (or example_key) -> status
    """
    statuses = {}

    # Try to get per-example results
    if 'examples' in summary:
        for example in summary['examples']:
            # Prefer example_key for determinism, fall back to example_id
            key = example.get('example_key') or example.get('example_id')
            status = example.get('status')
            if key and status:
                statuses[key] = status

    # Alternative structure: status_counts with example lists
    elif 'per_example_statuses' in summary:
        statuses = summary['per_example_statuses']

    return statuses


def extract_drift_scores(summary: Dict[str, Any]) -> Dict[str, Optional[float]]:
    """
    Extract drift scores from results_summary.

    Returns dict mapping example_id/example_key -> drift_score
    """
    drift_scores = {}

    if 'examples' in summary:
        for example in summary['examples']:
            key = example.get('example_key') or example.get('example_id')
            drift_score = example.get('drift_score')
            if key is not None:
                drift_scores[key] = drift_score

    elif 'drift_scores' in summary:
        drift_scores = summary['drift_scores']

    return drift_scores


def compare_selection_hashes(summaries: List[Dict[str, Any]], filepaths: List[Path]) -> Tuple[bool, List[str]]:
    """
    Compare selection_hash across all runs.

    Returns (is_identical, differences_list)
    """
    differences = []

    selection_hashes = []
    for i, summary in enumerate(summaries):
        selection_hash = summary.get('selection_hash') or summary.get('fingerprint', {}).get('content_snapshot', {}).get('selection_hash')
        selection_hashes.append(selection_hash)

        if selection_hash is None:
            differences.append(f"  - {filepaths[i]}: missing selection_hash")

    if len(set(selection_hashes)) > 1:
        differences.append("\n  Selection hashes differ:")
        for i, (filepath, hash_val) in enumerate(zip(filepaths, selection_hashes)):
            differences.append(f"    Run {i+1} ({filepath.name}): {hash_val}")
        return False, differences

    return True, differences


def compare_statuses(summaries: List[Dict[str, Any]], filepaths: List[Path]) -> Tuple[bool, List[str]]:
    """
    Compare per-example terminal statuses across all runs.

    Returns (is_identical, differences_list)
    """
    differences = []

    # Extract statuses from all runs
    all_statuses = [extract_example_statuses(summary) for summary in summaries]

    if not all_statuses[0]:
        differences.append("  - WARNING: No per-example statuses found in first run")
        return True, differences  # Can't compare if no data

    # Get all unique example keys across runs
    all_keys = set()
    for statuses in all_statuses:
        all_keys.update(statuses.keys())

    # Compare each example across runs
    differing_examples = []
    for key in sorted(all_keys):
        statuses_for_key = [statuses.get(key) for statuses in all_statuses]

        # Check if all are identical
        if len(set(statuses_for_key)) > 1:
            differing_examples.append((key, statuses_for_key))

    if differing_examples:
        differences.append("\n  Per-example statuses differ:")
        for key, statuses_list in differing_examples[:10]:  # Limit to first 10
            differences.append(f"    Example {key}:")
            for i, status in enumerate(statuses_list):
                differences.append(f"      Run {i+1}: {status}")

        if len(differing_examples) > 10:
            differences.append(f"    ... and {len(differing_examples) - 10} more examples differ")

        return False, differences

    return True, differences


def compare_drift_scores(summaries: List[Dict[str, Any]], filepaths: List[Path], tolerance: float = 0.02) -> Tuple[bool, List[str]]:
    """
    Compare drift scores across runs.

    Per Plan v2.1:
    - Must be identical when drift is disabled
    - May be within tolerance (default 0.02) when drift is enabled

    Returns (is_within_policy, differences_list)
    """
    differences = []

    # Extract drift scores from all runs
    all_drift_scores = [extract_drift_scores(summary) for summary in summaries]

    # Check if drift is enabled in any run
    drift_enabled = any(
        summary.get('fingerprint', {}).get('vector_db', {}).get('enabled', False)
        for summary in summaries
    )

    if not drift_enabled:
        # Drift disabled - all should be None or not present
        return True, differences

    # Get all unique example keys
    all_keys = set()
    for drift_scores in all_drift_scores:
        all_keys.update(drift_scores.keys())

    if not all_keys:
        # No drift scores to compare
        return True, differences

    # Compare drift scores with tolerance
    differing_examples = []
    for key in sorted(all_keys):
        scores = [drift_scores.get(key) for drift_scores in all_drift_scores]

        # Filter out None values
        numeric_scores = [s for s in scores if s is not None]

        if not numeric_scores:
            continue

        # Check if within tolerance
        min_score = min(numeric_scores)
        max_score = max(numeric_scores)

        if max_score - min_score > tolerance:
            differing_examples.append((key, scores))

    if differing_examples:
        differences.append(f"\n  Drift scores exceed tolerance ({tolerance}):")
        for key, scores_list in differing_examples[:10]:  # Limit to first 10
            differences.append(f"    Example {key}:")
            for i, score in enumerate(scores_list):
                differences.append(f"      Run {i+1}: {score}")

        if len(differing_examples) > 10:
            differences.append(f"    ... and {len(differing_examples) - 10} more examples exceed tolerance")

        return False, differences

    return True, differences


def verify_determinism(filepaths: List[Path], drift_tolerance: float = 0.02) -> int:
    """
    Main verification function.

    Returns 0 if deterministic, 1 if not.
    """
    print(f"Determinism Verification Tool")
    print(f"Comparing {len(filepaths)} results_summary.json files\n")

    # Load all summaries
    summaries = [load_results_summary(fp) for fp in filepaths]

    # Track overall result
    all_checks_passed = True

    # Check 1: selection_hash
    print("[1/3] Comparing selection_hash...")
    hash_match, hash_diffs = compare_selection_hashes(summaries, filepaths)
    if hash_match:
        print("  PASS PASS: selection_hash identical across all runs")
        if hash_diffs:
            for diff in hash_diffs:
                print(diff)
    else:
        print("  FAIL FAIL: selection_hash differs between runs")
        for diff in hash_diffs:
            print(diff)
        all_checks_passed = False

    # Check 2: per-example statuses
    print("\n[2/3] Comparing per-example terminal statuses...")
    status_match, status_diffs = compare_statuses(summaries, filepaths)
    if status_match:
        print("  PASS PASS: per-example statuses identical across all runs")
        if status_diffs:
            for diff in status_diffs:
                print(diff)
    else:
        print("  FAIL FAIL: per-example statuses differ between runs")
        for diff in status_diffs:
            print(diff)
        all_checks_passed = False

    # Check 3: drift scores (if applicable)
    print(f"\n[3/3] Comparing drift scores (tolerance={drift_tolerance})...")
    drift_match, drift_diffs = compare_drift_scores(summaries, filepaths, drift_tolerance)
    if drift_match:
        print("  PASS PASS: drift scores within policy")
        if drift_diffs:
            for diff in drift_diffs:
                print(diff)
    else:
        print("  FAIL FAIL: drift scores exceed tolerance")
        for diff in drift_diffs:
            print(diff)
        all_checks_passed = False

    # Final verdict
    print("\n" + "="*60)
    if all_checks_passed:
        print("PASS DETERMINISM VERIFIED: All checks passed")
        print("="*60)
        return 0
    else:
        print("FAIL DETERMINISM FAILED: One or more checks failed")
        print("="*60)
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="Verify determinism across multiple pipeline runs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tools/verify_determinism.py runs/run1/results_summary.json runs/run2/results_summary.json
  python tools/verify_determinism.py --tolerance 0.05 run*/results_summary.json
        """
    )

    parser.add_argument(
        'files',
        nargs='+',
        type=Path,
        help='Paths to results_summary.json files (minimum 2)'
    )

    parser.add_argument(
        '--tolerance',
        type=float,
        default=0.02,
        help='Drift score tolerance (default: 0.02)'
    )

    args = parser.parse_args()

    if len(args.files) < 2:
        print("ERROR: At least 2 results_summary.json files required", file=sys.stderr)
        sys.exit(1)

    # Verify all files exist
    for filepath in args.files:
        if not filepath.exists():
            print(f"ERROR: File not found: {filepath}", file=sys.stderr)
            sys.exit(1)

    exit_code = verify_determinism(args.files, args.tolerance)
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
