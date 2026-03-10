"""
Cleanup runtime-generated files for Docker deployments.

Removes ephemeral build/execution artifacts and applies TTL-based retention to
telemetry run directories, run fingerprints, and log files.

Usage
-----
    python scripts/maintenance/cleanup_runtime.py --dry-run
    python scripts/maintenance/cleanup_runtime.py --keep-days 7 --keep-runs 50
    python scripts/maintenance/cleanup_runtime.py --include-cache --keep-runs 20 --force
"""

import argparse
import json
import logging
import os
import re
import shutil
import sqlite3
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

# Only dirs matching this pattern are treated as run-id dirs (16 hex chars).
# Skips legacy scaffolding dirs like '00_context', '01_env_fix', etc.
RUN_ID_PATTERN = re.compile(r"^[0-9a-f]{16}$")

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def get_project_root() -> Path:
    return Path(__file__).parent.parent.parent


def _human_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def _resolve(base: Path, rel: str) -> Path:
    p = Path(rel)
    if p.is_absolute():
        return p
    return (base / p).resolve()


# ---------------------------------------------------------------------------
# Config / path loading
# ---------------------------------------------------------------------------

def load_paths(project_root: Path, config_override: str | None = None) -> dict:
    """Load canonical runtime paths.

    Priority: global.json -> environment variables -> hardcoded defaults.
    """
    config_path = Path(config_override) if config_override else project_root / "config" / "global.json"
    artifact_store = "./artifacts"
    telemetry_path = "./local-telemetry"
    db_path = "./data/example_reviewer.db"

    if config_path.exists():
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
            artifact_store = data.get("artifact_store_path", artifact_store)
            telemetry_path = data.get("telemetry", {}).get("local_telemetry_path", telemetry_path)
            db_path = data.get("database", {}).get("path", db_path)
        except Exception as exc:
            logger.warning("Failed to read %s: %s — using defaults", config_path, exc)

    # Env overrides (Docker-friendly)
    artifact_store = os.environ.get("ARTIFACT_STORE_PATH", artifact_store)
    telemetry_path = os.environ.get("LOCAL_TELEMETRY_PATH", telemetry_path)
    workspace = os.environ.get("WORKSPACE_DIR", "./workspace")
    runs_dir = os.environ.get("RUNS_DIR", "./runs")
    db_path = os.environ.get("DB_PATH", db_path)

    return {
        "artifacts":       _resolve(project_root, artifact_store),
        "workspace":       _resolve(project_root, workspace),
        "local_telemetry": _resolve(project_root, telemetry_path),
        "runs":            _resolve(project_root, runs_dir),
        "logs":            _resolve(project_root, "./logs"),
        "db":              _resolve(project_root, db_path),
    }


# ---------------------------------------------------------------------------
# Active-run safety guard
# ---------------------------------------------------------------------------

def detect_active_runs(db_path: Path) -> list[str]:
    """Return run_ids currently in 'running' state.

    Returns empty list if DB does not exist (fresh container).
    Raises RuntimeError if the DB is locked (pipeline actively writing).
    """
    if not db_path.exists():
        return []
    try:
        conn = sqlite3.connect(str(db_path), timeout=0.5)
        try:
            rows = conn.execute(
                "SELECT run_id FROM run_records WHERE status = 'running'"
            ).fetchall()
            return [r[0] for r in rows]
        finally:
            conn.close()
    except sqlite3.OperationalError as exc:
        raise RuntimeError(f"Cannot read DB (locked or corrupt): {exc}") from exc


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

@dataclass
class CleanupStats:
    label: str
    items_deleted: int = 0
    bytes_freed: int = 0
    errors: list[str] = field(default_factory=list)

    def merge(self, other: "CleanupStats") -> None:
        self.items_deleted += other.items_deleted
        self.bytes_freed += other.bytes_freed
        self.errors.extend(other.errors)


# ---------------------------------------------------------------------------
# Size helpers
# ---------------------------------------------------------------------------

def _dir_size(path: Path) -> int:
    total = 0
    try:
        with os.scandir(path) as it:
            for entry in it:
                if entry.is_file(follow_symlinks=False):
                    total += entry.stat().st_size
                elif entry.is_dir(follow_symlinks=False):
                    total += _dir_size(Path(entry.path))
    except PermissionError:
        pass
    return total


def _item_size(path: Path) -> int:
    if path.is_dir():
        return _dir_size(path)
    try:
        return path.stat().st_size
    except OSError:
        return 0


# ---------------------------------------------------------------------------
# Core deletion helpers
# ---------------------------------------------------------------------------

