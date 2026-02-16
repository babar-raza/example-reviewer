#!/usr/bin/env python3
"""Collect failure artifacts for Gate B verification."""
import json
import os
import shutil
from pathlib import Path

def collect_artifacts():
    """Collect all referenced artifacts from failures JSON."""

    # Read failures JSON
    failures_json = Path("reports/phase2_gateb_verify/run2_failures.json")
    with open(failures_json) as f:
        data = json.load(f)

    # Get database path to find workspace
    db_path = data.get("database_path", "")
    workspace_base = Path(db_path).parent.parent / "workspace"

    print(f"Database path: {db_path}")
    print(f"Workspace base: {workspace_base}")

    # Create output directory
    output_dir = Path("reports/phase2_gateb_verify/failure_artifacts")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Track what we collect
    collected = []
    missing = []

    # Process all failure statuses
    for status, examples in data["failures_by_status"].items():
        if status == "VERIFIED":
            continue

        print(f"\n=== Processing {status} ({len(examples)} examples) ===")

        for example in examples:
            example_id = example["example_id"]
            print(f"\nExample: {example_id}")

            # Create example subdirectory
            example_dir = output_dir / status / example_id
            example_dir.mkdir(parents=True, exist_ok=True)

            # Collect compile artifacts
            if example.get("last_compile_attempt"):
                compile_attempt = example["last_compile_attempt"]

                # Input code
                if compile_attempt.get("input_code_ref"):
                    src = workspace_base / compile_attempt["input_code_ref"]
                    dst = example_dir / "input.cs"
                    if src.exists():
                        shutil.copy2(src, dst)
                        collected.append(str(src))
                        print(f"  [OK] Copied input code: {src.name}")
                    else:
                        missing.append(str(src))
                        print(f"  [MISS] Missing input code: {src}")

                # Compiler log
                if compile_attempt.get("compiler_log_ref"):
                    src = workspace_base / compile_attempt["compiler_log_ref"]
                    dst = example_dir / "compile_log.txt"
                    if src.exists():
                        shutil.copy2(src, dst)
                        collected.append(str(src))
                        print(f"  [OK] Copied compiler log: {src.name}")
                    else:
                        missing.append(str(src))
                        print(f"  [MISS] Missing compiler log: {src}")

                # Output code (if exists)
                if compile_attempt.get("output_code_ref"):
                    src = workspace_base / compile_attempt["output_code_ref"]
                    dst = example_dir / "output.cs"
                    if src.exists():
                        shutil.copy2(src, dst)
                        collected.append(str(src))
                        print(f"  [OK] Copied output code: {src.name}")

            # Collect runtime artifacts
            if example.get("last_runtime_attempt"):
                runtime_attempt = example["last_runtime_attempt"]

                # Runtime log
                if runtime_attempt.get("runtime_log_ref"):
                    src = workspace_base / runtime_attempt["runtime_log_ref"]
                    dst = example_dir / "runtime_log.txt"
                    if src.exists():
                        shutil.copy2(src, dst)
                        collected.append(str(src))
                        print(f"  [OK] Copied runtime log: {src.name}")
                    else:
                        missing.append(str(src))
                        print(f"  [MISS] Missing runtime log: {src}")

    # Summary
    print(f"\n{'='*60}")
    print(f"Collection Summary:")
    print(f"  Collected: {len(collected)} files")
    print(f"  Missing: {len(missing)} files")

    if missing:
        print(f"\nMissing files:")
        for f in missing[:10]:  # Show first 10
            print(f"  - {f}")
        if len(missing) > 10:
            print(f"  ... and {len(missing) - 10} more")

    return output_dir

if __name__ == "__main__":
    output_dir = collect_artifacts()
    print(f"\nArtifacts collected in: {output_dir}")
