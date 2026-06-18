# Backfill and External Data Sources

Backfill is an optional mechanism to populate local caches so the pipeline can run without
manually preparing data.

**Implementation**: `src/services/backfill_service.py`

## What Can Be Backfilled

Backfill targets (global default list):

- `test_data`
- `api_catalog`
- `examples`
- `gist_source_code`

These can be triggered via CLI:

```bash
python -m src.cli.main backfill --family zip --targets test_data api_catalog examples gist_source_code
```

Or via MCP tool `backfill`.

## Test Data

**Source**:
- `family_config.example_repo.url`
- `family_config.example_repo.test_data_path`

**Destination**:
- `family_config.test_data.local_path`

**Behavior**:
- Skips if local path exists unless `--force`
- Skips if `download_if_missing` is `false` unless `--force`
- Requires GitPython (`pip install gitpython`) to clone/fetch repos

## API Catalog

The `api_catalog` target generates a local JSON file that lists every exported type, enum,
constructor, and method signature from the compiled NuGet assembly. This file is used by
the deterministic fixer (to resolve missing `using` directives, enum members, and constructor
overloads) and by the LLM (as type context injected into fix prompts).

**How it works**:
- Calls `scripts/setup/bootstrap_catalog.py` with `--family`, `--package`, and `--output` args
- The script downloads the NuGet package and runs .NET assembly reflection via a temporary
  C# reflector project
- Output is written to `config/families/<family>_api_catalog.json`

**Important**: `config/families/*_api_catalog.json` files are **gitignored** — they are
generated per machine and must be created before the first pipeline run. The setup wizard
(`scripts/setup/setup_wizard.py`) does this automatically.

To regenerate manually:

```bash
# Via backfill (preferred — handles path resolution automatically)
python -m src.cli.main backfill --family zip --targets api_catalog

# Or directly via the bootstrap script
python scripts/setup/bootstrap_catalog.py \
    --family zip \
    --package Aspose.Zip \
    --output config/families/zip_api_catalog.json
```

Without a catalog, the deterministic fixer cannot resolve missing `using` directives and
the LLM will receive no type context, significantly lowering the fix success rate.

## Examples

Used to populate the vector DB for similarity search.

**Source**:
- `family_config.example_repo.url`
- `family_config.example_repo.examples_path`

**Behavior**:
- Clones repo and discovers examples
- Adds extracted code to ChromaDB via `VectorDBService` (when enabled)

## Gist Source Code

Used to cache source code from gist references so later phases do not have to hit network APIs.

**Source**:
- Gist references stored in SQLite from discovery
- `GistResolver` in `src/services/discovery_service.py` uses GitHub Gist REST API

**Notes**:
- Public gists are accessible without authentication (rate-limited to 60 req/hr)
- Set `GITHUB_TOKEN` in `.env` to raise the rate limit to 5000 req/hr
- Authentication is not required for public gist access

## Note on barcode.json

`config/families/barcode.json` is gitignored (unlike `zip.json` and `words.json`, which are
committed). This is an inconsistency in the current setup — barcode shares the same config
structure as the committed families but was excluded from version control.

To get a working `barcode.json`, either:
1. Copy it from another installation that has it
2. Run the setup wizard and select the barcode family: `python scripts/setup/setup_wizard.py`
