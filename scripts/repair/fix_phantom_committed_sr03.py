"""
SR-03: Remediate 133 phantom-COMMITTED records in workspace DB.

Background
----------
Pipeline run 4e3505ec5f0f6c13 (imaging, 2026-03-05) had a bug where
_run_finalization_phase() iterated over `examples` (all 145 FINAL_REVIEW_PASSED)
instead of `committed_examples` (the 12 whose files were actually staged/committed
in git commit bb061962011a325a7273db7c6e77ba9a78022e5e).

This script resets the 133 incorrectly-COMMITTED example_run_state rows back to
FINAL_REVIEW_PASSED and checks whether the production DB was also contaminated via
copy_run_to_production.

Usage
-----
    # Dry run (no writes):
    python scripts/repair/fix_phantom_committed_sr03.py --dry-run

    # Apply fix:
    python scripts/repair/fix_phantom_committed_sr03.py

    # Target a specific DB path explicitly:
    python scripts/repair/fix_phantom_committed_sr03.py --db /path/to/example_reviewer.db
"""

import argparse
import json
import os
import subprocess
import sqlite3
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TARGET_RUN_ID = "4e3505ec5f0f6c13"
TARGET_COMMIT_SHA = "bb061962011a325a7273db7c6e77ba9a78022e5e"
WORKSPACE_DB_SUBPATH = "ExampleReviewer/workspaces/20260305_092348/db/example_reviewer.db"
PRODUCTION_DB_RELPATH = "data/example_reviewer.db"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_workspace_db_path() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if not local_app_data:
        raise RuntimeError("LOCALAPPDATA environment variable not set")
    return Path(local_app_data) / WORKSPACE_DB_SUBPATH


def get_project_root() -> Path:
    return Path(__file__).parent.parent.parent


def get_committed_file_paths_from_git(commit_sha: str, content_repo: str) -> list[str]:
    """Return absolute paths of files changed in the given commit.

    Derives the git root by running git in the content repo directory,
    then resolves each relative path to an absolute path.
    """
    result = subprocess.run(
        ["git", "show", "--stat", "--name-only", "--format=", commit_sha],
        cwd=content_repo,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"git show failed for {commit_sha!r} in {content_repo!r}:\n{result.stderr}"
        )

    # git show --name-only --format= produces blank first line then file paths,
    # possibly followed by a summary line like "5 files changed, ..."
    committed_rel_paths = [
        line.strip()
        for line in result.stdout.splitlines()
        if line.strip() and not line.strip().startswith(" ")
        and "file" not in line and "insertion" not in line and "deletion" not in line
    ]

    # Resolve to absolute paths
    repo_root = Path(subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=content_repo,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip())

    return [str((repo_root / p).resolve()) for p in committed_rel_paths if p]


def find_content_repo(db_conn: sqlite3.Connection, run_id: str) -> str:
    """Infer the content repo path from example file paths stored in DB."""
    db_conn.row_factory = sqlite3.Row
    row = db_conn.execute(
        """
        SELECT er.file_path
        FROM example_run_state ers
        JOIN example_records er ON ers.example_id = er.example_id
        WHERE ers.run_id = ?
        LIMIT 1
        """,
        (run_id,),
    ).fetchone()
    if not row:
        raise RuntimeError(f"No examples found for run_id {run_id!r}")
    # Walk up until we find a .git directory
    p = Path(row["file_path"]).resolve()
    for parent in [p, *p.parents]:
        if (parent / ".git").exists():
            return str(parent)
    raise RuntimeError(f"Could not find git root from path: {p}")


def get_example_ids_for_files(
    db_conn: sqlite3.Connection,
    run_id: str,
    committed_abs_paths: list[str],
) -> set[str]:
    """Return example_ids whose file_path resolves to one of the committed paths."""
    db_conn.row_factory = sqlite3.Row
    rows = db_conn.execute(
        """
        SELECT er.example_id, er.file_path
        FROM example_run_state ers
        JOIN example_records er ON ers.example_id = er.example_id
        WHERE ers.run_id = ? AND ers.status = 'COMMITTED'
        """,
        (run_id,),
    ).fetchall()

    committed_set = {str(Path(p).resolve()) for p in committed_abs_paths}
    matched = set()
    for row in rows:
        if str(Path(row["file_path"]).resolve()) in committed_set:
            matched.add(row["example_id"])
    return matched


