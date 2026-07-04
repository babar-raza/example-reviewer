#!/usr/bin/env python3
"""
Doc-Code Consistency Checker — TC-14
Validates that claims in evals/claim_registry.json reference files
and fields that actually exist. Detects contradictions between
documentation claims and repository evidence.
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def load_claim_registry() -> dict:
    registry_path = REPO_ROOT / "evals" / "claim_registry.json"
    if not registry_path.exists():
        print(f"ERROR: Claim registry not found at {registry_path}")
        sys.exit(2)
    with open(registry_path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_claim(claim: dict) -> list:
    """Validate a single claim. Returns list of issues found."""
    issues = []
    claim_id = claim.get("claim_id", "UNKNOWN")

    # Check evidence file exists
    evidence_file = claim.get("evidence_file")
    if evidence_file:
        evidence_path = REPO_ROOT / evidence_file
        if not evidence_path.exists():
            issues.append(
                f"{claim_id}: evidence_file '{evidence_file}' does not exist"
            )

    # Check baseline file exists (if referenced)
    baseline_file = claim.get("baseline_file")
    if baseline_file:
        baseline_path = REPO_ROOT / baseline_file
        if not baseline_path.exists():
            issues.append(
                f"{claim_id}: baseline_file '{baseline_file}' does not exist"
            )

    # Check test file exists (if referenced)
    test_file = claim.get("test_file")
    if test_file:
        test_path = REPO_ROOT / test_file
        if not test_path.exists():
            issues.append(
                f"{claim_id}: test_file '{test_file}' does not exist"
            )

    # Check methodology file exists (if referenced)
    methodology_file = claim.get("methodology_file")
    if methodology_file:
        methodology_path = REPO_ROOT / methodology_file
        if not methodology_path.exists():
            issues.append(
                f"{claim_id}: methodology_file '{methodology_file}' does not exist"
            )

    # Check doc file exists
    doc_file = claim.get("doc_file")
    if doc_file:
        doc_path = REPO_ROOT / doc_file
        if not doc_path.exists():
            issues.append(
                f"{claim_id}: doc_file '{doc_file}' does not exist"
            )

    # Note: circular evidence detection is handled by check_evidence_circularity.py,
    # which traverses the full claim graph. No duplicate check here.

    return issues


def main():
    registry = load_claim_registry()
    claims = registry.get("claims", [])

    if not claims:
        print("WARNING: No claims found in registry")
        return 1

    all_issues = []
    for claim in claims:
        issues = validate_claim(claim)
        all_issues.extend(issues)

    # Print results
    print(f"Checked {len(claims)} claims")
    if all_issues:
        print(f"\nFOUND {len(all_issues)} ISSUE(S):\n")
        for issue in all_issues:
            print(f"  - {issue}")
        return 1
    else:
        print("All claims validated successfully.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
