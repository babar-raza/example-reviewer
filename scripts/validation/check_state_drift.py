#!/usr/bin/env python3
"""
State-Code Drift Detector — TC-15
Verifies that DB state matches filesystem reality:
- Examples marked VERIFIED in the DB should have corresponding
  markdown files that still exist at the recorded file_path.
"""

import json
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB = REPO_ROOT / "data" / "example_reviewer.db"


def check_state_drift(db_path: Path, run_id: str = None) -> dict:
    """Check for drift between DB state and filesystem."""
    if not db_path.exists():
        return {"error": f"Database not found: {db_path}", "issues": []}

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    query = """
        SELECT er.example_id, er.file_path, er.family, ers.status
        FROM example_records er
        JOIN example_run_state ers ON er.example_id = ers.example_id
        WHERE ers.status IN ('VERIFIED', 'MD_UPDATED', 'FINAL_REVIEW_PASSED', 'COMMITTED')
    """
    params = ()
    if run_id:
        query += " AND ers.run_id = ?"
        params = (run_id,)

    rows = conn.execute(query, params).fetchall()
    conn.close()

    issues = []
    checked = 0
    for row in rows:
        checked += 1
        file_path = Path(row["file_path"])
        if not file_path.is_absolute():
            file_path = REPO_ROOT / file_path

        if not file_path.exists():
            issues.append({
                "example_id": row["example_id"],
                "file_path": str(row["file_path"]),
                "family": row["family"],
                "status": row["status"],
                "issue": "markdown_file_missing",
            })

    return {
        "checked": checked,
        "issues_found": len(issues),
        "issues": issues,
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Check state-code drift")
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB)
    parser.add_argument("--run-id", type=str, default=None)
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    result = check_state_drift(args.db_path, args.run_id)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Checked {result['checked']} verified examples")
        if result.get("error"):
            print(f"ERROR: {result['error']}")
            return 2
        if result["issues"]:
            print(f"\nFOUND {result['issues_found']} DRIFT ISSUE(S):\n")
            for issue in result["issues"]:
                print(f"  - {issue['example_id']}: {issue['file_path']} ({issue['issue']})")
            return 1
        print("No state-code drift detected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
