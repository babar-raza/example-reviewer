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

See `KB/04-family-config-reference.md` for a full field-level reference.
