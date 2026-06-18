# scripts/ - Tooling and Automation

Scripts for setup, operations, pattern management, and validation.

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `setup/` | First-time setup: catalog generation, bootstrapping, family provisioning |
| `ops/` | Day-to-day operations: run gates, export results, monitoring |
| `patterns/` | Auto-learn pattern management: extraction, review, promotion |
| `validation/` | Safety checks: determinism verification, import analysis, context validation |
| `db/` | Database migration and catalog tools |
| `release/` | Release packaging |
| `test_fixtures/` | Test utility scripts for catalog and sample validation |

## Quick Reference

```bash
# Setup a new family
python scripts/setup/setup_all_families.py

# Generate API catalog from assembly
python scripts/setup/extract_assembly_catalog.py Aspose.Words 26.1.0 Aspose.Words --full

# Run all verification gates
python scripts/ops/run_all_gates.py --family zip

# Review auto-learned patterns
python scripts/patterns/review_patterns.py --family zip

# Run static import analysis
python scripts/validation/analyze_cli_imports.py src/cli/main.py
```
