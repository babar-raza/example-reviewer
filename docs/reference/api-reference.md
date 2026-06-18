# API Reference

## Command-Line Interface

**Entry point:** `python -m src.cli.main`

### Global Options

| Flag | Default | Description |
|------|---------|-------------|
| `--config-dir` | `config/families` | Family config directory |
| `--db-path` | `data/example_reviewer.db` | Database path |
| `--workspace-dir` | `workspace` | Working directory for compilations |
| `--verbose` / `-v` | off | Verbose logging |
| `--json` | off | JSON output format |

---

## Commands

### Pipeline Commands

| Command | Description |
|---------|-------------|
| `run --family <f> [--max-examples N] [--skip-runtime] [--skip-llm] [--dry-run] [--allow-md-write]` | Full VFV pipeline (discover through commit) |
| `scan --family <f> [--max-files N]` | Scan markdown files for code examples |
| `scan --directory <path> [--max-files N]` | Scan specific directory |
| `extract --family <f> [--max-files N]` | Extract C# code blocks from markdown |
| `compile-verify --family <f> [--max-examples N]` | Compile extracted examples |
| `compile-fix --family <f> [--max-examples N]` | Fix compilation errors (deterministic + LLM) |
| `runtime-verify --family <f> [--max-examples N]` | Run compiled examples |
| `runtime-fix --family <f> [--max-examples N]` | Fix runtime errors |
| `md-update --family <f> [--dry-run] --allow-md-write` | Update markdown with verified code |
| `final-review --family <f>` | LLM review of changes |
| `commit --family <f>` | Git commit verified changes |

### Utility Commands

| Command | Description |
|---------|-------------|
| `status [--family <f>]` | Show pipeline status and statistics |
| `list-families` | List configured product families |
| `backfill --family <f> [--targets ...] [--force]` | Download missing test data and gists |
| `clean-vector-db --family <f> [--max-drift 0.3]` | Clean vector DB entries exceeding drift |
| `visualize-drift --family <f> [--format ascii\|json]` | Visualize semantic drift scores |
| `drift-trends --family <f> [--last-n-runs N]` | Show drift score trends across runs |

---

## MCP Server

**Entry point:** `src/mcp_tools/server.py`

### Transport

- stdio, JSON-RPC 2.0, one JSON message per line
- Protocol version: `2024-11-05`
- Server capabilities: `{"tools": {"listChanged": false}}`

### Protocol Methods

| Method | Description |
|--------|-------------|
| `initialize` | Handshake with protocolVersion, capabilities, serverInfo |
| `notifications/initialized` | Client readiness notification (no response) |
| `notifications/cancelled` | Client cancellation notification (no response) |
| `ping` | Keep-alive, returns empty result |
| `tools/list` | Returns all 12 tool definitions with JSON Schema inputSchema |
| `tools/call` | Executes a tool, returns content array with isError flag |

### Available Tools (12)

`scan`, `extract`, `compile_verify`, `compile_fix`, `runtime_verify`, `runtime_fix`, `md_update`, `final_review`, `commit`, `backfill`, `status`, `run_pipeline`

`tools/call` returns a text blob containing serialized `ToolResult` JSON.

All tool schemas include `required` arrays and full parameter coverage matching method signatures. Schema drift is automatically detected by `tests/test_mcp_tool_definitions.py`.

---

## See Also

- [configuration.md](configuration.md) - Configuration reference
- [patching-strategies.md](../architecture/patching-strategies.md) - Markdown patching algorithm
- [entrypoints.md](../architecture/entrypoints.md) - Entry point details
