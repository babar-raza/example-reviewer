# scripts/validation/ - Safety and Validation

Scripts for verifying pipeline correctness and safety.

## Scripts

| Script | Purpose |
|--------|---------|
| `analyze_cli_imports.py` | Static import analysis (used in CI) |
| `verify_determinism.py` | Verify that pipeline runs are deterministic |
| `verify_no_md_changes.py` | Verify no unexpected markdown changes |
| `validate_strict_context_mode.py` | Validate strict context mode constraints |
| `validate_md_update_targets.py` | Validate markdown update targets |
| `validate_verified_examples_signatures.py` | Validate semantic signatures of verified examples |
| `run_vfv_validation.py` | Run VFV (Verify-Fix-Verify) validation suite |
| `verify_database.py` | Verify database integrity |
| `check_barcode_results.py` | Check barcode family results |