def _delete_item(path: Path, dry_run: bool) -> tuple[int, str | None]:
    """Delete a file or directory. Returns (bytes_freed, error_or_None)."""
    size = _item_size(path)
    if dry_run:
        logger.info("[DRY RUN] Would delete: %s (%s)", path, _human_bytes(size))
        return size, None
    try:
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
        logger.debug("Deleted: %s (%s)", path, _human_bytes(size))
        return size, None
    except Exception as exc:
        msg = f"Failed to delete {path}: {exc}"
        logger.warning(msg)
        return 0, msg


def delete_dir_contents(directory: Path, label: str, dry_run: bool) -> CleanupStats:
    """Delete all children of *directory*, preserving the directory itself."""
    stats = CleanupStats(label=label)
    if not directory.exists():
        return stats
    for child in sorted(directory.iterdir()):
        freed, err = _delete_item(child, dry_run)
        stats.items_deleted += 1
        stats.bytes_freed += freed
        if err:
            stats.errors.append(err)
    return stats


# ---------------------------------------------------------------------------
# TTL / retention helpers
# ---------------------------------------------------------------------------

def _list_run_id_dirs(base: Path) -> list[tuple[Path, float]]:
    """Return (path, mtime) for dirs matching RUN_ID_PATTERN, sorted oldest-first."""
    if not base.exists():
        return []
    result = []
    for child in base.iterdir():
        if child.is_dir() and RUN_ID_PATTERN.match(child.name):
            try:
                mtime = child.stat().st_mtime
            except OSError:
                mtime = 0.0
            result.append((child, mtime))
    result.sort(key=lambda x: x[1])
    return result


def apply_age_and_count_ttl(
    base: Path,
    label: str,
    keep_days: int,
    keep_runs: int,
    dry_run: bool,
) -> CleanupStats:
    """Delete run dirs older than keep_days AND enforce max keep_runs most recent."""
    stats = CleanupStats(label=label)
    candidates = _list_run_id_dirs(base)  # oldest first
    cutoff = time.time() - (keep_days * 86400)

    to_delete: list[Path] = []

    # Age pass
    remaining: list[Path] = []
    for path, mtime in candidates:
        if mtime < cutoff:
            to_delete.append(path)
        else:
            remaining.append(path)

    # Count pass on whatever's left
    if len(remaining) > keep_runs:
        excess = len(remaining) - keep_runs
        to_delete.extend(remaining[:excess])

    kept = len(candidates) - len(to_delete)
    logger.info(
        "%s: %d total run dirs — deleting %d, keeping %d",
        label, len(candidates), len(to_delete), kept,
    )

    for path in to_delete:
        freed, err = _delete_item(path, dry_run)
        stats.items_deleted += 1
        stats.bytes_freed += freed
        if err:
            stats.errors.append(err)

    return stats


def apply_count_ttl(base: Path, label: str, keep_runs: int, dry_run: bool) -> CleanupStats:
    """Keep the keep_runs most-recent run dirs, delete the rest."""
    stats = CleanupStats(label=label)
    candidates = _list_run_id_dirs(base)  # oldest first

    if len(candidates) <= keep_runs:
        logger.info("%s: %d dirs, within limit (%d) — nothing to delete", label, len(candidates), keep_runs)
        return stats

    to_delete = [p for p, _ in candidates[: len(candidates) - keep_runs]]
    logger.info(
        "%s: %d total run dirs — deleting %d, keeping %d",
        label, len(candidates), len(to_delete), keep_runs,
    )

    for path in to_delete:
        freed, err = _delete_item(path, dry_run)
        stats.items_deleted += 1
        stats.bytes_freed += freed
        if err:
            stats.errors.append(err)

    return stats


def apply_log_age_ttl(logs_dir: Path, label: str, keep_days: int, dry_run: bool) -> CleanupStats:
    """Delete .log files older than keep_days."""
    stats = CleanupStats(label=label)
    if not logs_dir.exists():
        return stats
    cutoff = time.time() - (keep_days * 86400)
    for log_file in sorted(logs_dir.glob("*.log")):
        try:
            mtime = log_file.stat().st_mtime
        except OSError:
            continue
        if mtime < cutoff:
            freed, err = _delete_item(log_file, dry_run)
            stats.items_deleted += 1
            stats.bytes_freed += freed
            if err:
                stats.errors.append(err)
    return stats


