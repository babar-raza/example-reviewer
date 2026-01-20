# interfaces.md

## CLI (`src/cli/main.py`)

Global flags:

* `--config-dir` (default `config/families`)
* `--db-path` (default `data/example_reviewer.db`)
* `--workspace-dir` (default `workspace`)
* `--verbose` / `-v`
* `--json`

Commands:

* `scan --family <family> [--max-files N]`
* `scan --directory <path> [--max-files N]`
* `extract --family <family> [--max-files N]`
* `compile-verify --family <family> [--max-examples N]`
* `compile-fix --family <family> [--max-examples N]`
* `runtime-verify --family <family> [--max-examples N]`
* `runtime-fix --family <family> [--max-examples N]`
* `md-update --family <family> [--dry-run] --allow-md-write`
* `final-review --family <family>`
* `commit --family <family>`
* `status [--family <family>]`
* `run --family <family> [--max-examples N] [--skip-runtime] [--skip-llm] [--dry-run] [--allow-md-write]`
* `list-families`
* `backfill --family <family> [--targets ...] [--force]`
* `clean-vector-db --family <family> [--max-drift 0.3]`
* `visualize-drift --family <family> [--format ascii|json]`
* `drift-trends --family <family> [--last-n-runs N]`

## MCP server (`src/mcp_tools/server.py`)

Transport:

* stdio, JSON-RPC 2.0, one JSON message per line

Methods:

* `initialize`
* `tools/list`
* `tools/call`

Tool names routed:

* `scan`, `extract`, `compile_verify`, `compile_fix`, `runtime_verify`, `md_update`, `final_review`, `commit`, `backfill`, `status`, `run_pipeline`

`tools/call` returns a text blob containing serialized `ToolResult` JSON.