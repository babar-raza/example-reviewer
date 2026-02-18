# system-design.md

## Purpose

Example Reviewer discovers **C# snippets in Markdown**, verifies them by **compiling and running** them, optionally **LLM-fixes** failures with drift controls, and (optionally) **writes verified code back** into Markdown with strict write guards.

## Primary use cases

* Verify documentation examples per product family (zip/pdf/words/etc).
* Auto-fix common compilation/runtime problems while preventing intent drift.
* Persist a full audit trail (attempts, logs, diffs, telemetry).
* Provide both a CLI and an MCP server interface over the same pipeline.

## High-level architecture

**Interfaces**

* **CLI**: `src/cli/main.py`
* **MCP Server (stdio JSON-RPC)**: `src/mcp_tools/server.py`

**Orchestration**

* **PipelineOrchestrator**: `src/pipeline/orchestrator.py`

  * Runs Phase A-F in sequence, creates run records, integrates telemetry, vector DB, drift and final review.

**Core platform**

* **ConfigurationManager**: `src/core/config.py`

  * Loads `config/global.json` and `config/families/<family>.json`
* **Database (SQLite)**: `src/core/database.py`

  * Persists examples, attempts, markdown edits, runs, telemetry.

**Services**

* Discovery: `src/services/discovery_service.py`
* Compilation: `src/services/compilation_service.py`
* Runtime: `src/services/runtime_service.py`
* LLM adapter: `src/services/llm_service.py`
* Markdown update (write-guarded): `src/services/markdown_service.py`
* Vector DB (optional): `src/services/vector_db_service.py`
* Telemetry (optional dual-write): `src/services/telemetry_service.py`
* Backfill (optional): `src/services/backfill_service.py`
* Resource detection: `src/services/resource_detection_service.py`

## Data stores and artifacts

* **SQLite DB**: default `./data/example_reviewer.db`
* **Artifacts**: default `./artifacts/`

  * compile logs, runtime logs, LLM request/response blobs, diffs
* **Vector DB persistence**: default `./data/chroma` (Chroma)
* **Local telemetry export**: default `./local-telemetry/`
* **API reference cache**: per-family path in family config (`api_reference.cache_path`)

## Trust boundaries

External dependencies are best-effort and should not crash the pipeline:

* LLM provider (OpenAI-compatible; Ollama supported)
* HTTP telemetry endpoint (via `httpx`)
* Git / Gist publishing (optional dependencies)

## Safety model

* Markdown writes are **opt-in** (global flag or CLI `--allow-md-write`)
* Writes to `test-data/`, `test-examples/`, `test-reference/` are **always blocked**
* Drift detection can **abort** LLM fixes that diverge too far

---