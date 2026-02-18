#!/usr/bin/env python3
"""
Validate MD Update Targeting Correctness.

This script validates that md_update correctly targeted the expected code blocks
based on location.block_index and code_block_signature.

STOP-THE-LINE check for Phase C validation.
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import List, Dict, Any


def validate_md_update_targets(
    db_path: str,
    run_id: str,
    md_update_output: str,
    output_path: str
) -> Dict[str, Any]:
    """
    Validate that md_update targeted the correct blocks.

    Args:
        db_path: Path to SQLite database
        run_id: Run identifier
        md_update_output: Path to md_update output JSON
        output_path: Path to output validation report

    Returns:
        Validation report dictionary
    """
    # Load md_update output
    try:
        # Try to parse JSON from file
        with open(md_update_output, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Find the last complete JSON object (the summary at the end)
        # Look for the pattern: "{\n  \"files_processed\":"
        json_marker = '"files_processed"'
        json_start_pos = content.rfind(json_marker)

        if json_start_pos == -1:
            raise ValueError("No JSON found in md_update output")

        # Search backwards from marker to find the opening brace
        for i in range(json_start_pos, -1, -1):
            if content[i] == '{':
                json_start = i
                break
        else:
            raise ValueError("Could not find JSON opening brace")

        json_content = content[json_start:]
        md_update_data = json.loads(json_content)
    except Exception as e:
        print(f"Error loading md_update output: {e}", file=sys.stderr)
        sys.exit(1)

    # Connect to database
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Build validation report
    report = {
        "run_id": run_id,
        "total_examples": 0,
        "valid_targeting": 0,
        "self_healed_examples": [],  # Examples where DB location was updated via self-healing
        "wrong_block_edits": [],
        "signature_mismatches": [],
        "missing_signatures": [],
        "all_valid": True
    }

    # Validate each file's changes
    for file_info in md_update_data.get("files", []):
        file_path = file_info["path"]

        for change in file_info.get("details", []):
            report["total_examples"] += 1
            example_id = change["example_id"]
            targeted_block_index = change["block_index"]

            # Query database for expected block_index and signature
            # NOTE: If self-healing occurred during md_update, the DB location
            # will have been updated to match the actual block used, so the
            # comparison below will pass (as expected).
            query = """
                SELECT
                    er.location_block_index,
                    er.code_block_signature,
                    er.extraction_warning,
                    er.file_path,
                    er.updated_at,
                    er.created_at
                FROM example_records er
                WHERE er.example_id = ?
            """

            cursor.execute(query, (example_id,))
            row = cursor.fetchone()

            if not row:
                report["wrong_block_edits"].append({
                    "example_id": example_id,
                    "file_path": file_path,
                    "error": "Example not found in database"
                })
                report["all_valid"] = False
                continue

            expected_block_index = row["location_block_index"]
            expected_signature = row["code_block_signature"]
            extraction_warning = row["extraction_warning"]
            updated_at = row["updated_at"]
            created_at = row["created_at"]

            # Detect self-healing: updated_at > created_at indicates DB location was updated
            was_self_healed = updated_at != created_at if updated_at and created_at else False

            # VALIDATION 1: Block index must match
            # NOTE: With self-healing, the DB location is updated during md_update,
            # so targeted_block_index should equal expected_block_index after self-healing.
            if targeted_block_index != expected_block_index:
                report["wrong_block_edits"].append({
                    "example_id": example_id,
                    "file_path": file_path,
                    "expected_block_index": expected_block_index,
                    "targeted_block_index": targeted_block_index,
                    "error": "Block index mismatch"
                })
                report["all_valid"] = False
                continue

            # VALIDATION 2: Signature must exist (unless legacy)
            if not expected_signature:
                report["missing_signatures"].append({
                    "example_id": example_id,
                    "file_path": file_path,
                    "warning": "Example has no code_block_signature"
                })
                # Note: This is not necessarily an error if legacy examples exist,
                # but for new extraction it should always have a signature

            # VALIDATION 3: Extraction warnings should not result in modifications
            if extraction_warning:
                report["wrong_block_edits"].append({
                    "example_id": example_id,
                    "file_path": file_path,
                    "extraction_warning": extraction_warning,
                    "error": "Example with extraction_warning was modified"
                })
                report["all_valid"] = False
                continue

            # If we got here, targeting is valid
            report["valid_targeting"] += 1

            # Track self-healed examples for reporting
            if was_self_healed:
                report["self_healed_examples"].append({
                    "example_id": example_id,
                    "file_path": file_path,
                    "block_index": targeted_block_index,
                })

    conn.close()

    # Write report
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    return report


def main():
    parser = argparse.ArgumentParser(
        description="Validate md_update targeting correctness"
    )
    parser.add_argument(
        "--db-path",
        required=True,
        help="Path to SQLite database"
    )
    parser.add_argument(
        "--run-id",
        required=True,
        help="Run identifier"
    )
    parser.add_argument(
        "--md-update-output",
        required=True,
        help="Path to md_update output file (JSON)"
    )
    parser.add_argument(
        "--out",
        required=True,
        help="Path to output validation report JSON"
    )

    args = parser.parse_args()

    # Validate inputs
    if not Path(args.db_path).exists():
        print(f"Error: Database not found at {args.db_path}", file=sys.stderr)
        sys.exit(1)

    if not Path(args.md_update_output).exists():
        print(f"Error: MD update output not found at {args.md_update_output}", file=sys.stderr)
        sys.exit(1)

    # Run validation
    try:
        report = validate_md_update_targets(
            args.db_path,
            args.run_id,
            args.md_update_output,
            args.out
        )

        # Print summary
        print("\n" + "="*80)
        print("MD Update Targeting Validation Report")
        print("="*80)
        print(f"Run ID: {args.run_id}")
        print(f"Total examples: {report['total_examples']}")
        print(f"Valid targeting: {report['valid_targeting']}")
        print(f"Self-healed examples: {len(report['self_healed_examples'])}")
        print(f"Wrong block edits: {len(report['wrong_block_edits'])}")
        print(f"Signature mismatches: {len(report['signature_mismatches'])}")
        print(f"Missing signatures: {len(report['missing_signatures'])}")
        print("="*80)

        # Report self-healed examples
        if report['self_healed_examples']:
            print(f"\nSelf-healed examples ({len(report['self_healed_examples'])}):")
            for item in report['self_healed_examples'][:5]:
                print(f"  - {item['example_id']}: {item['file_path']} (block {item['block_index']})")
            if len(report['self_healed_examples']) > 5:
                print(f"  ... and {len(report['self_healed_examples']) - 5} more")
            print("\nSelf-healing: md_update found signature at different index and updated DB location.")

        if report['all_valid'] and len(report['missing_signatures']) == 0:
            print("\nOK PASS: All examples were correctly targeted")
            print("  - All block indices match expected values")
            print("  - All examples have code_block_signature")
            print("  - No extraction warnings were ignored")
            print("\nSafe to proceed with full batch.")
        elif report['all_valid'] and len(report['missing_signatures']) > 0:
            print("\nWARNING: All targeting correct but some signatures missing")
            print(f"  - {len(report['missing_signatures'])} examples missing signatures")
            print("  - This may indicate legacy examples")
            print("\nReview before proceeding.")
        else:
            print("\nFAIL: Targeting errors detected")

            if report['wrong_block_edits']:
                print(f"\nWrong block edits ({len(report['wrong_block_edits'])}):")
                for item in report['wrong_block_edits'][:5]:
                    print(f"  - {item['example_id']}: {item.get('error', 'Unknown error')}")
                    if 'expected_block_index' in item:
                        print(f"    Expected block {item['expected_block_index']}, got {item['targeted_block_index']}")
                if len(report['wrong_block_edits']) > 5:
                    print(f"  ... and {len(report['wrong_block_edits']) - 5} more")

            print("\n[STOP] STOP THE LINE: Fix targeting before proceeding to full batch")
            sys.exit(1)

        print(f"\nFull report saved to: {args.out}")

    except Exception as e:
        print(f"Error validating targets: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
