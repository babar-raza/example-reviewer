#!/usr/bin/env python3
"""
Detect Manual Fixes — Extract patterns from manually-fixed examples.

Compares original_code vs compilable_code/verified_code in the database
to discover fix patterns that could be automated.

Usage:
    python scripts/detect_manual_fixes.py --family zip
    python scripts/detect_manual_fixes.py --family zip --min-occurrences 2

HEAL-01: Phase 0 Bootstrap Script (Task 2)
"""

import argparse
import json
import logging
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.stdout.reconfigure(encoding="utf-8")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "data" / "example_reviewer.db"


def get_fixed_examples(family: str) -> List[Tuple[str, str, str]]:
    """Get examples where code was modified by fixes."""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute(
        """SELECT er.example_id, er.original_code, ers.compilable_code
           FROM example_records er
           JOIN example_run_state ers ON er.example_id = ers.example_id
           WHERE er.family = ?
             AND ers.compilable_code IS NOT NULL
             AND ers.compilable_code != ''
             AND er.original_code IS NOT NULL
             AND er.original_code != ers.compilable_code
           ORDER BY er.example_id""",
        (family,),
    )
    rows = c.fetchall()
    conn.close()
    return rows


def diff_using_directives(original: str, fixed: str) -> List[str]:
    """Find using directives added in the fix."""
    orig_usings = set(re.findall(r"^using\s+([\w.]+)\s*;", original, re.MULTILINE))
    fixed_usings = set(re.findall(r"^using\s+([\w.]+)\s*;", fixed, re.MULTILINE))
    return sorted(fixed_usings - orig_usings)


def detect_variable_declarations(original: str, fixed: str) -> List[str]:
    """Find variable declarations added in the fix."""
    orig_vars = set(re.findall(r"\bvar\s+(\w+)\s*=", original))
    fixed_vars = set(re.findall(r"\bvar\s+(\w+)\s*=", fixed))
    return sorted(fixed_vars - orig_vars)


def detect_type_replacements(original: str, fixed: str) -> List[Tuple[str, str]]:
    """Find type name replacements (e.g., wrong API -> correct API)."""
    replacements = []
    orig_types = set(re.findall(r"\bnew\s+(\w+)\s*\(", original))
    fixed_types = set(re.findall(r"\bnew\s+(\w+)\s*\(", fixed))
    removed = orig_types - fixed_types
    added = fixed_types - orig_types
    if len(removed) == 1 and len(added) == 1:
        replacements.append((removed.pop(), added.pop()))
    return replacements


def analyze_fixes(family: str, min_occurrences: int = 1) -> Dict:
    """Analyze all fixed examples and extract patterns."""
    examples = get_fixed_examples(family)
    logger.info(f"Found {len(examples)} examples with fixes for family '{family}'")

    using_additions = Counter()
    variable_additions = Counter()
    type_replacements = Counter()

    for example_id, original, fixed in examples:
        usings = diff_using_directives(original, fixed)
        for u in usings:
            using_additions[u] += 1

        vars_added = detect_variable_declarations(original, fixed)
        for v in vars_added:
            variable_additions[v] += 1

        replacements = detect_type_replacements(original, fixed)
        for old, new in replacements:
            type_replacements[f"{old} -> {new}"] += 1

    patterns = {
        "family": family,
        "total_fixed_examples": len(examples),
        "using_directive_patterns": [
            {"namespace": ns, "count": count}
            for ns, count in using_additions.most_common()
            if count >= min_occurrences
        ],
        "variable_injection_patterns": [
            {"variable": var, "count": count}
            for var, count in variable_additions.most_common()
            if count >= min_occurrences
        ],
        "type_replacement_patterns": [
            {"replacement": rep, "count": count}
            for rep, count in type_replacements.most_common()
            if count >= min_occurrences
        ],
    }
    return patterns


def main():
    parser = argparse.ArgumentParser(description="Detect manual fix patterns")
    parser.add_argument("--family", required=True, help="Product family")
    parser.add_argument("--min-occurrences", type=int, default=1, help="Min pattern occurrences")
    parser.add_argument("--output", help="Output JSON path")
    args = parser.parse_args()

    if not DB_PATH.exists():
        logger.error(f"Database not found: {DB_PATH}")
        sys.exit(1)

    patterns = analyze_fixes(args.family, args.min_occurrences)

    if args.output:
        Path(args.output).write_text(json.dumps(patterns, indent=2), encoding="utf-8")
        logger.info(f"Wrote patterns to {args.output}")
    else:
        print(json.dumps(patterns, indent=2))

    total = (
        len(patterns["using_directive_patterns"])
        + len(patterns["variable_injection_patterns"])
        + len(patterns["type_replacement_patterns"])
    )
    logger.info(f"Detected {total} patterns from {patterns['total_fixed_examples']} fixed examples")


if __name__ == "__main__":
    main()