def repair_db(
    db_path: Path,
    run_id: str,
    legitimately_committed_ids: set[str],
    dry_run: bool,
) -> dict:
    """Reset phantom-COMMITTED rows to FINAL_REVIEW_PASSED.

    Returns a summary dict with keys: total_committed, phantom_count, reset_count.
    """
    if not db_path.exists():
        return {"skipped": True, "reason": f"DB not found: {db_path}"}

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    all_committed = conn.execute(
        "SELECT example_id FROM example_run_state WHERE run_id = ? AND status = 'COMMITTED'",
        (run_id,),
    ).fetchall()
    all_committed_ids = {r["example_id"] for r in all_committed}

    phantom_ids = all_committed_ids - legitimately_committed_ids
    phantom_count = len(phantom_ids)
    truly_committed = len(all_committed_ids & legitimately_committed_ids)

    print(f"\n  DB: {db_path}")
    print(f"    Total COMMITTED rows for run:   {len(all_committed_ids)}")
    print(f"    Legitimately committed (in git): {truly_committed}")
    print(f"    Phantom (to reset):              {phantom_count}")

    if dry_run:
        print("    [DRY RUN] No changes written.")
        conn.close()
        return {
            "db": str(db_path),
            "total_committed": len(all_committed_ids),
            "phantom_count": phantom_count,
            "reset_count": 0,
            "dry_run": True,
        }

    if phantom_count == 0:
        print("    Nothing to fix — already clean.")
        conn.close()
        return {
            "db": str(db_path),
            "total_committed": len(all_committed_ids),
            "phantom_count": 0,
            "reset_count": 0,
        }

    # Apply reset in a single transaction
    placeholders = ",".join("?" * len(phantom_ids))
    conn.execute(
        f"""
        UPDATE example_run_state
        SET status = 'FINAL_REVIEW_PASSED'
        WHERE run_id = ?
          AND status = 'COMMITTED'
          AND example_id IN ({placeholders})
        """,
        [run_id, *phantom_ids],
    )
    conn.commit()
    print(f"    Reset {phantom_count} phantom rows to FINAL_REVIEW_PASSED.")

    # Verify
    remaining = conn.execute(
        "SELECT COUNT(*) FROM example_run_state WHERE run_id = ? AND status = 'COMMITTED'",
        (run_id,),
    ).fetchone()[0]
    print(f"    Verification: COMMITTED rows remaining = {remaining} (expected {truly_committed})")
    conn.close()

    return {
        "db": str(db_path),
        "total_committed": len(all_committed_ids),
        "phantom_count": phantom_count,
        "reset_count": phantom_count,
        "remaining_committed": remaining,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="SR-03: Fix phantom COMMITTED records")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would change without writing anything",
    )
    parser.add_argument(
        "--db",
        default=None,
        help="Override workspace DB path (default: %%LOCALAPPDATA%%/ExampleReviewer/...)",
    )
    parser.add_argument(
        "--content-repo",
        default=None,
        help="Path to aspose.net content repo (auto-detected from DB if omitted)",
    )
    args = parser.parse_args()

    print("=" * 70)
    print("SR-03: Phantom COMMITTED record remediation")
    print(f"  Run ID:        {TARGET_RUN_ID}")
    print(f"  Git commit:    {TARGET_COMMIT_SHA[:16]}...")
    print(f"  Mode:          {'DRY RUN' if args.dry_run else 'LIVE'}")
    print("=" * 70)

    # 1. Resolve workspace DB
    workspace_db = Path(args.db) if args.db else get_workspace_db_path()
    if not workspace_db.exists():
        print(f"ERROR: Workspace DB not found at {workspace_db}", file=sys.stderr)
        return 1

    # 2. Determine content repo
    conn_tmp = sqlite3.connect(str(workspace_db))
    content_repo = args.content_repo or find_content_repo(conn_tmp, TARGET_RUN_ID)
    conn_tmp.close()
    print(f"\n  Content repo:  {content_repo}")

    # 3. Get truly committed file paths from git
    print(f"\nReading committed files from git commit {TARGET_COMMIT_SHA[:16]}...")
    try:
        committed_paths = get_committed_file_paths_from_git(TARGET_COMMIT_SHA, content_repo)
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    print(f"  Files in git commit: {len(committed_paths)}")
    for p in committed_paths:
        print(f"    {p}")

    # Guard: if git reports != expected count, abort to avoid over-correction
    if len(committed_paths) != 5:
        print(
            f"\nWARNING: Expected 5 files in commit {TARGET_COMMIT_SHA[:12]}, "
            f"got {len(committed_paths)}. Aborting to prevent incorrect reset.",
            file=sys.stderr,
        )
        return 2

    # 4. Resolve example_ids legitimately committed
    conn_tmp = sqlite3.connect(str(workspace_db))
    legitimately_committed_ids = get_example_ids_for_files(conn_tmp, TARGET_RUN_ID, committed_paths)
    conn_tmp.close()
    print(f"\n  Example IDs legitimately committed: {len(legitimately_committed_ids)}")

    # 5. Repair workspace DB
    print("\n--- Workspace DB ---")
    workspace_summary = repair_db(workspace_db, TARGET_RUN_ID, legitimately_committed_ids, args.dry_run)

    # 6. Check production DB
    prod_db = get_project_root() / PRODUCTION_DB_RELPATH
    print("\n--- Production DB ---")
    if prod_db.exists():
        prod_conn = sqlite3.connect(str(prod_db))
        prod_run = prod_conn.execute(
            "SELECT run_id FROM run_records WHERE run_id = ?", (TARGET_RUN_ID,)
        ).fetchone()
        prod_conn.close()
        if prod_run:
            prod_summary = repair_db(prod_db, TARGET_RUN_ID, legitimately_committed_ids, args.dry_run)
        else:
            print(f"  Run {TARGET_RUN_ID} not present in production DB — no action needed.")
            prod_summary = {"skipped": True, "reason": "run_id not in production DB"}
    else:
        print(f"  Production DB not found at {prod_db} — skipping.")
        prod_summary = {"skipped": True, "reason": "file not found"}

    # 7. Final summary
    print("\n" + "=" * 70)
    print("Summary")
    print(json.dumps({"workspace": workspace_summary, "production": prod_summary}, indent=2))
    if args.dry_run:
        print("\n[DRY RUN] Re-run without --dry-run to apply changes.")
    else:
        print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
