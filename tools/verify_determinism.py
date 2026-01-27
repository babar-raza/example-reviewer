"""
Verify Determinism Across Multiple Runs.

This tool compares results_summary.json files from multiple runs to verify determinism.
It ignores run_id and timestamps, and compares status counts and per-example terminal statuses.
Drift scores are compared with tolerance.

Usage:
    python tools/verify_determinism.py run1/results_summary.json run2/results_summary.json
    python tools/verify_determinism.py --drift-tolerance 0.02 run1/results_summary.json run2/results_summary.json

Exit Codes:
    0 - Runs are deterministic (match within tolerance)
    1 - Runs are NOT deterministic (differences detected)
    2 - Error (file not found, invalid JSON, etc.)

Comparison Logic:
    - Ignores: run_id, timestamps, duration fields
    - Compares: status counts, per-example terminal statuses
    - Drift scores: compared with tolerance (default 0.02)
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional


def setup_logging(verbose: bool = False) -> None:
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - [%(levelname)s] %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )


def load_json(filepath: Path) -> Optional[Dict[str, Any]]:
    """
    Load JSON file.

    Args:
        filepath: Path to JSON file

    Returns:
        Dict or None on error
    """
    logger = logging.getLogger(__name__)

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"File not found: {filepath}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {filepath}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error loading {filepath}: {e}")
        return None


def normalize_run(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize run data by removing non-deterministic fields.

    Removes:
        - run_id
        - timestamps (started_at, completed_at, etc.)
        - duration fields

    Args:
        data: Raw run data

    Returns:
        Normalized run data for comparison
    """
    normalized = {}

    # Copy all fields except non-deterministic ones
    ignore_keys = {
        'run_id', 'started_at', 'completed_at', 'timestamp',
        'duration_ms', 'duration_seconds', 'created_at', 'updated_at'
    }

    for key, value in data.items():
        if key in ignore_keys:
            continue

        # Handle nested dicts/lists
        if isinstance(value, dict):
            normalized[key] = normalize_run(value)
        elif isinstance(value, list):
            normalized[key] = [normalize_run(item) if isinstance(item, dict) else item for item in value]
        else:
            normalized[key] = value

    return normalized


def compare_drift_scores(
    score1: Optional[float],
    score2: Optional[float],
    tolerance: float
) -> bool:
    """
    Compare drift scores with tolerance.

    Args:
        score1: First drift score (or None)
        score2: Second drift score (or None)
        tolerance: Maximum allowed difference

    Returns:
        True if scores match within tolerance
    """
    # Both None = match
    if score1 is None and score2 is None:
        return True

    # One None, one value = no match
    if score1 is None or score2 is None:
        return False

    # Compare with tolerance
    return abs(score1 - score2) <= tolerance


def compare_status_counts(
    run1: Dict[str, Any],
    run2: Dict[str, Any]
) -> Tuple[bool, List[str]]:
    """
    Compare status count summaries between two runs.

    Args:
        run1: First run data
        run2: Second run data

    Returns:
        Tuple of (match: bool, differences: List[str])
    """
    differences = []

    # Extract status counts (might be in different keys depending on format)
    def get_status_counts(run_data: Dict[str, Any]) -> Dict[str, int]:
        """Extract status counts from run data."""
        # Try different possible locations
        if 'status_counts' in run_data:
            return run_data['status_counts']
        if 'by_status' in run_data:
            return run_data['by_status']
        if 'summary' in run_data and 'status_counts' in run_data['summary']:
            return run_data['summary']['status_counts']
        return {}

    counts1 = get_status_counts(run1)
    counts2 = get_status_counts(run2)

    # Get all status keys
    all_statuses = set(counts1.keys()) | set(counts2.keys())

    for status in sorted(all_statuses):
        count1 = counts1.get(status, 0)
        count2 = counts2.get(status, 0)

        if count1 != count2:
            differences.append(f"Status '{status}': run1={count1}, run2={count2}")

    return len(differences) == 0, differences


