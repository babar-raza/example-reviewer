#!/usr/bin/env python3
"""Create complete Phase-2 Gate B release package with all phases."""

import zipfile
from pathlib import Path

def create_complete_package():
    """Create comprehensive release package for all 5 phases."""

    # Define base directory
    base_dir = Path(__file__).parent
    release_dir = base_dir / "release"
    release_dir.mkdir(exist_ok=True)

    # Define output file
    output_file = release_dir / "phase2_gateb_complete_implementation.zip"

    # Define files to include
    files_to_include = [
        # Phase 1: Classifier and Persistence
        "src/core/app_context.py",
        "src/pipeline/app_context_classifier.py",
        "tests/test_app_context_classifier.py",
        "PROMPT1_IMPLEMENTATION_SUMMARY.md",

        # Phase 2: Same-Context Substitution
        "tests/test_substitution_context_filtering.py",
        "PROMPT2_IMPLEMENTATION_SUMMARY.md",

        # Phase 3: Context Drift Validator
        "src/pipeline/context_drift_validator.py",
        "tests/test_context_drift_validator.py",
        "PROMPT3_IMPLEMENTATION_SUMMARY.md",

        # Phase 4: Context-Specific Build Harness
        "src/services/context_harness_service.py",
        "tests/test_context_harness_service.py",
        "PROMPT4_IMPLEMENTATION_SUMMARY.md",

        # Phase 5: Validation
        "config/global_strict_context.json",
        "tools/validate_strict_context_mode.py",
        "PROMPT5_IMPLEMENTATION_SUMMARY.md",

        # Complete Summary
        "PHASE2_GATEB_COMPLETE_IMPLEMENTATION.md",
    ]

    print(f"Creating complete release package: {output_file}")
    print("=" * 80)

    with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file_path in files_to_include:
            full_path = base_dir / file_path
            if full_path.exists():
                zf.write(full_path, file_path)
                size = full_path.stat().st_size
                print(f"  [+] Added: {file_path:<60} ({size:>8,} bytes)")
            else:
                print(f"  [-] Missing: {file_path}")

    print("=" * 80)
    print(f"\n[SUCCESS] Complete package created: {output_file}")
    print(f"   Size: {output_file.stat().st_size:,} bytes")

    # Print summary
    print("\n" + "=" * 80)
    print("PACKAGE CONTENTS SUMMARY")
    print("=" * 80)
    print("\nPhase 1: app_context Classifier + Persistence")
    print("  - src/core/app_context.py")
    print("  - src/pipeline/app_context_classifier.py")
    print("  - tests/test_app_context_classifier.py")
    print("  - PROMPT1_IMPLEMENTATION_SUMMARY.md")

    print("\nPhase 2: Same-Context-Only Substitution")
    print("  - tests/test_substitution_context_filtering.py")
    print("  - PROMPT2_IMPLEMENTATION_SUMMARY.md")

    print("\nPhase 3: Context Drift Validator")
    print("  - src/pipeline/context_drift_validator.py")
    print("  - tests/test_context_drift_validator.py")
    print("  - PROMPT3_IMPLEMENTATION_SUMMARY.md")

    print("\nPhase 4: Context-Specific Build Harness")
    print("  - src/services/context_harness_service.py")
    print("  - tests/test_context_harness_service.py")
    print("  - PROMPT4_IMPLEMENTATION_SUMMARY.md")

    print("\nPhase 5: Strict Mode Validation")
    print("  - config/global_strict_context.json")
    print("  - tools/validate_strict_context_mode.py")
    print("  - PROMPT5_IMPLEMENTATION_SUMMARY.md")

    print("\nComplete Summary:")
    print("  - PHASE2_GATEB_COMPLETE_IMPLEMENTATION.md")

    print("\n" + "=" * 80)
    print("DEPLOYMENT INSTRUCTIONS")
    print("=" * 80)
    print("\n1. Extract the package to your project directory")
    print("2. Review PHASE2_GATEB_COMPLETE_IMPLEMENTATION.md for overview")
    print("3. Run tests: pytest tests/test_*context*.py -v")
    print("4. Enable strict mode: --config config/global_strict_context.json")
    print("5. Validate: python tools/validate_strict_context_mode.py --run-id <id>")
    print("\n" + "=" * 80)

    return output_file

if __name__ == "__main__":
    create_complete_package()
