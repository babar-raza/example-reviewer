#!/usr/bin/env python3
"""
Validate that all VERIFIED examples have required signature and block_index fields.

This is a STOP-THE-LINE check for Phase B.
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import List, Dict, Any


def validate_verified_examples(
    db_path: str,
    run_id: str,
    output_path: str
) -> Dict[str, Any]:
    """
    Validate all VERIFIED examples have code_block_signature and location.block_index.

    Args:
        db_path: Path to the SQLite database
        run_id: Run identifier to validate
        output_path: Path to output validation report

    Returns:
        Validation report dictionary
    """
    # Connect to database
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Query for VERIFIED examples with all required fields
    query = """
        SELECT
            ers.example_id,
            er.file_path,
            er.location_block_index,
            er.code_block_signature,
            er.extraction_warning,
            er.location_anchor,
            er.source_type
        FROM example_run_state ers
        JOIN example_records er ON ers.example_id = er.example_id
        WHERE ers.run_id = ? AND ers.status = 'VERIFIED'
        ORDER BY er.file_path, er.location_anchor
    """

    cursor.execute(query, (run_id,))
    rows = cursor.fetchall()

    # Validate each example
    report = {
        "run_id": run_id,
        "total_verified": len(rows),
        "valid": 0,
        "missing_signature": [],
        "missing_block_index": [],
        "has_extraction_warning": [],
        "all_valid": True
    }

    for row in rows:
        example_id = row["example_id"]
        file_path = row["file_path"]
        signature = row["code_block_signature"]
        block_index = row["location_block_index"]
        extraction_warning = row["extraction_warning"]
        source_type = row["source_type"]

        # Check for missing signature (only for inline examples)
        if source_type == "inline" and not signature:
            report["missing_signature"].append({
                "example_id": example_id,
                "file_path": file_path,
                "source_type": source_type
            })
            report["all_valid"] = False

        # Check for missing block_index (only for inline examples)
        # For inline examples, block_index should be >= 0
        if source_type == "inline" and (block_index is None or block_index < 0):
            report["missing_block_index"].append({
                "example_id": example_id,
                "file_path": file_path,
                "block_index": block_index,
                "source_type": source_type
            })
            report["all_valid"] = False

        # Check for extraction warnings
        if extraction_warning:
            report["has_extraction_warning"].append({
                "example_id": example_id,
                "file_path": file_path,
                "warning": extraction_warning
            })

        # Count valid examples
        # For inline: must have signature and block_index >= 0
        # For gist: block_index can be -1 (not applicable), signature not required for md_update
        if source_type == "inline":
            if signature and block_index is not None and block_index >= 0:
                report["valid"] += 1
        else:
            # Gist examples don't need signature/block_index for md_update
            report["valid"] += 1

    conn.close()

    # Write report to JSON file
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    return report


def main():
    parser = argparse.ArgumentParser(
        description="Validate VERIFIED examples have required signature/block_index"
    )
    parser.add_argument(
        "--db-path",
        required=True,
        help="Path to SQLite database"
    )
    parser.add_argument(
        "--run-id",
        required=True,
        help="Run identifier to validate"
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path to output validation report JSON"
    )

    args = parser.parse_args()

    # Verify database exists
    if not Path(args.db_path).exists():
        print(f"Error: Database not found at {args.db_path}", file=sys.stderr)
        sys.exit(1)

    # Validate examples
    try:
        report = validate_verified_examples(
            args.db_path,
            args.run_id,
            args.output
        )

        # Print summary
        print(f"\n{'='*80}")
        print("VERIFIED Examples Validation Report")
        print(f"{'='*80}")
        print(f"Run ID: {args.run_id}")
        print(f"Total VERIFIED examples: {report['total_verified']}")
        print(f"Valid (signature + block_index): {report['valid']}")
        print(f"Missing signature: {len(report['missing_signature'])}")
        print(f"Missing block_index: {len(report['missing_block_index'])}")
        print(f"Has extraction warning: {len(report['has_extraction_warning'])}")
        print(f"{'='*80}")

        if report['all_valid']:
            print("\nOK PASS: All VERIFIED examples have required fields")
            print("  - All examples have code_block_signature")
            print("  - All examples have location.block_index")
            print("\nSafe to proceed to md_update phase.")
        else:
            print("\nFAIL FAIL: Some VERIFIED examples missing required fields")
            if report['missing_signature']:
                print(f"\nMissing signature ({len(report['missing_signature'])}):")
                for item in report['missing_signature'][:5]:
                    print(f"  - {item['example_id']}: {item['file_path']}")
                if len(report['missing_signature']) > 5:
                    print(f"  ... and {len(report['missing_signature']) - 5} more")

            if report['missing_block_index']:
                print(f"\nMissing block_index ({len(report['missing_block_index'])}):")
                for item in report['missing_block_index'][:5]:
                    print(f"  - {item['example_id']}: {item['file_path']}")
                if len(report['missing_block_index']) > 5:
                    print(f"  ... and {len(report['missing_block_index']) - 5} more")

            print("\n[STOP] STOP THE LINE: Fix extraction persistence before md_update")
            sys.exit(1)

        if report['has_extraction_warning']:
            print(f"\n[WARNING]  WARNING: {len(report['has_extraction_warning'])} examples have extraction warnings")
            print("These examples may need manual review.")

        print(f"\nFull report saved to: {args.output}")

    except Exception as e:
        print(f"Error validating examples: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