def compare_example_statuses(
    run1: Dict[str, Any],
    run2: Dict[str, Any],
    drift_tolerance: float
) -> Tuple[bool, List[str]]:
    """
    Compare per-example terminal statuses between two runs.

    Args:
        run1: First run data
        run2: Second run data
        drift_tolerance: Tolerance for drift score comparison

    Returns:
        Tuple of (match: bool, differences: List[str])
    """
    differences = []

    # Extract examples (might be in different keys)
    def get_examples(run_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract examples dict from run data."""
        if 'examples' in run_data:
            return run_data['examples']
        if 'results' in run_data:
            return run_data['results']
        return {}

    examples1 = get_examples(run1)
    examples2 = get_examples(run2)

    # Get all example IDs
    all_example_ids = set(examples1.keys()) | set(examples2.keys())

    if not all_example_ids:
        # No per-example data to compare
        return True, []

    for example_id in sorted(all_example_ids):
        ex1 = examples1.get(example_id, {})
        ex2 = examples2.get(example_id, {})

        # Compare status
        status1 = ex1.get('status', 'UNKNOWN')
        status2 = ex2.get('status', 'UNKNOWN')

        if status1 != status2:
            differences.append(f"Example {example_id}: status run1={status1}, run2={status2}")

        # Compare drift_score if present
        drift1 = ex1.get('drift_score')
        drift2 = ex2.get('drift_score')

        if not compare_drift_scores(drift1, drift2, drift_tolerance):
            differences.append(
                f"Example {example_id}: drift_score run1={drift1}, run2={drift2} "
                f"(exceeds tolerance {drift_tolerance})"
            )

    return len(differences) == 0, differences


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Verify determinism across multiple pipeline runs',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument('files', nargs='+', type=str,
                        help='Results summary JSON files to compare (2 or more)')
    parser.add_argument('--drift-tolerance', type=float, default=0.02,
                        help='Tolerance for drift score comparison (default: 0.02)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Verbose output')

    args = parser.parse_args()

    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    if len(args.files) < 2:
        logger.error("Need at least 2 files to compare")
        return 2

    logger.info("Determinism Verification")
    logger.info("=" * 80)
    logger.info(f"Comparing {len(args.files)} runs")
    logger.info(f"Drift tolerance: {args.drift_tolerance}")
    logger.info("")

    # Load all files
    runs = []
    for filepath_str in args.files:
        filepath = Path(filepath_str)
        logger.info(f"Loading: {filepath}")

        data = load_json(filepath)
        if data is None:
            return 2

        runs.append({
            'filepath': filepath,
            'data': data,
            'normalized': normalize_run(data)
        })

    logger.info("")

    # Compare all pairs
    all_match = True
    comparison_count = 0

    for i in range(len(runs)):
        for j in range(i + 1, len(runs)):
            run1 = runs[i]
            run2 = runs[j]

            comparison_count += 1
            logger.info(f"Comparison {comparison_count}: {run1['filepath'].name} vs {run2['filepath'].name}")
            logger.info("-" * 80)

            # Compare status counts
            status_match, status_diffs = compare_status_counts(
                run1['normalized'],
                run2['normalized']
            )

            if not status_match:
                logger.error("Status count mismatch:")
                for diff in status_diffs:
                    logger.error(f"  {diff}")
                all_match = False
            else:
                logger.info("Status counts: MATCH")

            # Compare example statuses
            example_match, example_diffs = compare_example_statuses(
                run1['normalized'],
                run2['normalized'],
                args.drift_tolerance
            )

            if not example_match:
                logger.error("Per-example status mismatch:")
                for diff in example_diffs[:10]:  # Limit to 10 differences
                    logger.error(f"  {diff}")
                if len(example_diffs) > 10:
                    logger.error(f"  ... and {len(example_diffs) - 10} more differences")
                all_match = False
            else:
                logger.info("Per-example statuses: MATCH")

            logger.info("")

    # Final verdict
    logger.info("=" * 80)
    if all_match:
        logger.info("[OK] DETERMINISTIC - All runs match within tolerance")
        return 0
    else:
        logger.error("[FAIL] NOT DETERMINISTIC - Differences detected")
        return 1


if __name__ == '__main__':
    sys.exit(main())
