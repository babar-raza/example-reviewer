#!/usr/bin/env python3
"""
Export VERIFIED examples from a specific run to JSON.

This script queries the database for all examples with status=VERIFIED
for a given run_id and exports their details to JSON format.
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import List, Dict, Any


def export_verified_examples(
    db_path: str,
    run_id: str,
    output_path: str
) -> List[Dict[str, Any]]:
    """
    Export all VERIFIED examples for a given run_id.

    Args:
        db_path: Path to the SQLite database
        run_id: Run identifier to query
        output_path: Path to output JSON file

    Returns:
        List of VERIFIED example dictionaries
    """
    # Connect to database
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Query for VERIFIED examples
    query = """
        SELECT
            ers.example_id,
            er.file_path,
            er.location_anchor,
            er.description_context,
            ers.verified_code
        FROM example_run_state ers
        JOIN example_records er ON ers.example_id = er.example_id
        WHERE ers.run_id = ? AND ers.status = 'VERIFIED'
        ORDER BY er.file_path, er.location_anchor
    """

    cursor.execute(query, (run_id,))
    rows = cursor.fetchall()

    # Convert to list of dictionaries
    verified_examples = []
    for row in rows:
        verified_examples.append({
            "example_id": row["example_id"],
            "file_path": row["file_path"],
            "snippet_id": row["location_anchor"] or "",
            "app_context": row["description_context"] or "",
            "verified_code_ref": row["verified_code"] or ""
        })

    conn.close()

    # Write to JSON file
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(verified_examples, f, indent=2, ensure_ascii=False)

    print(f"Exported {len(verified_examples)} VERIFIED examples to {output_path}")

    return verified_examples


def main():
    parser = argparse.ArgumentParser(
        description="Export VERIFIED examples from a run to JSON"
    )
    parser.add_argument(
        "--db-path",
        required=True,
        help="Path to SQLite database"
    )
    parser.add_argument(
        "--run-id",
        required=True,
        help="Run identifier to export VERIFIED examples from"
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path to output JSON file"
    )

    args = parser.parse_args()

    # Verify database exists
    if not Path(args.db_path).exists():
        print(f"Error: Database not found at {args.db_path}", file=sys.stderr)
        sys.exit(1)

    # Export examples
    try:
        examples = export_verified_examples(
            args.db_path,
            args.run_id,
            args.output
        )

        # Print summary
        print(f"\nSummary:")
        print(f"  Run ID: {args.run_id}")
        print(f"  Database: {args.db_path}")
        print(f"  VERIFIED count: {len(examples)}")
        print(f"  Output file: {args.output}")

    except Exception as e:
        print(f"Error exporting examples: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
