# scripts/setup/ - First-Time Setup

Scripts for initial environment setup and family configuration.

## Scripts

| Script | Purpose |
|--------|---------|
| `setup_all_families.py` | Create/update configuration files for all Aspose families |
| `extract_assembly_catalog.py` | Generate API catalog from .NET assembly via reflection |
| `batch_generate_catalogs_v2.py` | Batch-generate catalogs for multiple families |
| `bootstrap_catalog.py` | Bootstrap API catalog database from JSON catalog files |
| `bootstrap_learned_patterns.py` | Initialize learned patterns database for a family |
| `validate_bootstrap.py` | Validate that bootstrapped data is consistent |
| `generate_barcode_fixtures.py` | Generate test fixtures for barcode family |
| `provision_test_data_zip.py` | Provision test data files for ZIP family |

## Typical Setup Flow

1. `python scripts/setup/setup_all_families.py` - Create family configs
2. `python scripts/setup/extract_assembly_catalog.py <Package> <Version> <NS> --full` - Generate catalog
3. `python scripts/setup/bootstrap_learned_patterns.py --family <name>` - Initialize patterns
