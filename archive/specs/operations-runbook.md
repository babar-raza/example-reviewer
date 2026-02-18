# operations-runbook.md

## Preconditions

* Python environment capable of importing `src/`
* .NET SDK installed and `dotnet` available on PATH

Python deps (inferred from imports; no manifest in snapshot):

* `pydantic`, `pydantic-settings`
* `httpx`
* `openai` (LLM)
* `instructor` (optional)
* `chromadb`, `sentence-transformers` (optional)
* `gitpython` (optional backfill)

## Typical safe workflow (no Markdown writes)

1. `extract`
2. `compile-verify`
3. `runtime-verify`

## Fix workflow (LLM enabled)

1. `compile-fix`
2. `runtime-fix`

## Apply updates to Markdown (guarded)

* `md-update --allow-md-write` (optionally `--dry-run`)

## Full pipeline

* `run --family ...` with optional flags

## LLM config

* `config/global.json -> llm`
* Ollama uses `provider="ollama"` and `base_url`, uses placeholder key

## Telemetry config

* `config/global.json -> telemetry`
* dual-write: local sqlite first, HTTP best-effort
