#!/usr/bin/env python3
"""
Repository Signal Manifest Generator — TC-19
Generates repo_signals.json declaring reviewer-expected signals.
Consumed by the reviewer application's footprint analysis step.
"""

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def check_signal(name: str) -> bool:
    """Check whether a specific reviewer signal is present in the repo."""
    checks = {
        "hasSourceDir": (REPO_ROOT / "src").is_dir(),
        "hasTestDir": (REPO_ROOT / "tests").is_dir(),
        "hasEntryPoints": (REPO_ROOT / "src" / "cli" / "main.py").is_file(),
        "hasReadme": (REPO_ROOT / "README.md").is_file(),
        "hasChangelog": (REPO_ROOT / "CHANGELOG.md").is_file(),
        "hasDocsDir": (REPO_ROOT / "docs").is_dir(),
        "hasContributing": (REPO_ROOT / "CONTRIBUTING.md").is_file(),
        "hasAgentsMd": (REPO_ROOT / "AGENTS.md").is_file(),
        "hasCiConfig": (
            (REPO_ROOT / ".gitlab-ci.yml").is_file()
            or (REPO_ROOT / ".github" / "workflows").is_dir()
        ),
        "hasDockerFiles": (REPO_ROOT / "Dockerfile").is_file(),
        "hasCodeowners": (REPO_ROOT / "CODEOWNERS").is_file(),
    }
    return checks.get(name, False)


SIGNAL_NAMES = [
    "hasSourceDir",
    "hasTestDir",
    "hasEntryPoints",
    "hasReadme",
    "hasChangelog",
    "hasDocsDir",
    "hasContributing",
    "hasAgentsMd",
    "hasCiConfig",
    "hasDockerFiles",
    "hasCodeowners",
]


def generate_repo_signals() -> dict:
    from datetime import datetime, timezone

    signals = {name: check_signal(name) for name in SIGNAL_NAMES}
    return {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(REPO_ROOT),
        "signals": signals,
    }


def main():
    manifest = generate_repo_signals()
    output_path = REPO_ROOT / "repo_signals.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"Wrote {output_path}")

    # Validate: all signals should be true for a healthy repo
    missing = [k for k, v in manifest["signals"].items() if not v]
    if missing:
        print(f"WARNING: Missing signals: {', '.join(missing)}")
        return 1
    print("All reviewer signals present.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
