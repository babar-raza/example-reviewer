#!/usr/bin/env python3
"""
Validator: Check that aprv_self_assessment.json is not stale.

Maps to RC-RATE-010: Self-assessment must be refreshed periodically
to prevent stale rating claims.

Exit codes:
    0 = Assessment is fresh (within max age)
    1 = Assessment is stale or missing
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ASSESSMENT_FILE = Path("aprv_self_assessment.json")
MAX_AGE_DAYS = 30


def main():
    if not ASSESSMENT_FILE.exists():
        print(f"FAIL: {ASSESSMENT_FILE} not found")
        return 1

    with open(ASSESSMENT_FILE) as f:
        data = json.load(f)

    assessed_at = data.get("assessed_at")
    if not assessed_at:
        print("FAIL: No assessed_at timestamp in self-assessment")
        return 1

    try:
        ts = datetime.fromisoformat(assessed_at)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
    except ValueError:
        print(f"FAIL: Cannot parse assessed_at: {assessed_at}")
        return 1

    now = datetime.now(timezone.utc)
    age = (now - ts).days

    print(f"Self-assessment date: {assessed_at}")
    print(f"Age: {age} days (max allowed: {MAX_AGE_DAYS})")

    if age > MAX_AGE_DAYS:
        print(f"\nFAIL: Self-assessment is {age} days old (stale)")
        return 1

    print("PASS: Self-assessment is fresh")
    return 0


if __name__ == "__main__":
    sys.exit(main())
