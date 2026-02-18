# Configuration Overview

Configuration is split into:

1. **Global Configuration**: `config/global.json`
2. **Per-Family Configuration**: `config/families/<family>.json`

The schema is represented by Pydantic models in `src/core/config.py`.

## Global Configuration (`config/global.json`)

### LLM

Key fields (`llm`):

- `provider`: `openai`, `azure`, `ollama`, `openrouter` (the code currently treats these as OpenAI-compatible endpoints)
- `model`: Model name for the selected provider
- `temperature`: Randomness in generations (lower is more deterministic)
- `max_retries` and `retry_backoff_seconds`: Retry controls
- `base_url`: Required for Ollama or proxyed endpoints (example: `http://localhost:11434/v1`)
- `timeout_seconds`

**Notes**:
- `src/services/llm_service.py` uses the OpenAI Python client. For Ollama, it sets `base_url` and uses a placeholder `api_key`.

### Markdown Write Guard

Key fields (`markdown_write`):

- `allow_markdown_write`: Default `false`

This is the primary safety lock. If it is `false`, `MarkdownUpdateService` will refuse to write markdown even if the rest of the pipeline succeeds.

You can also override via CLI `--allow-md-write` when using the `md-update` or `run` subcommands.

### Vector DB

Key fields (`vector_db`):

- `enabled`
- `embedding_model`
- `persist_directory`
- `search_k`
- `min_similarity_threshold`

The vector DB implementation is in `src/services/vector_db_service.py` and uses ChromaDB + sentence-transformers if available.

### Drift Control

Key fields (`drift`):

- `enabled`
- `threshold`: Default `0.3`
- `fail_on_exceed`: If `true`, LLM fixes that drift too far should be rejected
- `log_all_drift_scores`

Drift computation is implemented by `src/services/drift_detector.py` (cosine similarity via sentence-transformer embeddings).

### Telemetry

Key fields (`telemetry`):

- `internal_enabled`
- `local_telemetry_enabled` + `local_telemetry_path`
- `http_api_enabled` + `http_api_url`

Telemetry is coordinated by `src/services/telemetry_service.py` and DB tables in `src/core/database.py`.

### Database Configuration

**New in 2026-02-12**: Dual-database architecture support for separating production and development data.

Key fields (`database`):

- `path`: Primary database path (default: `./data/example_reviewer.db`)
- `production_path`: Optional production database path (default: `null`)
- `production_criteria`: How to identify production runs (currently only `"git_commit"` supported)

**How it works:**
- **Single-DB mode (default)**: All runs write to the primary database
- **Dual-DB mode**: Development runs write to `path`, production runs (with git commits) write to both databases
- Production database receives atomic copies of entire runs after successful git commits

**Configuration example:**
```json
{
  "database": {
    "path": "./data/example_reviewer.db",
    "production_path": "./data/example_reviewer_prod.db",
    "production_criteria": "git_commit"
  }
}
```

**CLI override:**
```bash
python -m src.cli.main run --family zip --prod-db-path ./data/production.db --commit
```

**Environment variable:**
```bash
export EXAMPLE_REVIEWER_DATABASE_PATH="./data/example_reviewer.db"
export EXAMPLE_REVIEWER_PROD_DB_PATH="./data/production.db"
```

**Use cases:**
- **Clean production analytics**: Query only committed, verified examples
- **Safe experimentation**: Test runs don't pollute production metrics
- **Audit trail**: Production DB contains only what actually shipped

**Backward compatibility:** If `production_path` is not set, the pipeline operates in single-database mode (pre-2026-02-12 behavior).

Implementation: `src/core/database.py` (`copy_run_to_production()` method).

### Backfill

Key fields (`backfill`):

- `auto_enabled`: If `true`, pipeline can auto-download missing data
- `targets`: List (`test_data`, `api_reference`, `examples`, `gist_source_code`)
- `github_timeout_seconds`

Backfill logic is in `src/services/backfill_service.py`.

