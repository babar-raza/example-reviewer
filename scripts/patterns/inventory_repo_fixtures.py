#!/usr/bin/env python3
"""
Repo Fixture Inventory Script

Scans all cached GitHub repos for test data files, cross-references against
each family's unresolvable list, and reports coverage gaps.

Usage:
    python scripts/inventory_repo_fixtures.py [--json]

Output:
    - Console summary: per-family file counts, resolvable unresolvables, gaps
    - Optional JSON report: detailed file-by-file inventory
"""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

# Allow running from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.config import ConfigurationManager


def scan_repo_data_dir(repo_data_dir: Path) -> dict:
    """Scan a repo data directory and return inventory."""
    files = []
    ext_counts = Counter()
    for f in repo_data_dir.rglob("*"):
        if f.is_file() and not f.name.startswith("."):
            ext = f.suffix.lower()
            ext_counts[ext] += 1
            files.append({
                "name": f.name,
                "ext": ext,
                "size": f.stat().st_size,
                "rel_path": str(f.relative_to(repo_data_dir)),
            })
    return {
        "total_files": len(files),
        "extension_counts": dict(ext_counts.most_common()),
        "files": files,
    }


def load_unresolvable_list(registry_path: Path) -> list:
    """Load unresolvable entries from a fixture registry."""
    if not registry_path.exists():
        return []
    try:
        data = json.loads(registry_path.read_text(encoding="utf-8"))
        unresolv = data.get("unresolvable", [])
        if isinstance(unresolv, list):
            return unresolv
        elif isinstance(unresolv, dict):
            return list(unresolv.keys())
        return []
    except (json.JSONDecodeError, OSError):
        return []


def check_resolvable_from_repo(unresolvable: list, repo_files: list) -> dict:
    """Cross-reference unresolvables against repo files."""
    repo_names = {f["name"].lower() for f in repo_files}
    repo_exts = {f["ext"] for f in repo_files}

    resolvable = []
    still_unresolvable = []
    for entry in unresolvable:
        if "*" in entry or "?" in entry or "{" in entry:
            continue  # Skip globs
        if entry.lower() in repo_names:
            resolvable.append(entry)
        elif Path(entry).suffix.lower() in repo_exts:
            resolvable.append(entry)  # Extension match possible
        else:
            still_unresolvable.append(entry)

    return {
        "resolvable_from_repo": resolvable,
        "still_unresolvable": still_unresolvable,
        "glob_patterns_skipped": [e for e in unresolvable if "*" in e or "?" in e],
    }


def main():
    sys.stdout.reconfigure(encoding="utf-8")

    output_json = "--json" in sys.argv

    config_mgr = ConfigurationManager()
    families_dir = Path("config/families")
    cache_base = Path(".cache/backfill")
    artifacts_base = Path("artifacts/backfill")

    report = {}

    for config_path in sorted(families_dir.glob("*.json")):
        family = config_path.stem
        if family.endswith("_api_catalog") or family in ("smoke", "test"):
            continue

        try:
            family_config = config_mgr.load_family_config(family)
        except Exception:
            continue

        entry = {
            "family": family,
            "has_example_repo": False,
            "repo_url": None,
            "test_data_path": None,
            "cache_exists": False,
            "repo_inventory": None,
            "unresolvable_count": 0,
            "cross_reference": None,
        }

        # Check example repo config
        if family_config.example_repo and family_config.example_repo.url:
            entry["has_example_repo"] = True
            entry["repo_url"] = family_config.example_repo.url
            entry["test_data_path"] = family_config.example_repo.test_data_path

            repo_name = family_config.example_repo.url.rstrip("/").split("/")[-1]
            repo_data_dir = cache_base / family / repo_name / family_config.example_repo.test_data_path

            if repo_data_dir.exists():
                entry["cache_exists"] = True
                entry["repo_inventory"] = scan_repo_data_dir(repo_data_dir)
            else:
                # Try to find any data dir in the cached repo
                repo_root = cache_base / family / repo_name
                if repo_root.exists():
                    entry["cache_exists"] = True
                    entry["repo_inventory"] = {"total_files": 0, "note": f"Configured path '{family_config.example_repo.test_data_path}' not found in repo"}

        # Load unresolvable list
        registry_path = artifacts_base / family / "fixture-registry.json"
        unresolvable = load_unresolvable_list(registry_path)
        entry["unresolvable_count"] = len(unresolvable)

        # Cross-reference
        if entry["repo_inventory"] and entry["repo_inventory"].get("files"):
            entry["cross_reference"] = check_resolvable_from_repo(
                unresolvable, entry["repo_inventory"]["files"]
            )

        report[family] = entry

    # Output
    if output_json:
        # Strip file lists for compact JSON
        for fam, data in report.items():
            if data.get("repo_inventory") and "files" in data["repo_inventory"]:
                del data["repo_inventory"]["files"]
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print("=" * 80)
        print("REPO FIXTURE INVENTORY REPORT")
        print("=" * 80)

        total_repo_files = 0
        total_unresolvable = 0
        total_resolvable = 0

        for family, data in sorted(report.items()):
            repo_files = data["repo_inventory"]["total_files"] if data.get("repo_inventory") else 0
            total_repo_files += repo_files
            total_unresolvable += data["unresolvable_count"]

            status = "OK" if data["cache_exists"] and repo_files > 0 else "NO DATA" if data["cache_exists"] else "NO CACHE"

            line = f"  {family:12s}  repo={repo_files:>4d} files  unresolv={data['unresolvable_count']:>3d}"

            if data.get("cross_reference"):
                xref = data["cross_reference"]
                n_resolvable = len(xref["resolvable_from_repo"])
                total_resolvable += n_resolvable
                line += f"  repo-can-fix={n_resolvable:>3d}"
                if xref["still_unresolvable"]:
                    remaining_exts = Counter(Path(f).suffix.lower() for f in xref["still_unresolvable"])
                    top = ", ".join(f"{ext}({c})" for ext, c in remaining_exts.most_common(3))
                    line += f"  gaps: {top}"

            line += f"  [{status}]"
            print(line)

        print("-" * 80)
        print(f"  TOTAL: {total_repo_files} repo files, {total_unresolvable} unresolvable, {total_resolvable} repo-fixable")
        print("=" * 80)


if __name__ == "__main__":
    main()