def apply_artifacts_root_ttl(artifacts_dir: Path, label: str, keep_days: int, dry_run: bool) -> CleanupStats:
    """Delete loose .log and *_report.json files directly in artifacts/ root older than keep_days."""
    stats = CleanupStats(label=label)
    if not artifacts_dir.exists():
        return stats
    cutoff = time.time() - (keep_days * 86400)
    for f in sorted(artifacts_dir.iterdir()):
        if not f.is_file():
            continue
        if not (f.suffix == ".log" or f.name.endswith("_report.json")):
            continue
        try:
            mtime = f.stat().st_mtime
        except OSError:
            continue
        if mtime < cutoff:
            freed, err = _delete_item(f, dry_run)
            stats.items_deleted += 1
            stats.bytes_freed += freed
            if err:
                stats.errors.append(err)
    return stats


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Clean up runtime-generated files. Safe to run while no pipeline is active.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/maintenance/cleanup_runtime.py --dry-run
  python scripts/maintenance/cleanup_runtime.py --keep-days 7 --keep-runs 50
  python scripts/maintenance/cleanup_runtime.py --include-cache --keep-runs 20
  python scripts/maintenance/cleanup_runtime.py --force  # skip active-run check
""",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without making any changes",
    )
    parser.add_argument(
        "--keep-days",
        type=int,
        default=7,
        metavar="N",
        help="Retain log files and telemetry dirs newer than N days (default: 7)",
    )
    parser.add_argument(
        "--keep-runs",
        type=int,
        default=50,
        metavar="N",
        help="Maximum number of run dirs to retain in local-telemetry/ and runs/ (default: 50)",
    )
    parser.add_argument(
        "--include-cache",
        action="store_true",
        help="Also clean artifacts/cache/ (slow to regenerate — off by default)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip active-run safety check",
    )
    parser.add_argument(
        "--config",
        default=None,
        metavar="PATH",
        help="Explicit path to global.json (overrides auto-discovery)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable DEBUG logging",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    args = parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
        stream=sys.stdout,
    )

    root = get_project_root()
    paths = load_paths(root, args.config)

    # Safety guard
    if not args.force:
        try:
            active = detect_active_runs(paths["db"])
        except RuntimeError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            print("Use --force to skip this check.", file=sys.stderr)
            return 2
        if active:
            print(
                f"ERROR: {len(active)} pipeline run(s) currently active: {active}",
                file=sys.stderr,
            )
            print("Wait for runs to complete or use --force to override.", file=sys.stderr)
            return 2

    mode_label = "DRY RUN (no changes made)" if args.dry_run else "LIVE"
    start = time.monotonic()
    all_stats: list[CleanupStats] = []

    # ---- Ephemeral dirs (wiped entirely) ----
    ephemeral = [
        ("workspace/",               paths["workspace"]),
        ("artifacts/compile/",       paths["artifacts"] / "compile"),
        ("artifacts/runtime/",       paths["artifacts"] / "runtime"),
        ("artifacts/diffs/",         paths["artifacts"] / "diffs"),
        ("artifacts/investigation/", paths["artifacts"] / "investigation"),
        ("artifacts/runs/",          paths["artifacts"] / "runs"),
    ]
    for label, directory in ephemeral:
        s = delete_dir_contents(directory, label, args.dry_run)
        all_stats.append(s)

    # ---- TTL dirs ----
    s = apply_age_and_count_ttl(
        paths["local_telemetry"],
        "local-telemetry/",
        args.keep_days,
        args.keep_runs,
        args.dry_run,
    )
    all_stats.append(s)

    s = apply_count_ttl(paths["runs"], "runs/", args.keep_runs, args.dry_run)
    all_stats.append(s)

    s = apply_log_age_ttl(paths["logs"], "logs/", args.keep_days, args.dry_run)
    all_stats.append(s)

    s = apply_artifacts_root_ttl(paths["artifacts"], "artifacts/ (root logs)", args.keep_days, args.dry_run)
    all_stats.append(s)

    # ---- Optional cache ----
    if args.include_cache:
        s = delete_dir_contents(paths["artifacts"] / "cache", "artifacts/cache/", args.dry_run)
        all_stats.append(s)

    elapsed = time.monotonic() - start

    # ---- Summary report ----
    total_items = sum(s.items_deleted for s in all_stats)
    total_bytes = sum(s.bytes_freed for s in all_stats)
    total_errors = sum(len(s.errors) for s in all_stats)

    print()
    print("=== Cleanup Report ===")
    print(f"Mode:          {mode_label}")
    print(f"Elapsed:       {elapsed:.1f}s")
    print(f"Items deleted: {total_items}")
    print(f"Bytes freed:   {_human_bytes(total_bytes)}")
    print(f"Errors:        {total_errors}")
    print()
    print("Breakdown:")
    for s in all_stats:
        if s.items_deleted > 0 or s.errors:
            print(f"  {s.label:<30} {s.items_deleted:>5} items,  {_human_bytes(s.bytes_freed):>10}")
    if total_items == 0:
        print("  (nothing to clean up)")

    if total_errors:
        print()
        print("Errors:")
        for s in all_stats:
            for err in s.errors:
                print(f"  {err}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
