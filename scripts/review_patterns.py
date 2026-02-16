#!/usr/bin/env python3
"""
Review Auto-Learn Patterns — Inspect, validate, and approve/retire patterns.

Queries all auto_approved=FALSE patterns from the catalog database,
groups them by fix_type, and provides automated validation:

- using_directive: validate namespace exists in family catalog -> auto-approve if valid
- regex_replace: test regex against example_before -> auto-approve if output matches example_after
- llm_prompt: list for manual review with prompt + confidence
- template: count only (not executable)

Usage:
    python scripts/review_patterns.py --family zip
    python scripts/review_patterns.py --family words --auto-approve
    python scripts/review_patterns.py --family ocr --retire-invalid
    python scripts/review_patterns.py --all-families
"""

import argparse
import json
import logging
import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.stdout.reconfigure(encoding="utf-8")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent
CATALOG_DB = PROJECT_ROOT / "data" / "api_catalog.db"


def get_pending_patterns(family: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get all patterns with auto_approved=FALSE."""
    conn = sqlite3.connect(str(CATALOG_DB))
    conn.row_factory = sqlite3.Row

    query = """
        SELECT lp.*, pp.times_applied, pp.times_succeeded, pp.success_rate
        FROM learned_patterns lp
        LEFT JOIN pattern_performance pp ON lp.id = pp.pattern_id
        WHERE lp.auto_approved = FALSE
          AND lp.source NOT LIKE 'retired_%'
    """
    params = []
    if family:
        query += " AND lp.family = ?"
        params.append(family)

    query += " ORDER BY lp.family, lp.fix_type, lp.error_signature"
    rows = conn.execute(query, params).fetchall()
    patterns = [dict(r) for r in rows]
    conn.close()
    return patterns


def get_all_families() -> List[str]:
    """Get all unique families with pending patterns."""
    conn = sqlite3.connect(str(CATALOG_DB))
    rows = conn.execute(
        "SELECT DISTINCT family FROM learned_patterns WHERE auto_approved = FALSE AND source NOT LIKE 'retired_%'"
    ).fetchall()
    conn.close()
    return [r[0] for r in rows]


def load_catalog_namespaces(family: str) -> Dict[str, str]:
    """Load type->namespace mapping from family catalog."""
    try:
        sys.path.insert(0, str(PROJECT_ROOT))
        from src.services.api_catalog_service import APICatalogService
        catalog = APICatalogService(family)
        if not catalog.is_loaded:
            return {}
        # Build type->namespace mapping
        mapping = {}
        for ns in catalog.get_all_namespaces():
            try:
                types = catalog.get_types_in_namespace(ns)
                for t in types:
                    mapping[t] = ns
            except Exception:
                pass
        return mapping
    except Exception as e:
        logger.warning(f"Could not load catalog for {family}: {e}")
        return {}


def validate_using_directive(pattern: Dict, catalog_map: Dict[str, str]) -> Dict[str, Any]:
    """Validate a using_directive pattern against the catalog."""
    fix_code = json.loads(pattern["fix_code"]) if pattern.get("fix_code") else {}
    directive = fix_code.get("directive", "")
    trigger_type = fix_code.get("trigger_type", "")

    result = {
        "valid": False,
        "reason": "",
        "directive": directive,
        "trigger_type": trigger_type,
    }

    if not directive:
        result["reason"] = "Missing directive in fix_code"
        return result

    # Extract namespace from directive (e.g., "using Aspose.Words.Drawing;" -> "Aspose.Words.Drawing")
    ns_match = re.match(r"using\s+([\w.]+)\s*;", directive)
    if not ns_match:
        result["reason"] = f"Invalid directive format: {directive}"
        return result

    namespace = ns_match.group(1)

    # Check if namespace exists in catalog (or is a known BCL namespace)
    bcl_namespaces = {"System", "System.IO", "System.Text", "System.Linq",
                      "System.Collections.Generic", "System.Threading.Tasks"}

    if namespace in bcl_namespaces:
        result["valid"] = True
        result["reason"] = f"BCL namespace: {namespace}"
        return result

    # Check if trigger_type is in catalog and maps to this namespace
    if trigger_type and trigger_type in catalog_map:
        expected_ns = catalog_map[trigger_type]
        if expected_ns == namespace:
            result["valid"] = True
            result["reason"] = f"Catalog match: {trigger_type} -> {namespace}"
        else:
            result["reason"] = f"Namespace mismatch: {trigger_type} is in {expected_ns}, not {namespace}"
        return result

    # Check if namespace exists in any catalog entry
    if namespace in set(catalog_map.values()):
        result["valid"] = True
        result["reason"] = f"Valid namespace in catalog: {namespace}"
        return result

    result["reason"] = f"Namespace {namespace} not found in catalog"
    return result


def validate_regex_replace(pattern: Dict) -> Dict[str, Any]:
    """Validate a regex_replace pattern by testing against examples."""
    fix_code = json.loads(pattern["fix_code"]) if pattern.get("fix_code") else {}
    regex_pattern = fix_code.get("pattern", "")
    replacement = fix_code.get("replacement", "")

    result = {
        "valid": False,
        "reason": "",
        "pattern": regex_pattern,
        "replacement": replacement,
    }

    if not regex_pattern:
        result["reason"] = "Missing pattern in fix_code"
        return result

    # Validate regex compiles
    try:
        compiled = re.compile(regex_pattern)
    except re.error as e:
        result["reason"] = f"Invalid regex: {e}"
        return result

    # If we have example_before and example_after, test the regex
    example_before = pattern.get("example_before")
    example_after = pattern.get("example_after")

    if example_before and example_after:
        actual_output = re.sub(regex_pattern, replacement, example_before)
        if actual_output.strip() == example_after.strip():
            result["valid"] = True
            result["reason"] = "Regex produces expected output"
        else:
            result["reason"] = f"Output mismatch: expected '{example_after}', got '{actual_output}'"
        return result

    # No examples to test against, but regex is valid
    result["valid"] = True
    result["reason"] = "Valid regex (no examples to verify against)"
    return result


def review_patterns(
    family: Optional[str] = None,
    auto_approve: bool = False,
    retire_invalid: bool = False,
) -> Dict[str, Any]:
    """
    Review all pending patterns.

    Returns summary dict with review results.
    """
    patterns = get_pending_patterns(family)
    if not patterns:
        print("No pending patterns to review.")
        return {"total": 0}

    # Group by fix_type
    by_type = defaultdict(list)
    for p in patterns:
        by_type[p.get("fix_type", "template")].append(p)

    # Load catalogs for relevant families
    families = set(p["family"] for p in patterns)
    catalogs = {}
    for f in families:
        catalogs[f] = load_catalog_namespaces(f)

    results = {
        "total": len(patterns),
        "by_type": {},
        "auto_approved": [],
        "retired": [],
        "needs_review": [],
    }

    # Initialize service for approval/retirement if needed
    service = None
    if auto_approve or retire_invalid:
        sys.path.insert(0, str(PROJECT_ROOT))
        from src.services.learned_patterns_service import LearnedPatternsService
        # Use a generic service (family doesn't matter for approve/retire)
        service = LearnedPatternsService("_review", db_path=CATALOG_DB)

    print(f"\n{'='*60}")
    print(f"Pattern Review: {len(patterns)} pending patterns")
    if family:
        print(f"Family: {family}")
    print(f"{'='*60}")

    # 1. Review using_directive patterns
    ud_patterns = by_type.get("using_directive", [])
    if ud_patterns:
        print(f"\n--- using_directive ({len(ud_patterns)} patterns) ---")
        approved_ids = []
        invalid_ids = []
        for p in ud_patterns:
            catalog_map = catalogs.get(p["family"], {})
            validation = validate_using_directive(p, catalog_map)
            status = "VALID" if validation["valid"] else "INVALID"
            print(
                f"  [{status}] #{p['id']} ({p['family']}/{p['error_signature']}): "
                f"{validation['directive']} -- {validation['reason']}"
            )
            if validation["valid"]:
                approved_ids.append(p["id"])
                results["auto_approved"].append(p["id"])
            else:
                invalid_ids.append(p["id"])
                results["needs_review"].append(p["id"])

        if auto_approve and service and approved_ids:
            count = service.bulk_approve(approved_ids)
            print(f"  -> Auto-approved {count} valid using_directive patterns")
        if retire_invalid and service and invalid_ids:
            for pid in invalid_ids:
                service.retire_pattern(pid, "invalid_namespace")
                results["retired"].append(pid)
            print(f"  -> Retired {len(invalid_ids)} invalid using_directive patterns")

        results["by_type"]["using_directive"] = {
            "total": len(ud_patterns),
            "valid": len(approved_ids),
            "invalid": len(invalid_ids),
        }

    # 2. Review regex_replace patterns
    rr_patterns = by_type.get("regex_replace", [])
    if rr_patterns:
        print(f"\n--- regex_replace ({len(rr_patterns)} patterns) ---")
        approved_ids = []
        invalid_ids = []
        for p in rr_patterns:
            validation = validate_regex_replace(p)
            status = "VALID" if validation["valid"] else "INVALID"
            print(
                f"  [{status}] #{p['id']} ({p['family']}/{p['error_signature']}): "
                f"s/{validation['pattern']}/{validation['replacement']}/ -- {validation['reason']}"
            )
            if validation["valid"]:
                approved_ids.append(p["id"])
                results["auto_approved"].append(p["id"])
            else:
                invalid_ids.append(p["id"])
                results["needs_review"].append(p["id"])

        if auto_approve and service and approved_ids:
            count = service.bulk_approve(approved_ids)
            print(f"  -> Auto-approved {count} valid regex_replace patterns")
        if retire_invalid and service and invalid_ids:
            for pid in invalid_ids:
                service.retire_pattern(pid, "invalid_regex")
                results["retired"].append(pid)
            print(f"  -> Retired {len(invalid_ids)} invalid regex_replace patterns")

        results["by_type"]["regex_replace"] = {
            "total": len(rr_patterns),
            "valid": len(approved_ids),
            "invalid": len(invalid_ids),
        }

    # 3. Review llm_prompt patterns (manual review needed)
    lp_patterns = by_type.get("llm_prompt", [])
    if lp_patterns:
        print(f"\n--- llm_prompt ({len(lp_patterns)} patterns - MANUAL REVIEW) ---")
        for p in lp_patterns:
            fix_code = json.loads(p["fix_code"]) if p.get("fix_code") else {}
            prompt = fix_code.get("prompt", "N/A")
            perf = f"{p.get('times_applied', 0)} uses, {p.get('success_rate', 0.0):.0%} success"
            print(
                f"  #{p['id']} ({p['family']}/{p['error_signature']}): "
                f"conf={p['confidence']:.2f}, {perf}"
            )
            # Truncate prompt for display
            prompt_display = prompt[:120] + "..." if len(prompt) > 120 else prompt
            print(f"    Prompt: {prompt_display}")
            results["needs_review"].append(p["id"])

        # Auto-approve llm_prompt with high performance
        if auto_approve and service:
            high_perf_ids = [
                p["id"] for p in lp_patterns
                if (p.get("times_applied", 0) >= 3 and (p.get("success_rate") or 0) >= 0.8)
            ]
            if high_perf_ids:
                count = service.bulk_approve(high_perf_ids)
                print(f"  -> Auto-approved {count} high-performance llm_prompt patterns")
                results["auto_approved"].extend(high_perf_ids)

        results["by_type"]["llm_prompt"] = {
            "total": len(lp_patterns),
            "needs_review": len(lp_patterns),
        }

    # 4. Count template patterns
    tpl_patterns = by_type.get("template", [])
    if tpl_patterns:
        print(f"\n--- template ({len(tpl_patterns)} patterns - NOT EXECUTABLE) ---")
        by_sig = defaultdict(int)
        for p in tpl_patterns:
            by_sig[f"{p['family']}/{p['error_signature']}"] += 1
        for sig, count in sorted(by_sig.items()):
            print(f"  {sig}: {count} patterns")

        results["by_type"]["template"] = {"total": len(tpl_patterns)}

    # Summary
    print(f"\n{'='*60}")
    print(f"Review Summary:")
    print(f"  Total pending: {results['total']}")
    print(f"  Auto-approved: {len(results['auto_approved'])}")
    print(f"  Retired: {len(results['retired'])}")
    print(f"  Needs manual review: {len(results['needs_review'])}")
    print(f"{'='*60}")

    if service:
        service.close()

    return results


def main():
    parser = argparse.ArgumentParser(description="Review auto-learn patterns")
    parser.add_argument("--family", help="Filter by family (default: all)")
    parser.add_argument("--all-families", action="store_true", help="Review all families")
    parser.add_argument("--auto-approve", action="store_true",
                        help="Auto-approve validated using_directive and regex_replace patterns")
    parser.add_argument("--retire-invalid", action="store_true",
                        help="Retire patterns that fail validation")
    args = parser.parse_args()

    if not CATALOG_DB.exists():
        logger.error(f"Catalog database not found: {CATALOG_DB}")
        sys.exit(1)

    family = None if args.all_families else args.family
    review_patterns(
        family=family,
        auto_approve=args.auto_approve,
        retire_invalid=args.retire_invalid,
    )


if __name__ == "__main__":
    main()
