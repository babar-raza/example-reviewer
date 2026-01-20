# Backfill and External Data Sources

Backfill is an optional mechanism to populate local caches so the pipeline can run without manually preparing data.

**Implementation**: `src/services/backfill_service.py`

## What Can Be Backfilled

Backfill targets (global default list):

- `test_data`
- `api_reference`
- `examples`
- `gist_source_code`

These can be triggered via CLI:

```bash
cli backfill --family zip --targets test_data api_reference examples gist_source_code
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

## API Reference

**Source**:
- `family_config.api_reference.sources[]`

**Destination**:
- `family_config.api_reference.cache_path`

**Behavior**:
- Copies files from sources into the cache
- The orchestrator loads API context from `cache_path` at runtime, truncated for prompt length

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
- This requires outbound network access.
- Authentication is optional but may be required to avoid rate limits.