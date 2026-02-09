#!/usr/bin/env python3
"""
Migrate API Catalog Database — Create schema for learned patterns.

Creates tables for API types, learned patterns, and performance tracking.
Idempotent: safe to re-run without data loss.

Usage:
    python scripts/migrate_api_catalog.py
    python scripts/migrate_api_catalog.py --populate --family zip

HEAL-04: Database Schema for Learned Patterns
"""

import argparse
import json
import logging
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "data" / "api_catalog.db"

SCHEMA_SQL = """
-- API types from catalog (populated from JSON)
CREATE TABLE IF NOT EXISTS api_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    family TEXT NOT NULL,
    type_name TEXT NOT NULL,
    namespace TEXT NOT NULL,
    using_directive TEXT NOT NULL,
    is_ambiguous BOOLEAN DEFAULT FALSE,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(family, type_name, namespace)
);
CREATE INDEX IF NOT EXISTS idx_api_types_family ON api_types(family);
CREATE INDEX IF NOT EXISTS idx_api_types_name ON api_types(type_name);

-- Learned patterns from auto-learn (Phase C)
CREATE TABLE IF NOT EXISTS learned_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    family TEXT NOT NULL,
    pattern_type TEXT NOT NULL,  -- 'using_directive', 'type_replacement', 'code_transform'
    error_signature TEXT,        -- regex or error code that triggers this pattern
    match_condition TEXT,        -- condition to check before applying
    fix_template TEXT NOT NULL,  -- the fix to apply
    confidence REAL DEFAULT 0.5,
    auto_approved BOOLEAN DEFAULT FALSE,
    source TEXT,                 -- 'bootstrap', 'auto_learn', 'manual'
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_learned_patterns_family ON learned_patterns(family);
CREATE INDEX IF NOT EXISTS idx_learned_patterns_type ON learned_patterns(pattern_type);

-- Learning history (audit trail)
CREATE TABLE IF NOT EXISTS learning_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    family TEXT NOT NULL,
    run_id TEXT NOT NULL,
    failure_cluster_id TEXT,
    pattern_type TEXT,
    fix_applied TEXT,
    auto_approved BOOLEAN,
    confidence REAL,
    validation_status TEXT,  -- 'pending', 'validated', 'rejected'
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_learning_history_run ON learning_history(run_id);
CREATE INDEX IF NOT EXISTS idx_learning_history_family ON learning_history(family);

-- Pattern performance tracking
CREATE TABLE IF NOT EXISTS pattern_performance (
    pattern_id INTEGER PRIMARY KEY,
    family TEXT NOT NULL,
    times_applied INTEGER DEFAULT 0,
    times_succeeded INTEGER DEFAULT 0,
    success_rate REAL DEFAULT 0.0,
    last_used TEXT,
    retire_if_below_threshold REAL DEFAULT 0.5,
    FOREIGN KEY (pattern_id) REFERENCES learned_patterns(id)
);
CREATE INDEX IF NOT EXISTS idx_pattern_perf_family ON pattern_performance(family);
"""

# Schema V2 additions (2026-02-06) - Executable fix logic for learned patterns
SCHEMA_V2_COLUMNS = [
    # (table, column, type, default)
    ("learned_patterns", "fix_type", "TEXT", "'template'"),  # 'regex_replace' | 'using_directive' | 'code_transform' | 'llm_prompt'
    ("learned_patterns", "fix_code", "TEXT", "NULL"),  # JSON with executable fix logic
    ("learned_patterns", "priority", "INTEGER", "50"),  # Execution order (lower = first)
    ("learned_patterns", "requires_llm", "BOOLEAN", "FALSE"),  # If true, pattern needs LLM to apply
    ("learned_patterns", "example_before", "TEXT", "NULL"),  # Few-shot example: code before fix
    ("learned_patterns", "example_after", "TEXT", "NULL"),  # Few-shot example: code after fix
]


def upgrade_schema_v2(db_path: Path) -> int:
    """Add V2 columns for executable fix logic (idempotent)."""
    conn = sqlite3.connect(str(db_path))
    added = 0

    for table, column, col_type, default in SCHEMA_V2_COLUMNS:
        try:
            # Check if column exists
            cursor = conn.execute(f"PRAGMA table_info({table})")
            existing_columns = [row[1] for row in cursor.fetchall()]

            if column not in existing_columns:
                default_clause = f"DEFAULT {default}" if default != "NULL" else ""
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type} {default_clause}")
                logger.info(f"Added column {table}.{column}")
                added += 1
            else:
                logger.debug(f"Column {table}.{column} already exists")
        except sqlite3.Error as e:
            logger.warning(f"Could not add {table}.{column}: {e}")

    conn.commit()
    conn.close()
    return added


def create_schema(db_path: Path) -> None:
    """Create all tables and apply migrations (idempotent)."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    conn.close()
    logger.info(f"Schema created/verified at {db_path}")

    # Apply V2 schema upgrades (executable fix logic)
    added = upgrade_schema_v2(db_path)
    if added > 0:
        logger.info(f"Schema V2: Added {added} new columns for executable fix logic")


def populate_from_catalog(db_path: Path, family: str) -> int:
    """Populate api_types table from JSON catalog. Returns count of rows inserted."""
    catalog_path = PROJECT_ROOT / "config" / "families" / f"{family}_api_catalog.json"
    if not catalog_path.exists():
        logger.error(f"Catalog not found: {catalog_path}")
        return 0

    data = json.loads(catalog_path.read_text(encoding="utf-8"))
    types = data.get("types", {})
    using_map = data.get("using_directive_map", {})
    ambiguous = data.get("namespace_ambiguous_types", {})

    conn = sqlite3.connect(str(db_path))
    inserted = 0

    for type_name, namespace in types.items():
        directive = using_map.get(type_name, f"using {namespace};")
        is_ambiguous = type_name in ambiguous
        try:
            conn.execute(
                "INSERT OR IGNORE INTO api_types (family, type_name, namespace, using_directive, is_ambiguous) "
                "VALUES (?, ?, ?, ?, ?)",
                (family, type_name, namespace, directive, is_ambiguous),
            )
            inserted += 1
        except sqlite3.IntegrityError:
            pass

    conn.commit()
    total = conn.execute("SELECT COUNT(*) FROM api_types WHERE family = ?", (family,)).fetchone()[0]
    conn.close()
    logger.info(f"Populated {inserted} types for '{family}' (total in DB: {total})")
    return inserted


def main():
    parser = argparse.ArgumentParser(description="Migrate API catalog database")
    parser.add_argument("--db-path", default=str(DB_PATH), help="Database path")
    parser.add_argument("--populate", action="store_true", help="Populate from catalog JSON")
    parser.add_argument("--family", help="Family to populate (required with --populate)")
    args = parser.parse_args()

    db_path = Path(args.db_path)

    # Always create/verify schema
    create_schema(db_path)

    if args.populate:
        if not args.family:
            parser.error("--family required with --populate")
        populate_from_catalog(db_path, args.family)

    # Print summary
    conn = sqlite3.connect(str(db_path))
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    print(f"\nDatabase: {db_path}")
    print(f"Tables: {', '.join(t[0] for t in tables)}")
    for table_name in [t[0] for t in tables]:
        count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        print(f"  {table_name}: {count} rows")
    conn.close()


if __name__ == "__main__":
    main()