### Resource Detection and Limits

- `limits`: Provides CPU/RAM/VRAM constraints
- `resource_detection`: Controls auto GPU detection and logging

Implementation: `src/services/resource_detection_service.py`.

## Family Configuration (`config/families/<family>.json`)

Each family config declares:

- Where to scan content
- How to compile and run examples (NuGet, target frameworks)
- Namespace policies and code defaults
- Runtime validation rules (required files, aliases)
- Optional external sources (example repo, API reference sources)

### Top-Level Fields

- **family** (required, string): Short identifier for the product family. Used for directory names and database keys. Example: `"zip"`, `"words"`, `"pdf"`.
- **display_name** (optional, string): Human-readable name for UI/reporting. Example: `"Aspose.ZIP for .NET"`.
- **content_roots** (required, array): Directories containing markdown blog posts to scan.

### nuget_config

Configuration for NuGet packages required for compilation.

- **primary_package.name** (required, string): Main NuGet package. Example: `"Aspose.Zip"`.
- **primary_package.version_strategy** (required, string): `"latest_stable"` or `"pinned"`.
- **primary_package.pinned_version** (conditional, string): Required if `version_strategy` is `"pinned"`.
- **additional_packages** (optional, array): Additional NuGet packages (`name` + `version`).
- **target_frameworks** (optional, array): .NET target frameworks. Defaults to `["net8.0"]`.

### code_defaults

- **default_usings** (optional, array): `using` directives injected into generated Program.cs.
- **safe_usings** (optional, array): Namespaces always safe to add during error fixing.

### api_catalog

- **catalog_path** (required, string): Path to assembly-reflected API catalog JSON.
- **dll_name** (optional, string): Assembly DLL name for reflection.

### runtime_validation

- **required_files** (optional, array): Files to stage before execution.
- **file_aliases** (optional, object): Filename aliases (e.g., `"sample.zip": ["input.zip"]`).
- **required_dirs** (optional, array): Directories that must exist in test-data.
- **expected_outputs** (optional, array): Glob patterns for expected output files.

### fixture_resolver

- **enabled** (optional, boolean): Enable intelligent fixture resolution.
- **canonical_files** (optional, object): Canonical source files for generation.
- **registry_path** (optional, string): Path to persistent fixture registry JSON.

### learned_patterns

- **db_path** (required, string): Path to learned patterns database.
- **min_confidence** (optional, float): Minimum confidence to apply a pattern.

### compilation / runtime

- **timeout_seconds** (optional, integer): Timeout for compile/run operations.
- **max_retries** (optional, integer): Maximum retry attempts.

### Validation Rules

1. `family` must be non-empty lowercase alphanumeric with hyphens.
2. `nuget_config.primary_package.name` must be a valid NuGet package identifier.
3. If `version_strategy` is `"pinned"`, `pinned_version` must be provided.
4. `target_frameworks` must contain at least one valid .NET target framework moniker.

### Example: Aspose.ZIP Family Config

```json
{
  "family": "zip",
  "display_name": "Aspose.ZIP for .NET",
  "content_roots": ["D:/content/blog.aspose.net/content/"],
  "nuget_config": {
    "primary_package": {
      "name": "Aspose.Zip",
      "version_strategy": "latest_stable"
    },
    "target_frameworks": ["net8.0"]
  },
  "code_defaults": {
    "default_usings": ["Aspose.Zip", "Aspose.Zip.Saving"]
  },
  "safe_usings": ["System", "System.IO", "Aspose.Zip", "Aspose.Zip.Saving"],
  "api_catalog": {
    "catalog_path": "config/families/zip_api_catalog.json"
  },
  "runtime_validation": {
    "required_files": ["sample.zip", "sample_dir"],
    "file_aliases": {
      "sample.zip": ["input.zip", "archive.zip", "example.zip"]
    }
  }
}
```

See individual family configs in `config/families/` for complete examples.
