"""
SR-06: Patch run_summary.json for run 4e3505ec5f0f6c13.

The run_summary.json was written at pipeline completion time when the
commit_records table was empty (SR-01 bug) and before the phantom COMMITTED
records were corrected (SR-03 bug).

This script patches the existing run_summary.json to add the correct
`committed_to_git` and `commit_count` fields.  It does NOT touch
`examples_successful` — that field counts all verified-pipeline examples
(FINAL_REVIEW_PASSED, COMMITTED, VERIFIED, MD_UPDATED), which is a correct
business metric independent of how many files were staged in git.

Usage
-----
    python scripts/repair/fix_telemetry_metrics_sr06.py --dry-run
    python scripts/repair/fix_telemetry_metrics_sr06.py
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

TARGET_RUN_ID = "4e3505ec5f0f6c13"
TARGET_COMMIT_SHA = "bb061962011a325a7273db7c6e77ba9a78022e5e"


def get_project_root() -> Path:
    return Path(__file__).parent.parent.parent


def count_files_in_commit(commit_sha: str, content_repo: str) -> int:
    result = subprocess.run(
        ["git", "show", "--stat", "--name-only", "--format=", commit_sha],
        cwd=content_repo,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git show failed: {result.stderr}")
    paths = [
        line.strip()
        for line in result.stdout.splitlines()
        if line.strip()
        and not any(kw in line for kw in ("file", "insertion", "deletion"))
    ]
    return len(paths)


def find_content_repo_from_summary(summary: dict) -> str:
    """Try to infer content repo from a nearby DB."""
    # Fallback: common location used by this project
    candidate = Path("D:/onedrive/Documents/GitHub/aspose.net")
    if candidate.exists():
        return str(candidate)
    raise RuntimeError("Cannot determine content repo path; pass --content-repo")


def main() -> int:
    parser = argparse.ArgumentParser(description="SR-06: Patch run_summary.json committed_to_git")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--content-repo", default=None)
    args = parser.parse_args()

    summary_path = get_project_root() / "local-telemetry" / TARGET_RUN_ID / "run_summary.json"
    if not summary_path.exists():
        print(f"run_summary.json not found at {summary_path} — nothing to patch.")
        return 0

    with open(summary_path, encoding="utf-8") as f:
        summary = json.load(f)

    print(f"Patching: {summary_path}")
    print(f"  Current committed_to_git: {summary.get('committed_to_git', '<missing>')}")
    print(f"  Current commit_count:     {summary.get('commit_count', '<missing>')}")

    content_repo = args.content_repo or find_content_repo_from_summary(summary)
    committed_files = count_files_in_commit(TARGET_COMMIT_SHA, content_repo)

    new_committed_to_git = committed_files
    new_commit_count = 1  # exactly one git commit for this run

    print(f"  New committed_to_git:     {new_committed_to_git}  (from git show {TARGET_COMMIT_SHA[:12]})")
    print(f"  New commit_count:         {new_commit_count}")

    if args.dry_run:
        print("\n[DRY RUN] No changes written.")
        return 0

    summary["committed_to_git"] = new_committed_to_git
    summary["commit_count"] = new_commit_count

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)
        f.write("\n")

    print("\nPatched successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
