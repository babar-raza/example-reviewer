#!/usr/bin/env python3
"""
Validator: Detect circular evidence chains in claim_registry.json.

Maps to RC-RATE-002: Accuracy claims backed by self-generated reports
are flagged as circular. This validator ensures the team is aware of
unresolved circular evidence and prevents silent regression.

Exit codes:
    0 = No blocking circular evidence found (warnings are OK)
    1 = Critical circular evidence detected without acknowledged grounding_gap
"""
import json
import sys
from pathlib import Path

CLAIM_REGISTRY = Path("evals/claim_registry.json")


def main():
    if not CLAIM_REGISTRY.exists():
        print(f"SKIP: {CLAIM_REGISTRY} not found")
        return 0

    with open(CLAIM_REGISTRY) as f:
        registry = json.load(f)

    claims = registry.get("claims", [])
    circular = [c for c in claims if c.get("status") == "self-reported"]
    partial = [c for c in claims if c.get("status") == "partial"]

    if circular:
        print(f"WARNING: {len(circular)} claim(s) have circular evidence:")
        for c in circular:
            gap = c.get("grounding_gap", "no gap description")
            print(f"  {c['claim_id']}: {c.get('claim_text', '')[:80]}")
            print(f"    Gap: {gap[:120]}")

    if partial:
        print(f"WARNING: {len(partial)} claim(s) have partial evidence:")
        for c in partial:
            gap = c.get("grounding_gap", "no gap description")
            print(f"  {c['claim_id']}: {c.get('claim_text', '')[:80]}")
            print(f"    Gap: {gap[:120]}")

    # Fail only if circular claims lack a grounding_gap explanation
    unacknowledged = [
        c for c in circular if not c.get("grounding_gap")
    ]
    if unacknowledged:
        print(f"\nFAIL: {len(unacknowledged)} circular claim(s) have no grounding_gap explanation")
        return 1

    total_issues = len(circular) + len(partial)
    if total_issues:
        print(f"\nPASS (with {total_issues} acknowledged evidence gap(s))")
    else:
        print("PASS: All claims have grounded evidence")
    return 0


if __name__ == "__main__":
    sys.exit(main())
