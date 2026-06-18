# MCP Server Reference

The Example Reviewer exposes its pipeline through an MCP (Model Context Protocol)
server so MCP-compatible clients can drive the same functionality as the CLI.

## Overview

- Transport: JSON-RPC 2.0 over stdio
- Process model: the server runs as a local subprocess of the MCP client
- Implementation: `src/mcp_tools/server.py` delegates to `src/mcp_tools/tools.py`
- Shared behavior: the CLI and MCP use the same `ExampleReviewerTools` methods

Because the server is local to the client, it can directly access local
`content_roots`, the SQLite database, git, and the .NET SDK on that machine.

## Start the Server

```bash
PYTHONPATH=. venv/Scripts/python.exe -m src.mcp_tools.server

PYTHONPATH=. venv/Scripts/python.exe -m src.mcp_tools.server \
    --config-dir config/families \
    --db-path data/example_reviewer.db \
    --workspace-dir workspace \
    --verbose
```

### Claude Desktop Example

```json
{
  "mcpServers": {
    "example-reviewer": {
      "command": "C:/path/to/repo/venv/Scripts/python.exe",
      "args": ["-m", "src.mcp_tools.server"],
      "cwd": "C:/path/to/repo",
      "env": {
        "PYTHONPATH": "."
      }
    }
  }
}
```

## Protocol Lifecycle

### `initialize`

Client request:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "clientInfo": {"name": "my-client", "version": "1.0"},
    "capabilities": {}
  }
}
```

Server response includes:

- `protocolVersion`
- `capabilities.tools`
- `serverInfo.name`
- `serverInfo.version`

### `notifications/initialized`

The server accepts `notifications/initialized` as a JSON-RPC notification and
does not emit a response.

### `ping`

`ping` returns an empty `result` object and is safe as a lightweight liveness
check for long-running clients.

### `tools/list`

Returns all tool definitions with JSON Schema `inputSchema`.

### `tools/call`

Invokes a tool by name. Tool responses are wrapped in the MCP result payload
with `content` and `isError`.

## Tool Surface

The server currently exposes 14 tools:

1. `scan`
2. `extract`
3. `compile_verify`
4. `compile_fix`
5. `runtime_verify`
6. `runtime_fix`
7. `md_update`
8. `final_review`
9. `commit`
10. `backfill`
11. `status`
12. `run_pipeline`
13. `validate_articles`
14. `validate_code_snippet`

## Key Parameters

### `content_roots`

`scan`, `extract`, and `run_pipeline` accept `content_roots` so callers can
override the family config's markdown source locations without editing JSON on
disk.

Example:

```json
{
  "name": "run_pipeline",
  "arguments": {
    "family": "zip",
    "content_roots": [
      "C:/content/blog/zip",
      "C:/content/docs/zip"
    ]
  }
}
```

### `validate_articles`

`validate_articles` performs deterministic markdown checks without running the
full compile/runtime pipeline:

- fence and structure validation
- duplicate code overlap detection
- prose/code alignment audit when `audit_prose=true` and an LLM reviewer is available

Example:

```json
{
  "name": "validate_articles",
  "arguments": {
    "family": "words",
    "file_list": [
      "D:/onedrive/Documents/GitHub/aspose.net/content/kb.aspose.net/words/en/how-to-add-watermarks-word-documents-aspnet-api.md"
    ],
    "audit_prose": true
  }
}
```

### `run_pipeline`

`run_pipeline` now also accepts `audit_prose=true` to pass the same prose/code
alignment audit into the markdown update phase for changed code blocks.

### `validate_code_snippet`

`validate_code_snippet` performs lightweight catalog-backed validation of code:

- detects missing or hallucinated Aspose types
- checks namespace violations
- can optionally compile when `compile_verify=true`

This is intended for agent workflows that need fast validation without running
the full pipeline.

## HTTP API

The same tool surface is also available over HTTP via `src/http_server.py`.

Key endpoints:

- `GET /healthz`
- `GET /api/v1/tools`
- `POST /api/v1/tools/{tool_name}`
- `POST /api/v1/validate-code`

The HTTP layer delegates back to `MCPServer.call_tool()` so behavior stays in
sync with the MCP and CLI paths.

## Verification

Relevant tests:

```bash
PYTHONPATH=. venv/Scripts/python.exe -m pytest -q \
    tests/test_mcp_tool_result.py \
    tests/test_mcp_tool_definitions.py \
    tests/test_mcp_tools.py \
    tests/test_mcp_server.py \
    tests/test_validate_code_snippet.py \
    tests/test_http_server.py
```

These tests cover:

- tool registration and schema drift
- JSON-RPC request handling
- tool dispatch and error shaping
- catalog-backed validation behavior
- HTTP wrapper behavior

## Adding a Tool

To add a new MCP-exposed tool:

1. Add the method to `ExampleReviewerTools`.
2. Add the schema entry to `TOOL_DEFINITIONS`.
3. Register the handler in `MCPServer.__init__`.
4. Add CLI wiring if the feature also belongs in the CLI.
5. Run the MCP and schema tests.
