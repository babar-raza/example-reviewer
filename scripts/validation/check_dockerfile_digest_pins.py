#!/usr/bin/env python3
"""
Regression guard for TC-EPIC3-02 (digest-pin Docker base images).

Fails if any ``FROM`` line in the Dockerfile references a base image without
an ``@sha256:<digest>`` suffix -- the exact mechanism that prevents the pin
from silently reverting to a floating tag in a future edit. Docker permits
``image:tag@sha256:digest`` syntax, so the human-readable tag stays legible
in code review while the actual pull remains fully reproducible.

Usage:
    python scripts/validation/check_dockerfile_digest_pins.py [Dockerfile]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

_FROM_RE = re.compile(r"^\s*FROM\s+(\S+)", re.IGNORECASE)
_DIGEST_RE = re.compile(r"@sha256:[0-9a-f]{64}$")


def check(dockerfile: Path) -> list[str]:
    """Return a list of violation messages (empty if clean)."""
    violations = []
    for i, line in enumerate(dockerfile.read_text(encoding="utf-8").splitlines(), start=1):
        match = _FROM_RE.match(line)
        if not match:
            continue
        image_ref = match.group(1)
        # `FROM <stage-name>` (a later stage building on an earlier one,
        # e.g. `FROM dotnet-sdk`) has no registry image to pin -- skip it.
        if "/" not in image_ref and ":" not in image_ref and "@" not in image_ref:
            continue
        if not _DIGEST_RE.search(image_ref):
            violations.append(
                f"{dockerfile}:{i}: FROM line lacks an @sha256:<digest> pin: {image_ref!r}"
            )
    return violations


def main(argv: list[str] = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    dockerfile = Path(argv[0]) if argv else Path("Dockerfile")

    if not dockerfile.exists():
        print(f"check_dockerfile_digest_pins: {dockerfile} not found", file=sys.stderr)
        return 1

    violations = check(dockerfile)
    if not violations:
        print(f"check_dockerfile_digest_pins: clean ({dockerfile})")
        return 0

    print(f"check_dockerfile_digest_pins: {len(violations)} violation(s):")
    for v in violations:
        print(f"  {v}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
